"""
NXtransformations
code taken from https://github.com/DanPorter/i16_diffractometer
"""
import hdfmap
import numpy as np
import h5py

import mmg_toolbox.nexus.nexus_names as nn
from mmg_toolbox.utils.units import METERS
from mmg_toolbox.utils.rotations import norm_vector, rotation_t_matrix, translation_t_matrix, transform_by_t_matrix
from mmg_toolbox.nexus.nexus_functions import nx_find_all, bytes2str

H5pyType = h5py.File | h5py.Group | h5py.Dataset


def get_depends_on(root: None | str | H5pyType) -> str:
    """Return depends_on value from group or dataset"""
    if isinstance(root, h5py.Group):
        if nn.NX_DEPON in root:
            return str(root[nn.NX_DEPON].asstr()[...])
        else:
            raise Exception(f"group: {root} does not contain 'depends_on'")
    elif isinstance(root, h5py.Dataset):
        if nn.NX_DEPON in root.attrs:
            return bytes2str(root.attrs[nn.NX_DEPON])
        else:
            raise Exception(f"dataset: {root} does not contain 'depends_on'")
    elif not root:
        return '.'
    else:
        return root


def nx_depends_on_chain(path: str, hdf_file: h5py.Group) -> list[str]:
    """
    Returns list of paths in a transformation chain, linked by 'depends_on'
    :param path: hdf path of initial dataset or group
    :param hdf_file: Nexus file object
    :return:
    """
    if path in hdf_file:
        depends_on = get_depends_on(hdf_file[path])
    else:
        depends_on = path
    out = []
    if depends_on != '.':
        out.append(depends_on)
        out.extend(nx_depends_on_chain(depends_on, hdf_file))
    return out


def nx_direction(path: str, hdf_file: h5py.Group) -> np.ndarray:
    """
    Return a unit-vector direction from a dataset
    :param path: hdf path of NXtransformation path or component group with 'depends_on'
    :param hdf_file: Nexus file object
    :return: unit-vector array
    """
    depends_on = get_depends_on(hdf_file[path])
    if depends_on == '.':
        dataset = hdf_file[path]
    else:
        dataset = hdf_file[depends_on]

    vector = np.asarray(dataset.attrs.get(nn.NX_VECTOR, (0, 0, 0)))
    return norm_vector(vector)


def nx_transformations_max_size(path: str, hdf_file: h5py.Group) -> int:
    """
    Return the maximum dataset size from a chain of transformations
    :param path: hdf dataset path of NX transformation, or group containing 'depends_on'
    :param hdf_file: Nexus file object
    :return: int : largest dataset.size
    """
    dataset = hdf_file[path]
    dataset_size = dataset.size if isinstance(dataset, h5py.Dataset) else 0
    depends_on = get_depends_on(dataset)
    if depends_on != '.':
        size = nx_transformations_max_size(depends_on, hdf_file)
        return size if size > dataset_size else dataset_size
    return dataset_size


def nx_transformations(path: str, index: int, hdf_file: h5py.Group, print_output=False) -> list[np.ndarray]:
    """
    Create list of 4x4 transformation matrices matching transformations along an NXtransformations chain
    :param path: str hdf path of the first point in the chain (Group or Dataset)
    :param index: int index of point in scan
    :param hdf_file: Nexus file object
    :param print_output: bool, if true the operations will be printed
    :return: list of 4x4 arrays [T1, T2, T3, ... Tn]
    """
    dataset = hdf_file[path]
    depends_on = get_depends_on(dataset)
    if print_output:
        print(f"{dataset}, depends on: {depends_on}")

    if isinstance(dataset, h5py.Group):
        return nx_transformations(depends_on, index, hdf_file, print_output)

    this_index = index if dataset.size > 1 else 0
    value = dataset[np.unravel_index(this_index, dataset.shape)]

    transformation_type = dataset.attrs.get(nn.NX_TTYPE, b'').decode()
    vector = np.array(dataset.attrs.get(nn.NX_VECTOR, (1, 0, 0)))
    offset = dataset.attrs.get(nn.NX_OFFSET, (0, 0, 0))
    units = dataset.attrs.get(nn.NX_UNITS, b'').decode()

    if transformation_type == nn.NX_TROT:
        if print_output:
            print(f"Rotating about {vector} by {value} {units}  | {path}")
        if units == 'deg':
            value = np.deg2rad(value)
        elif units != 'rad':
            value = np.deg2rad(value)
            print(f"Warning: Incorrect rotation units: '{units}'")
        matrix = rotation_t_matrix(value, vector, offset)
    elif transformation_type == nn.NX_TTRAN:
        if print_output:
            print(f"Translating along {vector} by {value} {units}  | {path}")
        if units in METERS:
            unit_multiplier = METERS[units]
        else:
            unit_multiplier = 1.0
            print(f"Warning: unknown translation untis: {units}")
        value = value * unit_multiplier * 1000  # distance in mm
        matrix = translation_t_matrix(value, vector, offset)
    else:
        if print_output:
            print(f"transformation type of '{path}' not recognized: '{transformation_type}'")
        matrix = np.eye(4)

    if depends_on == '.':  # end chain
        return [matrix]
    return [matrix] + nx_transformations(depends_on, index, hdf_file, print_output)


