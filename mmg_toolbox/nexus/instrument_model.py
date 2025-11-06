"""
Instrument Model from NeXus files

Makes use of NeXus classes and NXtransformations to build a structure of the instrument from a scan file.
"""

import h5py
import numpy as np

from mmg_toolbox.nexus import nexus_names as nn
from mmg_toolbox.nexus.nexus_functions import nx_find, get_dataset_value
from mmg_toolbox.nexus.nexus_transformations import nx_direction, nx_transformations_max_size, \
    nx_transformations_matrix, nx_transform_vector
from mmg_toolbox.utils.rotations import norm_vector, transform_by_t_matrix
from mmg_toolbox.utils.xray_utils import wavevector, photon_energy, photon_wavelength, bmatrix
from mmg_toolbox.plotting.matplotlib import Axes3D

# types
Shape = tuple[int, int, int]  #  (n, i, j) == (frame, slow_pixel, fast_pixel) #TODO: should this be fast, slow?
Pixel = tuple[int, float, float]  # (n, i, j) pixel coordinates

#TODO: add polarisation
#TODO: improve docs

class NXBeam:
    """
    NXbeam object
    """

    def __init__(self, path: str, hdf_file: h5py.File):
        self.file = hdf_file
        self.path = path
        self.beam = hdf_file[path]

        self.direction = nx_direction(path, hdf_file)
        self.en, self.wl = self.energy_wavelength()
        self.wv = wavevector(self.wl)
        self.incident_wavevector = self.wv * self.direction

    def energy_wavelength(self):
        """
        Return beam energy in keV and wavelength in A
        :return: incident_energy, incident_wavelength
        """
        if nn.NX_WL in self.beam:
            wl = get_dataset_value(nn.NX_WL, self.beam, units='A')
            return photon_energy(wl), wl
        elif nn.NX_EN in self.beam:
            en = get_dataset_value(nn.NX_EN, self.beam, units='keV')
            return en, photon_wavelength(en)
        else:
            raise KeyError(f"{self.beam} contains no '{nn.NX_WL}' or '{nn.NX_EN}'")

    def __repr__(self):
        return f"NXBeam({self.beam})"


class NXSsample:
    """
    NXsample object
    """

    def __init__(self, path: str, hdf_file: h5py.File):
        self.file = hdf_file
        self.path = path
        self.sample = hdf_file[path]

        self.name = get_dataset_value(nn.NX_NAME, self.sample, 'none')
        self.unit_cell = get_dataset_value(nn.NX_SAMPLE_UC, self.sample, np.array([1., 1, 1, 90, 90, 90]))
        self.orientation_matrix = get_dataset_value(nn.NX_SAMPLE_OM, self.sample, np.eye(3))
        self.ub_matrix = get_dataset_value(nn.NX_SAMPLE_UB, self.sample, bmatrix(*self.unit_cell))

        self.size = nx_transformations_max_size(path, hdf_file)
        self.transforms = [
            nx_transformations_matrix(path, n, hdf_file)
            for n in range(self.size)
        ]  # list of 4x4 transformation matrices

    def __repr__(self):
        return f"NXSsample({self.sample})"

    def hkl2q(self, hkl: tuple[float, float, float] | np.ndarray, index: int = 0) -> np.ndarray:
        """
        Returns wavevector direction for given hkl in lab space
        :param hkl: Miller indices (h, k, l), in units of reciprocal lattice vectors
        :param index: index of scan
        :return: Q position in inverse Angstroms
        """
        hkl = np.reshape(hkl, (-1, 3))
        z = self.transforms[index][:3, :3]
        ub = 2 * np.pi * self.ub_matrix
        return np.dot(z, np.dot(ub, hkl.T)).T


