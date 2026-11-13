"""
Absorption Edge classes and functions
"""

import json
import re
import numpy as np
from pathlib import Path
from collections.abc import Iterator

# Regular expressions
ELEMENTS = (
    r"He|Li|Be|Ne|Na|Mg|Al|Si|Cl|Ar|Ca|Sc|Ti|Cr|Mn|Fe|Co|Ni|Cu|Zn|Ga|Ge|As|Se|Br|Kr|Rb"
    r"|Sr|Zr|Nb|Mo|Tc|Ru|Rh|Pd|Ag|Cd|In|Sn|Sb|Te|Xe|Cs|Ba|La|Ce|Pr|Nd|Pm|Sm|Eu|Gd|Tb|Dy"
    r"|Ho|Er|Tm|Yb|Lu|Hf|Ta|Re|Os|Ir|Pt|Au|Hg|Tl|Pb|Bi|Po|At|Rn|Fr|Ra|Ac|Th|Pa|Np|Pu|Am"
    r"|Cm|Bk|Cf|Es|Fm|Md|No|Lr|Rf|Db|Sg|Bh|Hs|Mt|Ds|Rg|Cn|Nh|Fl|Mc|Lv|Ts|Og"
    r"|H|B|C|N|O|F|P|S|K|V|Y|I|W|U"
)
regex_element = re.compile(f"({ELEMENTS})")
regex_oxidation = re.compile(rf"({ELEMENTS})(\d?)([+-]?)")
regex_edges = re.compile(r"\b([KLMN])([1-5])?(?:,*([1-5]))?\b", re.IGNORECASE)


EDGE_FILE = Path(__file__).parent.parent / 'data' / 'xray_edges.json'
EDGES: dict[str, dict[str, str | float]] = {}
SEARCH_EDGES = ('L3', 'L2')
# PREFERRED_EDGES = ('L3', 'L2', 'K', 'M5', 'M4')
PREFERRED_EDGES = ('L3', 'K', 'M5', 'L2', 'M4')

# Neutral d-electron counts for transition metals
NEUTRAL_D_ELECTRONS = {
    "Sc": 1, "Ti": 2, "V": 3, "Cr": 4, "Mn": 5, "Fe": 6, "Co": 7, "Ni": 8, "Cu": 9, "Zn": 10,  # 3d
    "Y": 1, "Zr": 2, "Nb": 3, "Mo": 4, "Tc": 5, "Ru": 3, "Rh": 7, "Pd": 8, "Ag": 9, "Cd": 10,  # 4d
    "La": 1, "Hf": 2, "Ta": 3, "W": 4, "Re": 5, "Os": 6, "Ir": 7, "Pt": 8, "Au": 9, "Hg": 10  # 5d
}

def _get_edges() -> dict[str, dict[str, str | float]]:
    if not EDGES:
        with open(EDGE_FILE, 'r') as infile:
            EDGES.update(json.load(infile))
    return EDGES


def _load_edge_file(edges: list[str] | tuple[str, ...] | None = SEARCH_EDGES) -> dict[str, float]:
    """Load edges from file"""
    edge_energies = {
        label: float(edge['energy']) for label, edge in _get_edges().items()
        if not edges or (edge['edge'] in edges)
    }
    return edge_energies


def load_edge_energies(edges: list[str] | tuple[str, ...] | None = SEARCH_EDGES) -> tuple[np.ndarray, np.ndarray]:
    """
    return arrays of energies and labels for x-ray absorption edges
    :param edges: if not None, only return energies for these edges, e.g. ('L3', 'L2')
    :return: energies[ndarray], labels[ndarray]
    """
    edge_energies = _load_edge_file(edges)
    energies = np.array(list(edge_energies.values()))
    labels = np.array(list(edge_energies.keys()))
    idx = np.argsort(energies)
    return energies[idx], labels[idx]


def split_element_edge(symbol: str) -> tuple[str, list[str]]:
    """
    Split string into element symbol and edges

        'Co', ['L3', 'L2'] = split_element_edge('Co L3,2')

    Rules: Element must come before edges, edges defined by [KLMN][int].
    Multiple edges allowed but only a single element.

    :param symbol: string with element symbol and edge spec
    :return: 'element', list(edges)
    """
    elements = regex_element.finditer(symbol)
    match = next(elements, None)
    if match is None:
        raise ValueError(f"No known elements in '{symbol}'")
    element = match.group()
    edges_symbol = symbol.strip().removeprefix(element)
    edges = []
    matches = regex_edges.finditer(edges_symbol)
    for match in matches:
        edge, n1, n2 = match.groups()
        edges.append(edge.upper() + (n1 if n1 else ""))
        if n2 is not None:
            edges.append(edge.upper() + n2)
    return element, sorted(edges, reverse=True)


