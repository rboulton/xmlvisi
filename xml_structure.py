#!/usr/bin/env python
#
# Copyright (c) 2010 Richard Boulton
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""xml_structure.py: Parse an XML file and dump some details of what's in it.

Currently very simple: dumps counts of the number of times an element occurs,
and a dump of the number of times each sub-element occurs as a child of that
element.

The input file is not read into memory at once, so this can be used to parse
extremely large xml files.

Output format is text, with indentation indicating the heirarchy: first a dump
with one element per line, in the form:

  <element>{count}:
    <sub-element>{count}:

Secondly, a more verbose dump which includes details of attributes, and their
counts:

  <element>{count} (
   <attrib_name>{count}
   <next_attrib_name>{count}
  ):
    <sub-element>{count} (
     <attrib_name>{count}
    )

It would be easy to extend the code to produce output in other formats, and to
track other details of the XML contents (perhaps automatically recognising
fields which containin only numeric or date contents).

"""

import datetime
try:
    from simplejson import json
except ImportError:
    import json
import lxml.etree as etree
import os
import sys
import time

class SchemaElement(object):
    def __init__(self, prefix, shorttag):
        self.prefix = prefix
        self.shorttag = shorttag
        # Number of times this element occurred
        self.count = 0

        # Children (map from full tag to SchemaElement)
        self.children = {}

        # Attributes (map from attribute name to count of times it occurred)
        self.attrib = {}

    def add_instance(self, attrib):
        self.count += 1
        for k in attrib.iterkeys():
            self.attrib[k] = self.attrib.get(k, 0) + 1

    def add_child(self, tag, prefix, shorttag, attrib):
        try:
            child = self.children[tag]
        except KeyError:
            child = SchemaElement(prefix, shorttag)
            self.children[tag] = child
        child.add_instance(attrib)
        return child

    def __str__(self):
        return 'SchemaElement(%s, %s)' % (self.prefix, self.shorttag)

    def pformat(self, attribs=False):
        """Format the result "prettily".

        """
        result = []
        def recurse(element, indent=0):
            result.append(' ' * indent)
            if element.prefix:
                result.append(element.prefix)
                result.append(':')
            result.append(element.shorttag)
            result.append('{')
            result.append(str(element.count))
            result.append('}')
            if attribs and element.attrib:
                result.append(' (')
                for at in sorted(element.attrib.keys()):
                    result.append('\n')
                    result.append(' ' * (indent + 1))
                    result.append(at)
                    result.append('{')
                    result.append(str(element.attrib[at]))
                    result.append('}')
                result.append('\n')
                result.append(' ' * indent)
                result.append('):\n')
            else:
                result.append(':\n')
            for key in sorted(element.children.keys()):
                recurse(element.children[key], indent=indent+2)
  
        recurse(self)
        return u''.join(result)

class ProgressFd(object):
    """Wrap a file descriptor in something which indicates its progress.

    """
    def __init__(self, fd, size):
        self.fd = fd
        self.count = 0
        self.size = size
        self.starttime = time.time()
        self.lastdisplay = self.starttime

    def display(self):
        if self.count == 0:
            return
        now = time.time()
        if now - self.lastdisplay < 1:
            return
        self.lastdisplay = now
        proportion = float(self.count) / self.size
        elapsed = now - self.starttime
        remaining = (elapsed / proportion) - elapsed
        eta = datetime.datetime.fromtimestamp(now + remaining)
        sys.stderr.write("\r%.2f%%: remaining %.0fs, ETA: %s" %
                         (100 * proportion, remaining, eta))

    def read(self, bytes):
        result = self.fd.read(bytes)
        self.count += len(result)
        self.display()
        return result

def scan(filename, progress=False, as_html=False):
    """Scan the contents of a file, and return a derived "schema".

    If `progress` is True, report rough progress stats.

    If `as_html` is True, expect HTML instead of XML.  This will result in
    `progress` being much less accurate, and will cause the whole file to be
    read into memory before being processed.

    """
    schema = SchemaElement('', '')
    events = ('start', 'end', )
    stack = [schema]
    fd = open(filename)
    if progress:
        fd = ProgressFd(fd, os.path.getsize(filename))
    if as_html:
        # iterparse doesn't allow us to specify the parser, so we have to fall
        # back to parsing and using iterwalk on the DOM.
        it = etree.iterwalk(etree.parse(fd, etree.HTMLParser()), events=events)
    else:
        it = etree.iterparse(fd, events=events)
    for event, element in it:
        # Get tag, prefix and shorttag (which is the tag without namespace)
        tag = element.tag
        prefix = element.prefix
        try:
            ns = '{%s}' % element.nsmap[prefix]
        except KeyError:
            ns = ''
        assert tag.startswith(ns)
        shorttag = tag[len(ns):]

        if event == 'start':
            curschema = stack[-1].add_child(tag, prefix, shorttag, element.attrib)
            stack.append(curschema)
        elif event == 'end':
            del stack[-1]
            # Clean up children and previous siblings
            element.clear()
            if element.getprevious() is not None:
                p = element.getparent()
                if p is not None:
                    del p[0]
    return schema.children.values()[0]

def dump_schema(schema):
    print "Overview"
    print "========"
    print schema.pformat()
    print ""
    print "Details"
    print "======="
    print schema.pformat(True)

if __name__ == '__main__':
    # Scan, with progress display
    as_html = False
    if len(sys.argv) > 2:
        if sys.argv[1] == '--html':
            del sys.argv[1]
            as_html=True
    if len(sys.argv) != 2:
        print "Usage: %s [--html] <xml filename>" % sys.argv[0]
    schema = scan(sys.argv[1], True, as_html)
    dump_schema(schema)
