import requests
import json
import sys
from os import listdir, makedirs, system, remove, rmdir
from os.path import isfile, isdir, splitext, split, join, exists
from urllib.parse import urlparse
import time
import re

# scrape all the albums of a photobucket user

# update printhelp
def printHelp():
	print("Usage:", "py download.py -u [USERNAME] -o [OUTPUT DIR]\n\n"+
	"Arguments:\n", "  -h, --help\t\tdisplay this usage info\n",
	"  -u, --username\tuser to download albums from\n",
	"  -o, --output-dir\toutput directory\n",
	"  -ua, --user-agent\toverride default useragent")
	exit()

def queryPB(apiURL, operation, query, variables, headers, session = requests.Session()):
	PBheaders=headers
	PBheaders["Origin"]="https://app.photobucket.com"
	
	payload = {}
	if operation!='': payload['operation']=operation
	if variables!='': payload['variables']=variables
	if query!='': payload['query']=query
	
	response = session.post(apiURL, headers=headers, json=payload)
	if response.status_code!=200: raise Exception
	return response

def main():
	apiURL = 'https://app.photobucket.com/api/graphql/v2'
	useragent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36'
	queriedUser=''
	baseDir=''
	
	if len(sys.argv[1:]) == 0: printHelp()
	i=1 # for arguments like [--command value] get the value after the command
	# first arg in sys.argv is the python file
	for arg in sys.argv[1:]:
		if (arg in ['help', '/?', '-h', '--help']): printHelp()
		if (arg in ['-u', '--username']): queriedUser = sys.argv[1:][i]
		if (arg in ['-o', '--outdir']): baseDir = sys.argv[1:][i]
		if (arg in ['-ua', '--user-agent']): useragent = sys.argv[1:][i]
		
		i+=1
	if '' in [queriedUser, baseDir]: printHelp() # these args are critical, print help if not present
	
	session = requests.Session()
	headers = {
		"User-Agent": useragent
	}
	
	# make sure outdir exists
	outDir = join(baseDir, queriedUser)
	if exists(outDir):
		if isfile(outDir): makedirs(outDir)
	else: makedirs(outDir)
	
	variables = {'owner': queriedUser, 'sortBy': {'field': 'DATE_TAKEN'}}
	query = 'query GetAllPublicAlbums($sortBy: Sorter!, $owner: String!) {\n  getAllPublicAlbums(sortBy: $sortBy, owner: $owner) {\n    id\n    title\n    privacyMode\n    parentAlbumId\n    imageCount\n    __typename\n  }\n}'
	response = queryPB(apiURL, 'GetAllPublicAlbums', query, variables, headers, session)
	apiResp = json.loads(response.text)
	albums = apiResp['data']['getAllPublicAlbums']
	apiResponses=[]
	for album in albums:
		albumDir = join(outDir, album['id'])
		if exists(join(albumDir,'meta.json')): continue # skip if folder exists and meta.json exists
		# if album['id'] != '101a35ec-e354-47ab-950b-09044dbd155c': continue
		# if album['id'] != 'a9e1c167-9eef-4d67-9012-b390c9778320': continue
		# if album['id'] != '455eba41-6e45-4ee8-8bf6-09459c2eb08b': continue
		if not exists(albumDir): makedirs(albumDir)
		
		print(f"downloading {album['title']}")
		
		images=[]
		stringPointer=None
		while True: # grab image urls
			variables = {"albumId": album['id'],"pageSize": 150,"sortBy": {"field": "DATE","desc": True}}
			if stringPointer!=None: variables['scrollPointer']=stringPointer
			query = "query GetPublicAlbumImagesV2($albumId: String!, $sortBy: Sorter, $scrollPointer: String, $pageSize: Int, $password: String) {\n  getPublicAlbumImagesV2(\n    albumId: $albumId\n    sortBy: $sortBy\n    scrollPointer: $scrollPointer\n    pageSize: $pageSize\n    password: $password\n  ) {\n    scrollPointer\n    items {\n      ...MediaFragment\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment MediaFragment on Image {\n  id\n  title\n  dateTaken\n  uploadDate\n  isVideoType\n  username\n  isBlurred\n  image {\n    width\n    size\n    height\n    url\n    isLandscape\n    exif {\n      longitude\n      eastOrWestLongitude\n      latitude\n      northOrSouthLatitude\n      altitude\n      altitudeRef\n      cameraBrand\n      cameraModel\n      __typename\n    }\n    __typename\n  }\n  thumbnailImage {\n    width\n    size\n    height\n    url\n    isLandscape\n    __typename\n  }\n  originalImage {\n    width\n    size\n    height\n    url\n    isLandscape\n    __typename\n  }\n  livePhoto {\n    width\n    size\n    height\n    url\n    isLandscape\n    __typename\n  }\n  albumId\n  description\n  userTags\n  clarifaiTags\n  uploadDate\n  originalFilename\n  isMobileUpload\n  albumName\n  attributes\n  __typename\n}"
			response = queryPB(apiURL, 'GetPublicAlbumImagesV2', query, variables, headers, session)
			apiResp = json.loads(response.text)
			apiResponses.append(apiResp)
			newImages=apiResp['data']['getPublicAlbumImagesV2']['items']
			images+=newImages
			if apiResp['data']['getPublicAlbumImagesV2']['scrollPointer']==None: break
			else: stringPointer=apiResp['data']['getPublicAlbumImagesV2']['scrollPointer']
			time.sleep(1) # be nice
		
		# get a list of videos
		videos=[]
		for image in images:
			if image['isVideoType']==True: videos.append(image)
		
		if len(videos)>0:
			time.sleep(1) # be nice
			videoIDs=[]
			for video in videos:
				videoIDs.append(video['id'])
			
			variables = {'ids': videoIDs}
			query = "query GetDirectVideoLinks($ids: [String]!, $password: String) {\n  getDirectVideoLinks(ids: $ids, password: $password)\n}"
			response = queryPB(apiURL, 'GetDirectVideoLinks', query, variables, headers, session)
			apiResp = json.loads(response.text)
			videoURLs = apiResp['data']['getDirectVideoLinks']
		
		pVideos = []
		for video in videos:
			tmpVid = {}
			tmpVid['id']=video['id']
			tmpVid['originalFilename']=video['originalFilename']
			tmpVid['thumbURL']=video['originalImage']['url']
			tmpVid['videoURL']=None
			thumbPath = urlparse(tmpVid['thumbURL'])[2]
			for videoURL in videoURLs:
				if thumbPath in videoURL:
					tmpVid['videoURL']=videoURL
					break
			pVideos.append(tmpVid)
		
		# actually download images/vids
		
		if not exists(join(albumDir, 'images')): makedirs(join(albumDir, 'images'))
		for image in images:
			print(f"downloading image {image['originalFilename']}")
			imageURL = image['originalImage']['url']
			imageBin = session.get(imageURL, headers=headers)
			if imageBin.status_code==200: pass
			elif imageBin.status_code==422: pass # if video thumbnail doesn't have a preview
			else: raise Exception
			
			if imageBin.headers['Content-Type']=='image/jpeg': imageExt='.jpg'
			elif imageBin.headers['Content-Type']=='image/png': imageExt='.png'
			elif imageBin.headers['Content-Type']=='image/webp': imageExt='.webp'
			elif imageBin.headers['Content-Type']=='image/gif': imageExt='.gif'
			else: imageExt='.unk'
			# we overwrite existing images because it's not worth our time to restart album downloads
			with open(join(albumDir, 'images', image['id']+imageExt), 'wb') as f:
				f.write(imageBin.content)
			time.sleep(0.25) # be nice
		
		if not exists(join(albumDir, 'videos')): makedirs(join(albumDir, 'videos'))
		for video in pVideos:
			print(f"downloading video {video['originalFilename']}")
			videoBin = session.get(video['videoURL'], headers=headers)
			if videoBin.status_code!=200: raise Exception
			
			if videoBin.headers['Content-Type']=='video/mp4': videoExt='.mp4'
			elif videoBin.headers['Content-Type']=='video/webm': videoExt='.webm'
			else: videoExt='.unk'
			with open(join(albumDir, 'videos', video['id']+videoExt), 'wb') as f:
				f.write(videoBin.content)
			time.sleep(0.5) # be nice
		
		# as the last thing write a meta.json, use this to tell if an album had successfully downloaded
		with open(join(albumDir,'meta.json'), 'w+') as f:
			metaDump={}
			metaDump['album']=album
			metaDump['getPublicAlbumImagesV2']=apiResponses
			metaDump['videoInfo']=pVideos
			f.write(json.dumps(metaDump))
if __name__=='__main__':
	main()