def split_element_oxidation(symbol: str) -> tuple[str, int]:
    """
    Split element symbol and oxidation state

        'O', -2 = split_element_oxidation('O2-')

    :param symbol: element symbol, 'Fe3+'
    :return: Element, int(oxidation)
    """
    match = regex_oxidation.match(symbol)
    if match is None:
        raise ValueError(f"No known elements in '{symbol}'")
    element, oxidation, sign = match.groups()
    if sign == '+':
        oxidation_value = int(oxidation or 1)
    elif sign == '-':
        oxidation_value = -int(oxidation or 1)
    else:
        oxidation_value = 0
    return element, oxidation_value


class Element:
    def __init__(self, symbol: str) -> None:
        element, oxidation = split_element_oxidation(symbol)
        self.symbol = element
        self.oxidation = oxidation

    def __repr__(self) -> str:
        return f"{self.symbol}"

    def __eq__(self, o: object) -> bool:
        o = Element(o) if isinstance(o, str) else o
        if isinstance(o, Element):
            return self.atomic_number == o.atomic_number
        return False

    def __hash__(self) -> int:
        return hash(self.atomic_number)

    def __gt__(self, o: object) -> bool:
        o = Element(o) if isinstance(o, str) else o
        if isinstance(o, Element):
            return self.atomic_number > o.atomic_number
        return False

    def __lt__(self, o: object) -> bool:
        o = Element(o) if isinstance(o, str) else o
        if isinstance(o, Element):
            return self.atomic_number < o.atomic_number
        return False

    def _get_props(self) -> dict[str, str | float]:
        return _get_edges()[f"{self.symbol} K"]

    @property
    def atomic_number(self) -> int:
        """Return atomic number, Z"""
        return int(self._get_props()['z'])

    @property
    def block(self) -> str:
        """Return Periodic table block of Element"""
        return str(self._get_props()['block'])

    @property
    def name(self) -> str:
        """Return element name"""
        return str(self._get_props()['name'])

    @property
    def weight(self) -> float:
        """Return weight of element"""
        return float(self._get_props()['weight'])

    def _edges(self) -> dict[str, dict[str, str | float]]:
        return {name: edge for name, edge in _get_edges().items() if name.startswith(self.symbol)}

    def edges(self) -> list[Edge]:
        return [Edge(edge) for edge in self._edges()]

    def is_d(self) -> bool:
        return self.symbol in NEUTRAL_D_ELECTRONS

    def d_electrons(self, oxidation: float | None = None) -> float:
        oxidation = self.oxidation if oxidation is None else oxidation
        if not self.is_d():
            raise ValueError(f"Element {self} is not in the d-band")

        # Oxidation removes s electrons first, then d electrons
        # All these metals have 2 s-electrons in the neutral state
        neutral_d = NEUTRAL_D_ELECTRONS[self.symbol]
        s_removed = min(oxidation, 2)
        d_removed = max(0, oxidation - 2)
        d_electrons = max(0, neutral_d - d_removed)
        return d_electrons

    def d_holes(self, oxidation: float | None = None) -> float:
        return 10 - self.d_electrons(oxidation)


class Edge:
    def __init__(self, symbol: str) -> None:
        element, edges = split_element_edge(symbol)
        self.element = Element(symbol)
        if not edges:
            raise ValueError(f"No known edges in '{symbol}'")
        self.edge = edges[0]

    def __repr__(self) -> str:
        return f"{self.element} {self.edge}"

    def __str__(self) -> str:
        return f"{self.energy} eV: {self.element} {self.edge}"

    def __eq__(self, o: object) -> bool:
        o = Edge(o) if isinstance(o, str) else o
        if isinstance(o, Edge):
            return self.element == o.element and self.edge == o.edge
        return False

    def __hash__(self) -> int:
        return hash(self.element.symbol + self.edge)

    def __gt__(self, o: object) -> bool:
        o = Edge(o) if isinstance(o, str) else o
        if isinstance(o, Edge):
            return self.energy > o.energy
        return False

    def __lt__(self, o: object) -> bool:
        o = Edge(o) if isinstance(o, str) else o
        if isinstance(o, Edge):
            return self.energy < o.energy
        return False

    def _get_props(self) -> dict[str, str | float]:
        this_edge = self.__repr__()
        return _get_edges()[this_edge]

    @property
    def energy(self) -> float:
        """Return energy of edge in eV"""
        return float(self._get_props()['energy'])

    @property
    def orbital(self) -> str:
        """Returns the highest atomic orbital"""
        return str(self._get_props()['orbital'])


