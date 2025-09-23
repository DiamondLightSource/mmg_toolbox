"""
Jupyter Notebook commands
"""

from urllib.request import urlopen
import webbrowser
import subprocess

SUBPROCESSES = []


def popen_jupyter_server(cmd='notebook', directory: str | None = None, file: str | None = None):
    """
    Start a jupyter server quietly in the background.

    :param cmd: 'notebook' | 'lab'
    :param directory: None, or directory to start in
    :param file: None, or file to open
    """
    command = ['jupyter', cmd]
    if directory:
        command.append('--ServerApp.root_dir=' + directory)
    elif file:
        command.append(file)
    print(f"Running: {' '.join(command)}")
    output = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    SUBPROCESSES.append(output)


def check_notebook_servers() -> list[str]:
    list_servers = subprocess.run("jupyter server list", shell=True, capture_output=True)
    output = list_servers.stdout.decode()
    urls = [item for item in output.split() if item.startswith('http')]
    # Check urls exist
    for url in urls:
        try:
            with urlopen(url) as response:
                pass
        except OSError:
            urls.remove(url)
    print('Notebook Server URLs:')
    print(urls)
    return urls


def terminate_notebooks():
    subprocess.run("jupyter server stop", shell=True)


def launch_jupyter_notebook(cmd='notebook', directory: str | None = None, file: str | None = None):
    """
    Open a running jupyter server or launch one.

    :param cmd: 'notebook' | 'lab'
    :param directory: None, or directory to start in
    :param file: None, or file to open
    """
    running_notebooks = check_notebook_servers()
    if running_notebooks:
        webbrowser.open(running_notebooks[-1])
    else:
        popen_jupyter_server(cmd, directory, file)

