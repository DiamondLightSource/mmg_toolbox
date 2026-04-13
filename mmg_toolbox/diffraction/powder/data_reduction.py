from dataclasses import dataclass
import numpy as np
from mmg_toolbox import Experiment, metadata
from mmg_toolbox.nexus.nexus_scan import NexusScan
import pyFAI
import numpy.typing as npt
from pyFAI.integrator.azimuthal import AzimuthalIntegrator
from math import isclose
import logging
import fabio
import os
from pyFAI.multi_geometry import MultiGeometry
logger = logging.getLogger(__name__)
@dataclass
class PowderData():
    tth: float
    energy: float
    image: np.array
    scan_number: int
@dataclass
class PowderReductionKeys():
    tth: str = "tthArea"
    energy: str = "pgm_energy"
    detector: str = "thpimte"

class PowderDataReduction():
    def __init__(self, calibration:str | dict[float, str], keys: PowderReductionKeys|None=None):
        self._data: list[PowderData] = []
        self.keys = PowderReductionKeys() if keys is None else keys
        self._data_folder = None
        self.result: tuple[np.array, np.array] | None = None
        self.cali_map:dict[float, AzimuthalIntegrator] | None = None
        if isinstance(calibration, dict):
            for angle, path in calibration.items():
                if not os.path.exists(path):
                    raise FileNotFoundError(f"Calibration file for {angle} not found: {path}")
                self.cali_map[angle] = pyFAI.load(path)
            self.base_ai = list(self.cali_map.values())[0]
            logger.info(f"Loaded {len(self.cali_map)} calibration files.")
        else:
            if not os.path.exists(calibration):
                raise FileNotFoundError(f"Calibration file not found: {calibration}")
            self.base_ai = pyFAI.load(calibration)
            self.cali_map = None # Single calibration mode
            logger.info(f"Loaded single calibration from {calibration}")
        
    @property
    def data(self):
        if not self._data:
            raise ValueError("No data loaded. Please run load_data() first.")
        return self._data
    @data.setter
    def data(self, value):        
        self._data.append(value)
    
    @property
    def data_folder(self):
        if self._data_folder is None:
            raise ValueError("Data folder path not set. Please provide a valid path.")
        return self._data_folder
    @data_folder.setter
    def data_folder(self, value):
        if not os.path.exists(value):
            raise FileNotFoundError(f"Data folder not found: {value}")
        self._data_folder = value


    def _get_best_ai(self, target_tth: float) -> AzimuthalIntegrator:
        """Helper to find the closest PONI file if multiple are provided."""
        if self.cali_map is None:
            return self.base_ai
        best_angle = min(self.cali_map.keys(), key=lambda x: abs(x - target_tth))
        if not isclose(best_angle, target_tth, abs_tol=1):
            logger.warning(f"No exact PONI for {target_tth}deg. Using closest: {best_angle}deg")
        return self.cali_map[best_angle]
    
    def load_data(self, scan_number: list[int] | None = None, data_folder: str|None = None,  beamline: str | None = None):
        """
        Loads data from a specific folder.
        """
        if data_folder is not None:
            self.data_folder = data_folder
        self._data = []
        exp = Experiment(self.data_folder, instrument=beamline)
        scan_list = exp.scans(scan_number) if scan_number is not None else exp.scans()
        
        if not scan_list:
            logger.warning(f"No scans found in {data_folder}")
            return

        temp_images = []
        last_tth = scan_list[0](self.keys.tth)

        for scan in scan_list:
            try:
                current_tth = scan(self.keys.tth)
                
                if not isclose(current_tth, last_tth, abs_tol=1e-2):
                    self._process_angle(temp_images, last_tth, scan)
                    temp_images = []
                    last_tth = current_tth
                
                temp_images.append(scan(self.keys.detector))
                
            except KeyError as e:
                logger.warning(f"Scan {scan.scan_number} missing key {e}. Skipping.")

        if temp_images:
            self._process_angle(temp_images, last_tth, scan_list[-1])

    def _process_angle(self, images: list[np.array], tth: float, last_scan: NexusScan):
        avg_image = np.mean(images, axis=0)
        try:
            count_time = float(last_scan(metadata.cmd).split()[-1])
        except (ValueError, IndexError):
            logger.warning(f"Could not extract count time from command: {last_scan(metadata.cmd)}. Defaulting to 1.0s.")
            count_time = 1.0
            
        normalized_image = avg_image / count_time
        final_image = normalized_image
        self.data = PowderData(
            tth=tth,
            energy=last_scan(self.keys.energy),
            image=final_image,
            scan_number=last_scan.scan_number()
        )
    def reduces_images_to_1d(self, radial_range=(35, 155), detector_centre: tuple[int, int]|None = None, tth_off:float=0.0, mask : npt.NDArray| None = None, oversampling=1)-> tuple[np.array, np.array]:
        if not self.data:
            raise ValueError("No data to reduce.")
        ais = []
        images = []
        if detector_centre is not None:
            self.set_beam_center_pixels(*detector_centre)        
        for entry in self.data:
            source_ai = self._get_best_ai(entry.tth)
            local_ai = AzimuthalIntegrator(
                dist=source_ai.dist, 
                poni1=source_ai.poni1, 
                poni2=source_ai.poni2,
                rot1=source_ai.rot1,
                rot3=source_ai.rot3,
                detector=source_ai.detector,
                wavelength=1.23984193e-6 / entry.energy
            )
            if detector_centre is not None:
                self.set_beam_center_pixels(*detector_centre) 

            sign = 1 if self.base_ai.rot2 >= 0 else -1 # Determine sign based on the original calibration's rot2
            local_ai.rot2 = np.radians(sign*entry.tth+tth_off)
            
            ais.append(local_ai)
            images.append(entry.image)

        mg = MultiGeometry(ais, unit="2th_deg", radial_range=radial_range)
        pixel_size = self.base_ai.detector.pixel1
        dist = self.base_ai.dist
        
        angular_range_rad = np.deg2rad(max(radial_range) - min(radial_range))
        pixel_angular_width = np.arctan2(pixel_size, dist)
        npt = int(oversampling * angular_range_rad / pixel_angular_width)
        logger.info(f"Integrating {len(images)} images into {npt} bins.")

        self.result = mg.integrate1d(images, npt,lst_mask=mask)

        return self.result
    
    def set_beam_center_pixels(self, pixel1: int, pixel2: int):

        p1_metres = pixel1 * self.base_ai.detector.pixel1
        p2_metres = pixel2 * self.base_ai.detector.pixel2
        self.base_ai.poni1 = p1_metres
        self.base_ai.poni2 = p2_metres
        logger.info(f"Updated beam center to pixels ({pixel1}, {pixel2}) -> ({p1_metres:.4f} m, {p2_metres:.4f} m)")

    def write_output(self, output_folder: str, sample_name: str| None = None):
        """
        Saves corrected 2D TIFFs and the stitched 1D result.
        """
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            logger.info(f"Created directory: {output_folder}")

        if sample_name is None:
            sample_name = f"sample_{self.data[0].scan_number}"
        # 1. Save the individual corrected 2D images
        for entry in self.data:
            filename = f"{sample_name}_corrected_E{entry.energy:.1f}eV_tth{entry.tth:.2f}.tiff"
            filepath = os.path.join(output_folder, filename)
            tif_image = fabio.tifimage.TifImage(data=entry.image.astype(np.float32))
            tif_image.header["Energy"] = str(entry.energy)
            tif_image.header["TwoTheta"] = str(entry.tth)
            tif_image.header["ScanNumber"] = str(entry.scan_number)
            
            tif_image.write(filepath)
            logger.info(f"Saved 2D: {filepath}")

        if self.result is not None:
            tth, intensity = self.result
            energy_val = self.data[0].energy
            dat_filename = f"{sample_name}_stitched_E{energy_val:.1f}eV.dat"
            dat_path = os.path.join(output_folder, dat_filename)
            
            # Save as two-column ASCII
            header = f"Stitched Powder Pattern\nEnergy: {energy_val} eV\nColumns: Two-Theta (deg), Intensity"
            np.savetxt(dat_path, np.column_stack((tth, intensity)), header=header)
            logger.info(f"Saved 1D result: {dat_path}")