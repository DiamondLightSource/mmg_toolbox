import h5py
import numpy as np
from matplotlib import pyplot as plt

from mmg_toolbox import nexus_names as nn
from mmg_toolbox.nexus_functions import nx_find, get_dataset_value
from mmg_toolbox.nexus_transformations import nx_direction, nx_transformations_max_size, \
    nx_transformations_matrix, nx_transform_vector
from mmg_toolbox.rotations import norm_vector, transform_by_t_matrix
from mmg_toolbox.xray_utils import wavevector, photon_energy, photon_wavelength, bmatrix


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
            dataset = self.beam[nn.NX_WL]
            units = dataset.attrs.get(nn.NX_UNITS, b'nm').decode()
            wl = dataset[()]
            if units == 'nm':
                wl = 10 * wl  # wavelength in Angstroms
            return photon_energy(wl), wl
        elif nn.NX_EN in self.beam:
            dataset = self.beam[nn.NX_WL]
            units = dataset.attrs.get(nn.NX_UNITS, b'ev').decode()
            en = dataset[()]
            if units.lower() == 'ev':
                en = en / 1000.  # wavelength in keV
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

    def hkl2q(self, hkl: tuple[float, float, float] | np.ndarray):
        """
        Returns wavecector direction for given hkl
        :param hkl: Miller indices, in units of reciprocal lattice vectors
        :return: Q position in inverse Angstroms
        """
        hkl = np.reshape(hkl, (-1, 3))
        z = self.transforms[0][:3, :3]
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

    def shape(self):
        """
        Return scan shape of module
            (n, i, j)
        Where:
            n = frames in scan
            i = pixels along slow axis
            j = pixels along fast axis
        """
        return self.size, self.data_size[0], self.data_size[1]

    def pixel_wavevector(self, point: tuple[int, int, int], wavelength_a) -> np.ndarray:
        """
        Return wavevector of pixel
        :param point: (n, i, j) == (frame, slow_axis_pixel, fast_axis_pixel)
        :param wavelength_a: wavelength in Angstrom
        :return: [dx, dy, dz] unit vector
        """
        return wavevector(wavelength_a) * self.pixel_direction(point)

    def pixel_direction(self, point: tuple[int, int, int]) -> np.ndarray:
        """
        Return direction of pixel
        :param point: (n, i, j) == (frame, slow_axis_pixel, fast_axis_pixel)
        :return: [dx, dy, dz] unit vector
        """
        return norm_vector(self.pixel_position(point))

    def pixel_position(self, point: tuple[int, int, int]) -> np.ndarray:
        """
        Return position of pixel (n, i, j)
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


class NXScan:
    """
    NXScan object
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
        beam_obj = nx_find(self.sample_obj, nn.NX_BEAM)
        self.beam = NXBeam(beam_obj.name, hdf_file)

    def __repr__(self):
        return f"NXScan({self.file})"

    def shape(self):
        detector_module = self.detectors[0].modules[0]
        return detector_module.shape()

    def detector_q(self, point: tuple[int, int, int] = (0, 0, 0)):
        wavelength = self.beam.wl
        ki = self.beam.incident_wavevector
        detector_module = self.detectors[0].modules[0]
        kf = detector_module.pixel_wavevector(point, wavelength)
        return kf - ki

    def hkl(self, point: tuple[int, int, int] = (0, 0, 0)):
        q = self.detector_q(point)
        z = self.sample.transforms[-1][:3, :3]  #TODO: should this chain all transforms?
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

    def plot_instrument(self, figsize=[16, 6], dpi=100):
        fig = plt.figure(figsize=figsize, dpi=dpi)
        ax = fig.add_subplot(projection='3d')

        instrument_name = get_dataset_value('name', self.instrument, 'no name')
        max_distance = max([np.linalg.norm(position) for position in self.component_positions.values()])
        max_position = max_distance * self.beam.direction

        ax.plot([-max_position[0], 0], [-max_position[2], 0], [-max_position[1], 0], 'k-')  # beam
        beam_cont = np.linalg.norm(self.detectors[0].position) * self.beam.direction
        ax.plot([0, beam_cont[0]], [0, beam_cont[2]], [0, beam_cont[1]], 'k:')  # continued beam
        # detectors
        for detector in self.detectors:
            pos = detector.position
            ax.plot([0, pos[0]], [0, pos[2]], [0, pos[1]], 'k-')  # scattered beam
        # components
        for component, position in self.component_positions.items():
            ax.plot(position[0], position[2], position[1], 'r+')
            ax.text(position[0], position[2], position[1], s=component)

        ax.set_xlabel('X [mm]')
        ax.set_ylabel('Z [mm]')
        ax.set_zlabel('Y [mm]')
        ax.set_title(f"Instrument: {instrument_name}")
        # ax.set_aspect('equalxz')
        fig.show()

    def plot_wavevectors(self, figsize=[16, 6], dpi=100):
        fig = plt.figure(figsize=figsize, dpi=dpi)
        ax = fig.add_subplot(projection='3d')

        pixel_centre = tuple([i // 2 for i in self.shape()])
        ki = self.beam.incident_wavevector
        detector_module = self.detectors[0].modules[0]
        kf = detector_module.pixel_wavevector(pixel_centre, self.beam.wl)
        q = kf - ki

        ax.plot([-ki[0], 0], [-ki[2], 0], [-ki[1], 0], '-k')
        ax.plot([0, kf[0]], [0, kf[2]], [0, kf[1]], '-k')
        ax.plot([0, q[0]], [0, q[2]], [0, q[1]], '-r')

        shape = self.shape()
        wl = self.beam.wl
        for frame in range(shape[0]):
            corners = np.vstack([
                detector_module.pixel_wavevector((frame, 0, 0), wl),  # module origin
                detector_module.pixel_wavevector((frame, shape[1], 0), wl),  # module origin + slow pixels
                detector_module.pixel_wavevector((frame, shape[1], shape[2]), wl),  # o + slow + fast
                detector_module.pixel_wavevector((frame, 0, shape[2]), wl),  # o + fast
                detector_module.pixel_wavevector((frame, 0, 0), wl),  # module origin
            ])
            ax.plot(corners[:, 0], corners[:, 2], corners[:, 1], '-k')
            corners_q = corners - ki
            ax.plot(corners_q[:, 0], corners_q[:, 2], corners_q[:, 1], '-r')

        # plot Reciprocal lattice
        astar, bstar, cstar = self.hkl2q(np.eye(3))
        ax.plot([0, astar[0]], [0, astar[2]], [0, astar[1]], '-g')
        ax.plot([0, bstar[0]], [0, bstar[2]], [0, bstar[1]], '-g')
        ax.plot([0, cstar[0]], [0, cstar[2]], [0, cstar[1]], '-g')
        ax.text(astar[0], astar[2], astar[1], s='a*')
        ax.text(bstar[0], bstar[2], bstar[1], s='b*')
        ax.text(cstar[0], cstar[2], cstar[1], s='c*')

        ax.set_xlabel('X')
        ax.set_ylabel('Z')
        ax.set_zlabel('Y')
        ax.set_title(f"Wavevectors\nHKL: {self.hkl(pixel_centre)}")
        ax.set_aspect('equal')
        fig.show()

    def plot_hkl(self, figsize=[16, 6], dpi=100):
        fig = plt.figure(figsize=figsize, dpi=dpi)
        ax = fig.add_subplot(projection='3d')

        shape = self.shape()
        pixel_centre = tuple([i // 2 for i in shape])
        for frame in range(shape[0]):
            corners = np.vstack([
                self.hkl((frame, 0, 0)),  # module origin
                self.hkl((frame, shape[1], 0)),  # module origin + slow pixels
                self.hkl((frame, shape[1], shape[2])),  # o + slow + fast
                self.hkl((frame, 0, shape[2])),  # o + fast
                self.hkl((frame, 0, 0)),  # module origin
            ])
            ax.plot(corners[:, 0], corners[:, 2], corners[:, 1], '-r')
        origin = self.hkl((0, 0, 0))
        ax.plot(origin[0], origin[2], origin[1], '+k')

        ax.set_xlabel('H')
        ax.set_ylabel('L')
        ax.set_zlabel('K')
        ax.set_title(f"HKL: {self.hkl(pixel_centre)}")
        ax.set_aspect('equal')
        fig.show()
