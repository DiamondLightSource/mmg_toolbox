# XAS and XMCD/XMLD Analysis

*mmg_toolbox* contains some useful tools for analysis of XAS spectra, in particular for calculation of subtracted
polarised spectra for calculation of dichroic signals like XMCD and XMLD.

## Introduction to the Spectra object
X-Ray Absorption Spectroscopy (XAS) spectra can be loaded as a pythonic object with special behaviours and attributes.

- A Spectra object contains an energy array and a signal array. For example this could represent the TEY spectra from a scan.
- Multiple Spectra can be contained within a SpectraContainer - for example different detectors for a single scan. SpectraContainers also contain metadata for a scan.
- Spectra and SpectraContainers contain methods to perform background subtractions and other processing.
- Spectra and SpectraContainers can be combined (averaged) and subtracted.
- Both objects contain a history of all processes performed on them.

## Spectra Data model
```
spectra = Spectra(energy, signal, mode, process)
metadata = XasMetadata(scan_no=1234, default_mode='tey', sample_name='Fe')
scan = SpectraContainer('name', {'mode': spectra}, metadata=metadata)
scan2 = scan + 2  # add 2 to signal of each contained mode
scan.remove_background()  # apply operation to each contained mode, store previous version in scan.parents
```

## Spectra & SpectraContainer 
### Selected Behaviours (see Docs for full list)
| command                                                                        |                                                                  |
|--------------------------------------------------------------------------------|------------------------------------------------------------------|
| `print(spectra1)`                                                              | displays contained spectra, metadata and previous analysis steps |
| `spectra1 + spectra2`                                                          | Averages contained spectra on a regular energy grid              |
| `spectra1 - spectra2`                                                          | Subtracts spectra on an interpolated energy grid                 |
| `spectra1.trim(ev_from_start=1)`                                               | trim contained spectra by 1 eV                                   |
| `spectra1.divide_by_preedge()`                                                 | divide contained spectra by preedge signal                       |
| `spectra1.remove_background(type)` \ Subtract background using various methods |
| `spectra1.analysis_steps_str()`                                                | returns a formatted string of previous analysis steps            |
| `spectra1.create_background_figure()`                                          | create a matplotlib figure of all contained spectra              |
| `spectra1.create_background_figure()`                                          | create a matplotlib figure including background subtraction      |
| `spectra1.write_nexus('filename.nxs')`                                         | write a processed NeXus file                                     |

#### spectra.remove_background() options

| Option             | parameters                          |
|--------------------|-------------------------------------|
| 'flat'             | ev_from_start                       |
| 'norm'             | ev_from_start                       |
| 'linear'           | ev_from_start                       |
| 'curve'            | ev_from_start                       |
| 'exp'              | ev_from_start, ev_from_end          |
| 'step'             | ev_from_start                       |
| 'double_edge_step' | l3_energy, l2_energy, peak_width_ev |
| 'poly_edges'       | *step_energies, peak_width_ev       |
| 'exp_edges'        | *step_energies, peak_width_ev       |

## Example Script - single XAS scan
```python
from mmg_toolbox import xas
import matplotlib.pyplot as plt

# Load from NeXus file
spectra, = xas.load_xas_scans('12345.nxs', sample_name='mysample', mode='all', dls_loader=True)  # loads a SpectraContainer containing all Spectra in scan
print(spectra)

# SpectraContainer documentation
help(spectra)

# Plot Raw spectra
spectra.create_figure(figsize=[12, 4], dpi=60)

# Process spectra
spectra = spectra.divide_by_preedge()
spectra = spectra.remove_background('linear')  # options listed below

# list all processes performed, including any fitting parameters
print(spectra)

# Plot background subtracted spectra
spectra.create_background_figure(figsize=[12, 6], dpi=60)
plt.show()
```

