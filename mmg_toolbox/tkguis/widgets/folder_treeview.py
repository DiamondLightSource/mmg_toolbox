"""
Treeview widget for folders
"""

import os
import time
import tkinter as tk
from tkinter import ttk
from threading import Thread

from mmg_toolbox.utils.file_functions import list_files, list_path_time, display_timestamp, get_hdf_string, folder_summary
from mmg_toolbox.utils.env_functions import open_terminal
from ..misc.styles import create_hover
from ..misc.functions import select_folder, post_right_click_menu
from ..misc.jupyter import launch_jupyter_notebook
from ..misc.logging import create_logger
from .treeview import CanvasTreeview

logger = create_logger(__file__)


class FolderTreeViewFrame(CanvasTreeview):
    """Frame with TreeView and entry for Folders"""

    def __init__(self, extension: str, root: tk.Misc, initial_directory: str | None = None):
        self.root = root
        self.search_str = ""
        self.search_time = time.time()
        self.search_reset = 3.0  # seconds
        self._prev_folder = ''
        self.extensions = (extension, '.*')

        # Variables
        self.filepath = tk.StringVar(root, os.path.expanduser('~'))
        self.extension = tk.StringVar(root, extension)
        self.hdf_path = tk.StringVar(root, '')
        self.show_hidden = tk.BooleanVar(root, False)
        self.read_datasets = tk.BooleanVar(root, True)
        self.search_label = tk.StringVar(root, '')

        # Columns
        columns = [
            # (name, text, width, reverse, sort_col)
            ("#0", 'Folder', 200, False, None),
            ("modified", 'Modified', 150, True, "modified_time"),
            ('modified_time', 'Modified', 0, False, None),
            ("files", 'Files', 30, False, None),
            ("data", 'Data', 200, False, None),
            ("filepath", 'File Path', 0, False, None),
        ]

        # Build widgets
        self.ini_folderpath()
        super().__init__(root, *columns)
        self.tree.bind("<<TreeviewOpen>>", self.populate_files)
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Return>", self.on_double_click)
        self.tree.bind("<KP_Enter>", self.on_double_click)
        self.tree.bind('<KeyPress>', self.on_key_press)
        self.tree.bind("<Button-3>", self.right_click_menu())

        # search label
        frm = ttk.Frame(self.root)
        frm.pack(fill=tk.X, side=tk.TOP)
        ttk.Label(frm, textvariable=self.search_label, style='smallMsg.TLabel').pack()

        # Populate
        if initial_directory:
            self.filepath.set(initial_directory)
        self.populate_folders()

    "======================================================"
    "================= init functions ====================="
    "======================================================"

    def ini_folderpath(self):
        frm = ttk.Frame(self.root)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)

        var = ttk.Button(frm, text='Browse', command=self.browse_folder, width=8)
        var.pack(side=tk.LEFT)
        var = ttk.Button(frm, text=u'\u2302', command=self.home_folder, width=3)
        var.pack(side=tk.LEFT)
        var = ttk.Button(frm, text=u'\u2190', command=self.back_folder, width=3)
        var.pack(side=tk.LEFT)
        var = ttk.Button(frm, text=u'\u2191', command=self.up_folder, width=3)
        var.pack(side=tk.LEFT)
        var = ttk.Entry(frm, textvariable=self.filepath, width=30)
        var.pack(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH)
        var.bind('<Return>', self.populate_folders)
        var.bind('<KP_Enter>', self.populate_folders)

        # var = ttk.Checkbutton(frm, text='Show hidden', variable=self.show_hidden, command=self.populate_folders)
        # var.pack(side=tk.LEFT)

        var = ttk.Button(frm, text='Options', command=self.file_options)
        var.pack(side=tk.RIGHT)
        var = ttk.Button(frm, text='Search', command=self.search_options)
        var.pack(side=tk.RIGHT)

    "======================================================"
    "=============== populate functions ==================="
    "======================================================"

    def _get_extension(self):
        extension = self.extension.get()
        return '' if extension.lower() in ['.*', 'any'] else extension

    def set_folder(self, folder_path: str):
        self.filepath.set(folder_path)
        self.populate_folders()

    def populate_folders(self, event=None):
        path_time = list_path_time(self.filepath.get())
        self._delete_tree()
        # ('modified', 'modified_time', 'files', 'dataset', 'filepath')
        self.tree.insert("", tk.END, text="..", values=('', '', '', '', ''))
        hide_hidden = not self.show_hidden.get()
        for path, mtime in path_time:
            name_str = os.path.basename(path)
            if hide_hidden and name_str != '.' and (name_str.startswith('.') or name_str.startswith('_')):
                continue
            if path == '.':
                path = self.filepath.get()
            time_str = display_timestamp(mtime)
            self.tree.insert("", tk.END, text=name_str, values=(time_str, mtime, '', '', path))
        self.update_folder_nfiles()

    def update_folder_nfiles(self, event=None):
        """Update the number of files in each directory, as a seperate process"""

        extension = self._get_extension()

        def fun():
            for branch in self.tree.get_children():  # folders
                if not self.tree.winfo_exists():
                    return
                folder = self.tree.set(branch, 'filepath')
                nfiles = len(list_files(folder, extension=extension))
                self.tree.set(branch, 'files', nfiles)
                if nfiles > 0:  # add subdirectory for files
                    self.tree.insert(branch, tk.END)  # empty
                    self.tree.item(branch, open=False)
        th = Thread(target=fun)
        #TODO: add deamon?
        th.start()  # will run until complete, may error if TreeView is destroyed

    def populate_files(self, event=None):
        """Add list of files below folder on folder expand"""
        item = self.tree.focus()
        if not item:
            return
        nfiles = self.tree.set(item, 'files')  # number of hdf files in folder
        if not nfiles:
            return
        else:
            # if len(self.tree.get_children(item)) == 1:
            # remove old entries
            self.tree.delete(*self.tree.get_children(item))
            # add hdf files
            path = self.tree.set(item, 'filepath')
            files = list_files(path, self._get_extension())
            start_time = time.time()
            for file in files:
                timestamp = os.stat(file).st_mtime
                mtime = display_timestamp(timestamp)
                self.tree.insert(item, tk.END, text=os.path.basename(file), values=(mtime, timestamp, '', '', file))
            if self.read_datasets.get():
                self.update_datasets(self.hdf_path.get())
            logger.info(f"Expanding took {time.time() - start_time:.3g} s")

    def update_datasets(self, event=None):
        """Update dataset values column for hdf files under open folders"""
        pass

    "======================================================"
    "============= navigation functions ==================="
    "======================================================"

    def browse_folder(self):
        self._prev_folder = self.filepath.get()
        folder_directory = select_folder(parent=self.root)
        if folder_directory:
            self.set_folder(folder_directory)

    def home_folder(self):
        self._prev_folder = self.filepath.get()
        self.set_folder(os.path.expanduser("~"))

    def back_folder(self):
        if self._prev_folder:
            self.set_folder(self._prev_folder)

    def up_folder(self):
        self._prev_folder = self.filepath.get()
        self.set_folder(os.path.abspath(os.path.join(self.filepath.get(), '..')))

    def on_double_click(self, event=None):
        """Open a folder or open a file in a new window"""
        filename, foldername = self.get_filepath()
        if filename:
            pass
        else:
            self.filepath.set(foldername)
            self.populate_folders()

    "======================================================"
    "================= button functions ==================="
    "======================================================"

    def file_options(self):
        window, fun_close = create_hover(self.root)

        frm = ttk.Frame(window, borderwidth=2)
        frm.pack(side=tk.TOP, fill=tk.BOTH)
        ttk.Label(frm, text='Extension: ').pack(side=tk.LEFT)
        ttk.OptionMenu(frm, self.extension, self.extension.get(), *self.extensions).pack(side=tk.LEFT)

        frm = ttk.Frame(window, borderwidth=2)
        frm.pack(side=tk.TOP, fill=tk.BOTH)
        ttk.Checkbutton(
            frm, text='Show hidden files', variable=self.show_hidden, command=self.populate_folders
        ).pack(side=tk.LEFT)
        
        def close():
            self.update_datasets()
            fun_close()

        frm = ttk.Frame(window, borderwidth=10)
        frm.pack(side=tk.BOTTOM, fill=tk.BOTH)
        ttk.Button(frm, text='Close', command=close).pack(side=tk.LEFT, fill=tk.X, expand=tk.YES)
        
        return window

    def search_options(self):
        window, fun_close = create_hover(self.root)

        file_search = tk.StringVar(window, '')
        match_case = tk.BooleanVar(window, False)
        whole_word = tk.BooleanVar(window, False)

        frm = ttk.Frame(window, borderwidth=2)
        frm.pack(side=tk.TOP, fill=tk.BOTH)
        ttk.Label(frm, text='Filename: ').pack(side=tk.LEFT)
        ttk.Entry(frm, textvariable=file_search, width=20).pack(side=tk.LEFT)
        ttk.Checkbutton(frm, text='Match case: ', variable=match_case).pack(side=tk.LEFT)
        ttk.Checkbutton(frm, text='Whole word: ', variable=whole_word).pack(side=tk.LEFT)

        def search():
            self._search(
                query=file_search.get(),
                match_case=match_case.get(),
                whole_word=whole_word.get(),
            )

        frm = ttk.Frame(window, borderwidth=10)
        frm.pack(side=tk.BOTTOM, fill=tk.BOTH)
        ttk.Button(frm, text='Search', command=search).pack(side=tk.LEFT, fill=tk.X, expand=tk.YES, padx=5)
        ttk.Button(frm, text='Close', command=fun_close).pack(side=tk.LEFT, fill=tk.X, expand=tk.YES)

        return window

    "======================================================"
    "================ general functions ==================="
    "======================================================"

    def get_filepath(self) -> tuple[str, str]:
        """
        Return filepath and folderpath of current selection
        :returns filename: str full filepath or None if selection isn't a file
        :returns foldername: str folder path
        """
        filename = None
        foldername = self.filepath.get()
        for iid in self.tree.selection():
            item = self.tree.item(iid)
            if self.tree.set(iid, 'files') == '' and item['text'] != '..':  # item is a file
                filename = self.tree.set(iid, 'filepath')
                foldername = os.path.dirname(filename)
            else:  # item is a folder
                foldername = self.tree.set(iid, 'filepath')
        logger.debug(f"Selected item: filename='{filename}', foldername='{foldername}'")
        return filename, foldername

    def copy_path(self):
        filepath, folderpath = self.get_filepath()
        self.root.clipboard_clear()
        if filepath:
            self.root.clipboard_append(filepath)
        else:
            self.root.clipboard_append(folderpath)

    def open_terminal(self):
        filepath, folderpath = self.get_filepath()
        cmd = f"cd {folderpath}"
        open_terminal(cmd)

    def open_jupyter_notebook(self):
        filename, foldername = self.get_filepath()
        if filename:
            launch_jupyter_notebook('notebook', file=filename)
        else:
            launch_jupyter_notebook('notebook', directory=foldername)

    def _right_click_folder(self) -> tk.Menu:
        # right-click menu - folder options
        m_folder = tk.Menu(self.root, tearoff=0)
        m_folder.add_command(label="Copy path", command=self.copy_path)
        m_folder.add_command(label="Open Terminal", command=self.open_terminal)
        # TODO: add these
        # m_folder.add_command(label='Launch Jupyter', command=self.launch_jupyter)
        # m_folder.add_command(mode="Open Folder Datasets", command=self.menu_folder_files)
        # m_folder.add_command(mode="Open Folder Plots", command=self.menu_folder_plot)
        # # m_folder.add_command(mode="Display Contents", command=self.menu_folder_plot)
        m_folder.add_command(label="Display Summary", command=self.open_folder_summary)
        return m_folder

    def _right_click_file(self) -> tk.Menu:
        # right-click menu - file options
        m_file = tk.Menu(self.root, tearoff=0)
        #TODO: add these
        m_file.add_command(label="Copy path", command=self.copy_path)
        # m_file.add_command(mode="open Treeview", command=self.open_nexus_treeview)
        # m_file.add_command(mode="open Plot", command=self.open_nexus_plot)
        # m_file.add_command(mode="open Image", command=self.open_nexus_image)
        # m_file.add_command(mode="open Namespace", command=self.menu_namespace_gui)
        # m_file.add_command(mode="open Nexus Classes", command=self.menu_class_gui)
        return m_file

    def right_click_menu(self):
        logger.info('Creating right click menu')
        def menu_popup(event):
            # select item
            iid = self.tree.identify_row(event.y)
            if iid:
                self.tree.selection_set(iid)
                filename, foldername = self.get_filepath()
                if filename:
                    logger.debug(f"Right click menu created for file: {filename}")
                    menu = self._right_click_file()
                else:
                    logger.debug(f"Right click menu created for folder: {foldername}")
                    menu = self._right_click_folder()
                post_right_click_menu(menu, event.x_root, event.y_root)
        return menu_popup

    def _delete_tree(self):
        self.tree.delete(*self.tree.get_children())

    def _on_close(self):
        # self.root.unbind_all('<KeyPress>')
        self.root.destroy()

    def on_key_press(self, event):
        """any key press performs search of folders, selects first matching folder"""
        # return if clicked on entry box
        # event.widget == self.tree
        if str(event.widget).endswith('entry'):
            return
        # reset search str after reset time
        ctime = time.time()
        if ctime > self.search_time + self.search_reset:
            self.search_label.set('')
            self.search_str = ""
        # update search time, add key to query
        self.search_time = ctime
        self.search_str += event.char
        self.search_label.set(self.search_str)

        self.tree.selection_remove(self.tree.selection())
        # search folder list
        for branch in self.tree.get_children():  # folders
            folder = self.tree.item(branch)['text']
            if self.search_str in folder[:len(self.search_str)].lower():
            # if folder.lower().startswith(self.search_str):
                self.tree.selection_add(branch)
                self.tree.see(branch)
                break

    "======================================================"
    "=============== widget functions ====================="
    "======================================================"

    def open_nexus_treeview(self):
        filename, foldername = self.get_filepath()
        logger.info(f"Opening nexus viewer for filename: {filename}")
        if filename:
            from .. import create_nexus_viewer
            create_nexus_viewer(filename, parent=self.root)

    def open_nexus_plot(self):
        filename, foldername = self.get_filepath()
        logger.info(f"Opening nexus plot viewer for filename: {filename}")
        if filename:
            from ..apps.nexus import create_nexus_plotter
            create_nexus_plotter(filename, parent=self.root)

    def open_nexus_image(self):
        filename, foldername = self.get_filepath()
        logger.info(f"Opening nexus image viewer for filename: {filename}")
        if filename:
            from ..apps.nexus import create_nexus_image_plotter
            create_nexus_image_plotter(filename, parent=self.root)

    def open_folder_summary(self):
        filename, foldername = self.get_filepath()
        logger.info(f"Opening folder summary for filename: {filename}")
        if foldername:
            from mmg_toolbox.tkguis.apps.edit_text import EditText
            summary = folder_summary(foldername)
            EditText(summary, self.root).show()

    "======================================================"
    "================= misc functions ====================="
    "======================================================"

    def _search(self, query: str, match_case: bool = False, whole_word: bool = False,
                file_only: bool = False, data_only: bool = False):
        for branch in self.tree.get_children():  # folders
            # folder = self.tree.item(branch)['text']
            for leaf in self.tree.get_children(branch):  # files
                item = self.tree.item(leaf)
                if len(item['values']) < 3:
                    continue
                file = item['text']
                value = self.tree.set(leaf, 'data')
                if file_only:
                    test = file
                elif data_only:
                    test = value
                else:
                    test = f"{file} {value}"
                test = test if match_case else test.lower()
                test = test.split() if whole_word else test
                if query in test:
                    self.tree.selection_add(leaf)
                    self.tree.see(leaf)


