# MMG Autoprocessing Jupyter Notebooks

Autoprocessing for MMG beamlines at Diamond Light Source is performed via [gda-zocalo-connector](https://gitlab.diamond.ac.uk/scisoft/beamlines/i20/gda-zocalo-connector).
Processing steps are defined in yaml files, mainly these run jupyter notebooks defined on
the file system and run in a specific python environment on the Module system. 
MMG autoprocessing notebooks are stored here and deployed onto the file system. 
All notebooks run in the mmg module:
```commandline
module load mmg
jupyter notebook notebook.ipynb
# OR
papermill notebook.ipynb output.ipynb -p inpath 12345.nxs -p outpath output.nxs
```

### List of notebooks

| Name                                 | Description                                                                  |
|--------------------------------------|------------------------------------------------------------------------------|
| xas_notebook.ipynb                   | analyse NXxas scan, subtract background and create output file               |
| xmcd_processor.ipynb                 | analyse dummy scan for scan numbers, subtract polarisations for XMCD or XMLD |
| msmapper_processor.ipynb             | Look for msmapper result and plot the hkl volume                             |
| i21_Image_Processing.ipynb           | I21 image processing pipeline                                                |
| nexus_processor.ipynb                | Default processor, displays data, generates .dat file                        |
| detector_calibration_processor.ipynb | I16 detector calibration for msmapper                                        |


### Location of notebooks
`/dls_sw/i06/scripts/gda-zocalo/notebooks`

### Autoprocessing pipeline

1. Dawn-Consumer service running on control PC (start IOC in Hardware status screen in EPICS)
2. User starts scan
2. Scan finishes, GDA sends message
3. GDA-Zocalo-Connector (via Dawn-Consumer) captures message
   1. Creates scan database entry in ispyb, including metadata and plot
   2. start autoprocessing step, running on kubernetes client. Process found at:
      1. processor classes defined by factory in gda-zocalo-connector/processors/__init__.py
      2. processors.yaml in gda-zocalo-connector/processors
      2. processors.yaml pointed to in gda-zocalo-connector/beamlines.yaml
6. Results available in ispyb and notebooks in visit/processed.


### Deploying Notebooks to beamlines

1. Make and commit changes to ipynb notebook
2. Ensure notebook passes tests
2. Ensure notebook completes in current python environment
3. Ensure notebook completes in module load mmg
4. Copy notebook from notebooks to `/dls_sw/i06/scripts/gda-zocalo/notebooks`

#### Or

1. Run `deploy_zocalo_processors.py`


### Creating new Processors

1. Create notebook here, add tests to tests/test_notebooks.py
2. Add section to `deplpy_zocalo_processors.py`
3. Run deploy script.
2. Add an entry to `/dls_sw/i06/scripts/gda-zocalo/notebooks/processors.yaml`
