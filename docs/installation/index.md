# Installation

Currently, the mmg_toolbox module can only be installed manually. PyPi integration will come later.

*Requires:* Python >=3.10, Numpy, h5py, matplotlib and others


=== "PyPi"

    ### pip installation
    ```bash
    pip install mmg_toolbox
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
    python -m pip install mmg_toolbox
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