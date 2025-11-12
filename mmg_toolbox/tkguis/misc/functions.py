"""
Various tkinter functions
"""

import os
import tkinter
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import ImageGrab

from .styles import RootWithStyle, theme_menu


def topmenu(root: RootWithStyle, menu_dict: dict, add_themes=False, add_about=False,
            config: dict | None = None):
    """
    Add a file menu to root
    :param root: tkinter root
    :param menu_dict: {Menu name: {Item name: function}}
    :param add_themes: add themes menu item
    :param add_about: add about menu item
    :param config: add Config menu if config dict is added
    :return: None
    """
    if config is not None:
        menu_dict.update(config_menu(root, config))
    if add_themes and hasattr(root, 'style'):
        menu_dict.update(theme_menu(root.style))
    if add_about:
        menu_dict.update(about_menu(root))

    def add_menu(menu: tk.Menu, **this_menu_dict):
        for name, item in this_menu_dict.items():
            if type(item) is dict:
                new_menu = tk.Menu(menu, tearoff=False)
                add_menu(new_menu, **item)
                menu.add_cascade(label=name, menu=new_menu)
            else:
                menu.add_command(label=name, command=item)

    menubar = tk.Menu(root)
    add_menu(menubar, **menu_dict)
    root.config(menu=menubar)


def about_menu(root: tk.Misc | None = None):
    """About menu items"""
    menu = {
        'Help': {
            'Docs': open_docs,
            'About': lambda: popup_about(root)
        }
    }
    return menu


def config_menu(root: tk.Misc, config: dict) -> dict:
    """Config menu items"""
    from ..apps.config_editor import ConfigEditor
    from .config import reset_config
    menu = {
        'Config': {
            'Edit Config.': lambda: ConfigEditor(root, config),
            'Reset Config.': lambda: reset_config(config),
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


def select_folder(parent, initial_directory: str | None = None):
    """Select folder"""
    foldername = filedialog.askdirectory(
        initialdir=initial_directory,
        title='Select folder...',
        mustexist=True,
        parent=parent,
    )
    return foldername


def check_new_file(parent, filename: str | None = None) -> str | None:
    """Check if filename is new and writable"""
    path, name = os.path.split(filename)
    if not os.access(path, os.W_OK):
        show_error(f"new file cannot be written as path is not writable: '{path}'",
                   parent=parent, raise_exception=False)
        return None

    if os.path.exists(filename):
        if os.access(filename, os.W_OK):
            answer = messagebox.askyesnocancel(
                title='Create File',
                message=f"Overwrite {name}? Yes to overwrite or No to create new file.",
                parent=parent
            )
            if answer is None:
                return None
            if answer:
                return filename
        # amend name
        name, ext = os.path.splitext(name)
        n_tries = 1
        while os.path.exists(filename):
            if n_tries > 100:
                return None
            filename = os.path.join(path, name + str(n_tries) + ext)
            n_tries += 1
    return filename


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


def open_docs():
    """Open web-browser at docs site"""
    import webbrowser
    webbrowser.open_new_tab("https://diamondlightsource.github.io/mmg_toolbox/")


def popup_about(root: tk.Misc | None = None):
    """Create about message"""
    from mmg_toolbox import version_info, module_info, title
    msg = (
        f"{version_info()}\n\n" +
        "A selection of useful functions and methods for the mmg beamlines at Diamond" +
        "\n\n" +
        f"Module Info:\n{module_info()}\n\n" +
        "By Dan Porter, Diamond Light Source Ltd"
    )
    if root is not None:
        msg += f"\n\nScreen size: {root.winfo_screenwidth()}x{root.winfo_screenheight()}"
    messagebox.showinfo(
        title=f"About: {title()}",
        message=msg,
        parent=root,
    )


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
    var.grid(column=1, row=0, sticky='nsew')
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


def capture(root: tk.Misc, filename='img.png'):
    """Take screenshot of the passed widget. Untested!"""

    x0 = root.winfo_rootx()
    y0 = root.winfo_rooty()
    x1 = x0 + root.winfo_width()
    y1 = y0 + root.winfo_height()

    im = ImageGrab.grab(bbox=(x0, y0, x1, y1))  # bbox means boundingbox, which is shown in the image below
    im.save(filename)  # Can also say im.show() to display it


def copy_image_to_clipboard(root: tk.Misc, canvas: tk.Canvas):
    """copy tk canvas to clipboard. Untested!"""

    # https://www.tutorialspoint.com/how-to-copy-a-picture-from-tkinter-canvas-to-clipboard
    import io
    from PIL import Image

    # Retrieve the image from the canvas
    canvas_image = canvas.postscript()

    # Create an in-memory file-like object
    image_buffer = io.BytesIO()

    # Save the canvas image to the buffer in PNG format
    image = Image.open(canvas_image)
    image.save(image_buffer, format="PNG")
    image_buffer.seek(0)

    # Copy the image to the clipboard
    root.clipboard_clear()
    root.clipboard_append(image_buffer, format="image/png")