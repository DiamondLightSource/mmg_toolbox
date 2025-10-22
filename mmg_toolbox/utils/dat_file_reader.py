"""
Read measurement ASCII ####.dat files
Also known as SRS files
"""

import numpy as np

from mmg_toolbox.utils.misc_functions import DataHolder, data_holder


def read_dat_file(filename: str) -> DataHolder:
    """
    Reads #####.dat files from instrument, returns class instance containing all data
    Input:
      filename = string filename of data file
    Output:
      d = dict with attional attributes:
         d.*item* - returns scanned item as 1D array
         d.metadata - class containing all metadata from datafile
         d.metadata.*item* - returns value of metadata item
         d.keys() - returns all parameter names
         d.values() - returns all parameter values
         d.items() - returns parameter (name,value) tuples
    """
    with open(filename, 'r') as f:
        lines = f.readlines()

    # Read metadata
    meta = {}
    lineno = 0
    for ln in lines:
        lineno += 1
        if '&END' in ln: break
        ln = ln.strip(' ,\n')
        neq = ln.count('=')
        if neq == 1:
            'e.g. cmd = "scan x 1 10 1"'
            inlines = [ln]
        elif neq > 1:
            'e.g. SRSRUN=571664,SRSDAT=201624,SRSTIM=183757'
            inlines = ln.split(',')
        else:
            'e.g. <MetaDataAtStart>'
            continue

        for inln in inlines:
            vals = inln.split('=')
            if len(vals) != 2: continue  # skip any lines with more than 1 '='
            try:
                meta[vals[0]] = eval(vals[1])
            except SyntaxError: # catch strings without quotations
                meta[vals[0]] = vals[1]

    # Read Scanned data
    # previous loop ended at &END, now starting on list of names
    names = lines[lineno].split()
    # Load 2D arrays of scanned values
    vals = np.loadtxt(lines[lineno + 1:], ndmin=2)
    # Assign arrays to a dictionary
    scanned = {
        name: value for name, value in zip(names, vals.T)
    }

    # Convert to class instance
    return data_holder(scanned, meta)