class NXDetectorModule:
    """
    NXdetector_module object
    """

    def __init__(self, path: str, hdf_file: h5py.File):
        self.file = hdf_file
        self.path = path
        self.module = hdf_file[path]

        self.data_origin = get_dataset_value(nn.NX_MODULE_ORIGIN, self.module, np.array([0, 0]))
        self.data_size = get_dataset_value(nn.NX_MODULE_SIZE, self.module, np.array([1, 1]))

        self.module_offset_path = f"{self.path}/{nn.NX_MODULE_OFFSET}"
        self.fast_pixel_direction_path = f"{self.path}/{nn.NX_MODULE_FAST}"
        self.slow_pixel_direction_path = f"{self.path}/{nn.NX_MODULE_SLOW}"

        self.size = nx_transformations_max_size(self.module_offset_path, hdf_file)
        self.offset_transforms = [
            nx_transformations_matrix(self.module_offset_path, n, hdf_file)
            for n in range(self.size)
        ]  # list of 4x4 transformation matrices
        self.fast_transforms = [
            nx_transformations_matrix(self.fast_pixel_direction_path, n, hdf_file)
            for n in range(self.size)
        ]  # list of 4x4 transformation matrices
        self.slow_transforms = [
            nx_transformations_matrix(self.slow_pixel_direction_path, n, hdf_file)
            for n in range(self.size)
        ]  # list of 4x4 transformation matrices

    def __repr__(self):
        return f"NXDetectorModule({self.module})"

    def shape(self) -> Shape:
        """
        Return scan shape of module
            (n, i, j)
        Where:
            n = frames in scan
            i = pixels along slow axis
            j = pixels along fast axis
        """
        return self.size, self.data_size[0], self.data_size[1]

    def pixel_wavevector(self, point: Pixel, wavelength_a) -> np.ndarray:
        """
        Return wavevector of pixel in lab frame
        :param point: (n, i, j) == (frame, slow_axis_pixel, fast_axis_pixel)
        :param wavelength_a: wavelength in Angstrom
        :return: [x, y, z] in inverse Angstrom
        """
        return wavevector(wavelength_a) * self.pixel_direction(point)

    def pixel_direction(self, point: Pixel) -> np.ndarray:
        """
        Return direction of pixel in lab frame
        :param point: (n, i, j) == (frame, slow_axis_pixel, fast_axis_pixel)
        :return: [dx, dy, dz] unit vector
        """
        return norm_vector(self.pixel_position(point))

    def pixel_position(self, point: Pixel) -> np.ndarray:
        """
        Return position of pixel (n, i, j) in lab frame
            n = frame in scan
            i = pixel along slow axis
            j = pixel along fast axis
        """
        index, ii, jj = point

        module_origin = transform_by_t_matrix([0, 0, 0], self.offset_transforms[index])
        fast_pixel = transform_by_t_matrix([0, 0, 0], self.fast_transforms[index])
        slow_pixel = transform_by_t_matrix([0, 0, 0], self.slow_transforms[index])

        fast_direction = fast_pixel - module_origin
        slow_direction = slow_pixel - module_origin
        return np.squeeze(ii * slow_direction + jj * fast_direction + module_origin)

    def corners(self, frame: int) -> np.ndarray:
        """return corners of the detector module at this frame in scan"""
        shape = self.shape()
        corners = np.vstack([
            self.pixel_position((frame, 0, 0)),  # module origin
            self.pixel_position((frame, int(shape[1]), 0)),  # module origin + slow pixels
            self.pixel_position((frame, int(shape[1]), int(shape[2]))),  # o + slow + fast
            self.pixel_position((frame, 0, int(shape[2]))),  # o + fast
            self.pixel_position((frame, 0, 0)),  # module origin
        ])
        return corners


