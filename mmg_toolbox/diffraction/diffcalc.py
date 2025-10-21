"""
Wrapper functions for DiffCalc

Requires:
    pip install diffcalc-core

Example:
    from mmg_toolbox.diffcalc import UB
    ub = UB()
    ub.latt(2.85, 2.85, 10.8, 90, 90, 120)
    ub.add_reflection('ref1', ...)
    ub.add_reflection('ref2', ...)
    ub.calc_ub('ref1', 'ref2')
    ub.con('gamma',0, 'mu',0, 'bisect')

    angles = ub.hkl2angles((1,1,1), energy_kev=6)
    hkl = ub.angles2hkl(phi, chi, eta, mu, delta, gamma, energy_kev)
    solutions = ub.all_solutions((1, 1, 1), energy_kev=6)
"""

import numpy as np
from diffcalc.hkl.calc import HklCalculation
from diffcalc.hkl.constraints import Constraints
from diffcalc.hkl.geometry import Position
from diffcalc.ub.calc import UBCalculation

from mmg_toolbox.utils.xray_utils import photon_wavelength, photon_energy

# Euler to Kappa angles
KALPHA = 50.0 # limits the range of possible chi in different modes.
#Maybe the angle between kth and kappa arms when phi || z ? Or angle needed for chi=90?
CHI_MAGIC = 65.595503 # some unexplained angle


DEFAULT_LATTICE = ('Hexagonal', 2.85, 10.8)
DEFAULT_CONSTRAINTS = {
    'gamma': 0.0,
    'mu': 0.0,
    'phi': 0.0
}
DEFAULT_LIMITS = {
    # angle: (min, max)
    'phi': (-180, 180),
    'chi': (-10, 100),
    'eta': (-20, 120),
    'mu': (-10, 180),
    'delta': (-10, 120),
    'gamma': (-10, 120),
}
RENAME_AXES = {
    # my name: DiffCalc name
    'gamma': 'nu'
}


