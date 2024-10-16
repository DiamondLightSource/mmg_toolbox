
import os
import hdfmap


def read_Nexus_file(filename: str):
    return hdfmap.nexus_data_block(filename)


def readscan_Nexus(num):
    if os.path.isdir(filedir) == False:
        print("I can't find the directory: {}".format(filedir))
        return None

    file = os.path.join(filedir, nxsfile_format % num)

    try:
        d = read_Nexus_file(file)
        # d = dnp.io.load(file,warn=False) # from SciSoftPi
    except:
        print("Scan {} doesn't exist or can't be read".format(num))
        return None
    return (d)