class NexusFolderTreeViewFrame(FolderTreeViewFrame):
    def __init__(self, root: tk.Misc, initial_directory: str | None = None, hdf_path: str | None = None):
        logger.info('Creating NexusFolderTreeViewFrame')
        super().__init__('.nxs', root, initial_directory)
        self.extensions = ('.nxs', '.hdf', '.hdf5', '.h5', '.*')
        if hdf_path:
            self.hdf_path.set(hdf_path)

    def _right_click_file(self) -> tk.Menu:
        # right-click menu - file options
        m_file = super()._right_click_file()
        m_file.add_command(label="open Treeview", command=self.open_nexus_treeview)
        m_file.add_command(label="open Plot", command=self.open_nexus_plot)
        m_file.add_command(label="open Image", command=self.open_nexus_image)
        # m_file.add_command(mode="open Namespace", command=self.menu_namespace_gui)
        # m_file.add_command(mode="open Nexus Classes", command=self.menu_class_gui)
        return m_file

    def on_double_click(self, event=None):
        """Open a folder or open a file in a new window"""
        if not self.tree.focus():
            return
        iid = self.tree.focus()
        item = self.tree.item(iid)
        if self.tree.set(iid, 'files') == '' and item['text'] != '..':
            self.open_nexus_treeview()
        else:
            # item is a folder, open folder
            self._prev_folder = self.filepath.get()
            self.set_folder(os.path.abspath(os.path.join(self._prev_folder, item['text'])))

    def update_datasets(self, event=None):
        """Update dataset values column for hdf files under open folders"""

        def fn():
            hdf_path = self.hdf_path.get()
            self.tree.heading("data", text=hdf_path)
            for branch in self.tree.get_children():  # folders
                folder = self.tree.set(branch, 'filepath')
                for leaf in self.tree.get_children(branch):  # files
                    if not self.tree.winfo_exists():
                        return
                    file = self.tree.item(leaf)['text']
                    if file:
                        filename = os.path.join(folder, file)
                        value = get_hdf_string(filename, hdf_path, '...')
                        self.tree.set(leaf, 'data', value)

        th = Thread(target=fn)
        th.start()  # will run until complete, may error if TreeView is destroyed

    def file_options(self):
        from hdfmap import create_nexus_map
        window = super().file_options()

        filename, foldername = self.get_filepath()
        hdf_filename = tk.StringVar(window, filename if filename else '')
        dataset_name = tk.StringVar(window, '')

        def get_hdf_path(event):
            _filename = hdf_filename.get()
            _name = dataset_name.get()
            if _filename and _name:
                nexus_map = create_nexus_map(filename)
                self.hdf_path.set(
                    nexus_map.get_path(_name)
                )

        sec = ttk.LabelFrame(window, text='NeXus Files')
        sec.pack(side=tk.TOP, fill=tk.BOTH)

        frm = ttk.Frame(sec, borderwidth=2)
        frm.pack(side=tk.TOP, fill=tk.BOTH)
        ttk.Checkbutton(
            frm, text='Read dataset', variable=self.read_datasets
        ).pack(side=tk.LEFT)

        frm = ttk.Frame(sec, borderwidth=2)
        frm.pack(side=tk.TOP, fill=tk.BOTH)
        ttk.Label(frm, text='File:', width=12).pack(side=tk.LEFT)
        var = ttk.Entry(frm, textvariable=hdf_filename)
        var.pack(side=tk.LEFT)
        var.bind('<Return>', get_hdf_path)
        var.bind('<KP_Enter>', get_hdf_path)

        frm = ttk.Frame(sec, borderwidth=2)
        frm.pack(side=tk.TOP, fill=tk.BOTH)
        ttk.Label(frm, text='Name:', width=12).pack(side=tk.LEFT)
        var = ttk.Entry(frm, textvariable=dataset_name)
        var.pack(side=tk.LEFT)
        var.bind('<Return>', get_hdf_path)
        var.bind('<KP_Enter>', get_hdf_path)

        frm = ttk.Frame(sec, borderwidth=2)
        frm.pack(side=tk.TOP, fill=tk.BOTH)
        # ttk.Button(frm, text='NeXus Dataset Path', command=self.select_dataset).pack(side=tk.LEFT)
        ttk.Label(frm, text='Path:', width=12).pack(side=tk.LEFT)
        var = ttk.Entry(frm, textvariable=self.hdf_path)
        var.pack(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH)
        var.bind('<Return>', self.update_datasets)
        var.bind('<KP_Enter>', self.update_datasets)

    def search_options(self):
        window, fun_close = create_hover(self.root)

        file_search = tk.StringVar(window, '')
        match_case = tk.BooleanVar(window, False)
        whole_word = tk.BooleanVar(window, False)

        dataset_search = tk.StringVar(window, '')
        ds_match_case = tk.BooleanVar(window, False)
        ds_whole_word = tk.BooleanVar(window, False)

        frm = ttk.Frame(window, borderwidth=2)
        frm.pack(side=tk.TOP, fill=tk.BOTH)
        ttk.Label(frm, text='Filename: ', width=12).pack(side=tk.LEFT)
        ttk.Entry(frm, textvariable=file_search, width=20).pack(side=tk.LEFT)
        ttk.Checkbutton(frm, text='Match case: ', variable=match_case).pack(side=tk.LEFT)
        ttk.Checkbutton(frm, text='Whole word: ', variable=whole_word).pack(side=tk.LEFT)

        sec = ttk.LabelFrame(window, text='NeXus', borderwidth=4)
        sec.pack(side=tk.TOP, fill=tk.BOTH)

        frm = ttk.Frame(sec, borderwidth=2)
        frm.pack(side=tk.TOP, fill=tk.BOTH)
        ttk.Label(frm, text='Dataset: ', textvariable=self.hdf_path).pack(side=tk.LEFT)

        frm = ttk.Frame(sec, borderwidth=2)
        frm.pack(side=tk.TOP, fill=tk.BOTH)
        ttk.Label(frm, text='Search: ', width=12).pack(side=tk.LEFT)
        ttk.Entry(frm, textvariable=dataset_search, width=20).pack(side=tk.LEFT)
        ttk.Checkbutton(frm, text='Match case: ', variable=ds_match_case).pack(side=tk.LEFT)
        ttk.Checkbutton(frm, text='Whole word: ', variable=ds_whole_word).pack(side=tk.LEFT)

        def search():
            self._search(
                query=file_search.get(),
                match_case=match_case.get(),
                whole_word=whole_word.get(),
                file_only=True,
            )

        def ds_search():
            self._search(
                query=dataset_search.get(),
                match_case=ds_match_case.get(),
                whole_word=ds_whole_word.get(),
                data_only=True,
            )

        frm = ttk.Frame(window, borderwidth=10)
        frm.pack(side=tk.BOTTOM, fill=tk.BOTH)
        ttk.Button(frm, text='Dataset\nSearch', command=ds_search).pack(side=tk.LEFT, fill=tk.X, expand=tk.YES, padx=5)
        ttk.Button(frm, text='Search', command=search).pack(side=tk.LEFT, fill=tk.X, expand=tk.YES, padx=5)
        ttk.Button(frm, text='Close', command=fun_close).pack(side=tk.LEFT, fill=tk.X, expand=tk.YES)

        return window


class JupyterFolderTreeViewFrame(FolderTreeViewFrame):
    def __init__(self, root: tk.Misc, initial_directory: str | None = None):
        logger.info('Creating JupyterFolderTreeViewFrame')
        super().__init__('.ipynb', root, initial_directory)
        self.tree.configure(displaycolumns=('modified', 'files'))  # hide columns

    def _right_click_file(self) -> tk.Menu:
        # right-click menu - file options
        m_file = super()._right_click_file()
        m_file.add_command(label="start jupyter", command=self.open_jupyter_notebook)
        m_file.add_command(label="view html", command=self.open_jupyter_html)
        return m_file


    def open_jupyter_html(self):
        from mmg_toolbox.utils.nb_runner import view_jupyter_notebook, view_notebook_html

        filename, foldername = self.get_filepath()
        if filename:
            html = filename.replace('.ipynb', '.html')
            if os.path.isfile(html):
                view_jupyter_notebook(html)
            else:
                # generate html in TMP
                view_notebook_html(filename)