def _euler2kappa(phi: float, chi: float, eta: float,
                 mode: int = 1, kalpha: float = KALPHA, chi_magic: float = CHI_MAGIC) -> tuple[float, float, float]:
    """
    Convert from Eulerian space angles to real world motor angles
    in: e_angles = [eta, chi, phi] # in degrees
    out : k_angles = [ktheta, kappa, kphi] # in degrees

    This function takes some weird constant parameters, and a mode parameter.
    The code requires mu constraints (mu = 0 or mu = 180 degrees) to work in the specified modes.
    The modes allow to invert the movement of kappa (kappa -> (-1)*kappa) and adjust
    the other angles accordingly.
    The inverted modes could be useful when working with large equipment.

    # Coversion Modes:
    # Mode; Constraint; Effect
    # "  1; mu=0      ; Normal operation
    # "  2; mu=0      ; kappa -> (-1)*kappa
    # "  3; mu=180    ; Normal operation, with mu on the opposite side of the diffractometer.
    phi rotates >180 degrees, be careful with pipes!
    # "  4; mu=180    ; kappa -> (-1)*kappa, with mu on the opposite side.
    phi rotates >180 degrees, be careful with pipes!

    Potential upgrade: Include mu in the calculations so the code could work for any value of mu.

    Known Bugs:
        1. Rotation matrix algebra cannot be varified

    Fixed Bugs (since version 1.0):
        1. Weird behaviour at chi=100.
        2. Errors of accessing undefined k_angle variables
        3. Total ugliness
        4. Added setRange before checking abs(chi)
    """
    cos = lambda x: np.cos(np.deg2rad(x))
    sin = lambda x: np.sin(np.deg2rad(x))
    tan = lambda x: np.tan(np.deg2rad(x))
    asin = lambda x: np.rad2deg(np.arcsin(x))

    def _set_range(value, min_angle: float = -180, max_angle: float = 180):
        if value < min_angle:
            return _set_range(value + 360, min_angle, max_angle)
        elif value > max_angle:
            return _set_range(value - 360, min_angle, max_angle)
        else:
            return value

    # calculates modes 1 and 2 for -100 < chi < 100
    if abs(chi) < 2 * kalpha:
        delta1 = -asin(tan(chi / 2.) / tan(kalpha))
        kappa = -asin(cos(delta1) * sin(chi) / sin(kalpha))

        if abs(chi) > chi_magic and chi > 0.:
            kappa = _set_range(180 - kappa)
        elif abs(chi) > chi_magic and chi < 0.:
            kappa = _set_range(-180 - kappa)

        theta_K1 = _set_range(eta - delta1, -90., 270.)
        phi_K1 = _set_range(phi - delta1, -90., 270.)

        theta_K2 = _set_range(eta - (180 - delta1), -90., 270.)
        phi_K2 = _set_range(phi - (180 - delta1), -90., 270.)
        K2 = _set_range(-kappa)

    # if chi is out of range
    else:
        kappa = None
        K2 = None
        phi_K1 = None
        phi_K2 = None
        theta_K1 = None
        theta_K2 = None

    # calculates modes 3 and 4 for -180 < chi < -100 and 100 < chi < 180
    if abs(chi) > (180. - kalpha * 2):
        chi_r = _set_range(180 - chi)
        delta3 = -asin(tan(chi_r / 2.) / tan(kalpha))
        K3 = -asin(cos(delta3) * sin(chi_r) / sin(kalpha))

        if abs(chi_r) > chi_magic and chi_r > 0.:
            K3 = _set_range(180 - K3)
        elif abs(chi_r) > chi_magic and chi_r < 0.:
            K3 = _set_range(-180 - K3)

        theta_K3 = _set_range(eta - delta3, -90., 270.)
        phi_K3 = _set_range(phi - delta3 + 180, -90., 270.)
        theta_K4 = _set_range(eta - (180 - delta3), -90., 270.)
        phi_K4 = _set_range(phi - (180 - delta3) * 180., -90., 270.)
        K4 = _set_range(-K3)

    # if chi is out of range
    elif abs(chi) <= (180. - kalpha * 2):
        K3 = None
        K4 = None
        phi_K3 = None
        phi_K4 = None
        theta_K3 = None
        theta_K4 = None

    else:
        raise Exception('chi is wrong')

    Kvalues = [
        [theta_K1, kappa, phi_K1],
        [theta_K2, K2, phi_K2],
        [theta_K3, K3, phi_K3],
        [theta_K4, K4, phi_K4]
    ]
    ktheta, kappa, kphi = Kvalues[mode - 1]
    return kphi, kappa, ktheta


def _kappa2euler(kphi: float, kappa: float, ktheta: float,
                 mode: int = 1, kalpha: float = KALPHA) -> tuple[float, float, float]:
    """
    Convert k_angles of real motors to e_angles in Eulerian space
    in : k_angles = [ktheta, kappa, kphi] # in degrees
    out: e_angles = [eta_now, chi_now, phi_now] # in degrees
    mode: must be the same mode as in EtoK()
    """
    cos = lambda x: np.cos(np.deg2rad(x))
    sin = lambda x: np.sin(np.deg2rad(x))
    tan = lambda x: np.tan(np.deg2rad(x))
    asin = lambda x: np.rad2deg(np.arcsin(x))
    atan = lambda x: np.rad2deg(np.arctan(x))

    def _set_range(value, min_angle: float = -180, max_angle: float = 180):
        if value < min_angle:
            return _set_range(value + 360, min_angle, max_angle)
        elif value > max_angle:
            return _set_range(value - 360, min_angle, max_angle)
        else:
            return value

    ktheta = _set_range(ktheta, -90, 270)
    kappa = _set_range(kappa)
    kphi = _set_range(kphi, -90, 270)

    if mode == 1:
        gamma = -atan(cos(kalpha) * tan(kappa / 2.))
        chi = -2 * asin(sin(kappa / 2) * sin(kalpha))
        theta = ktheta - gamma
        phi = kphi - gamma

    elif mode == 2:
        gamma = -atan(cos(kalpha) * tan(kappa / 2)) + 180.
        chi = 2 * asin(sin(kappa / 2) * sin(kalpha))
        theta = ktheta - gamma
        phi = kphi - gamma

    elif mode == 3:
        gamma = -atan(cos(kalpha) * tan(kappa / 2.))
        chi = 2 * asin(sin(kappa / 2) * sin(kalpha)) + 180.
        theta = ktheta - gamma
        phi = kphi - gamma + 180.

    elif mode == 4:
        gamma = -atan(cos(kalpha) * tan(kappa / 2.))
        chi = -2 * asin(sin(kappa / 2) * sin(kalpha)) + 180.
        theta = ktheta - gamma + 180.
        phi = kphi - gamma
        theta = _set_range(theta, -90., 270.)
        chi = _set_range(chi)
        phi = _set_range(phi, -90., 270.)

    else:
        raise Exception('mode not recognized')

    eta, chi, phi = _set_range(theta, -90., 270.), _set_range(chi), _set_range(phi, -90., 270.)
    return phi, chi, eta


