"""
Treeview widget for folders
"""

import os
import time
import tkinter as tk
from tkinter import ttk
from threading import Thread

from ...file_functions import list_files, list_path_time, display_timestamp, get_hdf_string
from ..misc.styles import create_root
from ..misc.functions import treeview_sort_column, post_right_click_menu, select_folder
from ..misc.logging import create_logger

logger = create_logger(__file__)


class NexusFolderTreeViewFrame:
    """Frame with TreeView and entry for Folders"""

    def __init__(self, root: tk.Misc, initial_directory: str | None = None):
        logger.info('Creating NexusFolderTreeViewFrame')
        self.root = root
        self.search_str = ""
        self.search_time = time.time()
        self.search_reset = 3.0  # seconds
        self._prev_folder = ''

        # Variables
        self.filepath = tk.StringVar(root, os.path.expanduser('~'))
        self.extension = tk.StringVar(root, '.nxs')
        self.hdf_path = tk.StringVar(root, '')
        self.show_hidden = tk.BooleanVar(root, False)
        self.read_datasets = tk.BooleanVar(root, True)
        self.search_box = tk.StringVar(root, '')
        self.search_matchcase = tk.BooleanVar(root, False)
        self.search_wholeword = tk.BooleanVar(root, True)

        # Columns
        self.columns = (
            # (name, text, width, reverse, sort_col)
            ("#0", 'Folder', 100, False, None),
            ("modified", 'Modified', 150, True, "modified_time"),
            ('modified_time', 'Modified', 0, False, None),
            ("files", 'Files', 15, False, None),
            ("data", 'Data', 200, False, None),
            ("filepath", 'File Path', 0, False, None),
        )

        # Build widgets
        self.ini_folderpath()
        self.tree = self.folder_treeview()
        self.tree.configure(displaycolumns=('modified', 'files', 'data'))  # hide columns
        self.tree.bind("<<TreeviewOpen>>", self.populate_files)
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind('<KeyPress>', self.on_key_press)
        self.tree.bind("<Button-3>", self.right_click_menu())

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
        var = ttk.Entry(frm, textvariable=self.filepath)
        var.pack(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH)
        var.bind('<Return>', self.populate_folders)
        var.bind('<KP_Enter>', self.populate_folders)

        var = ttk.Checkbutton(frm, text='Show hidden', variable=self.show_hidden, command=self.populate_folders)
        var.pack(side=tk.LEFT)

        var = ttk.Button(frm, text='Nexus Files', command=self.nexus_file_options)
        var.pack(side=tk.RIGHT)
        var = ttk.Button(frm, text='Search', command=self.search_options)
        var.pack(side=tk.RIGHT)

    def folder_treeview(self) -> ttk.Treeview:
        """
        Creates a ttk.TreeView object inside a frame with columns for folders
        """
        main = ttk.Frame(self.root)
        main.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)

        frm = ttk.Frame(main)
        frm.pack(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH)

        tree = ttk.Treeview(frm, columns=[c[0] for c in self.columns[1:]])
        tree.pack(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH)

        var = ttk.Scrollbar(frm, orient="vertical", command=tree.yview)
        var.pack(side=tk.LEFT, fill=tk.Y)
        tree.configure(yscrollcommand=var.set)

        def tree_sort(col, reverse, sort_col=None):
            return lambda: treeview_sort_column(tree, col, reverse=reverse, sort_col=sort_col)

        for name, text, width, reverse, sort_col in self.columns:
            tree.heading(name, text=text, command=tree_sort(sort_col or name, reverse, name if sort_col else None))
            tree.column(name, width=width)
        return tree

    "======================================================"
    "=============== populate functions ==================="
    "======================================================"

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
            time_str = display_timestamp(mtime)
            self.tree.insert("", tk.END, text=name_str, values=(time_str, mtime, '', '', path))
        self.update_folder_nfiles()

    def update_folder_nfiles(self, event=None):
        """Update the number of files in each directory, as a seperate process"""

        extension = self.extension.get()
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
            if len(self.tree.get_children(item)) == 1:
                # remove old entries
                self.tree.delete(*self.tree.get_children(item))
                # add hdf files
                path = self.tree.set(item, 'filepath')
                files = list_files(path, self.extension.get())
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

    "======================================================"
    "================= button functions ==================="
    "======================================================"

    def nexus_file_options(self):
        root = create_root('', self.root)
        root.wm_overrideredirect(True)

        window = ttk.Frame(root, borderwidth=20, relief=tk.RAISED)
        window.pack(side=tk.TOP, fill=tk.BOTH)

        frm = ttk.Frame(window, borderwidth=10)
        frm.pack(side=tk.TOP, fill=tk.BOTH)

        var = ttk.Button(frm, text='NeXus Dataset Path', command=self.select_dataset)
        var.pack(side=tk.LEFT)
        var = ttk.Entry(frm, textvariable=self.hdf_path)
        var.pack(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH)
        var.bind('<Return>', self.update_datasets)
        var.bind('<KP_Enter>', self.update_datasets)

        frm = ttk.Frame(window, borderwidth=10)
        frm.pack(side=tk.TOP, fill=tk.BOTH)
        var = ttk.Checkbutton(frm, text='Read dataset', variable=self.read_datasets)
        var.pack(side=tk.LEFT)
        var = ttk.Label(frm, text=' | Extension: ')
        var.pack(side=tk.LEFT)
        var = ttk.OptionMenu(frm, self.extension, None, *('.nxs', '.hdf', '.hdf5'))
        var.pack(side=tk.LEFT)

        def close():
            self.update_datasets()
            root.destroy()

        frm = ttk.Frame(window, borderwidth=2)
        frm.pack(side=tk.TOP, fill=tk.BOTH)
        var = ttk.Button(frm, text='Close', command=close)
        var.pack(side=tk.LEFT, fill=tk.X, expand=tk.YES)

    def select_dataset(self):
        pass

    def search_options(self):
        pass

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

    def right_click_menu(self):
        logger.info('Creating right click menu')
        # right-click menu - file options
        m_file = tk.Menu(self.root, tearoff=0)
        m_file.add_command(label="Copy path", command=self.copy_path)
        m_file.add_command(label="open Treeview", command=self.open_nexus_treeview)
        m_file.add_command(label="open Plot", command=self.open_nexus_plot)
        m_file.add_command(label="open Image", command=self.open_nexus_image)
        # m_file.add_command(label="open Namespace", command=self.menu_namespace_gui)
        # m_file.add_command(label="open Nexus Classes", command=self.menu_class_gui)
        # right-click menu - folder options
        m_folder = tk.Menu(self.root, tearoff=0)
        m_folder.add_command(label="Copy path", command=self.copy_path)
        # m_folder.add_command(label="Open Folder Datasets", command=self.menu_folder_files)
        # m_folder.add_command(label="Open Folder Plots", command=self.menu_folder_plot)
        # # m_folder.add_command(label="Display Contents", command=self.menu_folder_plot)
        # m_folder.add_command(label="Display Summary", command=self.menu_folder_summary)

        def menu_popup(event):
            # select item
            iid = self.tree.identify_row(event.y)
            if iid:
                self.tree.selection_set(iid)
                filename, foldername = self.get_filepath()
                if filename:
                    logger.debug(f"Right click menu created for file: {filename}")
                    menu = m_file
                else:
                    logger.debug(f"Right click menu created for folder: {foldername}")
                    menu = m_folder
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
            self.search_str = ""
        # update search time, add key to query
        self.search_time = ctime
        self.search_str += event.char

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
            from ..main import create_nexus_viewer
            create_nexus_viewer(filename, parent=self.root)

    def open_nexus_plot(self):
        filename, foldername = self.get_filepath()
        logger.info(f"Opening nexus plot viewer for filename: {filename}")
        if filename:
            from ..main import create_nexus_plotter
            create_nexus_plotter(filename, parent=self.root)

    def open_nexus_image(self):
        filename, foldername = self.get_filepath()
        logger.info(f"Opening nexus image viewer for filename: {filename}")
        if filename:
            pass

    "======================================================"
    "================= misc functions ====================="
    "======================================================"

    def fun_search(self, event=None):
        self.tree.selection_remove(self.tree.selection())
        query = self.search_box.get()
        match_case = self.search_matchcase.get()
        whole_word = self.search_wholeword.get()
        query = query if match_case else query.lower()

        for branch in self.tree.get_children():  # folders
            # folder = self.tree.item(branch)['text']
            for leaf in self.tree.get_children(branch):  # files
                item = self.tree.item(leaf)
                if len(item['values']) < 3:
                    continue
                file = item['text']
                value = item['values'][2]
                test = f"{file} {value}"
                test = test if match_case else test.lower()
                test = test.split() if whole_word else test
                if query in test:
                    self.tree.selection_add(leaf)
                    self.tree.see(leaf)

