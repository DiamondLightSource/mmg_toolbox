"""
Various utilities for reading and writing nexus files
"""
import typing

import numpy as np
import h5py

from mmg_toolbox.nexus import nexus_names as nn
from mmg_toolbox.utils.units import METERS, unit_converter
from mmg_toolbox.utils.xray_utils import photon_energy, photon_wavelength


def bytes2str(value: str | bytes | list | tuple) -> str:
    """Convert bytes or string to string"""
    if isinstance(value, (str, bytes)):
        return value.decode('utf-8', errors='ignore') if hasattr(value, 'decode') else value
    return bytes2str(next(iter(value), ''))


def get_attr_datasets(group: h5py.Group, attr_name: str) -> list[h5py.Dataset]:
    """Return list of datasets mentioned in group attribute"""
    attribute = group.attrs.get(attr_name, '')
    if isinstance(attribute, (str, bytes)):
        attribute = [attribute]
    # attribute is a list e.g. @axes=['x', 'y']
    return [dataset for name in attribute if (dataset := group.get(name))]


def reorder_group_items(group: h5py.Group) -> dict[str, h5py.Group | h5py.Dataset]:
    """re-order the group.items list to get the put @default objects first"""
    # 1. put default objects first in the list
    items = {}
    if nn.NX_DEFAULT in group.attrs and group.attrs[nn.NX_DEFAULT] in group:
        items[group.attrs[nn.NX_DEFAULT]] = group[group.attrs[nn.NX_DEFAULT]]
    # 2. put datasets before groups to avoid catching lower-level matches
    items.update({key: ds for key, ds in group.items() if isinstance(ds, h5py.Dataset)})
    # 3. add remaining items
    items.update(group.items())
    return items


def update_args(name: str, obj: h5py.Group, axes: str, signal: str, *args: str) -> list[str]:
    """remove object from search arguments if it matches"""
    # expand match-names with SEARCH_ATTRS
    names = [name] + [bytes2str(obj.attrs.get(attr, '')) for attr in nn.SEARCH_ATTRS]
    # Add NX application definition
    if isinstance(obj, h5py.Group) and nn.NX_DEFINITION in obj:
        names.append(bytes2str(obj[nn.NX_DEFINITION][()]))
    # Add axes & signal from parent group
    if name == axes:
        names.append(nn.NX_AXES)
    if name == signal:
        names.append(nn.NX_SIGNAL)
    # check if object matches first arg, otherwise drill down or continue
    return list(args[1:] if args[0] in names else args)


def nx_find(parent: h5py.Group, *field_or_class: str) -> h5py.Dataset | h5py.Group | None:
    """
    Return default or first object to match a set of NXclass or field names

    Example:
        with h5py.File('/path/to/file.h5', 'r') as hdf
            group = nx_find(hdf, 'NXentry', 'NXinstrument', 'NXdetector')  # returns NXdetector group
            dataset = nx_find(hdf, 'NXdata', 'signal')  # returns @signal dataset in @default NXdata
            data = dataset[()]

    Accepted field_or_class arguments:
        - dataset name, e.g. 'data' (returns dataset)
        - group name, e.g. 'entry' (returns group)
        - NX class name, e.g. 'NX_class' (returns NXclass group)
        - NXclass definition, e.g. 'NXmx' (returns NXentry group)
        - local_name attribute name, e.g. 'eta.eta' (returns dataset)
        - 'axes' or 'signal' in NXdata group (returns dataset)
        - hdf path, e.g. 'group/dataset' (returns dataset)

    Parameters:
    :param parent: parent group, must be h5py.File or h5py.Group
    :param field_or_class: names to search for, in hierarchical order.
    :returns: matching Dataset, Group or None if no match
    """

    def recursor(group: h5py.Group, *args):
        # return object from path, e.g. obj['group/data']
        if len(args) == 1 and args[0] in group:
            return group[args[0]]
        # Get group axes & signal datasets
        axes = bytes2str(group.attrs.get(nn.NX_AXES, ''))
        signal = bytes2str(group.attrs.get(nn.NX_SIGNAL, ''))

        items = reorder_group_items(group)  # @default first
        for name, obj in items.items():
            new_args = update_args(name, obj, axes, signal, *args)
            if len(new_args) == 0:
                return obj
            if isinstance(obj, h5py.Group):
                found_obj = recursor(obj, *new_args)
                if found_obj:
                    return found_obj
        return None
    return recursor(parent, *field_or_class)


