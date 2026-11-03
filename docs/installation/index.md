# Installation

mmg_toolbox is available through most modern package repositories, including PyPi and conda-forge, 
although the latest version can always be installed directly from GitHub.

*Requires:* Python >=3.10, Numpy, h5py, scipy, matplotlib and others

For full dependencies list including optional dependencies, see [pyproject.toml](../../pyproject.toml)


=== "PyPi"

    ### pip installation
    ```bash
    pip install mmg_toolbox
    ```
    Or for full installation:
    ```bash
    pip install mmg_toolbox[full]
    ```

=== "GitHub"

    ### pip installation from latest GitHub repo
    ```bash
    python -m pip install --upgrade git+https://github.com/DiamondLightSource/mmg_toolbox.git
    ```

=== "Conda"

    ### Install in your environment
    ```bash
    conda activate your_env
    conda install mmg_toolbox
    ```

    ### Full installation of Python environment using conda miniforge
    See [conda-forge](https://github.com/conda-forge/miniforge)
    #### Install miniforge (any conda env will do)
    ```bash
    cd location/of/miniforge
    curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
    bash Miniforge3-Linux-x86_64.sh
    ```
    You will be asked to enter the location to install conda and whether to change terminal commands [yes]. 
    
    #### Install MMG_Toolbox
    Then, in a new terminal:
    ```bash
    conda env create -f https://raw.githubusercontent.com/DiamondLightSource/mmg_toolbox/main/environment.yml
    conda activate mmg_toolbox
    (mmg_toolbox)$ python -m pip install--upgrade git+https://github.com/DiamondLightSource/mmg_toolbox.git
    ```

=== "UV"

    ### Install in UV virtual environment
    ```bash
    uv add mmg_toolbox
    ```

    ### Full installation of UV and virtual env
    ```bash
    # install uv
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # create venv
    cd /loc/of/project
    uv venv --python 3.14
    # install packages (full installation with additional packages like pytest and jupyter)
    uv add mmg_toolbox[dev]
    # activate venv
    source .venv/bin/activate
    ```