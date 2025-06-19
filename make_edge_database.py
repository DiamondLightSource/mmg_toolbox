"""
Use Dans_Diffraction to make a element edge database
"""

import os
import numpy as np
import json
from Dans_Diffraction.functions_crystallography import atom_properties

EDGE_FILE = 'mmg_toolbox/data/xray_edges.json'

edges = ['K', 'L1', 'L2', 'L3', 'M1', 'M2', 'M3', 'M4', 'M5', 'N1', 'N2', 'N3']
orbitals = ['1s', '2s', '2p1/2', '2p3/2', '3s', '3p1/2', '3p3/2', '3d3/2', '3d5/2', '4s', '4p1/2', '4p3/2']

props = atom_properties()
# convert numpy structured array to dict {'element': {'property': value}}
elements = {e: {p: props[n][p] for p in props.dtype.names} for n, e in enumerate(props['Element'])}

# format strings
edge_label = "{element} {edge}"
ele_doc = "Z={z}, name=\"{name}\", standar_atomic_weight={weight}"
edge_doc = " orbital=\"{orbital}\", electron_binding_energy_ev={energy:.0f}"
item_fmt = "    <item value=\"{element} {edge}\"> <doc>" + ele_doc + edge_doc + "</doc> </item>"

# create format dict
edge_dict = {
    edge_label.format(element=element, edge=edge): {
        'element': element,
        'edge': edge,
        'orbital': orbital,
        'energy': float(1000 * edge_energy),  # energy in eV
        'z': int(elements[element]['Z']),
        'block': elements[element]['Block'],
        'name': elements[element]['Name'],
        'weight': float(elements[element]['Weight'])
    }
    for element in elements for edge, orbital in zip(edges, orbitals)
    if (edge_energy := elements[element][edge]) > 0.001
}

# element_dict = {
#     element: {
#         'z': int(elements[element]['Z']),
#         'block': elements[element]['Block'],
#         'name': elements[element]['Name'],
#         'weight': float(elements[element]['Weight'])
#     } for element in elements
# }

# write dict to json
with open(EDGE_FILE, 'w') as outfile:
    json.dump(edge_dict, outfile)


# Test
test_range = np.array([694.9287, 695.1218, 695.3457, 695.5315, 695.742 , 695.9376,
       696.1434, 696.3255, 696.5386, 696.7285, 696.9368, 697.1285,
       697.3562, 697.5649, 697.8035, 698.0175, 698.2534, 698.4753,
       698.7166, 698.9296, 699.1641, 699.3621, 699.6025, 699.7998,
       700.0282, 700.2354, 700.432 , 700.6419, 700.8357, 701.0275,
       701.2096, 701.4196, 701.603 , 701.7998, 701.989 , 702.1994,
       702.3981, 702.6262, 702.8396, 703.0772, 703.2857, 703.5345,
       703.7633, 704.0166, 704.2395, 704.4843, 704.6962, 704.9315,
       705.1406, 705.3622, 705.5554, 705.768 , 705.948 , 706.1524,
       706.3295, 706.5305, 706.7395, 706.9273, 707.1219, 707.314 ,
       707.5245, 707.7351, 707.9328, 708.1692, 708.3807, 708.609 ,
       708.8266, 709.0573, 709.2657, 709.4894, 709.6859, 709.8962,
       710.0852, 710.2957, 710.4801, 710.6793, 710.8592, 711.0402,
       711.2118, 711.3978, 711.5616, 711.742 , 711.9055, 712.0897,
       712.2576, 712.4488, 712.6322, 712.8215, 713.0025, 713.2158,
       713.433 , 713.6392, 713.8603, 714.0779, 714.2855, 714.5071,
       714.7261, 714.9575, 715.1593, 715.3803, 715.5823, 715.7961,
       715.9893, 716.19  , 716.3673, 716.564 , 716.7388, 716.9362,
       717.1118, 717.3078, 717.484 , 717.6808, 717.8594, 718.0794,
       718.2641, 718.4812, 718.6865, 718.9183, 719.1363, 719.3744,
       719.5899, 719.8353, 720.063 , 720.3141, 720.5459, 720.7697,
       720.9932, 721.2048, 721.4258, 721.628 , 721.8335, 722.0316,
       722.2509, 722.4454, 722.6508, 722.8455, 723.0653, 723.2499,
       723.4727, 723.6673, 723.9018, 724.1196, 724.3746, 724.6003,
       724.872 , 725.1139, 725.3893, 725.6359, 725.9074, 726.1439,
       726.402 , 726.6295, 726.878 , 727.0992, 727.3442, 727.553 ,
       727.7873, 727.9909, 728.2232, 728.4486, 728.6812, 728.9162,
       729.1691, 729.4127, 729.6832, 729.9393, 730.2235, 730.4856,
       730.7829, 731.036 , 731.3215, 731.5699, 731.8447, 732.0969,
       732.3536, 732.5916, 732.856 , 733.0898, 733.3383, 733.5539,
       733.8083, 734.031 , 734.2689, 734.4867, 734.7407, 734.969 ,
       735.2368, 735.4856, 735.7622, 736.0109, 736.3048, 736.612 ,
       736.8878, 737.1547, 737.4275, 737.6937, 737.9448, 738.1665,
       738.4225, 738.6377])


if __name__ == '__main__':
    from mmg_toolbox.spectra_analysis import xray_edges_in_range, energy_range_edge_label

    print('\nxray edges in range')
    print(xray_edges_in_range(test_range.min(), test_range.max()))

    print('\nxray energy range mode')
    print(energy_range_edge_label(test_range.min(), test_range.max()))
