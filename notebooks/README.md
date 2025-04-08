# MMG Autoprocessing Jupyter Notebooks

### List of notebooks

| Name                  | Description |
|-----------------------|-------------|
| xas_notebook.ipynb    | xas         |
| xmcd_processor.ipynb  | blah        |

### Location of notebooks
/dls_sw/i06/scripts/gda-zocalo/notebooks

### Autoprocessing pipeline

1. Dawn-Consumer service running on control PC (start IOC in Hardware status screen in EPICS)
2. User starts scan
2. Scan finishes, GDA sends message
3. GDA-Zocalo-Connector (via Dawn-Consumer) captures message
   1. Creates scan database entry in ispyb, including metadata and plot
   2. start autoprocessing step, running on kubernetes client
6. Results available in ispyb and notebooks in visit/processed.