def nx_find_all(parent: h5py.Group, *field_or_class: str) -> list[h5py.Dataset | h5py.Group]:
    """
    Return all objects that match a set of NXclass or field names

    Example:
        with h5py.File('/path/to/file.h5', 'r') as hdf
            groups = nx_find_all(hdf, 'NXdetector')  # returns list of NXdetector group
            datasets = nx_find(hdf, 'NXdata', 'signal')  # returns list of @signal datasets in NXdata groups
            arrays = [dataset[()] for dataset in datasets]

    Accepted field_or_class arguments:
        - dataset name, e.g. 'data' (returns dataset)
        - group name, e.g. 'entry' (returns group)
        - NX class name, e.g. 'NX_class' (returns NXclass group)
        - NXclass definition, e.g. 'NXmx' (returns NXentry group)
        - local_name attribute name, e.g. 'eta.eta' (returns dataset)
        - 'axes' or 'signal' in NXdata group (returns dataset)

    Parameters:
    :param parent: parent group, must be h5py.File or h5py.Group
    :param field_or_class: names to search for, in hierarchical order.
    :returns: list of matching Datasets or Groups
    """

    def recursor(group: h5py.Group, *args):
        found = []
        # object from path, e.g. obj['group/data']
        if len(args) == 1 and args[0] in group:
            found.append(group[args[0]])
            return found
        # Get group axes & signal datasets
        axes = bytes2str(group.attrs.get(nn.NX_AXES, ''))
        signal = bytes2str(group.attrs.get(nn.NX_SIGNAL, ''))

        for name, obj in group.items():
            new_args = update_args(name, obj, axes, signal, *args)
            if len(new_args) == 0:
                found.append(obj)
                continue
            if isinstance(obj, h5py.Group):
                found += recursor(obj, *new_args)
        return found
    return recursor(parent, *field_or_class)


def nx_find_data(parent: h5py.Group, *field_or_class: str, default=None):
    """Use nx_find to get dataset, return data or default"""
    dataset = nx_find(parent, *field_or_class)
    if isinstance(dataset, h5py.Dataset):
        if np.issubdtype(dataset.dtype, np.number):
            return dataset[...]
        return dataset.asstr()[...]
    return default


def get_axes_signals(nxdata: h5py.Group) -> tuple[list[h5py.Dataset], list[h5py.Dataset]]:
    """Return lists of axes and signal+auxiliary_signals datasets"""
    axes_datasets = get_attr_datasets(nxdata, nn.NX_AXES)
    signal_datasets = get_attr_datasets(nxdata, nn.NX_SIGNAL)
    aux_datasets = get_attr_datasets(nxdata, nn.NX_AUXILIARY)
    return axes_datasets, signal_datasets + aux_datasets


def get_dataset_string(dataset: h5py.Dataset) -> str:
    """Return formatted string of value stored in dataset"""
    if np.issubdtype(dataset, np.number):
        if dataset.size > 1:
            # numeric ndarray
            return f"{dataset.dtype} {dataset.shape}"
        value = np.squeeze(dataset[()])
        if 'decimals' in dataset.attrs:
            value = value.round(dataset.attrs['decimals'])
        if 'units' in dataset.attrs:
            return f"{value} {bytes2str(dataset.attrs['units'])}"
        return str(value)
    try:
        string_dataset = dataset.asstr()[()]
        if dataset.ndim == 0:
            return str(string_dataset)  # bytes or str -> str
        return f"['{string_dataset[0]}', ...({len(string_dataset)})]"  # str array
    except ValueError:
        return str(np.squeeze(dataset[()]))  # other np.ndarray


def get_metadata(group: h5py.Group, *name_paths_default: tuple[str, tuple, str]) -> dict[str, str]:
    """Return a dict with metadata available in hdf Group. All metadata formated as strings"""
    metadata = {
        name: get_dataset_string(dataset)
        if (dataset := nx_find(group, *paths)) else default
        for name, paths, default in name_paths_default
    }
    return metadata


def get_dataset_value(path: str, group: h5py.Group,
                      default: str | float | np.ndarray | None = None, units: str = '') -> np.ndarray | None:
    """
    Get value from dataset in group, or return default
    :param path: hdf path of dataset in group
    :param group: hdf group
    :param default: returned if path doesn't exist
    :param units: converts to given units if units in attrs
    :return: value or default as ndarray, or None if default is None
    """
    if path in group:
        dataset = group[path]
        if np.issubdtype(dataset, np.number):
            data = np.squeeze(dataset[...])
            if units and 'units' in dataset.attrs:
                return unit_converter(data, bytes2str(dataset.attrs['units']), units)
            return data
        return dataset.asstr()[...]
    return None if default is None else np.asarray(default)


def nx_beam_energy(beam: h5py.Group) -> tuple[float, float]:
    """
    Return beam energy in keV and wavelength in A
    :param beam: Nexus NXbeam group
    :return: incident_energy, incident_wavelength
    """
    if nn.NX_WL in beam:
        dataset = beam[nn.NX_WL]
        units = dataset.attrs.get(nn.NX_UNITS, b'nm').decode()
        wl = dataset[()]
        if units.lower() in METERS:
            wl = wl * METERS[units] * 1e-10  # wavelength in Angstroms
        else:
            print(f"Warning: unknown translation units: {units}")
        return photon_energy(wl), wl
    elif nn.NX_EN in beam:
        dataset = beam[nn.NX_WL]
        units = dataset.attrs.get(nn.NX_UNITS, b'ev').decode()
        en = dataset[()]
        if units.lower() == 'ev':
            en = en / 1000.  # wavelength in keV
        return en, photon_wavelength(en)
    else:
        raise KeyError(f"{beam} contains no '{nn.NX_WL}' or '{nn.NX_EN}'")
