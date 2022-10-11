# download photobucket users albums
 Download all of a photobucket user's public albums

# Usage
```
Usage: py download.py -u [USERNAME] -o [OUTPUT DIR]

Arguments:
   -h, --help           display this usage info
   -u, --username       user to download albums from
   -o, --output-dir     output directory
   -ua, --user-agent    override default useragent
```

### Notes:  
Not really tested much.  
Uses IDs for filenames because I don't want to deal with filename sanitization.  
Won't resume downloading a specific album, will start an unfinished album download over.  
