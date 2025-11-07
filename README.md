[![PyPI](https://img.shields.io/pypi/v/dls-dodal.svg)](https://pypi.org/project/mmg_toolbox)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![](https://img.shields.io/github/forks/DiamondLightSource/mmg_toolbox?label=GitHub%20Repo&style=social)](https://github.com/DiamondLightSource/mmg_toolbox)

# mmg_toolbox
Repository for useful python data analysis functions for the Diamond Magnetic Materials Group


Source          | <https://github.com/DiamondLightSource/mmg_toolbox>
:---:           | :---:
PyPI            | `pip install mmg_toolbox`
Documentation   | <https://diamondlightsource.github.io/mmg_toolbox>
Releases        | <https://github.com/DiamondLightSource/mmg_toolbox/releases>


### Installation
*Requires:* Python >=3.10, Numpy, h5py, matplotlib, hdfmap, nexus2srs
```bash
python -m pip install mmg_toolbox
```

### @DLS
mmg_toolbox is available via the module system:
```bash
$ module load mmg
(python)$ dataviewer
```

### Usage - DataViewer
Start the dataviewer from a terminal
```bash
$ dataviewer
```
Or, to open the data viewer in the current folder:
```bash
$ dataviewer .
```
Or, to open the file viewer for a specific file:
```bash
dataviewer path/to/file.nxs
```

### Usage - Scripting
mmg_toolbox contains many useful tools for data analysis in python scripts, for example:

```python
import matplotlib.pyplot as plt
from mmg_toolbox import Experiment

exp = Experiment('/path/to/files')

# list scans
all_scans = exp.all_scan_numbers()  # {scan_number: filename}
print('\n'.join(exp.scans_str(*all_scans)))

exp.plot(1108746, 1108747, 1108748)

scans = exp.scans(*range(-10, 0))
for scan in scans:
    scan.plot()
    axes, signal = scan.eval('axes, signal')
```

### Dataviewer
mmg_toolbox contains a tkinter based dataviewer for viewing data in NeXus files. Various plotting and processing 
capabilities are available.
![mmg_dataviewer](docs/images/mmg_dataviewer.png)


## Feedback
mmg_toolbox is still under development, so if you have any feedback, found any bugs or have any feature requests - 
please do let me know! 

