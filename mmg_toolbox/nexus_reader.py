

import hdfmap

from mmg_toolbox.misc_functions import DataHolder, data_holder


def nexus_data_holder(hdf_map: hdfmap.NexusMap, flatten_scannables: bool = True) -> DataHolder:
    """
    Create DataHolder object from Nexus file
    """
    with hdf_map.load_hdf() as hdf:
        metadata = hdf_map.get_metadata(hdf)
        scannables = hdf_map.get_scannables(hdf, flatten=flatten_scannables)
    d = data_holder(scannables, metadata)
    d.map = hdf_map
    d.eval = lambda expression: hdf_map.eval(hdf_map.load_hdf(), expression)
    d.format = lambda expression: hdf_map.format_hdf(hdf_map.load_hdf(), expression)
    return d


def read_nexus_file(filename: str) -> DataHolder:
    """
    Read Nexus file as DataHolder
    """
    hdf_map = hdfmap.create_nexus_map(filename)
    return nexus_data_holder(hdf_map)

