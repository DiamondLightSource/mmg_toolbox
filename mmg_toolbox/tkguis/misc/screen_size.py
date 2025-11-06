"""
Handle small screens by adjusting size of elements
"""

import tkinter as tk
from .config import (C, TEXT_HEIGHT, TEXT_HEIGHT_SMALL, TEXT_WIDTH,
                     FIGURE_SIZE, IMAGE_SIZE, FIGURE_DPI, MAX_PLOT_SCREEN_PERCENTAGE, SMALL_SCREEN_HEIGHT)


def get_screen_size_inches(root: tk.Misc, dpi: int = 60) -> tuple[float, float]:
    """Return the screen size in inches: [width, height]"""
    width, height = root.winfo_screenwidth(), root.winfo_screenheight()
    return width / dpi, height / dpi


def get_text_size(root: tk.Misc, config: dict | None = None) -> tuple[int, int]:
    """Return textbox size adjusted for screen size in [characters, lines]"""
    width, height = root.winfo_screenwidth(), root.winfo_screenheight()
    config = config or {}
    if height <= config.get(C.small_screen_height, SMALL_SCREEN_HEIGHT):
        print(f"Small screen size, reducing Text Height to {TEXT_HEIGHT_SMALL}")
        characters, lines = config.get(C.text_size_small, (TEXT_WIDTH, TEXT_HEIGHT_SMALL))
    else:
        characters, lines = config.get(C.text_size, (TEXT_WIDTH, TEXT_HEIGHT))
    return characters, lines


def get_figure_size(root: tk.Misc, config: dict | None = None, config_label: str = C.plot_size) -> tuple[int, int]:
    """Return figure size adjusted for screen size in [width, height] inches"""
    config = config or {}

    fig_width, fig_height = config.get(config_label, FIGURE_SIZE)
    width_inches, height_inches = get_screen_size_inches(root, config.get(C.plot_dpi, FIGURE_DPI))
    wid_perc = 100 * (fig_width / width_inches)
    hgt_perc = 100 * (fig_height / height_inches)
    max_wid, max_hgt = config.get(C.plot_max_percent, MAX_PLOT_SCREEN_PERCENTAGE)

    if hgt_perc > max_hgt:
        print(f"Figure size as % of screen: {width_inches:.2f}x{height_inches:.2f}\" = {wid_perc:.0f}x{hgt_perc:.0f}%")
        print(f"Reducing to {max_hgt}% height")
        fig_height = max_hgt * height_inches / 100.
    return fig_width, fig_height


def update_config(root: tk.Misc, config: dict) -> None:
    """Update config for screen size"""
    width, height = root.winfo_screenwidth(), root.winfo_screenheight()
    small_height = config.get(C.small_screen_height, SMALL_SCREEN_HEIGHT)
    scale = 1.0 if height > small_height else 0.6
    new = {
        C.text_size: (TEXT_WIDTH, TEXT_HEIGHT_SMALL if height > small_height else TEXT_HEIGHT),
        C.plot_size: (FIGURE_SIZE[0], FIGURE_SIZE[1] * scale),
        C.image_size: (IMAGE_SIZE[0], IMAGE_SIZE[1] * scale),
    }
    config.update(new)