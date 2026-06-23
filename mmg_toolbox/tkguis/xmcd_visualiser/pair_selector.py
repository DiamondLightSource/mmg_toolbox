import tkinter as tk
from tkinter import ttk
from typing import Callable

from mmg_toolbox.utils.misc_functions import string2numbers
from mmg_toolbox.xas import SpectraContainer, polarised_pairs
from mmg_toolbox.xas.spectra import BACKGROUND_FUNCTIONS
from ..misc.functions import create_scrollable_window
from .average_tab import Average


BACKGROUNDS = ['None'] + list(BACKGROUND_FUNCTIONS)


class PairSelector:
    def __init__(self, root: tk.Misc, base: Average, scan_range_str: str = '12345-12355'):
        self._base = base
        self.root = root

        # variables
        modes = ['TEY', 'TFY']
        backgrounds = BACKGROUNDS
        self.scan_range = tk.StringVar(self.root, '')
        self.dls_loader = tk.BooleanVar(self.root, False)
        self.mode_option = tk.StringVar(self.root, modes[0])
        self.bkg_option = tk.StringVar(self.root, backgrounds[0])
        self.pair_numbers: list[tuple[tk.IntVar, tk.IntVar, Callable]] = []

        grid_options = dict(padx=5, pady=5, sticky='nsew')
        self.root.rowconfigure(0, weight=0)  # scan numbers
        self.root.rowconfigure(1, weight=1)  # pairs
        self.root.rowconfigure(2, weight=0)  # options

        # Files
        frm = ttk.LabelFrame(self.root, text='Scan Numbers')
        # frm.pack(side='top', fill='x')
        frm.grid(row=0, column=0, **grid_options)
        var = entry_with_placeholder(frm, self.scan_range, scan_range_str)
        var.bind('<Return>', self.btn_find_pairs)
        var.pack(side='left')
        ttk.Checkbutton(frm, text='DLS Loader', variable=self.dls_loader).pack(side='left')
        ttk.Button(frm, text='List', command=self.btn_list_scans).pack(side='left')
        ttk.Button(frm, text='Find Pairs', command=self.btn_find_pairs).pack(side='left')

        # Pairs
        frm = ttk.LabelFrame(self.root, text='Pairs', relief='groove')
        # frm.pack(side='top', fill='x')
        frm.grid(row=1, column=0, **grid_options)
        self.pair_frm = create_scrollable_window(frm, height=100, width=100)
        # self.pair_frm.pack(side='top', fill='x')
        ttk.Button(frm, text='+', command=self.add_pair).pack(side='top', fill='x')
        self.add_pair()

        # Options
        frm = ttk.LabelFrame(self.root, text='Options')
        # frm.pack(side='top', fill='x')
        frm.grid(row=2, column=0, **grid_options)
        self.ch_modes = ttk.OptionMenu(frm, self.mode_option, modes[0], *modes,
                                       command=self._base.update_plots)
        self.ch_modes.pack(side='top', fill='x', padx=4)
        ttk.OptionMenu(frm, self.bkg_option, backgrounds[0], *backgrounds,
                       command=self._base.update_plots).pack(side='top', fill='x', padx=4)
        ttk.Button(frm, text='Plot', command=self._base.plot_pairs).pack(side='top', fill='x', padx=10, pady=3)

    def add_pair(self, number1: int | None = None, number2: int | None = None):
        var1 = tk.IntVar(self.root, number1)
        var2 = tk.IntVar(self.root, number2)
        label = tk.StringVar(self.root, '')

        frm = ttk.Frame(self.pair_frm)
        frm.pack(side='top', fill='x')

        def update_label(event=None):
            n1, n2 = var1.get(), var2.get()
            if n1 and n2:
                s1, s2 = self._base.load_pair(n1, n2)
                subtract = s1 - s2
                label.set(subtract.label())

        def remove():
            self.pair_numbers.remove((var1, var2, update_label))
            frm.destroy()

        en = ttk.Entry(frm, textvariable=var1, width=10)
        en.pack(side='left')
        en.bind('<Return>', update_label)
        en = ttk.Entry(frm, textvariable=var2, width=10)
        en.pack(side='left')
        en.bind('<Return>', update_label)
        ttk.Button(frm, text='X', command=remove, width=1).pack(side='left', padx=1)
        ttk.Label(frm, textvariable=label).pack(side='left')
        self.pair_numbers.append((var1, var2, update_label))
        update_label()

    def get_pair_numbers(self) -> list[tuple[int, int]]:
        return [
            vals for v1, v2, update in self.pair_numbers
            if all(vals := (v1.get(), v2.get()))
        ]

    def set_pair_numbers(self, pair_numbers: list[tuple[int, int]]) -> None:
        for n, (scan_no1, scan_no2) in enumerate(pair_numbers):
            if n < len(self.pair_numbers):
                v1, v2, update = self.pair_numbers[n]
                v1.set(scan_no1)
                v2.set(scan_no1)
                update()
            else:
                self.add_pair(scan_no1, scan_no2)
            if n == 0:
                scan, = self._base.load_scans(scan_no1)
                self.update_modes(scan)

    def update_modes(self, scan: SpectraContainer):
        modes = list(scan.spectra)
        self.ch_modes.set_menu(modes[0], *modes)

    def btn_list_scans(self):
        from ..apps.edit_text import EditText
        scan_numbers = string2numbers(self.scan_range.get())
        scans = self._base.load_scans(*scan_numbers, dls_loader=self.dls_loader.get())
        out = '\n'.join(s.label() for s in scans)
        EditText(
            expression=out,
            parent=self.root,
            textwidth=50,
            title=f'Spectra Scans in range: {scan_numbers}',
        )

    def btn_find_pairs(self, event=None):
        scan_numbers = string2numbers(self.scan_range.get())
        scans = self._base.load_scans(*scan_numbers, dls_loader=self.dls_loader.get())
        if scans:
            self.update_modes(scans[0])
            pol_pairs = polarised_pairs(*scans)
            for n, (s1, s2) in enumerate(pol_pairs):
                if n < len(self.pair_numbers):
                    v1, v2, update = self.pair_numbers[n]
                    v1.set(s1.metadata.scan_no)
                    v2.set(s2.metadata.scan_no)
                    update()
                else:
                    self.add_pair(s1.metadata.scan_no, s2.metadata.scan_no)
            self._base.plot_pairs()


def entry_with_placeholder(root: tk.Misc, text: tk.Variable, placeholder_text: str, **kwargs) -> ttk.Entry:
    """Create an entry widget with placeholder text"""

    def on_focus_in(event):
        if entry.get() == placeholder_text:
            entry.delete(0, tk.END)
            entry.config(fg="black")

    def on_focus_out(event):
        if entry.get() == "":
            entry.insert(0, placeholder_text)
            entry.config(fg="grey")

    entry = tk.Entry(root, textvariable=text, fg="grey", **kwargs)
    entry.insert(0, placeholder_text)

    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)
    return entry
