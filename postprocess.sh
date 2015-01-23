#!/bin/bash
gcode-to-ngc $@ > $@.tmp
mv $@.tmp $@