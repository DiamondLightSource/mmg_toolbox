"""
tk widget for editing the Config file
"""

from ..misc.styles import tk, ttk, create_root
from ..misc.logging import create_logger
from ..misc.config import get_config, save_config, default_config
from ..misc.matplotlib import COLORMAPS, DEFAULT_COLORMAP

logger = create_logger(__file__)

TEXTWIDTH = 50


class ConfigEditor:
    """
    Edit the Configuration File in an inset window
    """

    def __init__(self, parent: tk.Misc, config: dict | None = None):
        self.root = create_root('Config. Editor', parent)
        # self.root.wm_overrideredirect(True)

        if config is None:
            self.config = get_config()
        else:
            self.config = config
        self.config_vars = {}

        self.window = ttk.Frame(self.root, borderwidth=20, relief=tk.RAISED)
        self.window.pack(side=tk.TOP, fill=tk.BOTH)

        frm = ttk.Frame(self.window)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)
        var = ttk.Label(frm, text='Edit Config. Parameters', style="Red.TLabel")
        var.pack(expand=tk.YES, fill=tk.X, padx=10, pady=10)

        # reset
        ttk.Button(frm, text='Reset', command=self.reset_config).pack(side=tk.TOP, fill=tk.X)

        # parameter entry boxes
        self.create_param('config_file', 'Config File:')
        self.create_param('beamline', 'Beamline:')
        self.create_param('normalise_factor', 'Normalise:')
        # self.create_param('figure_size', 'Plot Size:')
        # self.create_param('image_size', 'Image Size:')
        # self.create_param('figure_dpi', 'Figure DPI:')

        # Colormaps
        frm = ttk.Frame(self.window)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.X)
        default_colormap = self.config.get('default_colormap', DEFAULT_COLORMAP)
        self.config_vars['default_colormap'] = tk.StringVar(self.root, default_colormap)
        colormap = tk.StringVar(self.root, default_colormap)
        var = ttk.Combobox(frm, textvariable=colormap, values=COLORMAPS)
        var.pack(side=tk.LEFT)
        var.bind('<<ComboboxSelected>>', lambda e: self.config_vars['default_colormap'].set(colormap.get()))

        # metadata string textbox
        frm = ttk.LabelFrame(self.window, text='Metadata expression')
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH, padx=5, pady=5)

        self.text = tk.Text(frm, wrap=tk.NONE, width=TEXTWIDTH)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)
        self.text.insert('1.0', self.config.get('metadata_string', ''))

        var = ttk.Scrollbar(frm, orient=tk.VERTICAL, command=self.text.yview)
        var.pack(side=tk.LEFT, fill=tk.Y)
        self.text.configure(yscrollcommand=var.set)

        # Buttons at bottom
        frm = ttk.Frame(self.window)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)
        var = ttk.Button(frm, text='Save', command=self.save_config)
        var.pack(side=tk.LEFT, expand=tk.YES)
        var = ttk.Button(frm, text='Update', command=self.save_config)
        var.pack(side=tk.LEFT, fill=tk.X, expand=tk.YES)

    def create_param(self, config_name: str, label: str):
        variable = tk.StringVar(self.root, self.config.get(config_name, ''))
        self.config_vars[config_name] = variable

        frm = ttk.Frame(self.window)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH, padx=10, pady=5)
        var = ttk.Label(frm, text=label, width=20)
        var.pack(side=tk.LEFT, padx=2)
        var = ttk.Entry(frm, textvariable=variable)
        var.pack(side=tk.LEFT, fill=tk.X, expand=tk.YES)

    def update_config(self):
        updated_config = {
            name: var.get() for name, var in self.config_vars.items()
        }
        updated_config['metadata_string'] = self.text.get('1.0', tk.END)
        self.config.update(updated_config)
        self.root.destroy()

    def set_from_config(self, config: dict):
        for name, var in self.config_vars.items():
            if name in config:
                var.set(config[name])
        if 'metadata_string' in config:
            self.text.delete('1.0', tk.END)
            self.text.insert('1.0', config['metadata_string'])

    def reset_config(self):
        beamline = self.config_vars['beamline'].get()
        default = default_config(beamline)
        self.set_from_config(default)

    def save_config(self):
        config = {
            name: var.get() for name, var in self.config_vars.items()
        }
        save_config(config)
        self.root.destroy()

