import re
import sys
import os
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from mmg_toolbox.utils.env_functions import run_python_string


# Define colors for the various types of tokens
class Colours:
    normal = '#eaeaea'  # rgb((234, 234, 234))
    keywords = '#ea5f5f'  # rgb((234, 95, 95))
    commands = '#54AAE3'
    comments = '#5feaa5'  # rgb((95, 234, 165))
    string = '#eaa25f'  # rgb((234, 162, 95))
    function = '#5fd3ea'  # rgb((95, 211, 234))
    background = '#2a2a2a'  # rgb((42, 42, 42))

FONT = 'Consolas 15'
TAB_WIDTH = 4
INDENT = ' ' * TAB_WIDTH

# Define a list of Regex Pattern that should be colored in a certain way
REPL = [
    [
        r'(?:^|\s|\W)(False|None|True|and|as|assert|async|await|' +
        'break|class|continue|def|del|elif|else|except|finally|for|from|' +
        'global|if|import|in|is|lambda|nonlocal|not|or|pass|print|' +
        r'raise|return|try|while|with|yield)(?:$|\s|\W)',
        Colours.keywords
    ],
    # [r'(?:^|\s|\W)(scan|scancn|cscan|frange|pos|inc|go)(?:$|\s|\W)', commands],
    ['".*?"', Colours.string],
    ['\'.*?\'', Colours.string],
    ['#.*?$', Colours.comments],
]

SCRIPT = '''"""
Example Script
%s
"""

pos shutter 1
pos x1 1

scancn eta 0.01 101 pil 1 roi2

for chi_val in frange(84, 96, 2):
    pos chi chi_val
    scancn eta 0.01 101 pil 1 roi2
'''


def search_re(pattern, text):
    matches = []
    text = text.splitlines()
    regex = re.compile(pattern)
    for i, line in enumerate(text):
        for match in regex.finditer(line):
            if match.groups():
                matches.append((f"{i + 1}.{match.span(1)[0]}", f"{i + 1}.{match.span(1)[1]}"))
            else:
                matches.append((f"{i + 1}.{match.start()}", f"{i + 1}.{match.end()}"))
    return matches


def default_script():
    return SCRIPT % datetime.datetime.now().strftime('%Y-%m-%d %H:%M')


