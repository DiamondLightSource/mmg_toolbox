from dataclasses import dataclass
import numpy as np
from mmg_toolbox import Experiment, metadata
from mmg_toolbox.nexus.nexus_scan import NexusScan
import pyFAI
from pyFAI.detectors import Detector
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
    def __init__(self, calibration_file: str, keys: PowderReductionKeys|None=None):
        self._data: list[PowderData] = []
        self.keys = PowderReductionKeys() if keys is None else keys
        self._data_folder = None
        self.result: tuple[np.array, np.array] | None = None
        if not os.path.exists(calibration_file):
            raise FileNotFoundError(f"Calibration file not found: {calibration_file}")
            
        self.base_ai = pyFAI.load(calibration_file)
        logger.info(f"Loaded calibration from {calibration_file} using {self.base_ai.detector.name}")
        
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
            raise ValueError("Data folder path not set."+
                            " Please provide a valid path by running load_data() with a data_folder argument."+
                            " Or set it directly using the setter.")
    def data_folder(self, value):
        if not os.path.exists(value):
            raise FileNotFoundError(f"Data folder not found: {value}")
        self._data_folder = value

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
    def reduces_images_to_1d(self, radial_range=(35, 155), tth_off:float=0.0,mask : np.array | None = None, oversampling=1)-> tuple[np.array, np.array]:
        if not self.data:
            raise ValueError("No data to reduce.")
        ais = []
        images = []
        
        for entry in self.data:
            local_ai = AzimuthalIntegrator(
                dist=self.base_ai.dist, 
                poni1=self.base_ai.poni1, 
                poni2=self.base_ai.poni2,
                rot1=self.base_ai.rot1,
                rot3=self.base_ai.rot3,
                detector=self.base_ai.detector,
                wavelength=0.123984193 / entry.energy
            )
            
            local_ai.rot2 = np.radians(-entry.tth+tth_off)
            
            ais.append(local_ai)
            images.append(entry.image)

        mg = MultiGeometry(ais, unit="2th_deg", radial_range=radial_range)
        pixel_size = self.base_ai.poni1
        dist = self.base_ai.dist
        
        npt = int(oversampling * np.deg2rad(max(radial_range) - min(radial_range)) / 
                  np.arctan2(pixel_size, dist))
        
        logger.info(f"Integrating {len(images)} images into {npt} bins.")

        self.result = mg.integrate1d(images, npt,lst_mask=mask)

        return self.result
    
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