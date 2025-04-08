"""
Try out Spectra
"""

import matplotlib.pyplot as plt
from mmg_toolbox.spectra_scan import SpectraScan, find_pol_pairs


files = [
    '/dls/i10-1/data/2025/cm40624-2/i10-1-26822.nxs',
    '/dls/i10-1/data/2025/cm40624-2/i10-1-26823.nxs',
    '/dls/i10-1/data/2025/cm40624-2/i10-1-26824.nxs',
    '/dls/i10-1/data/2025/cm40624-2/i10-1-26825.nxs',
]

scans = [SpectraScan(file) for file in files]

print(scans)

# pol1 = scans[0] + scans[3]
# pol2 = scans[1] + scans[2]
#
# print(pol1)
# pol1.create_figure()
#
# diff = pol1 - pol2
#
# print(diff)
#
# diff.create_figure()


pairs = find_pol_pairs(*scans)

for pair in pairs:
    pair.create_figure()

rem_bkg = [s.remove_background('flat').norm_to_jump() for s in scans]
pairs = find_pol_pairs(*rem_bkg)

for pair in pairs:
    pair.create_figure()

pol1 = [pair.spectra1 for pair in pairs]
pol2 = [pair.spectra2 for pair in pairs]
av_pol1 = sum(pol1[1:], pol1[0])
av_pol2 = sum(pol2[1:], pol2[0])
diff = av_pol1 - av_pol2
diff.create_figure()
print(diff)


plt.show()