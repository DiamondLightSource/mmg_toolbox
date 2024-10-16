
import numpy as np
from mmg_toolbox.nexus_reader import readscan_Nexus


def max_min_energy_Nexus(scanlist):
    max_list = []
    min_list = []

    for scanno in scanlist:

        d = readscan_Nexus(scanno)
        m = d.metadata
        ks = d.keys()
        scan_type = m.command.split()[1]

        if scan_type != 'fastEnergy':
            continue

        energy1 = d.fastEnergy

        min_list.append(energy1.min())
        max_list.append(energy1.max())

    min_list = np.array(min_list)
    max_list = np.array(max_list)

    energy_min = min_list.max()
    energy_max = max_list.min()
    points = len(energy1)

    energy = np.linspace(energy_min, energy_max, points)

    return energy