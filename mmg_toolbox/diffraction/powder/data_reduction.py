from dataclasses import dataclass
import numpy as np
from mmg_toolbox import Experiment, metadata
from math import isclose
import logging
logger = logging.getLogger(__name__)
@dataclass
class PowderData():
    tth: float
    energy: float
    image: np.array

class PowderDataReduction():
    def __init__(self,data_folder: str, beamline:str="i10", scan_number:list[int]|None=None, keys: dict[str,str]|None=None):
        self.data_folder = data_folder
        self.beamline = beamline
        self.data: list[PowderData] = []
        self.keys = {
                "tth": "tthArea",
                "energy": "pgm_energy",
                "detector": "thpimte"
            } if keys is None else keys
        self.load_data()   
        
    def load_data(self, scan_number: list[int] | None = None):
        exp = Experiment(self.data_folder)
        scan_list = exp.scans(scan_number) if scan_number is not None else exp.scans()
        
        if not scan_list:
            return

        temp_images = []
        last_tth = scan_list[0](self.keys["tth"])

        for scan in scan_list:
            try:
                current_tth = scan(self.keys["tth"])
                
                if not isclose(current_tth, last_tth, abs_tol=1e-2):
                    self._process_angle(temp_images, last_tth, scan)
                    temp_images = []
                    last_tth = current_tth
                
                temp_images.append(scan(self.keys["detector"]))
                
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
        self.data.append(PowderData(
            tth=tth,
            energy=last_scan(self.keys["energy"]),
            image=final_image
        ))

    def detector_correction(self, image: np.array):
        # Placeholder for actual detector correction logic, e.g., flat-field correction, dark current subtraction, etc.
        return image
    def write_output(self, output_folder: str):
        pass