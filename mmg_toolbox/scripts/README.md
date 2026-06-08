# How Scripts Work in mmg_toolbox

Files in mmg_toobox/scripts are templates for automatic generation, additional metadata will be added 
to them during deployment. Additional metadata is given in double brackets *{{name}}*, where **name**
is a predefined term given in [scripts.py](scripts.py) in the constants container `R`. 

Scripts and notebooks are deployed using the function `create_script` and `create_notebook`, for example:

```python
from mmg_toolbox.scripts import create_script, create_notebook, R, list_templates

print(list_templates())

template = {
    # {{template}}: replacement
    R.beamline: 'i16',
    R.description: 'a short description',
    R.filepaths: "'file1.nxs', 'file2.nxs', 'file3.nxs'",
    R.exp: 'path/to/dir',
    R.scanno: '-1',
    R.scannos: 'range(-10, 0)',
    R.title: 'a nice plot',
    R.xaxis: 'axes',
    R.yaxis: 'signal',
    R.value: 'sample_temperature?(300)'
}

create_script('path/of/my_script.py', 'example', **template)

create_notebook('path/of/my_notebook.ipynb', 'example', **template)
```

## Template Names

| Name          | Replace            | type     | Description                                             |
|---------------|--------------------|----------|---------------------------------------------------------|
| R.date        | {{date}}           | str      | The current date (added automatically by create_script) |
| R.beamline    | {{beamline}}       | str      | The beamline name                                       |
| R.description | {{description}}    | str      | Description of the script or notebook                   |
| R.filepaths   | {{filepaths}}      | str list | list of filepaths like `['file1.nxs', 'file2.nxs']`     |
| R.exp         | {{experiment_dir}} | str      | experiment directory (location of files)                |
| R.proc        | {{processing_dir}} | str      | processing directory (where to save results)            |
| R.scanno      | {{scan_number}}    | int      | single scan number                                      |
| R.scannos     | {{scan_numbers}}   | list     | list of scan numbers                                    |
| R.title       | {{title}}          | str      | title for plots                                         |
| R.xaxis       | {{x-axis}}         | str      | default x-axis for plots, as hdfmap name                |
| R.yaxis       | {{y-axis}}         | str      | default y-axis for plots, as hdfmap name                |
| R.value       | {{value}}          | str      | parameter to plot against like temperature or field     |

