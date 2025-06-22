#!/usr/bin/python

# usage: mhtmlsplit <file>
# arguments: --remove-js, --inline, --html-only

# Standard library imports
import argparse, html, os, sys

class MhtmlParseException(Exception):
    pass

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

def main():
    # Parse CLI arguments and filename
    parser = argparse.ArgumentParser("Convert MHTML archives to individual files")
    parser.add_argument("-o", "--html-only", action="store_true", help="Only extract the HTML (this will leave the HTML unchanged, typically remote sources will be rewritten to local ones)")
    parser.add_argument("-i", "--inline", action="store_true", help="Try to inline as many files as possible into the HTML file (not yet implemented)")
    parser.add_argument("-j", "--remove-js", action="store_true", help="Remove scripts from the extracted files (not yet implemented)")
    parser.add_argument("-z", "--zip", action="store_true", help="Store the files in a Zip archive, rather than as separate files (not yet implemented)")
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
    os.mkdir(getResDirName(args.mhtml_file))
    
    mhtml_data = mhtml_file.read()
    pointer = mhtml_data.find(b"\r\n\r\n\r\n") + 6 # pointer where to look for the next boundary, start after the header
    boundary = get_boundary(mhtml_data[:pointer]) # find the boundary within the header
    log_info(f"Boundary is {str(boundary, encoding="iso-8859-1")}", args.verbose)
    
    boundaryLine = b"".join((b"--", boundary ,b"\r\n"))
    # Skip to after the first boundary
    pointer += len(boundaryLine)
    
    finished = False
    part = 0
    while not finished:
        data_end = pointer + mhtml_data[pointer:].find(boundaryLine)
        nextpointer = data_end + len(boundaryLine)
        data_start = pointer + mhtml_data[pointer:nextpointer].find(b"\r\n\r\n") + 4
        part_data = mhtml_data[data_start:data_end]
        # TODO: parse part heading (contains encoding, MIME type, an ID and its original location -- which will probably be referenced in the HTML)
        
        # Write out the file under an appropriate name
        if part == 0:
            # The first part is assumed to be the main HTML document
            if not args.html_only:
                # TODO: rewrite external resources in the HTML to be local ones
                # Rewrite the URLs to be local ones, I guess hash the path up to that point to avoid duplication
                # Having the page URL may also be useful for relative URLs
                # Not all instances of src/href/content/etc need to be replaced I guess (e.g. within <a> tags)
                pass
            
            htmlFile = open(getOutputHtmlName(args.mhtml_file), 'wb')
            htmlFile.write(part_data)
            htmlFile.close()
        else:
            pass
    
        pointer = nextpointer
        part += 1
        if args.html_only:
            finished = True

    log_info("Closing file", args.verbose)
    mhtml_file.close()
    log_info(f"Summary: {part} parts written", args.verbose)
    
if __name__ == '__main__':
    main()