class NXDetector:
    """
    NXdetector object
    """

    def __init__(self, path: str, hdf_file: h5py.File):
        self.file = hdf_file
        self.path = path
        self.detector = hdf_file[path]
        self.size = nx_transformations_max_size(path, hdf_file)
        self.position = nx_transform_vector((0, 0, 0), path, self.size // 2, hdf_file).squeeze()

        self.modules = [
            NXDetectorModule(f"{self.path}/{p}", hdf_file)
            for p, obj in self.detector.items()
            if obj.attrs.get(nn.NX_CLASS) == nn.NX_MODULE.encode()
        ]

    def __repr__(self):
        return f"NXDetector({self.detector}) with {len(self.modules)} modules"


class NXInstrumentModel:
    """
    NXInstrumentModel object
    """

    def __init__(self, hdf_file: h5py.File):
        self.file = hdf_file

        self.entry = nx_find(hdf_file, nn.NX_ENTRY)
        self.instrument = nx_find(self.entry, nn.NX_INST)

        self.detectors = [
            NXDetector(f"{self.instrument.name}/{p}", hdf_file)
            for p, obj in self.instrument.items()
            if obj.attrs.get(nn.NX_CLASS) == nn.NX_DET.encode()
        ]
        self.components = [
            obj for obj in self.instrument.values()
            if isinstance(obj, h5py.Group) and 'depends_on' in obj
        ]
        self.component_positions = {
            obj.name.split('/')[-1]: nx_transform_vector((0, 0, 0), obj.name, 0, hdf_file).squeeze()
            for obj in self.components
        }
        self.component_positions['sample'] = np.array([0, 0, 0])

        sample_obj = nx_find(self.entry, nn.NX_SAMPLE)
        self.sample = NXSsample(sample_obj.name, hdf_file)
        beam_obj = nx_find(sample_obj, nn.NX_BEAM)
        self.beam = NXBeam(beam_obj.name, hdf_file)

    def __repr__(self):
        return f"NXInstrumentModel({self.file})"

    def _first_detector(self):
        return self.detectors[0].modules[0]

    def shape(self) -> Shape:
        """
        Return scan shape from the first detector module
            (n, i, j)
        Where:
            n = frames in scan
            i = pixels along slow axis
            j = pixels along fast axis
        """
        detector_module = self._first_detector()
        return detector_module.shape()

    def detector_q(self, point: Pixel = (0, 0, 0)) -> np.ndarray:
        """
        return wavevector transfer, kf-ki, of first detector module, in lab frame
        :param point: (n, i, j) == (frame, slow_axis_pixel, fast_axis_pixel)
        :return: [x, y, z] in inverse Angstrom
        """
        wavelength = self.beam.wl
        ki = self.beam.incident_wavevector
        detector_module = self._first_detector()
        kf = detector_module.pixel_wavevector(point, wavelength)
        return kf - ki

    def hkl(self, point: Pixel = (0, 0, 0)):
        """
        return wavevector transfer, Q, of pixel coordinate
        :param point: (n, i, j) == (frame, slow_axis_pixel, fast_axis_pixel)
        :return: [x, y, z] in inverse Angstrom
        """
        q = self.detector_q(point)
        z = self.sample.transforms[point[0]][:3, :3]
        ub = 2 * np.pi * self.sample.ub_matrix

        inv_ub = np.linalg.inv(ub)
        inv_z = np.linalg.inv(z)

        hphi = np.dot(inv_z, q)
        return np.dot(inv_ub, hphi).T

    def hkl2q(self, hkl: tuple[float, float, float] | np.ndarray):
        """
        Returns wavecector direction for given hkl
        :param hkl: Miller indices, in units of reciprocal lattice vectors
        :return: Q position in inverse Angstroms
        """
        return self.sample.hkl2q(hkl)

    def plot_instrument(self, axes: Axes3D):
        instrument_name = get_dataset_value('name', self.instrument, 'no name')
        max_distance = max([np.linalg.norm(position) for position in self.component_positions.values()])
        max_position = max_distance * self.beam.direction

        axes.plot([-max_position[0], 0], [-max_position[2], 0], [-max_position[1], 0], 'k-')  # beam
        beam_cont = np.linalg.norm(self.detectors[0].position) * self.beam.direction
        axes.plot([0, beam_cont[0]], [0, beam_cont[2]], [0, beam_cont[1]], 'k:')  # continued beam
        # detectors
        for detector in self.detectors:
            pos = detector.position
            axes.plot([0, pos[0]], [0, pos[2]], [0, pos[1]], 'k-')  # scattered beam
        # components
        for component, position in self.component_positions.items():
            axes.plot(position[0], position[2], position[1], 'r+')
            axes.text(position[0], position[2], position[1], s=component)

        axes.set_xlabel('X [mm]')
        axes.set_ylabel('Z [mm]')
        axes.set_zlabel('Y [mm]')
        axes.set_title(f"Instrument: {instrument_name}")
        # ax.set_aspect('equalxz')

    def plot_wavevectors(self, axes: Axes3D):
        frames, ii, jj = self.shape()
        pixel_centre = (frames // 2, ii // 2, jj // 2)
        ki = self.beam.incident_wavevector
        detector_module = self.detectors[0].modules[0]
        kf = detector_module.pixel_wavevector(pixel_centre, self.beam.wl)
        q = kf - ki
        hkl = self.hkl(pixel_centre)

        axes.plot([-ki[0], 0], [-ki[2], 0], [-ki[1], 0], '-k')
        axes.plot([0, kf[0]], [0, kf[2]], [0, kf[1]], '-k')
        axes.plot([0, q[0]], [0, q[2]], [0, q[1]], '-r')

        wl = self.beam.wl
        for frame in range(frames):
            corners = np.vstack([
                detector_module.pixel_wavevector((frame, 0, 0), wl),  # module origin
                detector_module.pixel_wavevector((frame, ii, 0), wl),  # module origin + slow pixels
                detector_module.pixel_wavevector((frame, ii, jj), wl),  # o + slow + fast
                detector_module.pixel_wavevector((frame, 0, jj), wl),  # o + fast
                detector_module.pixel_wavevector((frame, 0, 0), wl),  # module origin
            ])
            axes.plot(corners[:, 0], corners[:, 2], corners[:, 1], '-k')
            corners_q = corners - ki
            axes.plot(corners_q[:, 0], corners_q[:, 2], corners_q[:, 1], '-r')

        # plot Reciprocal lattice
        astar, bstar, cstar = self.hkl2q(np.eye(3))
        axes.plot([0, astar[0]], [0, astar[2]], [0, astar[1]], '-g')
        axes.plot([0, bstar[0]], [0, bstar[2]], [0, bstar[1]], '-g')
        axes.plot([0, cstar[0]], [0, cstar[2]], [0, cstar[1]], '-g')
        axes.text(astar[0], astar[2], astar[1], s='a*')
        axes.text(bstar[0], bstar[2], bstar[1], s='b*')
        axes.text(cstar[0], cstar[2], cstar[1], s='c*')

        axes.set_xlabel('X')
        axes.set_ylabel('Z')
        axes.set_zlabel('Y')
        axes.set_title(f"Wavevectors\nHKL: {hkl}")
        axes.set_aspect('equal')

    def plot_hkl(self, axes: Axes3D):
        frames, ii, jj = self.shape()
        pixel_centre = (frames // 2, ii // 2, jj // 2)
        hkl = self.hkl(pixel_centre)
        for frame in range(frames):
            corners = np.vstack([
                self.hkl((frame, 0, 0)),  # module origin
                self.hkl((frame, ii, 0)),  # module origin + slow pixels
                self.hkl((frame, ii, jj)),  # o + slow + fast
                self.hkl((frame, 0, jj)),  # o + fast
                self.hkl((frame, 0, 0)),  # module origin
            ])
            axes.plot(corners[:, 0], corners[:, 2], corners[:, 1], '-r')
        origin = self.hkl((0, 0, 0))
        axes.plot(origin[0], origin[2], origin[1], '+k')

        axes.set_xlabel('H')
        axes.set_ylabel('L')
        axes.set_zlabel('K')
        axes.set_title(f"HKL: {hkl}")
        axes.set_aspect('equal')

