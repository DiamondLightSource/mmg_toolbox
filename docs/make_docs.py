import os

# Function to check if a directory is a Python package
def is_package(dir_path):
    return os.path.isfile(os.path.join(dir_path, '__init__.py'))


# Function to sanitize names for markdown files
def sanitize_filename(name):
    return name.replace('.', '_').replace('/', '_')


# Function to walk through the directory and generate markdown files
def generate_md_files(root_dir, docs_dir):
    yaml = "  - Code Description:\n    - description/index.md\n"
    for current_path, dirs, files in os.walk(root_dir):
        if is_package(current_path):
            package_path = os.path.relpath(current_path, root_dir)
            yaml += f"    {'  ' * package_path.count('/')}- {os.path.basename(current_path)}\n"
            for file in (f for f in files if f.endswith('.py') and not f.startswith('_')):
                file_path = os.path.join(current_path, file)
                rel_path = os.path.relpath(file_path, root_dir + '/..')
                package_name = rel_path.replace(os.sep, '.') if rel_path != '.' else os.path.basename(root_dir)
                md_filename = f"description/{file.replace('.py', '.md')}"
                yaml += f"    {'  ' * package_path.count('/')}  - {md_filename}\n"

                # Write markdown content
                with open(md_filename, 'w', encoding='utf-8') as f:
                    f.write(f"# {file}\n\n")
                    f.write(f"::: {package_name}\n")
    print('mkdocs.yml:\n')
    print(yaml)


if __name__ == '__main__':
    print(os.path.abspath('../mmg_toolbox'))
    generate_md_files('../mmg_toolbox', 'description')