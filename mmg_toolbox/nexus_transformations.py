"""
NXtransformations
code taken from https://github.com/DanPorter/i16_diffractometer
"""

import numpy as np
import h5py

import mmg_toolbox.nexus_names as nn
from mmg_toolbox.nexus_names import METERS
from mmg_toolbox.rotations import norm_vector, rotation_t_matrix, translation_t_matrix, transform_by_t_matrix


def get_depends_on(root: None | str | h5py.Group | h5py.Dataset) -> str:
    """Return depends_on value from group or dataset"""
    if isinstance(root, h5py.Group):
        if nn.NX_DEPON in root:
            return str(root[nn.NX_DEPON].asstr()[...])
        else:
            raise Exception(f"group: {root} does not contain 'depends_on'")
    elif isinstance(root, h5py.Dataset):
        if nn.NX_DEPON in root.attrs:
            return str(root.attrs[nn.NX_DEPON])
        else:
            raise Exception(f"dataset: {root} does not contain 'depends_on'")
    elif not root:
        return '.'
    else:
        return root

# def get_depends_on(path: str, hdf_file: h5py.File) -> str:
#     """
#     Returns 'depends_on' path from this group or dataset
#     The returned path will point to a dataset, based on NeXus rules
#     :param path: path of a dataset
#     :param hdf_file: HDF5 file object
#     :return:
#     """
#     obj = hdf_file[path]
#     if nn.NX_DEPON in obj.attrs:
#         do_path = obj.attrs[nn.NX_DEPON]
#     elif isinstance(obj, h5py.Group) and nn.NX_DEPON in obj:
#         do_path = obj[nn.NX_DEPON][()]
#     else:
#         return '.'
#
#     if do_path in hdf_file:
#         return do_path.decode() if isinstance(do_path, bytes) else do_path
#     # walk up tree to find relative file path
#     while (isinstance(obj, h5py.Dataset) or do_path not in obj) and obj != obj.file:
#         obj = obj.parent
#     return obj[do_path].name if do_path in obj else '.'


def nx_depends_on_chain(path: str, hdf_file: h5py.File) -> list[str]:
    """
    Returns list of paths in a transformation chain, linked by 'depends_on'
    :param path: hdf path of initial dataset or group
    :param hdf_file: Nexus file object
    :return:
    """
    depends_on = get_depends_on(hdf_file[path])
    out = []
    if depends_on != '.':
        out.append(depends_on)
        out.extend(nx_depends_on_chain(depends_on, hdf_file))
    return out


def nx_direction(path: str, hdf_file: h5py.File) -> np.ndarray:
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


def nx_transformations_max_size(path: str, hdf_file: h5py.File) -> int:
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


def nx_transformations(path: str, index: int, hdf_file: h5py.File, print_output=False) -> list[np.ndarray]:
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


def nx_transformations_matrix(path: str, index: int, hdf_file: h5py.File) -> np.ndarray:
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


def nx_transform_vector(xyz, path: str, index: int, hdf_file: h5py.File) -> np.ndarray:
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


class NxTransformation:
    """
    Class containing single NXTransformation axis
    """
    def __init__(self, path: str, name: str, parent: str, value: float | np.array, transformation_type: str,
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


def load_transformation(path: str, index: int, hdf_file: h5py.File) -> NxTransformation:
    """Read Transformation Operation from HDF file"""
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
        parent='',
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
    def __init__(self, path: str, index: int, hdf_file: h5py.File):
        self.path = path
        self.name = path.split('/')[-1]
        chain = nx_depends_on_chain(path, hdf_file)
        self._chain = [
            load_transformation(path, index, hdf_file) for path in chain
        ]

    def __repr__(self):
        return f"NxTransformationChain('{self.path}', {self.name})"

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
