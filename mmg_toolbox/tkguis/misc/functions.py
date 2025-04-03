"""
Various tkinter functions
"""

import tkinter
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .styles import RootWithStyle, theme_menu


def topmenu(root: RootWithStyle, menu_dict: dict, add_themes=False, add_about=False):
    """
    Add a file menu to root
    :param root: tkinter root
    :param menu_dict: {Menu name: {Item name: function}}
    :param add_themes: add themes menu item
    :param add_about: add about menu item
    :return: None
    """
    if add_themes and hasattr(root, 'style'):
        menu_dict.update(theme_menu(root.style))
    if add_about:
        menu_dict.update(about_menu())

    menubar = tk.Menu(root)
    for item in menu_dict:
        men = tk.Menu(menubar, tearoff=0)
        for label, function in menu_dict[item].items():
            men.add_command(label=label, command=function)
        menubar.add_cascade(label=item, menu=men)
    root.config(menu=menubar)


def about_menu():
    """About menu items"""
    menu = {
        'Help': {
            'Docs': lambda: print('None'),
            'About': lambda: print('None'),
        }
    }
    return menu


def select_hdf_file(parent):
    """Select HDF file using filedialog"""
    from h5py import is_hdf5
    filename = filedialog.askopenfilename(
        title='Select file to open',
        filetypes=[('NXS file', '.nxs'),
                   ('HDF file', '.h5'), ('HDF file', '.hdf'), ('HDF file', '.hdf5'),
                   ('All files', '.*')],
        parent=parent
    )
    if filename and not is_hdf5(filename):
        messagebox.showwarning(
            title='Incorrect File Type',
            message=f"File: \n{filename}\n can't be read by h5py",
            parent=parent
        )
        filename = None
    return filename


def select_folder(parent):
    """Select folder"""
    foldername = filedialog.askdirectory(
        title='Select folder...',
        mustexist=True,
        parent=parent,
    )
    return foldername


def open_close_all_tree(treeview, branch="", openstate=True):
    """Open or close all items in ttk.treeview"""
    treeview.item(branch, open=openstate)
    for child in treeview.get_children(branch):
        open_close_all_tree(treeview, child, openstate)  # recursively open children


def treeview_sort_column(treeview: ttk.Treeview, col: str, reverse: bool, sort_col: str | None = None):
    """
    Function to sort columns in ttk.Treeview,
        tree.heading("#0", command=lambda _col="#0": treeview_sort_column(tree, _col, False))
    :param treeview: ttk.Treeview instance
    :param col: str, column specifier for items to sort
    :param reverse: Bool, sort direction
    :param sort_col: str or None, sort alternative column
    :return:
    """
    if sort_col is None:
        sort_col = col
    if col == "#0":
        def item(iid):
            return treeview.item(iid)['text']
    else:
        def item(iid):
            return treeview.set(iid, col)

    items = [(item(iid), iid) for iid in treeview.get_children('')]
    items.sort(reverse=reverse)

    # rearrange items in sorted positions
    for index, (val, k) in enumerate(items):
        treeview.move(k, '', index)
        if treeview.item(k)['text'] == '..':  # keep at top of column
            treeview.move(k, '', 0)

    # reverse sort next time
    treeview.heading(sort_col, command=lambda _col=col: treeview_sort_column(treeview, _col, not reverse, sort_col))


def show_error(message, parent=None, raise_exception=True):
    """Display and raise error"""
    messagebox.showwarning(
        title="HDF File Error",
        message=message,
        parent=parent,
    )
    if raise_exception:
        raise Exception(message)


def post_right_click_menu(menu: tkinter.Menu, xpos: int, ypos: int):
    """Post menu on arrow position"""

    def destroy(evt):
        menu.unpost()

    try:
        menu.bind('<FocusOut>', destroy)
        menu.tk_popup(xpos, ypos)
    finally:
        menu.grab_release()


def folder_treeview(parent: tk.Misc, columns: list[tuple[str, str, int, bool, str | None]],
                    width: int | None = None, height: int | None = None) -> ttk.Treeview:
    """
    Creates a ttk.TreeView object inside a frame with columns for folders
    """
    canvas = tk.Canvas(parent)
    # fixed size of grid in canvas
    canvas.grid_rowconfigure(0, weight=1)
    canvas.grid_columnconfigure(0, weight=1)
    if width and height:
        canvas.configure(width=width, height=height)
        canvas.pack()
    else:
        canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)
    canvas.grid_propagate(False)

    frm = ttk.Frame(canvas)
    frm.grid_rowconfigure(0, weight=1)
    frm.grid_columnconfigure(0, weight=1)

    tree = ttk.Treeview(frm, columns=[c[0] for c in columns[1:]])
    for c in columns:
        tree.column(c[0], stretch=False)

    var = ttk.Scrollbar(frm, orient="vertical", command=tree.yview)
    # var.pack(side=tk.RIGHT, fill=tk.Y)
    var.grid(column=1, row=0, sticky='ns')
    tree.configure(yscrollcommand=var.set)

    var = ttk.Scrollbar(frm, orient="horizontal", command=tree.xview)
    # var.pack(side=tk.BOTTOM, fill=tk.X)
    var.grid(column=0, row=1, sticky='ew')
    tree.configure(xscrollcommand=var.set)
    # tree.pack(side=tk.TOP)
    tree.grid(column=0, row=0, sticky='nsew')
    frm.grid(column=0, row=0)

    def tree_sort(col, reverse, sort_col=None):
        return lambda: treeview_sort_column(tree, col, reverse=reverse, sort_col=sort_col)

    for name, text, width, _reverse, _sort_col in columns:
        tree.heading(name, text=text, command=tree_sort(_sort_col or name, _reverse, name if _sort_col else None))
        tree.column(name, width=width, stretch=False)  # stretch stops columns from stretching when resized
    return tree