def nx_transformations_matrix(path: str, index: int, hdf_file: h5py.Group) -> np.ndarray:
    """
    Combine chain of transformation operations into single matrix
    :param path: str hdf path of the first point in the chain (Group or Dataset)
    :param index: int index of point in scan
    :param hdf_file: Nexus file object
    :return: 4x4 array
    """
    matrices = nx_transformations(path, index, hdf_file)
    # Combine the transformations in reverse
    return np.linalg.multi_dot(matrices[::-1])  # multiply transformations Tn..T3.T2.T1


def nx_transform_vector(xyz, path: str, index: int, hdf_file: h5py.Group) -> np.ndarray:
    """
    Transform a vector or position [x, y, z] by an NXtransformations chain
    :param xyz: 3D coordinates, n*3 [[x, y, z], ...]
    :param path: hdf path of first object in NXtransformations chain
    :param index: int index of point in scan
    :param hdf_file: Nexus file object
    :return: n*3 array([[x, y, z], ...]) transformed by operations
    """
    xyz = np.reshape(xyz, (-1, 3))
    t_matrix = nx_transformations_matrix(path, index, hdf_file)
    return (np.dot(t_matrix[:3, :3], xyz.T) + t_matrix[:3, 3:]).T


########################################################################################################################
########################################## Transformation Classes ######################################################
########################################################################################################################


class NxTransformation:
    """
    Class containing single NXTransformation axis
    """
    def __init__(self, path: str, name: str, parent: str, value: float | np.ndarray, transformation_type: str,
                 vector: tuple[float, float, float], offset: tuple[float, float, float],
                 units: str, offset_units: str, depends_on: str):
        self.path = path
        self.name = name
        self.parent = parent
        self.value = value
        self.type = transformation_type
        self.vector = vector
        self.offset = offset
        self.units = units
        self.offset_units = offset_units
        self.depends_on = depends_on

    def __repr__(self):
        return f"NxTransformation('{self.path}', {self.type}||{self.vector}={self.value})"

    def __str__(self):
        if self.type == nn.NX_TTRAN:
            return f"Translating {self.parent} along {self.vector} by {self.value} {self.units}  | {self.path}"
        else:
            return f"Rotating {self.parent} about {self.vector} by {self.value} {self.units}  | {self.path}"

    def t_matrix(self):
        if self.type == nn.NX_TTRAN:
            return translation_t_matrix(self.value, self.vector, self.offset)
        else:
            return rotation_t_matrix(self.value, self.vector, self.offset)

    def transform(self, vec: np.ndarray) -> np.ndarray:
        return transform_by_t_matrix(vec, self.t_matrix())


