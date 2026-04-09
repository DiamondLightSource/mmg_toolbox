from dataclasses import dataclass
import numpy as np
from mmg_toolbox import Experiment, metadata
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
@dataclass
class PowderReductionKeys():
    tth: str = "tthArea"
    energy: str = "pgm_energy"
    detector: str = "thpimte"
@dataclass
class CalibratedDetectorParameters():
    dist: float
    poni1: float
    poni2: float
    rot1: float
    rot2: float
    rot3: float
    detector: Detector

def detecotor_factory(name: str)->Detector:
        """
        Factory method to create pyFAI detector objects.
        Add new detectors here as needed.
        """
        name = name.lower()
        
        if name == "pimte":
            return Detector(pixel1=13.5e-6, pixel2=13.5e-6, max_shape=(2048, 2048))
        else:
            return pyFAI.detector_factory(name)
        

def beamline_detector_calibration_parameters(detector_name: str) -> CalibratedDetectorParameters:
    if detector_name.lower() == "i10_pimte":
        return CalibratedDetectorParameters(
            dist=0.13395446278751685,
            poni1=1.3e-05,
            poni2=1.3e-05,
            rot1=-0.09992925693033612,
            rot2=0.0,
            rot3=-7.649832649358263e-05,
            detector = detecotor_factory("pimte")
        )

class PowderDataReduction():
    def __init__(self,data_folder: str, detector_name: str, keys: PowderReductionKeys|None=None):
        self.data_folder = data_folder
        self._data: list[PowderData] = []
        self.keys = PowderReductionKeys() if keys is None else keys
        self.beamlineCalibration = beamline_detector_calibration_parameters(detector_name)
        self.result: tuple[np.array, np.array] | None = None
        
    @property
    def data(self):
        if not self._data:
            raise ValueError("No data loaded. Please run load_data() first.")
        return self._data
    @data.setter
    def data(self, value):        
        self._data.append(value)
    

    def load_data(self, scan_number: list[int] | None = None, beamline: str | None = None):
        exp = Experiment(self.data_folder, instrument=beamline)
        scan_list = exp.scans(scan_number) if scan_number is not None else exp.scans()
        
        if not scan_list:
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

    def _process_angle(self, images, tth, last_scan):
        avg_image = np.mean(images, axis=0)
        try:
            count_time = float(last_scan(metadata.cmd).split()[-1])
        except (ValueError, IndexError):
            logger.warning(f"Could not extract count time from command: {last_scan(metadata.cmd)}. Defaulting to 1.0s.")
            count_time = 1.0
            
        normalized_image = avg_image / count_time
        final_image = self.detector_correction(normalized_image)
        self.data = PowderData(
            tth=tth,
            energy=last_scan(self.keys.energy),
            image=final_image
        )
    def reduces_images_to_1d_multigeo(self, radial_range=(35, 155), tth_off:float=0.0,mask : np.array | None = None, oversampling=1)-> tuple[np.array, np.array]:
        if not self.data:
            raise ValueError("No data to reduce.")
        ais = []
        images = []
        
        for entry in self.data:
            local_ai = AzimuthalIntegrator(
                dist=self.beamlineCalibration.dist, 
                poni1=self.beamlineCalibration.poni1, 
                poni2=self.beamlineCalibration.poni2,
                rot1=self.beamlineCalibration.rot1,
                rot3=self.beamlineCalibration.rot3,
                detector=self.beamlineCalibration.detector,
                wavelength=0.123984193 / entry.energy
            )
            
            local_ai.rot2 = np.radians(-entry.tth+tth_off)
            
            ais.append(local_ai)
            images.append(entry.image)

        mg = MultiGeometry(ais, unit="2th_deg", radial_range=radial_range)
        pixel_size = self.beamlineCalibration.poni1
        dist = self.beamlineCalibration.dist
        
        npt = int(oversampling * np.deg2rad(max(radial_range) - min(radial_range)) / 
                  np.arctan2(pixel_size, dist))
        
        logger.info(f"Integrating {len(images)} images into {npt} bins.")

        self.result = mg.integrate1d(images, npt,lst_mask=mask)

        return self.result
    
    def write_output(self, output_folder: str):
        """
        Saves corrected 2D TIFFs and the stitched 1D result.
        """
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            logger.info(f"Created directory: {output_folder}")

        # 1. Save the individual corrected 2D images
        for entry in self.data:
            filename = f"corrected_E{entry.energy:.1f}eV_tth{entry.tth:.2f}.tiff"
            filepath = os.path.join(output_folder, filename)
            tif_image = fabio.tifimage.TifImage(data=entry.image.astype(np.float32))
            tif_image.header["Energy"] = str(entry.energy)
            tif_image.header["TwoTheta"] = str(entry.tth)
            
            tif_image.write(filepath)
            logger.info(f"Saved 2D: {filepath}")

        if self.result is not None:
            tth, intensity = self.result
            energy_val = self.data[0].energy
            dat_filename = f"stitched_E{energy_val:.1f}eV.dat"
            dat_path = os.path.join(output_folder, dat_filename)
            
            # Save as two-column ASCII
            header = f"Stitched Powder Pattern\nEnergy: {energy_val} eV\nColumns: Two-Theta (deg), Intensity"
            np.savetxt(dat_path, np.column_stack((tth, intensity)), header=header)
            logger.info(f"Saved 1D result: {dat_path}")

    def detector_correction(self, image: np.array):
        """
        Placeholder for dark current / flat field. 
        Note: pyFAI's integrate1d handles 'Solid Angle' correction automatically.
        """
        return image