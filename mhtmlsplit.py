#!/usr/bin/python

# usage: mhtmlsplit <file>
# arguments: --remove-js, --inline, --html-only

# Standard library imports
import argparse, html.parser, os, sys

class MhtmlParseException(Exception):
    pass

class LocaliserParser(html.parser.HTMLParser):
    locations = []
    mainFile = ""
    output = ""
    
    def __init__(self, ls, inName, remove_js, *, convert_charrefs=True):
        super().__init__()
        self.locations = ls
        self.mainFile = inName
        self.remove_js = remove_js
    
    def handle_starttag(self, tag, attrs):
        # If -j is defined, skip script tags
        if self.remove_js:
            if tag == "script":
                return
        
        self.output += "<" + tag
        for attr in attrs:
            (key,value) = attr
            
            if self.remove_js and key in ["onerror", "onclick"]: #TODO: maybe more attributes?
                continue
            
            if key in ["href","src","content"]:
                if value in self.locations:
                    # Replace it with the local file
                    self.output += f" {key}=\"{getResRelativePath(self.mainFile, value)}\""
                else:
                    self.output += f" {key}=\"{value}\""
            else:
                self.output += f" {key}=\"{value}\""
        self.output += ">"
    
    def handle_endtag(self, tag):
        self.output += f"</{tag}>"
    
    def handle_data(self, data):
        self.output += data
    
    def handle_comment(self, data):
        self.output += f"<!--{data}-->"
    
    def handle_decl(self, decl):
        self.output += f"<!{decl}>"

class Resource():
    data = None
    location = None
    encoding = None
    content_type = None
    
    def getDecodedData(self):
        if self.encoding == "binary":
            return self.data
        else:
            raise ValueError(f"Resource was not in binary encoding, but rather {self.encoding}")
        # TODO: decode base64, (maybe 7bit and 8bit too)

def log_info(msg, verbose):
    if verbose:
        print(msg)

def get_boundary(header):
    # Parse the header to get the boundary value from the Content-Type field
    
    # Remove unnecessary line breaks (indicated by lines starting with tabs)
    header = header.replace(b"\r\n\t", b"")
    
    for line in header.splitlines():
        (key, value) = line.split(b": ")
        if key == b"Content-Type":
            for ctfield in value.split(b";")[1:]: # ignore the first one, that'll just be 'multipart/related
                (ctkey, ctvalue) = ctfield.split(b"=", 1)
                if ctkey == b"boundary":
                    # Return the boundary with quotes removed
                    return ctvalue[1:-1]

def getOutputHtmlName(inName):
    basename = os.path.basename(inName)
    dot = basename.rfind(".")
    if dot == -1:
        # No extension, just add .html
        return basename + ".html"
    else:
        # Replace the last extension with html
        return basename[:dot] + ".html"

def getResDirName(inName):
    basename = os.path.basename(inName)
    dot = basename.find(".") # share the name up to the first dot, append _files
    if dot == -1:
        return basename + "_files"
    
    return basename[:dot] + "_files"

def getResRelativePath(inName, inLocation):
    if inLocation.rfind("?") != -1:
        inLocation = inLocation[:inLocation.rfind("?")]
    if inLocation.rfind("/") == -1:
        path = "none"
        basename = inLocation
    else:
        (path, basename) = inLocation.rsplit("/", 1)
    return getResDirName(inName) + "/" + str(hash(path) if hash(path) >= 0 else -hash(path)) + basename

