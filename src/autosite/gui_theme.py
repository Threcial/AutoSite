import os
import tkinter as tk
from tkinter import ttk


def set_dpi_aware():
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def center_window(root, width=960, height=680):
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = max(0, (sw - width) // 2)
    y = max(0, (sh - height) // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.minsize(width, height)


def apply_style():
    style = ttk.Style()
    available = style.theme_names()
    if "vista" in available:
        style.theme_use("vista")
    elif "xpnative" in available:
        style.theme_use("xpnative")
    else:
        style.theme_use("clam")
    return style


def make_card(parent, title, row=0, column=0, padx=8, pady=6, colspan=1, weight=None):
    f = ttk.LabelFrame(parent, text=title, padding=10)
    f.grid(row=row, column=column, padx=padx, pady=pady, sticky="nsew", columnspan=colspan)
    if weight is not None:
        f.columnconfigure(1, weight=weight)
    return f
