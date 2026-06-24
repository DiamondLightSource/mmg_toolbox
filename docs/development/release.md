# DevOps - Release a new version
**How to release a new version of mmg_toolbox**

The following steps must be completed.

## Prepare
1. Merge active+complete PRs into the main branch
2. Ensure all tests pass locally on a DLS computer (most tests require the DLS file system)
3. Update the version number and date in `mmg_toolbox/__init__.py`
4. Add any new packages or requirements to `pyproject.toml`
5. **sometimes**. Check versions of GitHub actions in `pypi-publish.yml`, upgrade if required.

## Release
1. At [GitHub](https://github.com/DiamondLightSource/mmg_toolbox), click *Releases* and *Draft New Release*
2. Create a new tag matching the version number, add details of the new features and changes, select *latest* and click *Release*.
3. Wait for the actions to complete successfully. This will publish the package to PyPI.

## Release at DLS
1. Pull the latest version: `cd /dls_sw/apps/mmg_toolbox/latest/mmg_toolbox&&git pull`
2. For a major version, create a new folder:
```bash
cd /dls_sw/apps/mmg_toolbox
mkdir 0.7
cd 0.7
git clone git@github.com:DiamondLightSource/mmg_toolbox.git --depth 1
cd /dls_sw/apps/Modules/modulefiles/mmg/
cp 0.6 0.7
nano 0.7  # update version numbers
```

## Update Workflows image
1. At [magnetic-materials-workflows](https://github.com/DiamondLightSource/magnetic-materials-workflows), click *Releases* and *Draft New Release*
2. Create a new tag, add details including the mmg_toolbox version number, select *latest* and click *Release*.
3. This will create a new set of images that can be used in Workflows.