def euler2kappa(phi: np.ndarray, chi: np.ndarray, eta: np.ndarray,
                mode: int = 1, kalpha: float = KALPHA, chi_magic: float = CHI_MAGIC
                ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    phi = np.reshape(phi, -1)
    chi = np.reshape(chi, -1)
    eta = np.reshape(eta, -1)
    kphi, kappa, ktheta = np.array([
        _euler2kappa(p, c, e,  mode=mode, kalpha=kalpha, chi_magic=chi_magic)
        for p, c, e in zip(phi, chi, eta)
    ]).T
    return kphi.squeeze(), kappa.squeeze(), ktheta.squeeze()


def kappa2euler(kphi: np.ndarray, kappa: np.ndarray, ktheta: np.ndarray,
                mode: int = 1, kalpha: float = KALPHA,
                ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    kphi = np.reshape(kphi, -1)
    kappa = np.reshape(kappa, -1)
    ktheta = np.reshape(ktheta, -1)
    phi, chi, eta = np.array([
        _kappa2euler(kph, kap, kth,  mode=mode, kalpha=kalpha)
        for kph, kap, kth in zip(kphi, kappa, ktheta)
    ]).T
    return phi.squeeze(), chi.squeeze(), eta.squeeze()


class UB:
    """
    Wrapper class for DiffCalc functionality
    """
    ubcalc: UBCalculation
    constrains: Constraints
    limits: dict[str, tuple[float, float]]
    hklcalc: HklCalculation

    def __init__(self,
                 lattice: tuple[float, float, float, float, float, float] | None = None,
                 ref1: tuple[tuple[int, int, int], float, float, float, float, float, float, float] | None = None,
                 ref2: tuple[tuple[int, int, int], float, float, float, float, float, float, float] | None = None,
                 constraints: dict[str, float | None] | None = None,
                 limits: dict[str, tuple[float, float]] | None = None,
                 azir: tuple[float, float, float] = (1, 0, 0),
                 surface: tuple[float, float, float] = (0, 0, 1),
                 ):
        self.ubcalc = UBCalculation("sixcircle")
        if lattice is None:
            lattice = DEFAULT_LATTICE
        self.ubcalc.set_lattice("sample", *lattice)
        self.ubcalc.n_hkl = azir # azimuthal reference, hkl
        self.ubcalc.surf_nhkl = surface  # surface vector, hkl
        if ref1 is not None:
            self.add_reflection('ref1', *ref1)
        if ref2 is not None:
            self.add_reflection('ref2', *ref2)
        if ref1 is not None and ref2 is not None:
            self.ubcalc.calc_ub('ref1', 'ref2')

        if constraints is None:
            constraints = DEFAULT_CONSTRAINTS.copy()
        self.constraints = Constraints(self._names2diffcalc(**constraints))
        if limits is None:
            limits = DEFAULT_LIMITS.copy()
        self.limits = limits
        self.hklcalc = HklCalculation(self.ubcalc, self.constraints)
        self.lab_transformation = np.eye(3)

    def __repr__(self):
        return repr(self.ubcalc)

    def __str__(self):
        return f"{self.ubcalc}\n\nCONSTRAINTS\n{self.constraints}"

    def add_reflection(self, label: str, hkl: tuple[float, float, float],
                       phi: float = 0, chi: float = 0, eta: float = 0, mu: float = 0,
                       delta: float = 0, gamma: float = 0,
                       energy_kev: float | None = None, wavelength_a: float | None = None):
        """
        Add a reflection location to the UB calculation
        """
        if energy_kev is None:
            energy_kev = photon_energy(wavelength_a)
        self.ubcalc.add_reflection(
            tag=label,
            hkl=hkl,
            position=Position(
                indegrees=True,
                phi=phi,
                chi=chi,
                eta=eta,
                mu=mu,
                delta=delta,
                nu=gamma,
            ),
            energy=energy_kev,
        )

    def add_orientation(self, label: str, hkl: tuple[float, float, float], xyz: tuple[float, float, float]):
        """
        Add an orientation to the UB calculation
        """
        self.ubcalc.add_orientation(
            # Add orientation of crystal, can be used together with reflection
            hkl=hkl,
            xyz=xyz,  # xyz in diffractometer basis
            position=None,
            tag=label
        )

    def latt(self, a: float = 5.0, b: float | None = None, c: float | None = None,
             alpha: float | None = None, beta: float | None = None, gamma: float | None = None,
             name: str = 'xtl', system: str = None):
        """
        Set the crystal lattice
        """
        self.ubcalc.set_lattice(name, system, a, b, c, alpha, beta, gamma)

    def calcub(self, tag1: str = 'ref1', tag2: str = 'ref2'):
        self.ubcalc.calc_ub(tag1, tag2)

    def set_lab_transformation(self, transformation: np.ndarray):
        """Assign a 3x3 transformation matrix to appy to angles"""
        self.lab_transformation = transformation

    def ub_matrix(self):
        return np.dot(self.lab_transformation, self.ubcalc.UB)

    def orientation_matrix(self):
        return np.dot(self.lab_transformation, self.ubcalc.U)

    def lp(self):
        xtl = self.ubcalc.crystal
        return xtl.a1, xtl.a2, xtl.a3, xtl.alpha1, xtl.alpha2, xtl.alpha3

    def asdict(self):
        return self.hklcalc.asdict.copy()

    def load_from_diffcalc(self, hklcalc: HklCalculation | None = None,
                           ubcalc: UBCalculation | None = None,
                           constraints: Constraints | None = None):
        if hklcalc is not None:
            self.hklcalc = hklcalc
            self.ubcalc = hklcalc.ubcalc
            self.constraints = hklcalc.constraints
        else:
            if ubcalc is not None:
                self.ubcalc = ubcalc
            if constraints is not None:
                self.constraints = constraints

    def azir(self, hkl: tuple[float, float, float]):
        """Set azimuthal reference reflection"""
        self.ubcalc.n_hkl = hkl

    def _names2diffcalc(self, **kwargs):
        return {
            RENAME_AXES[name] if name in RENAME_AXES else name: value
            for name, value in kwargs.items()
        }

    def _diffcalc2names(self, **kwargs):
        RENAME = {value: name for name, value in RENAME_AXES.items()}
        return {
            RENAME[name] if name in RENAME else name: value
            for name, value in kwargs.items()
        }

    def set_limits(self, **limits: [str, tuple[float, float]]):
        """Set limits"""
        limits = self._names2diffcalc(**limits)
        self.limits.update(limits)

    def _set_constraints(self, **constraints):
        """Set constraints"""
        constraints = self._names2diffcalc(**constraints)
        self.constraints.clear()
        for name, value in constraints.items():
            setattr(self.constraints, name, value)

    def con(self,
            con1: str, value1: float | bool,
            con2: str, value2: float | bool,
            con3: str, value3: float | bool = True):
        """Apply contraints to the DiffCalc calculation"""
        self._set_constraints(**{con1: value1, con2: value2, con3: value3})

    def bisect_vertical(self):
        self.con('gamma', 0, 'mu', 0, 'bisect')

    def bisect_horizontal(self):
        self.con('delta', 0, 'eta', 0, 'bisect')

    def fixed_phi_vertical(self, phi: float = 0):
        self.con('gamma', 0, 'mu', 0, 'phi', phi)

    def fixed_phi_horizontal(self, phi: float = 0):
        self.con('delta', 0, 'eta', 0, 'phi', phi)

    def fixed_psi_vertical(self, psi: float = 0):
        self.con('gamma', 0, 'mu', 0, 'psi', psi)

    def fixed_psi_horizontal(self, psi: float = 0):
        self.con('delta', 0, 'eta', 0, 'psi', psi)

    def all_solutions(self, hkl: tuple[float, float, float],
                      energy_kev: float | None = None, wavelength_a: float | None = None) -> list[dict[str, float]]:
        """Calculate all angle solutions for the given HKL"""
        if wavelength_a is None:
            wavelength_a = photon_wavelength(energy_kev)
        h, k, l = hkl
        all_pos = self.hklcalc.get_position(h, k, l, wavelength_a)
        solutions = []
        for posn, virtual_angles in all_pos:
            pos = posn.asdict.copy()
            pos['gamma'] = pos['nu']
            ktheta, kappa, kphi = euler2kappa(pos['phi'], pos['chi'], pos['eta'])
            kap = {
                'ktheta': ktheta,
                'kappa': kappa,
                'kphi': kphi
            }
            solutions.append(self._diffcalc2names(**{**pos, **virtual_angles, **kap}))
        return solutions

    def hkl2angles(self, hkl: tuple[float, float, float],
                   energy_kev: float | None = None, wavelength_a: float | None = None) -> dict[str, float] | None:
        """Calculate the angles for the given HKL"""
        if wavelength_a is None:
            wavelength_a = photon_wavelength(energy_kev)
        h, k, l = hkl
        all_pos = self.hklcalc.get_position(h, k, l, wavelength_a)
        for posn, virtual_angles in all_pos:
            pos = posn.asdict.copy()
            pos['gamma'] = pos['nu']
            if all(
                ax_min < pos.get(axis) < ax_max for axis, (ax_min, ax_max) in self.limits.items()
            ):
                ktheta, kappa, kphi = euler2kappa(pos['phi'], pos['chi'], pos['eta'])
                kap = {
                    'ktheta': ktheta,
                    'kappa': kappa,
                    'kphi': kphi
                }
                return self._diffcalc2names(**{**pos, **virtual_angles, **kap})
        return None

    def angles2hkl(self, phi: float = 0, chi: float = 0, eta: float = 0, mu: float = 0,
                   delta: float = 0, gamma: float = 0,
                   energy_kev: float | None = None, wavelength_a: float | None = None) -> tuple[float, float, float]:
        """Calculate the HKL for the given angles"""
        if wavelength_a is None:
            wavelength_a = photon_wavelength(energy_kev)
        pos = Position(
            # Eulerean angles in You. et al diffractometer basis
            # (z-along phi when all angles 0, y along beam, x vertical)
            nu=gamma,  # detector rotation, positive about diffractometer x-axis (gamma)
            delta=delta,  # detector rotation, negative about diffractometer z-axis
            mu=mu,  # sample rotation, positive about diffractometer x-axis
            eta=eta,  # sample rotation, negative about diffractometer z-axis
            chi=chi,  # sample rotation, positive about diffractometer y-axis
            phi=phi  # sample rotation, negative about diffractometer z-axis
        )
        return self.hklcalc.get_hkl(pos, wavelength_a)

    def kappa2hkl(self, ktheta: float = 0, kappa: float = 0, kphi: float = 0, mu: float = 0,
                  delta: float = 0, gamma: float = 0,
                  energy_kev: float | None = None, wavelength_a: float | None = None) -> tuple[float, float, float]:
        """Calculate the HKL for the given Kappa-angles"""
        if wavelength_a is None:
            wavelength_a = photon_wavelength(energy_kev)
        phi, chi, eta = kappa2euler(ktheta, kappa, kphi)
        pos = Position(nu=gamma, delta=delta, mu=mu, eta=eta, chi=chi, phi=phi)
        return self.hklcalc.get_hkl(pos, wavelength_a)

    def euler2kappa(self, phi: float = 0, chi: float = 0, eta: float = 0) -> tuple[float, float, float]:
        """Calculate the Euler angles for the given Kappa-angles"""
        return euler2kappa(phi, chi, eta)

    def kappa2euler(self, ktheta: float = 0, kappa: float = 0, kphi: float = 0) -> tuple[float, float, float]:
        """Calculate the Euler angles for the given Kappa-angles"""
        return kappa2euler(ktheta, kappa, kphi)

