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
    
    mhtml_data = mhtml_file.read()
    pointer = mhtml_data.find(b"\r\n\r\n") # pointer where to look for the next boundary, start after the header
    boundary = get_boundary(mhtml_data[:pointer]) # find the boundary within the header
    log_info(f"Boundary is {str(boundary, encoding="iso-8859-1")}", args.verbose)
    
    finished = False
    while not finished:
        print("Got to the boundary loop, exiting")
        break
    
    log_info("Closing file", args.verbose)
    mhtml_file.close()
    
if __name__ == '__main__':
    main()
