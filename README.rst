XMLvisi
=======

Currently, this contains a basic tool (xml_structure.py) to scan an XML
file and display information about the elements it contains (what they are,
what their children are, how often each element occurs as a child of
another, and how often each attribute of an element occurs).

The tool scans the file, rather than reading it all into memory at once,
which means that it can handle extremely large files.  For example, it took
around 3 minutes to process a 535Mb dump of the NaPTAN database from
http://www.dft.gov.uk/naptan/overview.htm

HTML files can be parsed by specifying the --html option.  However, the HTML
parser does read the entire file into memory at once, so won't work with quite
such big files.
