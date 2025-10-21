"""
Example Diffcalc Calculation

Requires:
 - python -m pip install diffcalc-core

By Dan Porter, October 2025
"""

from diffcalc.hkl.calc import HklCalculation
from diffcalc.hkl.constraints import Constraints
from diffcalc.hkl.geometry import Position
from diffcalc.ub.calc import UBCalculation


# Set up sample basis
ubcalc = UBCalculation("sixcircle")
"""
('Cubic', a) – sets Cubic system 
('Tetragonal', a, c) – sets Tetragonal system 
('Hexagonal', a, c) – sets Hexagonal system 
('Orthorhombic', a, b, c) – sets Orthorombic system 
('Rhombohedral', a, alpha) – sets Rhombohedral system 
('Monoclinic', a, b, c, beta) – sets Monoclinic system 
('Triclinic', a, b, c, alpha, beta, gamma) – sets Triclinic system
"""
ubcalc.set_lattice("SiO2", 'Hexagonal', 2.85, 10.8)
ubcalc.n_hkl = (1, 0, 0)  # azimuthal reference
# Add reflections and calculate UB
ubcalc.add_reflection(
    # add location of reflection
    hkl=(0, 0, 6),
    position=Position(
        # Eulerean angles in You. et al diffractometer basis
        # (z-along phi when all angles 0, y along beam, x vertical)
        nu=50.999,  # detector rotation, positive about diffractometer x-axis (gamma)
        delta=0.0,  # detector rotation, negative about diffractometer z-axis
        mu=51/2., # sample rotation, positive about diffractometer x-axis
        eta=0,  # sample rotation, negative about diffractometer z-axis
        chi=0.0,  # sample rotation, positive about diffractometer y-axis
        phi=0  # sample rotation, negative about diffractometer z-axis
    ),
    energy=8,  # keV
    tag="ref006",
)
ubcalc.add_orientation(
    # Add orientation of crystal, can be used together with reflection
    hkl=(1, 0, 0),
    xyz=(0, 1, 0),  # xyz in diffractometer basis
    position=None,
    tag="a_axis"
)
# Calculate UB matrix
ubcalc.calc_ub("ref006", "a_axis")

print("UBCalculation object representation.\n")
print(f"{ubcalc}")

# Constrain the diffractometer calculation
"""
Available constraints:
    Detector angles:
        nu, delta, qaz, naz
    Sample angles:
        mu, eta, chi, phi, bisect, omega
    Reference angles:
        alpha, beta, betain, betaout, a_eq_b, bin_eq_bout, psi
"""
cons = Constraints({"delta": 0, "eta": 0, "psi": 0})
hklcalc = HklCalculation(ubcalc, cons)

# Get Diffractometer angles for HKL reflections
print("\n\nhkl -> Position")
wavelength = 1.0
for h, k, l in ((0, 0, 1), (0, 1, 1), (1, 0, 2)):
    all_pos = hklcalc.get_position(h, k, l, wavelength)
    print(f"\n{'hkl':<8s}: [{h:1.0f} {k:1.0f} {l:1.0f}]")
    print(f"Solutions: {len(all_pos)}")
    for posn, virtual_angles in all_pos:
        if all((0 < posn.mu < 90, 0 < posn.nu < 90, -90 < posn.phi < 90)):
            print("-" * 18)
            for angle, val in posn.asdict.items():
                print(f"{angle:<8s}:{val:>8.2f}")
            print("-" * 18)
            for angle, val in virtual_angles.items():
                print(f"{angle:<8s}:{val:>8.2f}")

# Get HKL position of specific set of angles
pos1 = Position(
    # Eulerean angles in You. et al diffractometer basis
    # (z-along phi when all angles 0, y along beam, x vertical)
    nu=0,  # detector rotation, positive about diffractometer x-axis (gamma)
    delta=90,  # detector rotation, negative about diffractometer z-axis
    mu=0, # sample rotation, positive about diffractometer x-axis
    eta=45,  # sample rotation, negative about diffractometer z-axis
    chi=90.0,  # sample rotation, positive about diffractometer y-axis
    phi=0  # sample rotation, negative about diffractometer z-axis
)
hkl1 = hklcalc.get_hkl(pos1, wavelength)
print("\nPosition -> hkl")
for angle, val in pos1.asdict.items():
    print(f"{angle:<8s}:{val:>8.2f}")
print("-" * 18)
print(f"\n{'hkl':<8s}: [{hkl1[0]:1.1f} {hkl1[1]:1.1f} {hkl1[2]:1.1f}]")