def main():
    # Parse CLI arguments and filename
    parser = argparse.ArgumentParser("Convert MHTML archives to individual files")
    parser.add_argument("-o", "--html-only", action="store_true", help="Only extract the HTML (this will leave the HTML unchanged, typically remote sources will be rewritten to local ones)")
    parser.add_argument("-i", "--inline", action="store_true", help="Try to inline as many files as possible into the HTML file (not yet implemented)")
    parser.add_argument("-j", "--remove-js", action="store_true", help="Remove scripts from the extracted files (not fully implemented?)")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("mhtml_file", help="The MHTML file the split")
    
    args = parser.parse_args()
    
    # Try to open & parse the specified file
    try:
        log_info("Opening file", args.verbose)
        mhtml_file = open(args.mhtml_file, "rb")
    except IOError as e:
        print(f"Failed to open '{e.filename}': {e.strerror}", file=sys.stderr)
        exit(1)
    
    # Make a directory for the output files to go into
    try:
        os.mkdir(getResDirName(args.mhtml_file))
    except FileExistsError:
        pass
    
    mhtml_data = mhtml_file.read()
    pointer = mhtml_data.find(b"\r\n\r\n\r\n") + 6 # pointer where to look for the next boundary, start after the header
    boundary = get_boundary(mhtml_data[:pointer]) # find the boundary within the header
    log_info(f"Boundary is {str(boundary, encoding="iso-8859-1")}", args.verbose)
    
    boundaryLine = b"".join((b"--", boundary))
    # Skip to after the first boundary
    pointer += len(boundaryLine)
    
    html_data = b""
    resources = []
    
    finished = False
    part = 0
    while not finished:
        next_boundary = mhtml_data[pointer:].find(boundaryLine)
        if next_boundary == -1:
            finished = True
            next_boundary = len(mhtml_data) - 1

        data_end = pointer + next_boundary
        nextpointer = data_end + len(boundaryLine)
        data_start = pointer + mhtml_data[pointer:nextpointer].find(b"\r\n\r\n") + 4
        if data_start == pointer + 3:
            # No part header, we're done here
            break
        part_data = mhtml_data[data_start:data_end]
        part_heading = mhtml_data[pointer:data_start]
        
        # Write out the file under an appropriate name
        if part == 0:
            # The first part is assumed to be the main HTML document
            html_data = part_data
        else:
            r = Resource()
            for line in part_heading.splitlines():
                if not b': ' in line:
                    continue
                (key,value) = line.split(b": ", 1)
                if key == b"Content-Type":
                    try:
                        r.content_type = str(value, encoding="utf-8")
                    except UnicodeEncodeError:
                        r.content_type = str(value, encoding="iso-8819-1")
                if key == b"Content-Transfer-Encoding":
                    try:
                        r.encoding = str(value, encoding="utf-8")
                    except UnicodeEncodeError:
                        r.encoding = str(value, encoding="iso-8819-1")
                if key == b"Content-Location":
                    try:
                        r.location = str(value, encoding="utf-8")
                    except UnicodeEncodeError:
                        r.location = str(value, encoding="iso-8819-1")
            if (r.content_type == "text/javascript" or r.location.endswith(".js")) and args.remove_js:
                continue
            
            r.data = part_data
            resources.append(r)
            if r.location is not None:
                path = getResRelativePath(args.mhtml_file, r.location)
                resFile = open(path, 'xb')
                resFile.write(r.getDecodedData())
                resFile.close()
                
                log_info(f"Saved {r.location} as {path}", args.verbose)
    
        pointer = nextpointer
        part += 1
        if args.html_only:
            finished = True

    if not args.html_only:
        # Rewrite the URLs to be local ones, I guess hash the path up to that point to avoid duplication
        # TODO: relative URLs
        # Having the page URL may also be useful for relative URLs
        locations = []
        for r in resources:
            if r.location is not None:
                locations.append(r.location)
        parser = LocaliserParser(locations, args.mhtml_file, args.remove_js, convert_charrefs=False)
        html_string = str(html_data, encoding="utf-8") # TODO: use specified charset in the html
        parser.feed(html_string)
        processed_html_data = parser.output
    
    htmlFile = open(getOutputHtmlName(args.mhtml_file), 'wb')
    htmlFile.write(html_data if args.html_only else bytes(processed_html_data, encoding="utf-8"))
    htmlFile.close()

    log_info("Closing file", args.verbose)
    mhtml_file.close()
    log_info(f"Summary: {part} parts written", args.verbose)
    
if __name__ == '__main__':
    main()
