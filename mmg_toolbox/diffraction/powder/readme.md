# PowderDataReduction

A Python-based utility for processing and stitching multi-angle synchrotron powder diffraction data.
## 🚀 Features

* **Smart Calibration**: Supports a single `.poni` file or a dictionary mapping specific `.poni` files to detector angles.
* **Automatic Data Consolidation**: Groups scans by two-theta (`tth`) positions and averages frames at identical angles to boost Signal-to-Noise Ratio.
* **Flux Normalization**: Automatically normalizes detector counts by exposure time extracted directly from scan metadata.
* **Seamless Stitching**: Uses `pyFAI.multi_geometry` to merge disparate detector positions into a unified high-resolution 1D pattern.

## 📦 Requirements

To install all required packages, including the internal experimental tools:

```bash
pip install mmg_toolbox[powder]
```

## Usage

### 1. Single Calibration Mode
```python
from powder_reduction import PowderDataReduction

# Initialize with a single PONI file
reducer = PowderDataReduction(calibration="detector_calib.poni")

# Load scans 100 through 109 from the raw data directory
reducer.load_data(data_folder="./raw_data", scan_number=range(100, 110))

# Perform 1D integration with optional fine-tuning
tth, intensity = reducer.reduces_images_to_1d(
    radial_range=(35, 155),
    detector_centre=(1024, 1024), # Optional: manual center in pixels
    tth_off=0.01,                 # Optional: angular offset correction
    mask=my_mask_array,           # Optional: numpy boolean mask
    oversampling=1                # Optional: increase binning density
)

# Save processed 2D TIFFs and the final 1D .dat file
reducer.write_output(output_folder="./results", sample_name="Standard_Sample")
```
### 2. Single Calibration Mode
```python
# Map nominal motor angles to specific calibration files
calibrations = {
    35.0:  "calib_low_angle.poni",
    75.0:  "calib_mid_angle.poni",
    115.0: "calib_high_angle.poni"
}

reducer = PowderDataReduction(calibration=calibrations)
reducer.load_data(data_folder="./raw_data", scan_number=range(200, 250))
reducer.reduces_images_to_1d()
```

