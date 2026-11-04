import os
import ast
from pathlib import Path
from shutil import copyfile
from ruamel.yaml import YAML

# any paths in IGNORE will not be generated in docs
IGNORE = [
    'scripts'
]

DOCS = Path(__file__).parent
ROOT = DOCS.parent
SRC = ROOT / 'mmg_toolbox'

NOTEBOOKS = {
    # NAME: FILENAME
    'UB Matrices': 'notebook_i16_ub_matrix.ipynb',
    'MultiPeakFit': 'example_multipeakfit.ipynb',
    'ROI Peak Fitting': 'example_roi_peak_fitting.ipynb',
    'XMCD': 'example_xmcd.ipynb',
}

# Function to check if a directory is a Python package
def is_package(dir_path):
    return os.path.isfile(os.path.join(dir_path, '__init__.py'))


def update_yaml_code_description(yaml_file: str, *description_files: str):
    yaml = YAML()
    yaml.preserve_quotes = True

    with open(yaml_file, 'r') as f:
        yml_obj = yaml.load(f)

    nav = yml_obj['nav']
    i = next((n for n, obj in enumerate(nav) if isinstance(obj, dict) and 'Code Description' in obj))
    nav[i]['Code Description'] = ['description/index.md'] + list(description_files)

    with open(yaml_file, 'w') as f:
        yaml.dump(yml_obj, f)


def write_markdown(md_filename: str, script_path: str, package_path: str):
    rel_path = os.path.relpath(script_path, package_path + '/..')
    package_name = rel_path.replace(os.sep, '.')[:-3]
    with open(md_filename, 'w', encoding='utf-8') as f:
        f.write(f"# {os.path.basename(script_path)[:-3]}\n\n")
        f.write(f"::: {package_name}\n")
    print('Writing markdown file:', md_filename)


def create_md_files(root_dir: str, docs_dir: str, yaml_file: str ='mkdocs.yml'):

    def _recursor(top_dir: str) -> list[dict | str]:
        md_group_files = []
        for path in os.listdir(top_dir):
            full_path = os.path.join(top_dir, path)
            rel_path = os.path.relpath(full_path, root_dir)
            if rel_path in IGNORE:
                print('Ignoring', rel_path)
                continue
            if os.path.isdir(full_path):
                group = _recursor(full_path)
                if group:
                    md_group_files.append({path: group})
            elif os.path.isfile(full_path) and path.endswith('.py') and not path.startswith('_'):
                md_filename = f"{docs_dir}/{rel_path.replace(os.path.sep, '_')[:-3]}.md"
                md_group_files.append(os.path.relpath(md_filename, docs_dir + '/..'))
                write_markdown(md_filename, full_path, root_dir)
        return md_group_files
    md_files = _recursor(root_dir)
    print(f"\nUpdating {yaml_file} with:\n{md_files}")
    update_yaml_code_description(yaml_file, *md_files)


def create_examples_index_md(examples_dir: str, examples_file: str, examples_site_url: str):
    """Write a table in the examples markdown file"""

    examples_files = [
        os.path.join(examples_dir, file)
        for file in os.listdir(examples_dir)
        if file.endswith('.py') and file.startswith('example_')
    ]

    def get_doc_string(path: str) -> str:
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()
        module = ast.parse(text, filename=os.path.basename(path))
        doc = ast.get_docstring(module)
        if doc:
            line = ' '.join([ss for s in doc.splitlines() if s and (ss := s.strip())][:2])
            return line.replace('mmg_toolbox example ', '')
        return ''

    names_strings = [
        (os.path.relpath(path, examples_dir), get_doc_string(path))
        for path in examples_files
    ]

    table = "| Filename | Description |\n| --- | --- |\n"
    for filename, docstring in names_strings:
        table += f"| [{filename}]({examples_site_url}{filename}) | {docstring} |\n"
    table += "\n"

    markdown = "# Examples\n\nExample files listed in the examples directory:\n\n"
    markdown += table

    print(markdown)

    with open(examples_file, 'w', encoding='utf-8') as f:
        f.write(markdown)
    print('Overwriting examples markdown file:', examples_file)


def update_yaml_examples_notebooks(yaml_file: str, notebooks: dict[str, str]):
    _yaml = YAML()
    _yaml.preserve_quotes = True

    with open(yaml_file, 'r') as f:
        yml_obj = _yaml.load(f)

    nav = yml_obj['nav']
    i = next((n for n, obj in enumerate(nav) if isinstance(obj, dict) and 'Examples' in obj))

    # Link files in Examples folder
    docs_examples_dir = DOCS / 'examples'
    examples_dir = ROOT / 'examples'

    notebook_paths = []
    for name, filename in notebooks.items():
        # Find notebook
        docs_file = docs_examples_dir / filename
        if docs_file.is_file():
            print(f"Found {filename} in {docs_examples_dir}")
            notebook_paths.append({name: str(docs_file)})
        elif (examples_dir / filename).is_file():
            copyfile(examples_dir / filename, docs_file)
            print(f"Copied {filename} to {docs_examples_dir}")
            notebook_paths.append({name: str(docs_file)})
    nav[i]['Examples'].extend(notebook_paths)

    with open(yaml_file, 'w') as f:
        _yaml.dump(yml_obj, f)


if __name__ == '__main__':
    docs = DOCS / 'description'
    examples = ROOT / 'examples'
    examples_docs = DOCS / 'examples/index.md'
    yaml = ROOT / 'mkdocs.yml'
    examples_url = 'https://github.com/DiamondLightSource/mmg_toolbox/blob/main/examples/'
    print(ROOT, ROOT.is_dir())
    print(DOCS, DOCS.is_dir())
    print(yaml, yaml.is_file())
    create_md_files(str(SRC), str(docs), str(yaml))
    # create examples file
    create_examples_index_md(str(examples), str(examples_docs), examples_url)
    # copy notebook files & update examples yaml
    update_yaml_examples_notebooks(str(yaml), NOTEBOOKS)

