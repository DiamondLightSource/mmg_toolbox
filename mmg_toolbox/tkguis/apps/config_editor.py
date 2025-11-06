"""
tk widget for editing the Config file
"""
import os

from ..misc.styles import tk, ttk, create_root
from ..misc.logging import create_logger
from ..misc.functions import topmenu
from ..misc.config import get_config, save_config, default_config, C
from ..misc.matplotlib import COLORMAPS
from ..widgets.roi_editor import RoiEditor
from .edit_text import EditText

logger = create_logger(__file__)


class ConfigEditor:
    """
    Edit the Configuration File in an inset window
    """

    def __init__(self, parent: tk.Misc, config: dict | None = None):
        self.root = create_root('Config. Editor', parent)
        # self.root.wm_overrideredirect(True)
        self.config = config or get_config()
        self.config_setters = {}
        self.config_getters = {}

        menu = {
            'Config': {
                'Reset': self.reset_config,
                'Delete config file': self.delete_config,
                'View config file': self.view_config,
            }
        }

        topmenu(self.root, menu)

        self.window = ttk.Frame(self.root, borderwidth=20, relief=tk.RAISED)
        self.window.pack(side=tk.TOP, fill=tk.BOTH)

        frm = ttk.Frame(self.window)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)
        var = ttk.Label(frm, text='Edit Config. Parameters', style="title.TLabel")
        var.pack(expand=tk.YES, fill=tk.X, padx=10, pady=10)

        # parameter entry boxes
        self.create_param(C.conf_file, 'Config File:')
        self.create_param(C.beamline, 'Beamline:')
        self.create_param(C.normalise_factor, 'Normalise:')
        self.create_tuple_param(C.text_size, 'Text Size:', 'chars x rows')
        self.create_tuple_param(C.plot_size, 'Plot Size:', 'w x h inches')
        self.create_tuple_param(C.image_size, 'Image Size:', 'w x h inches')
        self.create_tuple_param(C.plot_max_percent, 'Max Plot Size:', 'w x h % of screen')
        self.create_param(C.plot_dpi, 'Figure DPI:')
        self.create_list_param(C.default_colormap, 'Default colormap:', *COLORMAPS)
        self.create_param(C.metadata_label, 'Metadata label', button=self.metadata_list_window)
        self.create_text_param(C.metadata_string, 'Metadata expression')

        # Buttons at bottom
        frm = ttk.Frame(self.window)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)
        var = ttk.Button(frm, text='ROIs', command=self.roi_window)
        var.pack(side=tk.LEFT, expand=tk.YES)
        var = ttk.Button(frm, text='Save', command=self.save_config)
        var.pack(side=tk.LEFT, expand=tk.YES)
        var = ttk.Button(frm, text='Update', command=self.update_config)
        var.pack(side=tk.LEFT, fill=tk.X, expand=tk.YES)

    def create_param(self, config_name: str, label: str, button=None):
        variable = tk.StringVar(self.root, self.config.get(config_name, ''))
        get_type = type(self.config.get(config_name, ''))
        self.config_setters[config_name] = lambda name=config_name: str(self.config.get(name, ''))
        self.config_getters[config_name] = lambda: get_type(variable.get())

        frm = ttk.Frame(self.window)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH, padx=10, pady=5)
        ttk.Label(frm, text=label, width=20).pack(side=tk.LEFT, padx=2)
        ttk.Entry(frm, textvariable=variable).pack(side=tk.LEFT, fill=tk.X, expand=tk.YES)
        if button is not None:
            ttk.Button(frm, text='...', command=button, width=3).pack(side=tk.LEFT)

    def create_tuple_param(self, config_name: str, label: str, units: str = ''):
        values = self.config.get(config_name, ())
        types = [type(val) for val in values]
        tuple_vars = tuple(
            tk.StringVar(self.root, str(val))
            for val in values
        )

        def setter(name=config_name, _vars=tuple_vars):
            _values = self.config.get(name, ())
            for _var, _val in zip(_vars, _values):
                _var.set(str(_val))

        def getter():
            return tuple([
                var_type(_var.get())
                for _var, var_type in zip(tuple_vars, types)
            ])

        frm = ttk.Frame(self.window)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH, padx=10, pady=5)
        ttk.Label(frm, text=label, width=20).pack(side=tk.LEFT, padx=2)
        for var in tuple_vars:
            ttk.Entry(frm, textvariable=var, width=4).pack(side=tk.LEFT)
        ttk.Label(frm, text=units).pack(side=tk.LEFT, fill=tk.X)

        self.config_setters[config_name] = setter
        self.config_getters[config_name] = getter
        setter()

    def create_list_param(self, config_name: str, label: str, *list_names: str):
        frm = ttk.Frame(self.window)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH, padx=10, pady=5)
        ttk.Label(frm, text=label, width=20).pack(side=tk.LEFT, padx=2)
        default = self.config.get(config_name, list_names[0])
        var = tk.StringVar(self.root, default)
        self.config_getters[config_name] = var.get
        self.config_setters[config_name] = lambda name=config_name: var.set(self.config.get(name, ''))
        var2 = tk.StringVar(self.root, default)
        cbox = ttk.Combobox(frm, textvariable=var2, values=list_names)
        cbox.pack(side=tk.LEFT)
        cbox.bind('<<ComboboxSelected>>', lambda e: var.set(var2.get()))

    def create_text_param(self, config_name: str, label: str):

        def button(name=config_name):
            text = self.config.get(name, '')
            new_text = EditText(
                expression=text,
                parent=self.root,
                textwidth=self.config.get(C.text_size, (50, 20))[0]
            ).show()
            if new_text:
                self.config[name] = new_text

        frm = ttk.Frame(self.window)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH, padx=10, pady=5)
        ttk.Label(frm, text=label, width=20).pack(side=tk.LEFT, padx=2)
        ttk.Button(frm, text='Edit', command=button, width=3).pack(side=tk.LEFT)

    def _update_config(self):
        updated_config = {
            name: var() for name, var in self.config_getters.items()
        }
        self.config.update(updated_config)

    def update_config(self):
        self._update_config()
        self.root.destroy()

    def set_from_config(self, config: dict):
        self.config.update(config)
        for name, setter in self.config_setters.items():
            print(name, self.config[name])
            setter()

    def reset_config(self):
        beamline = self.config_getters[C.beamline]()
        default = default_config(beamline)
        self.set_from_config(default)

    def delete_config(self):
        config_file = self.config.get(C.conf_file)
        if config_file and os.path.isfile(config_file):
            from tkinter import messagebox
            answer = messagebox.askyesno(
                title='Config',
                message='Delete config file?\n {}'.format(config_file),
                parent=self.root
            )
            if answer:
                os.remove(config_file)
                print('Removed config file')

    def save_config(self):
        self._update_config()
        save_config(self.config)
        self.root.destroy()

    def view_config(self):
        config_file = self.config.get(C.conf_file)
        if config_file and os.path.isfile(config_file):
            from .edit_text import EditText
            import json

            dump = json.dumps(json.load(open(config_file, 'r')), sort_keys=False, indent=4)
            EditText(dump, self.root).show()

    def roi_window(self):
        window = create_root('Regions of Interest (ROIs)', self.root)
        RoiEditor(window, self.config)

    def metadata_list_window(self):
        MetadataListEditor(self.root, self.config)


