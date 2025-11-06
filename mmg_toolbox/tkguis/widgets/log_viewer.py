"""
A python editor window
"""

import re

from ..misc.styles import tk, ttk
from ..misc.search import search_text
from ..misc.logging import create_logger

logger = create_logger(__file__)


# Define colors for the various types of tokens
class Colours:
    normal = '#eaeaea'  # rgb((234, 234, 234))
    keywords = '#ea5f5f'  # rgb((234, 95, 95))
    commands = '#54AAE3'
    comments = '#5feaa5'  # rgb((95, 234, 165))
    string = '#eaa25f'  # rgb((234, 162, 95))
    function = '#5fd3ea'  # rgb((95, 211, 234))
    background = '#2a2a2a'  # rgb((42, 42, 42))
    input = '#909184'  # rbb((0, 0, 255))
    highlight = '#baacab' # rgb 186, 172, 171

FONT = 'Consolas 15'

# Define a list of Regex Pattern that should be colored in a certain way
REPL = [
    [
        r'(?:^|\s|\W)(Scan|WARNING|ERROR)(?:$|\s|\W)',
        Colours.keywords
    ],
    [r'\A.*\| >>>.*\Z', Colours.input],
    # [r'(?:^|\s|\W)(scan|scancn|cscan|frange|pos|inc|go)(?:$|\s|\W)', commands],
    ['".*?"', Colours.string],
    ['\'.*?\'', Colours.string],
    ['#.*?$', Colours.comments],
]


def search_re(pattern, text):
    """Search text for regex pattern"""
    matches = []
    regex = re.compile(pattern)
    for i, line in enumerate(text.splitlines()):
        for match in regex.finditer(line):
            if match.groups():
                matches.append((f"{i + 1}.{match.span(1)[0]}", f"{i + 1}.{match.span(1)[1]}"))
            else:
                matches.append((f"{i + 1}.{match.start()}", f"{i + 1}.{match.end()}"))
    return matches


def update_tags(text: tk.Text):
    """ apply tags to textbox """

    # Remove all tags so they can be redrawn
    for tag in text.tag_names():
        text.tag_remove(tag, "1.0", tk.END)

    # Add tags where the search_re function found the pattern
    i = 0
    for pattern, color in REPL:
        for start, end in search_re(pattern, text.get('1.0', tk.END)):
            text.tag_add(f'{i}', start, end)
            text.tag_config(f'{i}', foreground=color)
            i += 1

    # Add tags to multiline comments
    start = None
    for n, line in enumerate(text.get('1.0', tk.END).splitlines()):
        for match in re.finditer('\'{3}|\"{3}', line):
            if start:
                text.tag_add(f'{i}', start, f"{n + 1}.{match.end()}")
                text.tag_config(f'{i}', foreground=Colours.comments)
                i += 1
                start = None
            else:
                start = f"{n + 1}.{match.start()}"


def log_tab(root: tk.Misc, log_string: str):
    """Create log textbox"""

    "----------- Textbox -----------"

    txt = ttk.Frame(root)
    txt.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)

    # Scrollbars
    scroll_x = ttk.Scrollbar(txt, orient=tk.HORIZONTAL)
    scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
    scroll_y = ttk.Scrollbar(txt, orient=tk.VERTICAL)
    scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

    # TEXT box
    text = tk.Text(
        txt,
        background=Colours.background,
        foreground=Colours.normal,
        insertbackground=Colours.normal,
        exportselection=True,
        relief=tk.FLAT,
        font=FONT,
        wrap=tk.NONE
    )
    text.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)
    text.insert('1.0', log_string)
    text.config(state=tk.DISABLED)

    # make scrollbars work
    text.config(xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set)
    scroll_x.config(command=text.xview)
    scroll_y.config(command=text.yview)

    update_tags(text)
    return text


class LogViewerWidget:
    """
    Editable textbox with numbers at side and key bindings for Python
    """

    def __init__(self, root: tk.Misc, log_tabs: dict[str, list[str]]):

        self.root = root
        self.search_box = tk.StringVar(self.root, '')
        self.search_matchcase = tk.BooleanVar(self.root, False)
        self.search_all_dates = tk.BooleanVar(self.root, True)
        self.search_number = tk.StringVar(self.root, '')

        main = ttk.Frame(root)
        main.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)

        self.ini_search(main)

        frm = ttk.Frame(main)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)

        # Tabs
        self.view_tabs = ttk.Notebook(frm)
        self.tab_texts = []
        for title, log in log_tabs.items():
            tab = ttk.Frame(self.view_tabs)
            self.view_tabs.add(tab, text=title)
            self.tab_texts.append(log_tab(tab, '\n'.join(log)))
        self.view_tabs.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)

    def ini_search(self, frame: tk.Misc):
        frm = ttk.Frame(frame)
        frm.pack(side=tk.TOP, anchor=tk.E)

        var = ttk.Entry(frm, textvariable=self.search_box, width=40)
        var.pack(side=tk.LEFT)
        # var.bind('<KeyRelease>', self.fun_search)
        var.bind('<Return>', self.fun_search)
        var.bind('<KP_Enter>', self.fun_search)
        var = ttk.Button(frm, text='Search', command=self.fun_search, width=10)
        var.pack(side=tk.LEFT)

        ttk.Checkbutton(frm, variable=self.search_matchcase, text='Case').pack(side=tk.LEFT)
        ttk.Checkbutton(frm, variable=self.search_all_dates, text='All Dates').pack(side=tk.LEFT)
        ttk.Label(frm, textvariable=self.search_number).pack(side=tk.LEFT)


    def fun_search(self, event=None):
        """Search currently active tab"""
        found = 0
        if self.search_all_dates.get():
            # search all tabs
            first_tab = False
            for tab_index, tab_text in enumerate(self.tab_texts):
                found += search_text(tab_text, self.search_box.get(), self.search_matchcase.get(), Colours.highlight)
                if not first_tab and found > 0:
                    self.view_tabs.select(tab_index)
                    first_tab = True
        else:
            tab_index = self.view_tabs.index(self.view_tabs.select())
            tab_text = self.tab_texts[tab_index]
            found += search_text(tab_text, self.search_box.get(), self.search_matchcase.get(), Colours.highlight)
        self.search_number.set(f"{found} found")


