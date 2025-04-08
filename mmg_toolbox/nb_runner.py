"""
Jupyter notebook runner

From /dls_sw/i16/software/python/jupyter_processor/jproc.py
"""

"""
Jupyter Notebook Processor

Copy a notebook, switch the filename in the first cell, process the notebook
and export a html.

Command line operation:
$ module load python/3
$ python jproc.py some/processing/notebook.ipynb some/nexus/file.nxs

Script operation:
    from jproc import process_notebook
    process_notebook('some/processing/notebook.ipynb', 'some/nexus/file.nxs')

The first argument ('processing-notebook.ipynb') can take several shortcuts:
    'scan': scan processor file
    'mapper': msmapper processor file

By Dan Porter
Beamline I16
Diamond Light Source Ltd
16/2/2022
"""

import os
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
from nbconvert import HTMLExporter

from .env_functions import run_command, TMPDIR


def read_notebook(filename: str) -> nbformat.NotebookNode:
    return nbformat.read(filename, as_version=4)


def save_notebook(nb: nbformat.NotebookNode, filename: str):
    with open(filename, 'w', encoding='utf-8') as f:
        nbformat.write(nb, f)


def add_code_cell(nb: nbformat.NotebookNode, source: str, index=-1):
    # cell = {
    #     'cell_type': "code",
    #     'execution_count': None,
    #     'metadata': {},
    #     'outputs': [],
    #     'source': source,
    # }
    cell = nbformat.v4.new_code_cell(source)
    nb.cells.insert(index, cell)


def add_inpath(nb: nbformat.NotebookNode, filename: str):
    """Add inpath=filename to top of notebook"""
    code = f"inpath = '{filename}'"
    first_cell = next(iter(nb.cells), {})
    first_cell_type = first_cell.get('cell_type', '')
    first_cell_source = first_cell.get('source', '')
    if first_cell_type == 'code' and 'inpath' in first_cell_source:
        # replace contents of cell
        first_cell['source'] = code
    else:
        # add a new cell
        add_code_cell(nb, code, index=0)


def html_processor(nb: nbformat.NotebookNode) -> tuple[str, dict]:
    """
    Process notebook and return (html, resources)
    """
    processor = ExecutePreprocessor()
    html_exporter = HTMLExporter()
    print('\n'.join(str(cell) for cell in nb.cells))
    processor.preprocess(nb, resources={'metadata': {}})
    return html_exporter.from_notebook_node(nb)


def process_template(template: str, nexus_filename: str, output_folder: str | None = None) -> tuple[str, str]:
    """
    Process jupyter notebook
    """
    nb = read_notebook(template)
    add_inpath(nb, nexus_filename)

    if output_folder is None:
        output_folder = TMPDIR
    out_name, ext = os.path.splitext(output_folder)
    if ext:
        out_html = out_name + '.html'
        out_pynb = out_name + '.ipynb'
    else:
        tmp_name, _ = os.path.splitext(os.path.basename(template))
        nxs_name, _ = os.path.splitext(os.path.basename(nexus_filename))
        out_name = f"{nxs_name}_{tmp_name}"
        out_html = os.path.join(output_folder, out_name + '.html')
        out_pynb = os.path.join(output_folder, out_name + '.ipynb')

    # run notebook
    (body, resources) = html_processor(nb)

    with open(out_html, 'w') as f:
        f.write(body)
    save_notebook(nb, out_pynb)
    print(f"Completed notebook, saved as: {out_pynb}")
    return out_pynb, out_html


def run_jupyter_notebook(notebook_filename: str):
    """
    Run a jupyter notebook
    """
    command = f"jupyter notebook {notebook_filename}"
    run_command(command)


def view_jupyter_notebook(notebook_filename: str):
    """
    Open a jupyter notebook.ipynb or .html file
    """
    if notebook_filename.endswith('.ipynb'):
        run_jupyter_notebook(notebook_filename)
    elif notebook_filename.endswith('.html'):
        import webbrowser
        webbrowser.open_new_tab(notebook_filename)