class MetadataListEditor:
    """
    Edit the metadata list
    """

    def __init__(self, parent: tk.Misc, config: dict | None = None):
        self.root = create_root('Metadata List', parent)
        # self.root.wm_overrideredirect(True)
        self.param_list = []

        if config is None:
            self.config = get_config()
        else:
            self.config = config

        metadata_list = self.config.get(C.metadata_list, {})
        self.window = ttk.Frame(self.root)
        self.window.pack(fill=tk.BOTH, expand=tk.YES)
        for name, expression in metadata_list.items():
            self.create_entry(name, expression)
        self.create_entry('', '')

        frm = ttk.Frame(self.root)
        frm.pack(side=tk.TOP, anchor=tk.W, padx=5)
        ttk.Button(frm, text='+', command=self.create_entry, width=4).pack(side=tk.LEFT)

        frm = ttk.Frame(self.root)
        frm.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)
        ttk.Button(frm, text='Update', command=self.update).pack(fill=tk.X, expand=tk.YES)

    def create_entry(self, name: str = '', expression: str = ''):
        name_var = tk.StringVar(self.root, name)
        expression_var = tk.StringVar(self.root, expression)
        self.param_list.append((name_var, expression_var))

        frm = ttk.Frame(self.window)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH, padx=10, pady=5)
        ttk.Entry(frm, textvariable=name_var, width=10).pack(side=tk.LEFT, fill=tk.X, expand=tk.YES)
        ttk.Entry(frm, textvariable=expression_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=tk.YES)

    def update(self):
        metadata_list = {
            name.get(): expression.get() for name, expression in self.param_list
            if name.get() and expression.get()
        }
        self.config[C.metadata_list] = metadata_list
        self.root.destroy()

