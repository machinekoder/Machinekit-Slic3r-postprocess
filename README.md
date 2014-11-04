Machinekit-Slic3r-postprocess
=============================

Python script to postprocess Slic3r output for Machinekit

## Install
Make sure you have the python binary in your path variable. Try following in any terminal:

    python --version

## Usage
Add following to your Slic3r postprocess settings (Print Settings > Output Options > Post-processing scripts):

    <path to script>/postprocess.py
    
## Configuring
Edit the replacements variable in the script to fit for your Machinekit configuration.