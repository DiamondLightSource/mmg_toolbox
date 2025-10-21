"""
Jupyter Notebook commands
"""

from signal import pthread_kill, SIGTSTP
from threading import Thread
import subprocess
from notebook.app import launch_new_instance

THREADS = []
SUBPROCESSES = []

def launch_jupyter_notebook():
    jupyter_thread = Thread(target=launch_new_instance)
    jupyter_thread.start()
    THREADS.append(jupyter_thread)
    return jupyter_thread


def check_threads():
    for th in THREADS:
        if th.is_alive():
            print(f'thread {th} is alive')
        else:
            print(f'thread {th} is not alive')
    print('That is all')


def kill_thread(thread: Thread):
    if thread.is_alive():
        print(f'Killing {thread}', end=', ')
        pthread_kill(thread.ident, SIGTSTP)
        thread.join()
        print('Killed')
    else:
        print(f'Thread {thread} is not alive')


def launch_notebook_subprocess():
    command = 'jupyter notebook'
    output = subprocess.run(command, shell=True, capture_output=False)


def launch_notebook_popen():
    command = ['jupyter', 'notebook']
    output = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    SUBPROCESSES.append(output)


def check_notebook_servers() -> list[str]:
    list_servers = subprocess.run("jupyter server list", shell=True, capture_output=True)
    output = list_servers.stdout.decode()
    urls = [item for item in output.split() if item.startswith('http')]
    return urls

def launch_notebook_subprocess_thread():
    th = Thread(target=launch_notebook_subprocess)
    th.start()
    THREADS.append(th)


if __name__ == '__main__':
    from time import sleep
    # print('Launching Jupyter Notebook')
    # launch_jupyter_notebook()
    # print('Started in thread')
    # sleep(10)
    # check_threads()
    # sleep(60)
    # for my_thread in THREADS:
    #     kill_thread(my_thread)

    # launch_new_instance()
    # launch_notebook_subprocess()

    # print('Launching Jupyter Notebook')
    # launch_notebook_subprocess_thread()
    # print('Started in thread')
    # sleep(10)
    # check_threads()
    # sleep(60)
    # for my_thread in THREADS:
    #     kill_thread(my_thread)

    print('Launching Jupyter Notebook')
    # launch_notebook_popen()
    print('Started in open')
    for n in range(3):
        sleep(10)
        print(check_notebook_servers())

    for proc in SUBPROCESSES:
        print(f"killing {proc}")
        proc.terminate()
        SUBPROCESSES.remove(proc)

    print('finished')
