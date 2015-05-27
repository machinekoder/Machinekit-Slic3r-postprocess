#!/usr/bin/python
# -*- coding: utf-8 -*-

#    Copyright 2013 Frank Tkalcevic (frank@franksworkshop.com.au)
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

# Version 1.1
#   - Fix problem not picking up F word
# Version 1.2 - modified by Alexander Roessler
#   - simplfied output
#   - added argparse


import sys
import re
import argparse
import math
import tempfile


class gcode(object):
    def __init__(self):
        self.inFile = None
        self.outFile = None
        self.tmpFile = None

    def initVariables(self):
        self.regMatch = {}
        self.line_count = 0
        self.output_line_count = 0
        self.prev_p = [999999, 999999, 999999, 999999, 999999]  # high number so we detect the change on first move
        self.prev_cross = 99999999
        self.prev_cross_line = 0
        self.currentInFile = None
        self.currentOutFile = None
        self.crossList = []
        self.totalCross = []
        self.crossTolerance = 0.05
        self.filament_d = 1.75
        self.retracted = True

    def convert(self, infile, outfile):
        self.inFile = infile
        self.outFile = outfile
        self.tmpFile = tempfile.TemporaryFile(mode='rw+b')
        self._load(self.inFile)

    def outputLine(self, line):
        self.currentOutFile.write(line + '\n')

    def loadList(self, l):
        self._load(l)

    def _load(self, gcodeFile):
        self.initVariables()
        lastx = 0
        lasty = 0
        lastz = 0
        lasta = 0
        lastf = 0
        
        filament_area = (self.filament_d ** 2) * math.pi / 4

        self.currentOutFile = self.tmpFile

        for line in gcodeFile:
            self.line_count = self.line_count + 1
            line = line.rstrip()
            original_line = line
            if type(line) is tuple:
                line = line[0]

            if ';' in line or '(' in line:
                sem_pos = line.find(';')
                par_pos = line.find('(')
                pos = sem_pos
                if pos is None:
                    pos = par_pos
                elif par_pos is not None:
                    if par_pos > sem_pos:
                        pos = par_pos
                comment = line[pos + 1:].strip()
                line = line[0:pos]
            else:
                comment = None

            # we only try to simplify G1 coordinated moves
            G = self.getCodeInt(line, 'G')
            if G == 1:    # Move
                x = self.getCodeFloat(line, 'X')
                y = self.getCodeFloat(line, 'Y')
                z = self.getCodeFloat(line, 'Z')
                a = self.getCodeFloat(line, 'A')
                f = self.getCodeFloat(line, 'F')
                
                retract = False
                unretract = False
                move = False

                if (a is None):
                    move = True                                          
                elif (x is None) and (y is None) and (z is None):
                    if (a - lasta) > 0:
                        unretract = True
                    else:
                        retract = True

                if x is None: 
                    x = lastx
                if y is None: 
                    y = lasty
                if z is None: 
                    z = lastz
                if a is None: 
                    a = lasta
                if f is None: 
                    f = lastf
                    
                diffx = x - lastx
                diffy = y - lasty
                diffz = z - lastz
                diffa = a - lasta

                dead = False
                if (diffx == 0.0) and (diffy == 0.0) and (diffz == 0.0) \
                   and (diffa == 0.0):
                    dead = True
                
                if retract:
                    self.outputLine("G22 ; retract")
                    self.output_line_count = self.output_line_count + 1
                    self.retracted = True
                elif unretract:
                    self.outputLine("G23 ; unretract")
                    self.output_line_count = self.output_line_count + 1
                    self.retracted = False
                elif move:
                    if not self.retracted:  # handle moves without retraction
                        self.simplifyCross(0.0)
                    self.simplifyLine(G, [x, y, z, f, None, None], comment)
                elif dead:
                        pass  # pass dead moves
                else:
                    length = math.hypot(diffx, diffy)
                    if diffz != 0.0:
                        length = math.hypot(length, diffz)
                    volume = diffa * filament_area
                    cross_section = volume / length
                    self.simplifyCross(cross_section)
                    self.simplifyLine(G, [x, y, z, f, None, None], comment)

                lastx = x
                lasty = y
                lastz = z
                lasta = a
                lastf = f
                
            elif (G == 2) or (G == 3):
                x = self.getCodeFloat(line, 'X')
                y = self.getCodeFloat(line, 'Y')
                z = self.getCodeFloat(line, 'Z')
                a = self.getCodeFloat(line, 'A')
                f = self.getCodeFloat(line, 'F')
                i = self.getCodeFloat(line, 'I')
                j = self.getCodeFloat(line, 'J')
                
                if x is None: 
                    x = lastx
                if y is None: 
                    y = lasty
                if z is None: 
                    z = lastz
                if a is None: 
                    a = lasta
                if f is None: 
                    f = lastf
                    
                diffa = a - lasta
                centerx = lastx + i
                centery = lasty + j

                print("x: " + str(x))
                print("y: " + str(y))
                print("a: " + str(a))
                print("centerx: " + str(centerx))
                print("centery: " + str(centery))
                print("lastx: " + str(lastx))
                print("lasty: " + str(lasty))
                print("i: " + str(i))
                print("j: " + str(j))
                r = (i ** 2 + j ** 2) ** 0.5
                w = ((x - lastx) ** 2 + (y - lasty) ** 2) ** 0.5
                angle = 2 * math.asin(w / (2 * r))
                innerp = centerx * x + centery * y
                len1 = (centerx ** 2 + centery ** 2) ** 0.5
                len2 = (x ** 2 + y ** 2) ** 0.5
                a1 = math.acos(innerp / (len1 * len2))
                innerp = centerx * lastx + centery * lasty
                len2 = (lastx ** 2 + lasty ** 2) ** 0.5
                a2 = math.acos(innerp / (len1 * len2))                
                if G == 2:
                    if a2 < a1:
                        a2 += math.pi * 2
                    angle2 = a2 - a1
                else:
                    if a1 < a2:
                        a1 += math.pi * 2
                    angle2 = a1 - a2
                print "a1",a1
                print "a2",a2
                length = angle2 * r
                print "length",length
                volume = diffa * filament_area
                print "volume",volume
                cross_section = volume / length
                print "cross_section",cross_section
                #height = cross_section / nozzle_d
                #print "height",height
                self.simplifyCross(cross_section)
                self.simplifyLine(G, [x, y, z, f, i, j], comment)
                
                lastx = x
                lasty = y
                lastz = z
                lasta = a
                lastf = f
                
            else:
                # any other move signifies the end of a list of line segments,
                # so we simplify them.

                # store retraction to detect unretracted moves without extrusion (infill)
                if (G == 22):
                    self.retracted = True
                elif (G == 23):
                    self.retracted = False

                if (G == 0) or (G == 92):    # Rapid - remember position
                    x = self.getCodeFloat(line, 'X')
                    y = self.getCodeFloat(line, 'Y')
                    z = self.getCodeFloat(line, 'Z')
                    a = self.getCodeFloat(line, 'A')
                    
                    if x is None: 
                        x = lastx
                    if y is None: 
                        y = lasty
                    if z is None: 
                        z = lastz
                    if a is None: 
                        a = lasta

                    lastx = x
                    lasty = y
                    lastz = z
                    lasta = a
                    
                    if G != 92:
                        self.simplifyLine(G, [x, y, z, None, None, None], comment)
                else:
                    self.outputLine(original_line)
                    self.output_line_count = self.output_line_count + 1

        self.outputLine("; GCode file processed by " + sys.argv[0])
        self.outputLine("; Input Line Count = " + str(self.line_count))
        self.outputLine("; Output Line Count = " + str(self.output_line_count))

        self.currentOutFile = self.outFile
        self.currentInFile = self.tmpFile
        self.tmpFile.seek(0)
        self.optimizeCross()
        #for line in self.tmpFile:
        #    self.currentOutFile.write(line)
        self.tmpFile.close()
        
    def getCodeInt(self, line, code):
        if code not in self.regMatch:
            self.regMatch[code] = re.compile(code + r'([^\s]+)', flags=re.IGNORECASE)
        m = self.regMatch[code].search(line)
        if m is None:
            return None
        try:
            return int(m.group(1))
        except ValueError:
            return None

    def getCodeFloat(self, line, code):
        if code not in self.regMatch:
            self.regMatch[code] = re.compile(code + r'([^\s]+)', flags=re.IGNORECASE)
        m = self.regMatch[code].search(line)
        if m is None:
            return None
        try:
            return float(m.group(1))
        except ValueError:
            return None

    def simplifyLine(self, g, p, c):
        self.output_line_count = self.output_line_count + 1
        #print "i, g,p,c=", i, g,p,c
        s = "G" + str(g) + " "
        if (p[0] is not None) and (p[0] != self.prev_p[0]):
            self.prev_p[0] = p[0]
            s = s + "X{0:g}".format(p[0]) + " "
        if (p[1] is not None) and (p[1] != self.prev_p[1]):
            self.prev_p[1] = p[1]
            s = s + "Y{0:g}".format(p[1]) + " "
        if (p[2] is not None) and (p[2] != self.prev_p[2]):
            self.prev_p[2] = p[2]
            s = s + "Z{0:g}".format(p[2]) + " "
        if (p[3] is not None) and (p[3] != self.prev_p[3]):
            self.prev_p[3] = p[3]
            s = s + "F{0:g}".format(p[3]) + " "
        if p[4] is not None:
            s = s + "I{0:g}".format(p[4]) + " "
        if p[5] is not None:
            s = s + "J{0:g}".format(p[5]) + " "
        if c is not None:
            s = s + "; " + c
        s = s.rstrip()
        self.outputLine(s)

    def compareValue(self, newValue, oldValue, tolerance):
        return (newValue < (oldValue * (1.0 - tolerance))) \
            or (newValue > (oldValue * (1.0 + tolerance)))

    def saveCrossMed(self):
        if len(self.crossList) > 0:
            crossMed = sum(self.crossList) / len(self.crossList)
            self.totalCross.append([self.prev_cross_line, crossMed])

    def simplifyCross(self, cross):
        if self.compareValue(cross, self.prev_cross, self.crossTolerance):
            self.saveCrossMed()
            self.crossList = [cross]
            self.prev_cross = cross
            self.prev_cross_line = self.output_line_count
            self.outputCross(cross)
            self.output_line_count = self.output_line_count + 1
        else:
            self.crossList.append(cross)

    def outputCross(self, cross):
        s = "M700 P{0:g}".format(cross) + " "
        self.outputLine(s)

    def optimizeCross(self):
        # crossList = []
        self.saveCrossMed()  # save last cross section medium
        self.totalCross.sort()
        # for line, cross in self.totalCross:
        #     match = False
        #     for i, item in enumerate(crossList):
        #         if ((cross > (item[0][0] * (1 - tolerance))) and (cross < (item[0][0] * (1 + tolerance)))):
        #             crossList[i][0].append(cross)
        #             crossList[i][1].append(line)
        #             match = True
        #             break
        #     if not match:
        #         crossList.append([[cross], [line]])
        # for i, item in enumerate(crossList):
        #     crossMed = sum(item[0]) / len(item[0])
        #     crossList[i][0] = crossMed
        for i, line in enumerate(self.currentInFile):
            if (len(self.totalCross) > 0) and (i == self.totalCross[0][0]):
                self.outputCross(self.totalCross[0][1])
                self.totalCross.pop(0)
            else:
                self.currentOutFile.write(line)


def main():
    parser = argparse.ArgumentParser(description='This application simplifies G1 straight feeds to G2 and G3 arc moves')
    parser.add_argument('infile', nargs='?', type=argparse.FileType('r'), 
                        default=sys.stdin, help='input file, takes input from stdin if not specified')
    parser.add_argument('outfile', nargs='?', type=argparse.FileType('w'), 
                        default=sys.stdout, help='output file, prints output to stdout of not specified')
    parser.add_argument('-p', '--plane', type=int, default=17, 
                        help='plane parameter')
    parser.add_argument('-pt', '--point_tolerance', type=float, default=0.05, 
                        help='point tolerance parameter')
    parser.add_argument('-lt', '--length_tolerance', type=float, default=0.005, 
                        help='length tolerance parameter')
    parser.add_argument('-d', '--debug', help='enable debug mode', action='store_true')
    args = parser.parse_args()

    inFile = args.infile
    outFile = args.outfile
    
    gcode().convert(inFile, outFile)
    
    inFile.close()
    outFile.close()
    
if __name__ == "__main__":
    main()