## Example Script - combining spectra
```python
from mmg_toolbox import xas
import matplotlib.pyplot as plt

spectra1, spectra2 = xas.load_xas_scans('12345.nxs', '123456.nxs',
                                        sample_name='mysample', mode='all', dls_loader=True)
# normalise
spectra1 = spectra1.divide_by_preedge()
spectra2 = spectra2.divide_by_preedge()

# Average the spectra
average = spectra1 + spectra2
print(average)

average.create_figure(figsize=[12, 4], dpi=60)

# Subtract the spectra
diff = spectra1 - spectra2
print(diff)  # Note that for subtractions the sum rules are automatically calculated using the edge element

diff.create_figure(figsize=[12, 4], dpi=60)

print(diff.sum_rules_report(n_holes=4, mode='tey'))

diff.create_sum_rules_figure()
plt.show()
```

## Example Script - Loading Spectra from an experiment
```python
from mmg_toolbox import Experiment, xas
import matplotlib.pyplot as plt

# Create experiment object - monitors one or more data folders for files
exp = Experiment('{{experiment_dir}}', instrument='{{beamline}}')

print(exp)

# print all scans in directory (could take a while...)
print(exp.all_scans_str())

# Load scan data and plot raw spectra
scan_numbers = [12345, 12346, 12347, 12348]
scans = exp.scans(*scan_numbers)  # loads Scan objects that can access NeXus data file
spectras = exp.load_xas(*scan_numbers, sample_name='mysample', mode='tey', dls_loader=True)  # only loads NXxas spectra (energy scans) and creates a Spectra object

for scan in spectras:
    print(scan)

# Plot each RAW spectra
n_spectra = len(spectras[0].spectra)

fig, axes = plt.subplots(1, n_spectra, figsize=[6 * n_spectra, 6], dpi=100, squeeze=False)
for scan in spectras:
    for ax, (mode, spectra) in zip(axes.flat, scan.spectra.items()):
        spectra.plot(ax)
        ax.set_ylabel(f"{mode} / monitor")
        ax.set_xlabel('E [eV]')
        ax.legend()

fig.tight_layout()

# process the spectra
spectras = [spectra.divide_by_preedge().remove_background('linear') for spectra in spectras]

fig, axes = plt.subplots(1, n_spectra, figsize=[6 * n_spectra, 6], dpi=100, squeeze=False)
for scan in spectras:
    for ax, (mode, spectra) in zip(axes.flat, scan.spectra.items()):
        spectra.plot(ax)
        ax.set_title(spectra.process_label)
        ax.set_ylabel(mode)
        ax.set_xlabel('E [eV]')
        ax.legend()
fig.tight_layout()

# Average polarised scans
for xas_scan in spectras:
    print(f"{xas_scan.name}: {xas_scan.metadata.pol}")
pol1, pol2 = xas.average_polarised_scans(*spectras)
print(pol1)
print(pol2)

if pol2 is None:
    raise  ValueError(f"No opposite polarisations found: {[s.metadata.pol for s in spectras]}")

# Plot averaged scans
fig, axes = plt.subplots(1, n_spectra, figsize=[6 * n_spectra, 6], dpi=100, squeeze=False)
for scan in [pol1, pol2]:
    for ax, (mode, spectra) in zip(axes.flat, scan.spectra.items()):
        spectra.plot(ax)
        ax.set_title(spectra.process_label)
        ax.set_ylabel(mode)
        ax.set_xlabel('E [eV]')
        ax.legend()

# Calculate XMCD
xmcd = pol1 - pol2
print(xmcd)

xmcd.create_sum_rules_figure(figsize=(8 * n_spectra, 6), dpi=100);
plt.tight_layout(h_pad=0.1, w_pad=0.1)

# fig, axes = plt.subplots(1, n_spectra, figsize=[6 * n_spectra, 6], dpi=100, squeeze=False)
# for ax, (mode, spectra) in zip(axes.flat, xmcd.spectra.items()):
#     spectra.plot(ax)
#     ax.set_title(spectra.process_label)
#     ax.set_ylabel(mode)
#     ax.set_xlabel('E [eV]')
#     ax.legend()

# Create output file
# create processed nexus file
xmcd_filename = f"{spectras[0].metadata.scan_no}-{spectras[-1].metadata.scan_no}_{xmcd.name}.nxs"
xmcd.write_nexus(xmcd_filename)

plt.show()
```