class MultiEdge:
    """
    Multiple-edges from a single element
    """
    def __init__(self, *edges: Edge) -> None:
        self.element = edges[0].element
        self.edges = edges

    @classmethod
    def from_symbol(cls, symbol: str) -> "MultiEdge":
        element, edges = split_element_edge(symbol)
        element = Element(element)
        if not edges:
            raise ValueError(f"No known edges in '{symbol}'")
        edges = [Edge(f"{element} {edge}") for edge in edges]
        return cls(*edges)

    @classmethod
    def from_spectra(cls, energy: np.ndarray, signal: np.ndarray | None = None,
                     edge_preference: tuple[str, ...] | None = PREFERRED_EDGES)-> "MultiEdge":
        return find_spectra_edge(energy, signal, edge_preference)

    @classmethod
    def from_range(cls, min_energy_ev: float, max_energy_ev: float | None = None,
                        energy_range_ev: float = 10.,
                        edge_preference: tuple[str, ...] | None = PREFERRED_EDGES) -> "MultiEdge":
        if max_energy_ev is None:
            max_energy_ev = min_energy_ev + (energy_range_ev / 2)
            min_energy_ev = min_energy_ev - (energy_range_ev / 2)
        energy = np.linspace(min_energy_ev, max_energy_ev, 10)
        return find_spectra_edge(energy, edge_preference=edge_preference)

    def __repr__(self) -> str:
        return f"{self.element} {self.symbol}"

    def __iter__(self) -> Iterator[Edge]:
        return iter(self.edges)

    def __len__(self) -> int:
        return len(self.edges)

    def __getitem__(self, item: int) -> Edge:
        return self.edges[item]

    @property
    def symbol(self) -> str:
        edge_str = ','.join([edge.edge for edge in self.edges])
        return edge_str[0] + (edge_str[1:].replace(edge_str[0], '') if len(edge_str) > 1 else "")

    def energies(self) -> list[float]:
        return [edge.energy for edge in self.edges]

    def edge_energy(self, edge: str) -> float | None:
        """Return the energy of a single edge, e.g. L3"""
        edge = edge.lower()
        return next((e.energy for e in self.edges if e.edge.lower() == edge), None)

    def split_energy(self) -> float:
        """Return the energy between edges"""
        if len(self.edges) > 1:
            return sum([edge.energy for edge in self.edges]) / len(self.edges)
        return self.edges[0].energy * 1.05 #+ soc


def xray_edges_in_range(min_energy_ev: float, max_energy_ev: float | None = None,
                        energy_range_ev: float = 10.,
                        search_edges: tuple[str, ...] | None = PREFERRED_EDGES) -> list[Edge]:
    """
    Return list of absorption edges within a given range

    :param min_energy_ev: minimum or central energy, in eV
    :param max_energy_ev: max energy of range, or None
    :param energy_range_ev: range in eV around min_energy_ev, if max is None
    :param search_edges: if not None, only return energies for these edges, e.g. ('L3', 'L2')
    :return: list of Edge objects
    """
    if max_energy_ev is None:
        max_energy_ev = min_energy_ev + (energy_range_ev / 2)
        min_energy_ev = min_energy_ev - (energy_range_ev / 2)
    energies, edge_labels = load_edge_energies(search_edges)
    edge_labels_in_range = edge_labels[(energies > min_energy_ev) & (energies < max_energy_ev)]
    return [Edge(edge) for edge in edge_labels_in_range]


def get_edges(*symbols: str) -> list[Edge]:
    """Return list of Edge objects from symbols"""
    edges = [MultiEdge.from_symbol(symbol) for symbol in symbols]
    return list({edge for multi_edge in edges for edge in multi_edge})


def find_spectra_edge(energy: np.ndarray, signal: np.ndarray | None = None,
                      edge_preference: tuple[str, ...] | None = PREFERRED_EDGES) -> MultiEdge:
    """
    Find edges from a single element in spectra
    :param energy: array of incident photon energies, in eV
    :param signal: array of spectra signal, or None
    :param edge_preference: tuple of preferred edge types, or None to use all edges. e.g. ('L3', 'L2')
    :return: MultiEdge object
    """
    edge_preference = PREFERRED_EDGES if edge_preference is None else edge_preference
    edges_in_range = xray_edges_in_range(energy.min(), energy.max(), search_edges=edge_preference)

    if signal is None:
        # Find element with most edges in range
        elements = [e.element.symbol for e in edges_in_range]
        element_count = [elements.count(e) for e in elements]
        edge_priority = [
            -(edge_preference.index(e.edge)-len(edges_in_range)) * count
            for e, count in zip(edges_in_range, element_count)
        ]
        priority, edge = max(zip(edge_priority, edges_in_range))
    else:
        # Find largest slope
        diff = np.abs(np.diff(signal))
        jumps = diff > 10 * diff.mean()
        if any(jumps):
            print(f"Warning: removing {sum(jumps)} large signal jumps")
            diff[jumps] = diff.mean()  # remove large jumps
        idx = np.argmax(diff)
        edge_energy = energy[idx]
        edge = min(edges_in_range, key=lambda e: abs(e.energy - edge_energy))

    return MultiEdge(*[e for e in edges_in_range if e.element.symbol == edge.element.symbol])