class PythonEditorFrame:
    """
    Editable textbox with numbers at side and key bindings for Python
    """

    def __init__(self, root: tk.Misc | tk.Tk, script_string=None, config: dict | None = None,
                 filename: str | None = None):
        self.root = root
        self.config = config
        # Variables
        self.filename = filename or ''
        self.script_string = script_string or default_script()

        "----------- Textbox -----------"

        txt = ttk.Frame(root)
        txt.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)

        # Scrollbars
        scanx = ttk.Scrollbar(txt, orient=tk.HORIZONTAL)
        scanx.pack(side=tk.BOTTOM, fill=tk.X)
        scany = ttk.Scrollbar(txt, orient=tk.VERTICAL)
        scany.pack(side=tk.RIGHT, fill=tk.Y)

        # Text numbers
        border = 10
        self.textno = tk.Text(txt, width=3, font=FONT, borderwidth=border, relief=tk.FLAT)
        self.textno.pack(side=tk.LEFT, fill=tk.Y, expand=tk.YES)
        self.textno.config(yscrollcommand=scany.set, state=tk.DISABLED)

        # TEXT box
        # Add a hefty border width so we can achieve a little bit of padding
        self.text = tk.Text(
            txt,
            background=Colours.background,
            foreground=Colours.normal,
            insertbackground=Colours.normal,
            relief=tk.FLAT,
            borderwidth=border,
            font=FONT,
            undo=True,
            autoseparators=True,
            maxundo=-1,
            wrap=tk.NONE
        )
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)
        self.text.insert('1.0', self.script_string)
        self.text.bind('<KeyRelease>', self.changes)
        self.text.bind('<Return>', self.auto_indent)
        self.text.bind('<KP_Enter>', self.auto_indent)
        self.text.bind('<Tab>', self.tab)
        self.text.bind('<Shift-Tab>', self.shift_tab)
        self.text.bind('<Control-slash>', self.comment)
        self.text.bind('<BackSpace>', self.delete)

        # make scrollbars work
        self.text.config(xscrollcommand=scanx.set, yscrollcommand=scany.set)
        scanx.config(command=self.text.xview)
        scany.config(command=self.text.yview)

        frm = ttk.Frame(root, relief=tk.RIDGE, borderwidth=2)
        frm.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)
        ttk.Button(frm, text='RUN', command=self.run).pack(side=tk.RIGHT, pady=5)


        self.changes()

    "------------------------------------------------------------------------"
    "-------------------------Load/Save Functions----------------------------"
    "------------------------------------------------------------------------"

    def set_filename(self, filename: str):
        self.filename = filename
        if hasattr(self.root, 'wm_title'):
            self.root.wm_title(filename)

    def new(self):
        answer = messagebox.askokcancel(
            title='Script editor',
            message='Do you want to replace the current script?',
            parent=self.root,
        )
        if answer:
            self.set_filename('new_file.py')
            self.text.delete('1.0', tk.END)
            self.text.insert('1.0', default_script())
            self.changes()

    def open(self):
        """Open new script"""
        filename = filedialog.askopenfilename(
            title='Open Python Script',
            initialdir=os.path.dirname(self.filename),
            defaultextension='*.py',
            filetypes=(("Python files", "*.py"), ("All files", "*.*"))
        )
        if filename:
            with open(filename, 'r') as f:
                self.script_string = f.read()
            self.text.delete('1.0', tk.END)
            self.text.insert('1.0', self.script_string)
            self.set_filename(filename)
            self.changes()

    def saveas(self):
        """Save as file"""
        filename = filedialog.asksaveasfilename(
            title='Python Script',
            initialfile=self.filename,
            defaultextension='.py'
        )
        if filename:
            with open(filename, 'w') as f:
                f.write(self.script_string)
            print('Written script to %s' % filename)
            self.set_filename(filename)

    def save(self):
        """Save script"""
        if self.filename == '':
            self.saveas()
            return
        with open(self.filename, 'w') as f:
            f.write(self.script_string)
        print('Written script to %s' % self.filename)

    def run(self):
        """Run script"""
        run_python_string(self.script_string)

    "------------------------------------------------------------------------"
    "--------------------------General Functions-----------------------------"
    "------------------------------------------------------------------------"

    def changes(self, event=None):
        """ Register Changes made to the Editor Content """

        # If actually no changes have been made stop / return the function
        if self.text.get('1.0', tk.END) == self.script_string:
            return

        # Remove all tags so they can be redrawn
        for tag in self.text.tag_names():
            self.text.tag_remove(tag, "1.0", tk.END)

        # Add tags where the search_re function found the pattern
        i = 0
        for pattern, color in REPL:
            for start, end in search_re(pattern, self.text.get('1.0', tk.END)):
                self.text.tag_add(f'{i}', start, end)
                self.text.tag_config(f'{i}', foreground=color)
                i += 1

        # Add tags to multiline comments
        start = None
        for n, line in enumerate(self.text.get('1.0', tk.END).splitlines()):
            for match in re.finditer('\'{3}|\"{3}', line):
                if start:
                    self.text.tag_add(f'{i}', start, f"{n + 1}.{match.end()}")
                    self.text.tag_config(f'{i}', foreground=Colours.comments)
                    i += 1
                    start = None
                else:
                    start = f"{n + 1}.{match.start()}"

        self.script_string = self.text.get('1.0', tk.END)

        self.textno.configure(state='normal')
        self.textno.replace('1.0', tk.END, '\n'.join(str(n+1) for n in range(self.script_string.count('\n'))))
        self.textno.configure(state='disabled')

    def tab(self, event=None):
        if event is None:
            text = self.text
        else:
            text = event.widget
        try:
            first = int(text.index(tk.SEL_FIRST).split('.')[0])
            last = int(text.index(tk.SEL_LAST).split('.')[0])
            for lineno in range(first, last + 1):
                text.insert('%d.0' % lineno, INDENT)
        except tk.TclError:
            text.insert(tk.INSERT, INDENT)
        return 'break'

    def shift_tab(self, event=None):
        if event is None:
            text = self.text
        else:
            text = event.widget
        try:  # selection
            first = int(text.index(tk.SEL_FIRST).split('.')[0])
            last = int(text.index(tk.SEL_LAST).split('.')[0])
            for lineno in range(first, last + 1):
                line = text.get('%d.0' % lineno, '%d.0 lineend' % lineno)
                spaceno = len(line) - len(line.lstrip())
                spaceno = 4 if spaceno > 4 else spaceno
                text.delete('%d.0' % lineno, '%d.%d' % (lineno, spaceno))
        except tk.TclError:  # single point
            lineno = int(text.index('insert').split('.')[0])
            line = text.get('%d.0' % lineno, '%d.0 lineend' % lineno)
            spaceno = len(line) - len(line.lstrip())
            text.delete('%d.0' % lineno, '%d.%d' % (lineno, spaceno))
        return 'break'

    def comment(self, event=None):
        if event is None:
            text = self.text
        else:
            text = event.widget
        try:
            first = int(text.index(tk.SEL_FIRST).split('.')[0])
            last = int(text.index(tk.SEL_LAST).split('.')[0])
            line = text.get('%d.0' % first, '%d.0 lineend' % first)
            if line.startswith('#'):  # remove comments
                for lineno in range(first, last + 1):
                    line = text.get('%d.0' % lineno, '%d.0 lineend' % lineno)
                    if line.startswith('# '):
                        text.delete('%d.0' % lineno, '%d.2' % lineno)
                    elif line.startswith('#'):
                        text.delete('%d.0' % lineno)
            else:  # add comments
                for lineno in range(first, last + 1):
                    line = text.get('%d.0' % lineno, '%d.0 lineend' % lineno)
                    if not line.startswith('#'):
                        text.insert('%d.0' % lineno, '# ')
        except tk.TclError:
            lineno = int(text.index('insert').split('.')[0])
            line = text.get('%d.0' % lineno, '%d.0 lineend' % lineno)
            if line.startswith('# '):
                text.delete('%d.0' % lineno, '%d.2' % lineno)
            elif line.startswith('#'):
                text.delete('%d.0' % lineno)
            else:
                text.insert('%d.0' % lineno, '# ')
        return 'break'

    def auto_indent(self, event=None):
        if event is None:
            text = self.text
        else:
            text = event.widget

        # get leading whitespace from current line
        line = text.get("insert linestart", "insert")
        match = re.match(r'^(\s+)', line)
        whitespace = match.group(0) if match else ""
        if any(line.strip().endswith(c) for c in [':', '{', '[', '(']):
            whitespace += INDENT

        # insert the newline and the whitespace
        text.insert("insert", f"\n{whitespace}")

        # return "break" to inhibit default insertion of newline
        return "break"

    def delete(self, event=None):
        if event is None:
            text = self.text
        else:
            text = event.widget

        try:
            text.delete(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            line = text.get("insert linestart", "insert")
            previous = text.get("insert -%d chars" % TAB_WIDTH, "insert")
            if line == " " * len(line) and len(line) % TAB_WIDTH > 0:  # delete tab
                text.delete("insert -%d chars" % (len(line) % TAB_WIDTH), "insert")
            elif previous == " " * TAB_WIDTH:  # delete tab
                text.delete("insert-%d chars" % TAB_WIDTH, "insert")
            elif '\n' in previous and previous[-1] != '\n':  # delete spaces to start of line
                text.delete("insert-%d chars" % len(line), "insert")
            else:  # normal delete
                text.delete("insert-1 chars", "insert")
        return "break"


class PythonTerminalFrame:
    """
    Editable textbox with numbers at side and key bindings for Python
    UNFINISHED
    """

    def __init__(self, root: tk.Misc):

        txt = ttk.Frame(root)
        txt.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)

        # Scrollbars
        scanx = ttk.Scrollbar(txt, orient=tk.HORIZONTAL)
        scanx.pack(side=tk.BOTTOM, fill=tk.X)
        scany = ttk.Scrollbar(txt, orient=tk.VERTICAL)
        scany.pack(side=tk.RIGHT, fill=tk.Y)

        # Text numbers
        border = 10
        self.textno = tk.Text(txt, width=3, font=FONT, borderwidth=border, relief=tk.FLAT)
        self.textno.pack(side=tk.LEFT, fill=tk.Y, expand=tk.NO)
        self.textno.config(yscrollcommand=scany.set, state=tk.DISABLED)

        # Terminal
        frm = ttk.Frame(txt)
        frm.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)
        # history
        self.history_str = f"Python {sys.version} on {sys.platform}\n"
        self.text = tk.Text(
            frm,
            background=Colours.background,
            foreground=Colours.normal,
            insertbackground=Colours.normal,
            relief=tk.FLAT,
            borderwidth=border,
            font=FONT,
            undo=True,
            autoseparators=True,
            maxundo=-1,
            wrap=tk.NONE
        )
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)
        self.text.insert('1.0', self.history_str)
        self.text.config(xscrollcommand=scanx.set, yscrollcommand=scany.set, state=tk.DISABLED)
        # entry
        self.entry = tk.Text(
            frm,
            background=Colours.background,
            foreground=Colours.normal,
            insertbackground=Colours.normal,
            relief=tk.FLAT,
            borderwidth=border,
            font=FONT,
            undo=True,
            autoseparators=True,
            maxundo=-1,
            wrap=tk.NONE,
            height=2
        )
        self.entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)
        self.entry.insert('1.0', ">>> ")
        self.entry.bind('<KeyRelease>', self.changes)
        self.entry.bind('<Return>', self.auto_indent)
        self.entry.bind('<KP_Enter>', self.auto_indent)
        self.entry.bind('<Tab>', self.tab)
        self.entry.bind('<Shift-Tab>', self.shift_tab)
        self.entry.bind('<Control-slash>', self.comment)
        self.entry.bind('<BackSpace>', self.delete)

        # make scrollbars work
        self.text.config(xscrollcommand=scanx.set, yscrollcommand=scany.set)
        scanx.config(command=self.text.xview)
        scany.config(command=self.text.yview)

        self.changes()

    "------------------------------------------------------------------------"
    "--------------------------General Functions-----------------------------"
    "------------------------------------------------------------------------"

    def changes(self, event=None):
        """ Register Changes made to the Editor Content """

        # If actually no changes have been made stop / return the function
        if self.text.get('1.0', tk.END) == self.history_str:
            return

        # Remove all tags so they can be redrawn
        for tag in self.text.tag_names():
            self.text.tag_remove(tag, "1.0", tk.END)

        # Add tags where the search_re function found the pattern
        i = 0
        for pattern, color in REPL:
            for start, end in search_re(pattern, self.text.get('1.0', tk.END)):
                self.text.tag_add(f'{i}', start, end)
                self.text.tag_config(f'{i}', foreground=color)
                i += 1

        # Add tags to multiline comments
        start = None
        for n, line in enumerate(self.text.get('1.0', tk.END).splitlines()):
            for match in re.finditer('\'{3}|\"{3}', line):
                if start:
                    self.text.tag_add(f'{i}', start, f"{n + 1}.{match.end()}")
                    self.text.tag_config(f'{i}', foreground=Colours.comments)
                    i += 1
                    start = None
                else:
                    start = f"{n + 1}.{match.start()}"

        self.history_str = self.text.get('1.0', tk.END)

        self.textno.configure(state='normal')
        self.textno.replace('1.0', tk.END, '\n'.join(str(n + 1) for n in range(self.history_str.count('\n'))))
        self.textno.configure(state='disabled')

    def tab(self, event=None):
        if event is None:
            text = self.text
        else:
            text = event.widget
        try:
            first = int(text.index(tk.SEL_FIRST).split('.')[0])
            last = int(text.index(tk.SEL_LAST).split('.')[0])
            for lineno in range(first, last + 1):
                text.insert('%d.0' % lineno, INDENT)
        except tk.TclError:
            text.insert(tk.INSERT, INDENT)
        return 'break'

    def shift_tab(self, event=None):
        if event is None:
            text = self.text
        else:
            text = event.widget
        try:  # selection
            first = int(text.index(tk.SEL_FIRST).split('.')[0])
            last = int(text.index(tk.SEL_LAST).split('.')[0])
            for lineno in range(first, last + 1):
                line = text.get('%d.0' % lineno, '%d.0 lineend' % lineno)
                spaceno = len(line) - len(line.lstrip())
                spaceno = 4 if spaceno > 4 else spaceno
                text.delete('%d.0' % lineno, '%d.%d' % (lineno, spaceno))
        except tk.TclError:  # single point
            lineno = int(text.index('insert').split('.')[0])
            line = text.get('%d.0' % lineno, '%d.0 lineend' % lineno)
            spaceno = len(line) - len(line.lstrip())
            text.delete('%d.0' % lineno, '%d.%d' % (lineno, spaceno))
        return 'break'

    def comment(self, event=None):
        if event is None:
            text = self.text
        else:
            text = event.widget
        try:
            first = int(text.index(tk.SEL_FIRST).split('.')[0])
            last = int(text.index(tk.SEL_LAST).split('.')[0])
            line = text.get('%d.0' % first, '%d.0 lineend' % first)
            if line.startswith('#'):  # remove comments
                for lineno in range(first, last + 1):
                    line = text.get('%d.0' % lineno, '%d.0 lineend' % lineno)
                    if line.startswith('# '):
                        text.delete('%d.0' % lineno, '%d.2' % lineno)
                    elif line.startswith('#'):
                        text.delete('%d.0' % lineno)
            else:  # add comments
                for lineno in range(first, last + 1):
                    line = text.get('%d.0' % lineno, '%d.0 lineend' % lineno)
                    if not line.startswith('#'):
                        text.insert('%d.0' % lineno, '# ')
        except tk.TclError:
            lineno = int(text.index('insert').split('.')[0])
            line = text.get('%d.0' % lineno, '%d.0 lineend' % lineno)
            if line.startswith('# '):
                text.delete('%d.0' % lineno, '%d.2' % lineno)
            elif line.startswith('#'):
                text.delete('%d.0' % lineno)
            else:
                text.insert('%d.0' % lineno, '# ')
        return 'break'

    def auto_indent(self, event=None):
        if event is None:
            text = self.text
        else:
            text = event.widget

        # get leading whitespace from current line
        line = text.get("insert linestart", "insert")
        match = re.match(r'^(\s+)', line)
        whitespace = match.group(0) if match else ""
        if any(line.strip().endswith(c) for c in [':', '{', '[', '(']):
            whitespace += INDENT

        # insert the newline and the whitespace
        text.insert("insert", f"\n{whitespace}")

        # return "break" to inhibit default insertion of newline
        return "break"

    def delete(self, event=None):
        if event is None:
            text = self.entry
        else:
            text = event.widget

        try:
            text.delete(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            line = text.get("insert linestart", "insert")
            previous = text.get("insert -%d chars" % TAB_WIDTH, "insert")
            if line == " " * len(line) and len(line) % TAB_WIDTH > 0:  # delete tab
                text.delete("insert -%d chars" % (len(line) % TAB_WIDTH), "insert")
            elif previous == " " * TAB_WIDTH:  # delete tab
                text.delete("insert-%d chars" % TAB_WIDTH, "insert")
            elif '\n' in previous and previous[-1] != '\n':  # delete spaces to start of line
                text.delete("insert-%d chars" % len(line), "insert")
            else:  # normal delete
                text.delete("insert-1 chars", "insert")
        return "break"

    def execute(self, event=None):
        if event is None:
            text = self.entry
        else:
            text = event.widget

        cmd = text.get('1.0', tk.END)
        cmd = cmd.strip('> ')  # remove preceding chevrons
        exec(cmd)
