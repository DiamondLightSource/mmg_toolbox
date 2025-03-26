"""
Treeview widget for folders
"""

import os
import time
import tkinter as tk
from tkinter import ttk
from threading import Thread, current_thread

from ...file_functions import list_files, display_timestamp, get_hdf_string
from ..misc.styles import create_root
from ..misc.functions import treeview_sort_column, post_right_click_menu, select_folder
from ..misc.logging import create_logger

logger = create_logger(__file__)


class FolderScanSelector:
    """Frame with TreeView for selection of folders"""

    def __init__(self, root: tk.Misc, initial_directory: str | None = None):
        logger.info('Creating FolderScanSelector')
        self.root = root
        self.search_str = ""
        self.search_time = time.time()
        self.search_reset = 3.0  # seconds
        self._prev_folder = ''
        self._update_time = 10  # seconds - poll folders for new files

        # Variables
        self.extension = tk.StringVar(root, '.nxs')
        self.hdf_path = tk.StringVar(root, '')
        self.read_datasets = tk.BooleanVar(root, True)
        self.search_box = tk.StringVar(root, '')
        self.search_matchcase = tk.BooleanVar(root, False)
        self.search_wholeword = tk.BooleanVar(root, True)

        # Columns
        self.columns = (
            # (name, text, width, reverse, sort_col)
            ("#0", 'Folder', 100, False, None),
            ("modified", 'Date', 100, True, "modified_time"),
            ('modified_time', 'Modified', 0, False, None),
            ("files", 'Files', 0, False, None),
            ("data", 'Data', 200, False, None),
            ("filepath", 'File Path', 0, False, None),
        )

        # Build widgets
        self.ini_folderpath()
        self.tree = self.folder_treeview()
        self.tree.configure(displaycolumns=('modified', 'data'))  # hide columns
        self.tree.bind("<<TreeviewOpen>>", self.populate_folder)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", self.on_double_click)
        # self.tree.bind('<KeyPress>', self.on_key_press)
        self.tree.bind("<Button-3>", self.right_click_menu())

        # Populate
        if initial_directory:
            self.add_folder(initial_directory)
        self.poll_files()

    "======================================================"
    "================= init functions ====================="
    "======================================================"

    def ini_folderpath(self):
        frm = ttk.Frame(self.root)
        frm.pack(side=tk.TOP, fill=tk.X)

        var = ttk.Button(frm, text='Add Folder', command=self.browse_folder)
        var.pack(side=tk.LEFT)
        var = ttk.Button(frm, text='Nexus Files', command=self.nexus_file_options)
        var.pack(side=tk.RIGHT)
        var = ttk.Button(frm, text='Search', command=self.search_options)
        var.pack(side=tk.RIGHT)

    def folder_treeview(self) -> ttk.Treeview:
        """
        Creates a ttk.TreeView object inside a frame with columns for folders
        """
        frm = ttk.Frame(self.root)
        frm.pack(side=tk.TOP)

        tree = ttk.Treeview(frm, columns=[c[0] for c in self.columns[1:]])

        var = ttk.Scrollbar(frm, orient="vertical", command=tree.yview)
        var.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=var.set)

        var = ttk.Scrollbar(frm, orient="horizontal", command=tree.xview)
        var.pack(side=tk.BOTTOM, fill=tk.X)
        tree.configure(xscrollcommand=var.set)
        tree.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)

        def tree_sort(col, reverse, sort_col=None):
            return lambda: treeview_sort_column(tree, col, reverse=reverse, sort_col=sort_col)

        for name, text, width, reverse, sort_col in self.columns:
            tree.heading(name, text=text, command=tree_sort(sort_col or name, reverse, name if sort_col else None))
            tree.column(name, width=width, stretch=False)  # stretch stops columns from stretching when resized
        return tree

    "======================================================"
    "=============== populate functions ==================="
    "======================================================"

    def add_folder(self, folder_path: str):
        iid = self.tree.insert("", tk.END, text=os.path.basename(folder_path),
                               values=('', '', '', '', folder_path))
        self.populate_files(iid)

    def populate_files(self, item):
        """Add list of files below folder on folder expand"""
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

    def populate_folder(self, event=None):
        """Add list of files below folder on folder expand"""
        iid = self.tree.focus()
        self.populate_files(iid)

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

    def update_files(self):
        """Check folders in the tree for new files"""
        hdf_path = self.hdf_path.get()
        hdf_value = ''
        for branch in self.tree.get_children():
            folder = self.tree.set(branch, 'filepath')
            files = list_files(folder, self.extension.get())
            for leaf in self.tree.get_children(branch):  # files
                if not self.tree.winfo_exists():
                    return
                file = self.tree.set(leaf, 'filepath')
                if file in files:
                    files.remove(file)

            logger.info(f"Updating {len(files)} in '{os.path.basename(folder)}'")
            logger.debug(f"update_files: Current thread: {current_thread()}, in process pid: {os.getpid()}")
            for file in files:
                if not self.tree.winfo_exists():
                    return
                timestamp = os.stat(file).st_mtime
                mtime = display_timestamp(timestamp)
                if self.read_datasets.get():
                    hdf_value = get_hdf_string(file, hdf_path, '...')
                self.tree.insert(branch, tk.END, text=os.path.basename(file),
                                 values=(mtime, timestamp, '', hdf_value, file))

    def poll_files(self):
        """Create background thread that checks the folders for new files"""
        def fn():
            while True:
                with open('mylog.txt', 'a') as mylog:  # delete this once you are happy it works
                    mylog.write(f"{time.ctime()} Current thread: {current_thread()}, in process pid: {os.getpid()}, exists: {self.tree.winfo_exists()}\n")
                if not self.tree.winfo_exists():
                    logger.info('poll_files exiting')
                    return
                self.update_files()
                time.sleep(self._update_time)

        th = Thread(target=fn)
        th.daemon = True  # runs thread in the background, outside mainloop, allowing python to close
        th.start()

    "======================================================"
    "============= navigation functions ==================="
    "======================================================"

    def browse_folder(self):
        folder_directory = select_folder(parent=self.root)
        if folder_directory:
            self.add_folder(folder_directory)

    def on_select(self, event=None):
        if not self.tree.focus():
            return
        # iid = self.tree.focus()
        # item = self.tree.item(iid)
        print(self.get_filepath())

    def on_double_click(self, event=None):
        """Action on double click of file"""
        if not self.tree.focus():
            return
        # iid = self.tree.focus()
        # item = self.tree.item(iid)
        self.open_nexus_treeview()

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
        foldername = None
        for iid in self.tree.selection():
            item = self.tree.item(iid)
            filepath = self.tree.set(iid, 'filepath')
            if os.path.isfile(filepath):
                filename = filepath
                foldername = os.path.dirname(filename)
            else:  # item is a folder
                foldername = filepath
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

