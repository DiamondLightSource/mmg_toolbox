"""
tkinter search functions
"""

import tkinter as tk
from tkinter import ttk


def search_text(text: tk.Text, query="", match_case=False, highlight_colour='red'):
    """
    Set selection of strings in Text widget based on search query
    :param text: tk.Text
    :param query: str search query
    :param match_case: if False, select items even if the case doesn't match
    :param highlight_colour: colour of the highlighted text
    :return:
    """
    text.tag_remove('search', '1.0', tk.END)
    text.tag_config('search', background=highlight_colour)

    count = 0
    set_see = True
    if query:
        if query not in text.mark_names():
            text.mark_set(query, '1.0')
        show_idx = text.index(query)
        idx = '1.0'
        while idx:
            idx = text.search(query, idx, nocase=not match_case, stopindex=tk.END)
            if not idx:
                return count
            last_idx = '%s+%dc' % (idx, len(query))
            text.tag_add('search', idx, last_idx)
            if set_see and idx > show_idx:  # set view point at first or next query point
                text.mark_set(query, last_idx)
                text.see(idx)
                set_see = False
            count += 1
            idx = last_idx
    return count


def search_tree(treeview: ttk.Treeview, branch="", query="entry", match_case=False, whole_word=False):
    """
    Set selection of items in treeview based on search query
    :param treeview: ttk.treeview
    :param branch: ttk.treeview item (str)
    :param query: str search query
    :param match_case: if False, select items even if the case doesn't match
    :param whole_word: if True, select only items where query matches final element of address
    :return:
    """
    query = query if match_case else query.lower()
    for child in treeview.get_children(branch):
        search_tree(treeview, child, query, match_case, whole_word)
        address = treeview.item(child)['text']
        address = address if match_case else address.lower()
        address = address.split('/')[-1] if whole_word else address
        if (whole_word and query == address) or (not whole_word and query in address):
            treeview.selection_add(child)
            treeview.see(child)