"""
Convenience wrapper for ttk.Treeview
"""

import tkinter as tk
from tkinter import ttk

from mmg_toolbox.tkguis.misc.functions import post_right_click_menu


TreeViewColumn = tuple[str, str, int, bool, str | None]  # name, title, width, reverse, sort_col


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
    
    c_item = lambda iid: treeview.item(iid)['text'] if col == '#0' else lambda iid: treeview.set(iid, col)
    # if col == "#0":
    #     def get_item(iid):
    #         return treeview.item(iid)['text']
    # else:
    #     def get_item(iid):
    #         return treeview.set(iid, col)

    items = [(c_item(iid), iid) for iid in treeview.get_children('')]
    items.sort(reverse=reverse)

    # rearrange items in sorted positions
    for index, (val, k) in enumerate(items):
        treeview.move(k, '', index)
        if treeview.item(k)['text'] == '..':  # keep at top of column
            treeview.move(k, '', 0)

    # reverse sort next time
    treeview.heading(sort_col, command=lambda _col=col: treeview_sort_column(treeview, _col, not reverse, sort_col))


class CanvasTreeview:
    """
    Treeview wrapper comprising a ttk.Treeview inside a canvas with scrollbars

        columns = [
            ('#0', "Number", 100, False, None),
            ('file', "Filename", 400, False, None),
        ]
        tv = CanvasTreeview(parent, *columns)

    *Note: the *name* parameter of the first column must be '#0'.

    :param root: parent tk Frame object
    :param columns: list of tuples where each tuple is ('name', 'Title', width, reverse, sort_col)
    :param width: width of widget, or None to fill and expand
    :param height: heigh of widget, or None to fill and expand
    """
    def __init__(self, root: tk.Misc, *columns: TreeViewColumn,
                 width: int | None = None, height: int | None = None,
                 pack: bool = True):
        self.root = root

        canvas = tk.Canvas(root)
        # fixed size of grid in canvas
        canvas.grid_rowconfigure(0, weight=1)
        canvas.grid_columnconfigure(0, weight=1)
        if width and height:
            canvas.configure(width=width, height=height)
            self.pack_treeview = lambda: canvas.pack()
        else:
            self.pack_treeview = lambda: canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)
        if pack:
            self.pack_treeview()
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
        # place the frame inside the canvas as a window and make it resize with the canvas
        _canvas_window = canvas.create_window(0, 0, anchor='nw', window=frm)

        def _on_canvas_configure(event):
            # ensure the inner frame (and thus the tree) matches the canvas size
            canvas.itemconfigure(_canvas_window, width=event.width, height=event.height)

        canvas.bind('<Configure>', _on_canvas_configure)

        def tree_sort(col, reverse, sort_col=None):
            return lambda: treeview_sort_column(tree, col, reverse=reverse, sort_col=sort_col)

        for name, title, width, _reverse, _sort_col in columns:
            tree.heading(name, text=title, command=tree_sort(_sort_col or name, _reverse, name if _sort_col else None))
            tree.column(name, width=width, stretch=False)  # stretch stops columns from stretching when resized

        # Hide columns
        display_columns = [name for name, title, width, reverse, sort_col in columns[1:] if width > 0]
        tree.configure(displaycolumns=display_columns)

        self.titles = {
            name: title for name, title, width, reverse, sort_col in columns
        }
        self.getters = {
            '#0': lambda iid: self.tree.item(iid)['text'],
            **{
                name: lambda iid, _name=name: self.tree.set(iid, _name)
                for name, _, _, _, _ in columns[1:]
            }
        }

        self.columns = columns
        self.tree = tree
        tree.bind("<Button-3>", self.right_click_menu())

    def first_item(self):
        return next(iter(self.tree.get_children()))

    def get_row(self, iid: str | int) -> dict:
        """Return data from row"""
        return {name: getter(iid) for name, getter in self.getters.items()}

    def get_selected(self) -> list[dict]:
        """Return values of current selection"""
        return [self.get_row(iid) for iid in self.tree.selection()]

    def get_index(self):
        iid = next(iter(self.tree.selection()), next(iter(self.tree.get_children())))
        return self.tree.index(iid)

    def populate(self, **kwargs):
        pass

    def delete(self):
        self.tree.delete(*self.tree.get_children())

    def bind_select(self, function):
        self.tree.bind('<<TreeviewSelect>>', function)

    def bind_dbl_click(self, function):
        self.tree.bind("<Double-1>", function)

    def right_click_menu(self):
        """
        Create right-click context menu for hdf_tree objects
        :return: menu_popup function
        """

        def copy_fun(tree_getter):
            def fun():
                for iid in self.tree.selection():
                    self.root.master.clipboard_clear()
                    self.root.master.clipboard_append(tree_getter(iid))
            return fun

        m = tk.Menu(self.root, tearoff=0)
        header_name = self.tree.heading('#0', 'text')
        header_getter = lambda iid: self.tree.item(iid)['text']
        m.add_command(label="Copy " + header_name, command=copy_fun(header_getter))
        for name, title, width, reverse, sort_col in self.columns:
            getter = lambda iid: self.tree.set(iid, name)
            m.add_command(label="Copy " + title, command=copy_fun(getter))

        def menu_popup(event):
            # select item
            iid = self.tree.identify_row(event.y)
            if iid:
                self.tree.selection_set(iid)
                post_right_click_menu(m, event.x_root, event.y_root)

        return menu_popup
