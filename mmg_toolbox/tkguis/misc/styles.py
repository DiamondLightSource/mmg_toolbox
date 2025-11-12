"""
tkinter styles

Uses ttk Themed Styles

Docs:
https://tkdocs.com/tutorial/styles.html
List of Themes:
https://wiki.tcl-lang.org/page/List+of+ttk+Themes
awlight/awdark theme download:
https://wiki.tcl-lang.org/page/awthemes
Fonts:
https://tkdocs.com/tutorial/fonts.html
"""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk
from .logging import create_logger

logger = create_logger(__name__)

AWTHEMES_PATH = '/dls/science/users/grp66007/tkinter/awthemes-10.4.0'
DEFAULT_THEME = 'clam'

def create_style(root):
    style = ttk.Style(root)
    if os.path.isdir(AWTHEMES_PATH):
        root.tk.call('lappend', 'auto_path', AWTHEMES_PATH)
        root.tk.call('package', 'require', 'awdark')
        root.tk.call('package', 'require', 'awlight')
    use_theme(style, DEFAULT_THEME)
    return style


def extra_styles(style: ttk.Style):
    """
    Add additional styles to use on individual ttk components
    """
    # style.configure("Red.TLabel", foreground='red', font='TkDefaultFont 24 bold')
    style.configure("title.TLabel", foreground='red', font='times 24 bold')
    style.configure("error.TLabel", foreground='red')
    style.configure("smallMsg.TLabel", font='TkDefaultFont 10 bold')


def use_theme(style: ttk.Style, theme_name: str):
    if theme_name in style.theme_names():
        style.theme_use(theme_name)
    else:
        logger.warning(f"ttk Style Theme not available: '{theme_name}'")
    extra_styles(style)


def theme_menu(style: ttk.Style) -> dict:
    """Generate theme menu dict"""
    menu = {
        "Themes": {
            name: lambda n=name: use_theme(style, n)
            for name in style.theme_names()
        }
    }
    return menu


class RootWithStyle(tk.Tk):
    style: ttk.Style | None = None


def create_root(window_title: str, parent: tk.Misc | RootWithStyle | None = None) -> RootWithStyle:
    """Create tkinter root object with style attribute"""
    if parent:
        root = tk.Toplevel(parent)
        # root.geometry(f"+{parent.winfo_x()+100}+{parent.winfo_y()+100}")
        root.transient(parent)
        if hasattr(parent, 'style'):
            root.style = parent.style
    else:
        root = tk.Tk()

    def update(event):
        root.update()
        print(root.winfo_reqwidth(), root.winfo_screenheight())
        print(root.winfo_screenwidth(), root.winfo_screenheight())

    # root.bind('<Configure>', update)

    if not hasattr(root, 'style'):
        style = create_style(root)
        root.style = style

    # Fix background (on windows)
    root.configure(bg=root.style.lookup('.', 'background'))

    root.wm_title(window_title)
    # self.root.minsize(width=640, height=480)
    # root.maxsize(width=root.winfo_screenwidth() * 3 // 4, height=root.winfo_screenheight() * 3 // 4)
    root.maxsize(width=int(root.winfo_screenwidth() - 50), height=int(root.winfo_screenheight()) - 100)
    return root


def create_hover(parent: tk.Misc | RootWithStyle):
    """
    Create tkinter frame hovering above the current widget

    E.G.
    window_frame, close = create_hover(widget)
    ttk.Button(window_frame, text='Close', command=close).pack()

    :param parent: tk widget or root
    :returns: ttk.Frame object inside tk.TopLevel with no window management
    :returns: function close() -> None (releases widget and destroys hover window)
    """
    # root = create_root('', parent)
    # root.wm_overrideredirect(True)

    base_x = parent.master.winfo_x()
    base_y = parent.master.winfo_y()
    base_height = parent.master.winfo_height()

    root = ttk.Frame(parent)
    root.place(x=base_x, y=base_y - base_height)


    window = ttk.Frame(root, borderwidth=20, relief=tk.RAISED)
    window.pack(side=tk.TOP, fill=tk.BOTH)

    def destroy(event=None):
        root.grab_release()
        root.destroy()

    root.grab_set()
    return window, destroy


def update_text_style(widget: tk.Text, style: ttk.Style):
    """
    Update a tk.Text widget with the current style
    """
    widget.configure(
        bg=style.lookup('.', 'background'),
        fg=style.lookup('.', 'foreground'),
        font=style.lookup('.', 'font') or 'TkDefaultFont',
    )


# from: https://stackoverflow.com/questions/45389166/how-to-know-all-style-options-of-a-ttk-widget

def _iter_layout(layout, tab_amnt=0, elements=[]):
    """Recursively prints the layout children."""
    el_tabs = '  '*tab_amnt
    val_tabs = '  '*(tab_amnt + 1)

    for element, child in layout:
        elements.append(element)
        print(el_tabs+ '\'{}\': {}'.format(element, '{'))
        for key, value in child.items():
            if type(value) == str:
                print(val_tabs + '\'{}\' : \'{}\','.format(key, value))
            else:
                print(val_tabs + '\'{}\' : [('.format(key))
                _iter_layout(value, tab_amnt=tab_amnt+3)
                print(val_tabs + ')]')

        print(el_tabs + '{}{}'.format('} // ', element))

    return elements


def stylename_elements_options(widget: tk.Misc):
    """
    Function to expose the options of every element associated to a widget stylename.

        widget = ttk.Button(None)
        class_ = widget.winfo_class()
        stylename_elements_options(class_, widget)
    """

    try:
        # Get widget elements
        stylename = widget.winfo_class()
        style = ttk.Style()
        layout = style.layout(stylename)
        config = widget.configure()

        print('{:*^50}\n'.format(f'Style = {stylename}'))

        print('{:*^50}'.format('Config'))
        for key, value in config.items():
            print('{:<15}{:^10}{}'.format(key, '=>', value))

        print('\n{:*^50}'.format('Layout'))
        elements = _iter_layout(layout)

        # Get options of widget elements
        print('\n{:*^50}'.format('element options'))
        for element in elements:
            print('{0:30} options: {1}'.format(
                element, style.element_options(element)))

    except tk.TclError:
        print('_tkinter.TclError: "{0}" in function'
                'widget_elements_options({0}) is not a regonised stylename.'
                .format(stylename))

