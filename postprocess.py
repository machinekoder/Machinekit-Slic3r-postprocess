#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import sys
import codecs

replacements = [
    [" E", " A"],
    ["M104", "M204"],
    ["M106", "M206"],
    ["M107", "M207"],
    ["M109", "M209"],
    ["M140", "M240"],
    ["M190", "M290"]
    ]


def do_replacements(line):
    for replacement in replacements:
        line = line.replace(replacement[0], replacement[1])
    return line

filepath = sys.argv[1]
#filedir = os.path.dirname(filepath)
#filename = os.path.filename(filepath)

inFile = codecs.open(filepath, "r", "utf-8")
outFile = codecs.open(filepath + ".new", "w", "utf-8")
for line in inFile:
    newline = do_replacements(line)
    outFile.write(newline)
inFile.close()
outFile.close()
os.rename(filepath + ".new", filepath)