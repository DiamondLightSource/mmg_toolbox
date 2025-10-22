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
        f.write(f"# {os.path.basename(script_path)[:-3]}\n\n")
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
                md_group_files.append(os.path.relpath(md_filename, docs_dir + '/..'))
                write_markdown(md_filename, full_path, root_dir)
        return md_group_files
    md_files = _recursor(root_dir)
    print(f"\nUpdating {yaml_file} with:\n{md_files}")
    update_yaml_code_description(yaml_file, *md_files)


if __name__ == '__main__':
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'mmg_toolbox'))
    docs = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'docs', 'description'))
    yaml = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'mkdocs.yml'))
    print(root, os.path.isdir(root))
    print(docs, os.path.isdir(docs))
    print(yaml, os.path.isfile(yaml))
    create_md_files(root, docs, yaml)