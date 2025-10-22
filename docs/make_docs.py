import os
from ruamel.yaml import YAML

# any paths in IGNORE will not be generated in docs
IGNORE = [
    'scripts'
]

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
        f.write(f"# {md_filename[:-3]}.py\n\n")
        f.write(f"::: {package_name}\n")
    print('Writing markdown file:', md_filename)


def create_md_files(root_dir: str, docs_dir, yaml_file='mkdocs.yml'):

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
                md_filename = f"{docs_dir}/{rel_path.replace('/', '_')[:-3]}.md"
                md_group_files.append(md_filename)
                write_markdown(md_filename, full_path, root_dir)
        return md_group_files
    md_files = _recursor(root_dir)
    print(f"\nUpdating {yaml_file} with:\n{md_files}")
    update_yaml_code_description(yaml_file, *md_files)


# Function to walk through the directory and generate markdown files
def generate_md_files(root_dir, docs_dir, yaml_file='mkdocs.yml'):
    md_files = []
    for current_path, dirs, files in os.walk(root_dir):
        if is_package(current_path):
            package_path = os.path.relpath(current_path, root_dir)
            # md_files.append(f"    {'  ' * package_path.count('/')}- {os.path.basename(current_path)}\n")
            md_group_files = []
            for file in (f for f in files if f.endswith('.py') and not f.startswith('_')):
                file_path = str(os.path.join(current_path, file))
                rel_path = os.path.relpath(file_path, root_dir + '/..')
                package_name = rel_path.replace(os.sep, '.')[:-3]
                md_file_path = os.path.relpath(file_path, root_dir)
                md_filename = f"{docs_dir}/{md_file_path.replace('/', '_').replace('.py', '.md')}"
                # md_files.append(f"    {'  ' * package_path.count('/')}  - {md_filename}\n")
                md_group_files.append(md_filename)
                # Write markdown content
                with open(md_filename, 'w', encoding='utf-8') as f:
                    f.write(f"# {file}\n\n")
                    f.write(f"::: {package_name}\n")
            if len(md_group_files) > 0:
                md_files.append({os.path.basename(current_path): md_group_files})

    update_yaml_code_description(yaml_file, *md_files)


if __name__ == '__main__':
    print(os.path.abspath('../mmg_toolbox'))
    # generate_md_files('../mmg_toolbox', 'description', '../mkdocs.yml')
    create_md_files('../mmg_toolbox', 'description', '../mkdocs.yml')