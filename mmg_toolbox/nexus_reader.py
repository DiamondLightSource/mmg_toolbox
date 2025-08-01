

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


def add_roi(hdf_map: hdfmap.NexusMap, name: str, cen_i: int | str, cen_j: int | str,
                wid_i: int = 30, wid_j: int = 30, image_name: str = 'IMAGE'):
    """
    Add an image ROI (region of interest) to the named expressions
    The ROI operates on the default IMAGE dataset, loading only the required region from the file.
    The following expressions will be added, for use in self.eval etc.
        *name* -> returns the whole ROI array
        *name*_total -> returns the sum of each image in the ROI array
        *name*_max -> returns the max of each image in the ROI array
        *name*_min -> returns the min of each image in the ROI array
    """
    islice = f"{cen_i}-{wid_i:.0f} // 2 : {cen_i}+{wid_i:.0f} // 2"
    jslice = f"{cen_j}-{wid_j:.0f} // 2 : {cen_j}+{wid_j:.0f} // 2"
    roi_array = f"d_{image_name}[..., {islice}, {jslice}]"
    roi_total = f"{roi_array}.sum(axis=(-1, -2))"
    roi_max = f"{roi_array}.max(axis=(-1, -2))"
    roi_min = f"{roi_array}.min(axis=(-1, -2))"
    alternate_names = {
        f"{name}_total": roi_total,
        f"{name}_max": roi_max,
        f"{name}_min": roi_min,
        name: roi_array,
    }
    hdf_map.add_named_expression(**alternate_names)

