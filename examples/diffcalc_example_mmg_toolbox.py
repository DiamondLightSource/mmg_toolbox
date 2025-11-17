"""
Example Diffcalc Calculation using mmg_toolbox wrapper

Requires:
 - python -m pip install mmg_toolbox

mmg_toolbox contains a wrapper for diffcalc-core, see:
https://github.com/DiamondLightSource/mmg_toolbox/blob/main/mmg_toolbox/diffraction/diffcalc.py
and
https://github.com/DiamondLightSource/diffcalc-core

By Dan Porter, October 2025
"""

from mmg_toolbox.diffraction.diffcalc import UB


en = 8  # keV

ub = UB()
ub.latt(2.85, 2.85, 10.8, 90, 90, 120)
ub.add_reflection('ref1', (0, 0, 6), eta=25.5, chi=91, delta=51, energy_kev=en)
# ub.add_orientation('or1', hkl=(1, 0, 0), xyz=(0, 1, 0))
ub.add_reflection('ref2', hkl=(1,1,4), eta=100.12, chi=91, delta=75.89, energy_kev=en)
ub.calcub('ref1', 'ref2')
ub.con('gamma',0, 'mu',0, 'bisect')

print(ub)

angles = ub.hkl2angles((0,0,4), energy_kev=6)
print('\n\nangles:\n', angles)

hkl = ub.angles2hkl(phi=36, chi=90, eta=25, mu=0, delta=55, gamma=0, energy_kev=8)
print('\nhkl:\n', hkl)

print('\nSolutions:')
solutions = ub.all_solutions((1, 1, 4), energy_kev=6)
for sol in solutions:
    print(sol)

print('Finished!')
