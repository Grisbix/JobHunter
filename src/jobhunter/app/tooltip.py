"""A tip shown while the pointer is over a widget (3.26).

The text is asked for each time the tip opens, so it follows what the widget shows
(the progress of a collection changes every second). An empty text shows nothing.
"""

import tkinter as tk
from collections.abc import Callable
from typing import Any


def bulle(widget: Any, texte: Callable[[], str]) -> None:
    """Shows `texte()` next to the pointer while it is over `widget`."""
    etat: dict[str, Any] = {"w": None}

    def cacher(_e: Any = None) -> None:
        if etat["w"] is not None:
            etat["w"].destroy()
            etat["w"] = None

    def montrer(e: Any) -> None:
        t = texte()
        if not t:
            cacher()
            return
        if etat["w"] is None:
            w = tk.Toplevel(widget)
            w.wm_overrideredirect(True)
            w.wm_attributes("-topmost", True)
            tk.Label(
                w, text=t, justify="left", bg="#fffbe6", relief="solid", bd=1, padx=8, pady=6
            ).pack()
            etat["w"] = w
        else:
            etat["w"].winfo_children()[0].configure(text=t)
        # Left of the pointer when near the right edge of the screen.
        x = e.x_root + 14
        largeur = etat["w"].winfo_reqwidth()
        if x + largeur > widget.winfo_screenwidth():
            x = max(0, e.x_root - largeur - 14)
        etat["w"].wm_geometry(f"+{x}+{e.y_root + 18}")

    def quitte(_e: Any) -> None:
        # Showing the tip itself sends <Leave>: only a pointer really outside hides it.
        x, y = widget.winfo_pointerxy()
        if not (
            widget.winfo_rootx() <= x < widget.winfo_rootx() + widget.winfo_width()
            and widget.winfo_rooty() <= y < widget.winfo_rooty() + widget.winfo_height()
        ):
            cacher()

    widget.bind("<Enter>", montrer, add="+")
    widget.bind("<Motion>", montrer, add="+")
    widget.bind("<Leave>", quitte, add="+")
    widget.bind("<Destroy>", cacher, add="+")