def load_transformation(path: str, index: int, hdf_file: h5py.Group, parent: str = '') -> NxTransformation:
    """Read Transformation Operation from HDF file"""
    if nn.NX_VECTOR in hdf_file[path].attrs:
        dataset = hdf_file[path]
    else:
        depends_on = get_depends_on(hdf_file[path])
        if depends_on == '.':
            dataset = hdf_file[path]
        else:
            dataset = hdf_file[depends_on]

    this_index = index if dataset.size > 1 else 0
    value = dataset[np.unravel_index(this_index, dataset.shape)]

    transformation_type = dataset.attrs.get(nn.NX_TTYPE, b'').decode()
    vector = dataset.attrs.get(nn.NX_VECTOR, (1, 0, 0))
    offset = dataset.attrs.get(nn.NX_OFFSET, (0, 0, 0))
    units = dataset.attrs.get(nn.NX_UNITS, b'').decode()
    offset_units = dataset.attrs.get(nn.NX_OFFSET_UNITS, b'').decode()
    depends_on = dataset.attrs.get(nn.NX_DEPON, b'').decode()
    return NxTransformation(
        path=path,
        name=dataset.name.split('/')[-1],
        parent=parent,
        value=value,
        transformation_type=transformation_type,
        vector=vector,
        offset=offset,
        units=units,
        offset_units=offset_units,
        depends_on=depends_on
    )


class NxTransformationChain:
    """
    Class containing chain of transformation operations
    """
    def __init__(self, object: H5pyType, index: int = 0):
        if isinstance(object, h5py.Dataset) and nn.NX_TTYPE not in object.attrs:
            raise Exception(f"{object} does not have '{nn.NX_TTYPE}' attribute")
        elif isinstance(object, h5py.Group) and nn.NX_DEPON not in object:
            raise Exception(f"{object} does not contain {nn.NX_DEPON}")
        self.path = object.name
        self.name = self.path.split('/')[-1]
        self.index = index
        chain = nx_depends_on_chain(self.path, object.file)
        self.size = nx_transformations_max_size(self.path, object.file)
        self._chain = [
            load_transformation(_path, index, object.file, self.name) for _path in chain
        ]

    def __repr__(self):
        return f"NxTransformationChain('{self.path}', index={self.index+1}/{self.size})"

    def __str__(self):
        return repr(self) + '\n' + '\n'.join(str(t) for t in self._chain)

    def __getitem__(self, item):
        return self._chain[item]

    def __iter__(self):
        return iter(self._chain)

    def __len__(self):
        return len(self._chain)

    def t_matrix_list(self) -> list[np.ndarray]:
        return [t.t_matrix() for t in self._chain]

    def t_matrix(self) -> np.ndarray:
        if len(self) == 1:
            return self._chain[0].t_matrix()
        else:
            return np.linalg.multi_dot(self.t_matrix_list()[::-1])

    def transform(self, vec: np.ndarray) -> np.ndarray:
        return transform_by_t_matrix(vec, self.t_matrix())


def generate_nxtranformations_string(filename: str) -> str:
    """
    return a string describing all the transformation chains in the NeXus file
    """
    out_str = "######################## NXtransformations ##########################\n"
    with hdfmap.load_hdf(filename) as nxs:
        datasets = nx_find_all(nxs, nn.NX_DEPON)
        for dataset in datasets:
            chain = NxTransformationChain(dataset.parent, 0)
            out_str += str(chain) + '\n\n'
    return out_str


#TODO: Merge this and NxTransformation
class TransformationAxis:
    """Holder for data to define an NXtransformation dataset"""
    def __init__(self, name: str, value: float | np.ndarray,
                 transformation_type: str = 'rotation', units: str = 'Deg',
                 vector: tuple[float, float, float] = (1, 0, 0), offset: tuple[float, float, float] = (0, 0, 0),
                 offset_units: str = 'mm'):
        self.name = name
        self.value = value
        self.units = units
        self.type = transformation_type
        self.vector = vector
        self.offset = offset
        self.offset_units = offset_units


class RotationAxis(TransformationAxis):
    """Holder for data to define a rotation NXtransformation dataset with units Degrees"""
    def __init__(self, name: str, value: float | np.ndarray,
                 vector: tuple[float, float, float] = (1, 0, 0), offset: tuple[float, float, float] = (0, 0, 0),
                 offset_units: str = 'mm'):
        super().__init__(name, value, 'rotation', 'Deg', vector, offset, offset_units)


class TranslationAxis(TransformationAxis):
    """Holder for data to define a translation NXtransformation dataset with units mm"""
    def __init__(self, name: str, value: float | np.ndarray,
                 vector: tuple[float, float, float] = (1, 0, 0), offset: tuple[float, float, float] = (0, 0, 0),
                 offset_units: str = 'mm'):
        super().__init__(name, value, 'translation', 'mm', vector, offset, offset_units)
