#!/usr/bin/env python3
"""Hotels Scraper GUI — Obsidian Pulse design."""

import math
import tkinter as tk
import customtkinter as ctk
import json
import sys
import threading
import queue
from pathlib import Path
from datetime import datetime
from loguru import logger

# ── Project root ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.logging_config import setup_loguru

# ── Color palette — Obsidian Pulse ────────────────────────────────────────────
C = {
    # Surface depth layers
    "bg":           "#10141a",   # surface — main background
    "panel":        "#181c22",   # surface-container-low — sidebar, panels
    "card":         "#1c2026",   # surface-container — cards, dialogs
    "card_hover":   "#262a31",   # surface-container-high
    "card_sel":     "#31353c",   # surface-container-highest — active
    "log_bg":       "#0a0e14",   # surface-container-lowest — terminal

    # Borders
    "border":       "#3b4a3d",
    "border_sel":   "#75ff9e",

    # Primary accent — neon green (kinetic)
    "accent":       "#75ff9e",
    "accent_h":     "#00e676",
    "accent_dim":   "#1a3d24",

    # Run button breathing (green-based)
    "btn_run":      "#006d35",
    "btn_run_h":    "#009950",
    "breathe_lo":   "#004a25",
    "breathe_hi":   "#00b358",

    # Text hierarchy
    "text":         "#dfe2eb",   # on-surface
    "text_dim":     "#b8c9d3",   # secondary
    "text_muted":   "#455a46",   # very muted

    # Status colors
    "success":      "#75ff9e",
    "error":        "#ffb4ab",
    "warning":      "#f59e0b",

    # Log terminal colors
    "log_time":     "#2e4035",
    "log_info":     "#b8c9d3",
    "log_success":  "#75ff9e",
    "log_error":    "#ffb4ab",
    "log_warning":  "#f59e0b",
    "log_sep":      "#1c2e22",

    # Toggle switch
    "toggle_off":   "#3b4b53",
    "toggle_on":    "#75ff9e",
}

FONT      = "Segoe UI"
FONT_MONO = "Consolas"


def _lerp_color(c1: str, c2: str, t: float) -> str:
    """Linearly interpolate between two #rrggbb hex colors."""
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


# ─────────────────────────────────────────────────────────────────────────────
#  Filter Warning Dialog
# ─────────────────────────────────────────────────────────────────────────────
class FilterWarningDialog(ctk.CTkToplevel):
    """Shown when the property-type filter fails to apply."""

    def __init__(self, parent, event: threading.Event, result: list):
        super().__init__(parent)
        self._event  = event
        self._result = result

        self.title("Filter Warning")
        self.geometry("500x310")
        self.configure(fg_color=C["card"])
        self.resizable(False, False)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self._on_abort)
        self.after(20, self._deferred_init)

    def _deferred_init(self):
        self._build()
        self.grab_set()
        self.update_idletasks()
        px, py = self.master.winfo_x(), self.master.winfo_y()
        pw, ph = self.master.winfo_width(), self.master.winfo_height()
        x = px + (pw - self.winfo_width()) // 2
        y = py + (ph - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        self.lift()

    def _build(self):
        badge_row = ctk.CTkFrame(self, fg_color="transparent")
        badge_row.pack(fill="x", padx=28, pady=(24, 0))

        badge = ctk.CTkFrame(
            badge_row, fg_color="#1a2e1a", corner_radius=10,
            border_width=1, border_color=C["border"],
        )
        badge.pack(anchor="w")

        ctk.CTkLabel(
            badge, text="  ⚠  Filter not applied  ",
            font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
            text_color=C["warning"],
        ).pack(padx=4, pady=6)

        ctk.CTkLabel(
            self,
            text=(
                "The Hotels filter could not be activated after\n"
                "all retry attempts."
            ),
            font=ctk.CTkFont(family=FONT, size=14),
            text_color=C["text"], justify="left",
        ).pack(anchor="w", padx=28, pady=(16, 4))

        ctk.CTkLabel(
            self,
            text=(
                "Without this filter, apartments, guesthouses, and\n"
                "other property types may be included in the results."
            ),
            font=ctk.CTkFont(family=FONT, size=13),
            text_color=C["text_dim"], justify="left",
        ).pack(anchor="w", padx=28)

        ctk.CTkFrame(self, fg_color=C["border"], height=1).pack(
            fill="x", padx=24, pady=(20, 20)
        )

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=28, pady=(0, 24))

        ctk.CTkButton(
            btns, text="Stop scraper", width=140, height=42,
            fg_color=C["card_hover"], hover_color=C["error"],
            text_color=C["text_dim"],
            font=ctk.CTkFont(family=FONT, size=14),
            corner_radius=9, command=self._on_abort,
        ).pack(side="right", padx=(10, 0))

        ctk.CTkButton(
            btns, text="Continue without filter", width=190, height=42,
            fg_color=C["accent_dim"], hover_color=C["accent"],
            text_color=C["accent"],
            border_width=1, border_color=C["border"],
            font=ctk.CTkFont(family=FONT, size=14, weight="bold"),
            corner_radius=9, command=self._on_continue,
        ).pack(side="right")

    def _on_continue(self):
        self._result[0] = True
        self._event.set()
        self.destroy()

    def _on_abort(self):
        self._result[0] = False
        self._event.set()
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
#  Add City Dialog
# ─────────────────────────────────────────────────────────────────────────────
class AddCityDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_save):
        super().__init__(parent)
        self._on_save = on_save

        self.title("Add City")
        self.geometry("540x340")
        self.configure(fg_color=C["card"])
        self.resizable(False, False)
        self.transient(parent)
        self.after(20, self._deferred_init)

    def _deferred_init(self):
        self._build()
        self.grab_set()
        self.update_idletasks()
        px, py = self.master.winfo_x(), self.master.winfo_y()
        pw, ph = self.master.winfo_width(), self.master.winfo_height()
        x = px + (pw - self.winfo_width()) // 2
        y = py + (ph - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        self.lift()
        self._name.focus()

    def _build(self):
        pad = {"padx": 32}

        ctk.CTkLabel(
            self, text="Add new city",
            font=ctk.CTkFont(family=FONT, size=17, weight="bold"),
            text_color=C["text"], anchor="w",
        ).pack(fill="x", pady=(26, 0), **pad)

        ctk.CTkFrame(self, fg_color=C["border"], height=1).pack(
            fill="x", padx=24, pady=(14, 20)
        )

        ctk.CTkLabel(
            self, text="CITY NAME OR FILTER LABEL",
            font=ctk.CTkFont(family=FONT, size=9, weight="bold"),
            text_color=C["accent"], anchor="w",
        ).pack(fill="x", **pad)

        self._name = ctk.CTkEntry(
            self, height=40,
            placeholder_text="e.g. Batumi",
            fg_color=C["bg"], border_color=C["border"], border_width=1,
            text_color=C["text"], placeholder_text_color=C["text_muted"],
            font=ctk.CTkFont(family=FONT, size=14), corner_radius=9,
        )
        self._name.pack(fill="x", pady=(5, 16), **pad)

        ctk.CTkLabel(
            self, text="BOOKING.COM SEARCH URL",
            font=ctk.CTkFont(family=FONT, size=9, weight="bold"),
            text_color=C["accent"], anchor="w",
        ).pack(fill="x", **pad)

        self._url = ctk.CTkEntry(
            self, height=40,
            placeholder_text="https://www.booking.com/searchresults.html?...",
            fg_color=C["bg"], border_color=C["border"], border_width=1,
            text_color=C["text"], placeholder_text_color=C["text_muted"],
            font=ctk.CTkFont(family=FONT, size=12), corner_radius=9,
        )
        self._url.pack(fill="x", pady=(5, 24), **pad)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", **pad, pady=(0, 24))

        ctk.CTkButton(
            btns, text="Cancel", width=100, height=40,
            fg_color=C["card_hover"], hover_color=C["border"],
            text_color=C["text_dim"],
            font=ctk.CTkFont(family=FONT, size=14), corner_radius=9,
            command=self.destroy,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btns, text="Save", width=150, height=40,
            fg_color=C["accent_dim"], hover_color=C["accent_h"],
            text_color=C["accent"],
            border_width=1, border_color=C["accent_dim"],
            font=ctk.CTkFont(family=FONT, size=14, weight="bold"),
            corner_radius=9, command=self._save,
        ).pack(side="right")

        self.bind("<Return>", lambda _: self._save())

    def _save(self):
        name = self._name.get().strip()
        url  = self._url.get().strip()
        if not name:
            self._name.configure(border_color=C["error"])
            return
        if not url.startswith("http"):
            self._url.configure(border_color=C["error"])
            return
        self._on_save(name, url)
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
#  City context menu (frameless dropdown)
# ─────────────────────────────────────────────────────────────────────────────
class CityContextMenu(tk.Toplevel):
    def __init__(self, parent, x: int, y: int, on_edit, on_delete):
        self._parent_root = parent.winfo_toplevel()
        self._bind_id     = None

        super().__init__(parent)
        self.overrideredirect(True)
        self.configure(bg=C["card_hover"])
        self.geometry(f"160x76+{x}+{y}")
        self.resizable(False, False)

        border = tk.Frame(self, bg=C["border"], padx=1, pady=1)
        border.pack(fill="both", expand=True)

        inner = tk.Frame(border, bg=C["card_hover"])
        inner.pack(fill="both", expand=True)

        def _item(text, color, command):
            f = tk.Frame(inner, bg=C["card_hover"], cursor="hand2")
            f.pack(fill="x")
            lbl = tk.Label(
                f, text=text, bg=C["card_hover"], fg=color,
                font=(FONT, 12), anchor="w", padx=14, pady=8,
            )
            lbl.pack(fill="x")
            for w in (f, lbl):
                w.bind("<Button-1>", lambda _, cmd=command: self._run(cmd))
                w.bind("<Enter>", lambda _, fw=f, lw=lbl: (
                    fw.configure(bg=C["card"]), lw.configure(bg=C["card"])
                ))
                w.bind("<Leave>", lambda _, fw=f, lw=lbl: (
                    fw.configure(bg=C["card_hover"]), lw.configure(bg=C["card_hover"])
                ))

        _item("  ✏  Edit URL",     C["text_dim"], on_edit)
        tk.Frame(inner, bg=C["border"], height=1).pack(fill="x", padx=8)
        _item("  ✕  Remove city",  C["error"],    on_delete)

        self.after(50, self._bind_outside_click)

    def _bind_outside_click(self):
        self._bind_id = self._parent_root.bind("<ButtonPress>", self._on_outside_click, "+")

    def _on_outside_click(self, event):
        try:
            wx, wy = self.winfo_rootx(), self.winfo_rooty()
            ww, wh = self.winfo_width(), self.winfo_height()
            if not (wx <= event.x_root < wx + ww and wy <= event.y_root < wy + wh):
                self._close()
        except tk.TclError:
            pass

    def _close(self):
        if self._bind_id:
            try:
                self._parent_root.unbind("<ButtonPress>", self._bind_id)
            except Exception:
                pass
            self._bind_id = None
        try:
            self.destroy()
        except Exception:
            pass

    def _run(self, command):
        self._close()
        command()


# ─────────────────────────────────────────────────────────────────────────────
#  Edit City Dialog
# ─────────────────────────────────────────────────────────────────────────────
class EditCityDialog(ctk.CTkToplevel):
    def __init__(self, parent, city: str, current_url: str, on_save):
        super().__init__(parent)
        self._city    = city
        self._cur_url = current_url
        self._on_save = on_save

        self.title("Edit City")
        self.geometry("540x300")
        self.configure(fg_color=C["card"])
        self.resizable(False, False)
        self.transient(parent)
        self.after(20, self._deferred_init)

    def _deferred_init(self):
        self._build()
        self.grab_set()
        self.update_idletasks()
        px, py = self.master.winfo_x(), self.master.winfo_y()
        pw, ph = self.master.winfo_width(), self.master.winfo_height()
        x = px + (pw - self.winfo_width()) // 2
        y = py + (ph - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        self.lift()
        self._url.focus()

    def _build(self):
        pad = {"padx": 32}

        top_row = ctk.CTkFrame(self, fg_color="transparent")
        top_row.pack(fill="x", pady=(24, 0), **pad)

        ctk.CTkLabel(
            top_row, text="Edit  ",
            font=ctk.CTkFont(family=FONT, size=17, weight="bold"),
            text_color=C["text"],
        ).pack(side="left")

        ctk.CTkLabel(
            top_row, text=self._city,
            font=ctk.CTkFont(family=FONT, size=17, weight="bold"),
            text_color=C["accent"],
        ).pack(side="left")

        ctk.CTkFrame(self, fg_color=C["border"], height=1).pack(
            fill="x", padx=24, pady=(14, 20)
        )

        ctk.CTkLabel(
            self, text="BOOKING.COM SEARCH URL",
            font=ctk.CTkFont(family=FONT, size=9, weight="bold"),
            text_color=C["accent"], anchor="w",
        ).pack(fill="x", **pad)

        self._url = ctk.CTkEntry(
            self, height=40,
            fg_color=C["bg"], border_color=C["border"], border_width=1,
            text_color=C["text"], placeholder_text_color=C["text_muted"],
            font=ctk.CTkFont(family=FONT, size=12), corner_radius=9,
        )
        self._url.insert(0, self._cur_url)
        self._url.pack(fill="x", pady=(5, 24), **pad)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", **pad, pady=(0, 24))

        ctk.CTkButton(
            btns, text="Cancel", width=100, height=40,
            fg_color=C["card_hover"], hover_color=C["border"],
            text_color=C["text_dim"],
            font=ctk.CTkFont(family=FONT, size=14), corner_radius=9,
            command=self.destroy,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btns, text="Save", width=150, height=40,
            fg_color=C["accent_dim"], hover_color=C["accent_h"],
            text_color=C["accent"],
            border_width=1, border_color=C["accent_dim"],
            font=ctk.CTkFont(family=FONT, size=14, weight="bold"),
            corner_radius=9, command=self._save,
        ).pack(side="right")

        self.bind("<Return>", lambda _: self._save())

    def _save(self):
        url = self._url.get().strip()
        if not url.startswith("http"):
            self._url.configure(border_color=C["error"])
            return
        self._on_save(self._city, url)
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
#  Confirm Delete Dialog
# ─────────────────────────────────────────────────────────────────────────────
class ConfirmDeleteDialog(ctk.CTkToplevel):
    def __init__(self, parent, city: str, on_confirm):
        super().__init__(parent)
        self._city       = city
        self._on_confirm = on_confirm

        self.title("Remove City")
        self.geometry("420x210")
        self.configure(fg_color=C["card"])
        self.resizable(False, False)
        self.transient(parent)
        self.after(20, self._deferred_init)

    def _deferred_init(self):
        self._build()
        self.grab_set()
        self.update_idletasks()
        px, py = self.master.winfo_x(), self.master.winfo_y()
        pw, ph = self.master.winfo_width(), self.master.winfo_height()
        x = px + (pw - self.winfo_width()) // 2
        y = py + (ph - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        self.lift()

    def _build(self):
        pad = {"padx": 28}

        ctk.CTkLabel(
            self, text="Remove city?",
            font=ctk.CTkFont(family=FONT, size=16, weight="bold"),
            text_color=C["text"], anchor="w",
        ).pack(fill="x", pady=(24, 6), **pad)

        ctk.CTkLabel(
            self,
            text=f'"{self._city}" will be removed from the list.\nThis does not delete any scraped data.',
            font=ctk.CTkFont(family=FONT, size=13),
            text_color=C["text_dim"], justify="left", anchor="w",
        ).pack(fill="x", **pad)

        ctk.CTkFrame(self, fg_color=C["border"], height=1).pack(
            fill="x", padx=20, pady=(20, 20)
        )

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", **pad, pady=(0, 24))

        ctk.CTkButton(
            btns, text="Cancel", width=90, height=38,
            fg_color=C["card_hover"], hover_color=C["border"],
            text_color=C["text_dim"],
            font=ctk.CTkFont(family=FONT, size=13), corner_radius=9,
            command=self.destroy,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btns, text="Remove", width=110, height=38,
            fg_color="#2a1010", hover_color="#8a2030",
            text_color=C["error"],
            border_width=1, border_color="#4a1020",
            font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
            corner_radius=9, command=self._confirm,
        ).pack(side="right")

        self.bind("<Return>", lambda _: self._confirm())
        self.bind("<Escape>", lambda _: self.destroy())

    def _confirm(self):
        self._on_confirm(self._city)
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
#  City card widget
# ─────────────────────────────────────────────────────────────────────────────
class CityCard(ctk.CTkFrame):
    def __init__(self, parent, city: str, selected: bool,
                 on_click, on_edit, on_delete, **kw):
        super().__init__(
            parent,
            fg_color=C["card_sel"] if selected else "transparent",
            corner_radius=8,
            cursor="hand2",
            **kw,
        )
        self.city       = city
        self._on_click  = on_click
        self._on_edit   = on_edit
        self._on_delete = on_delete
        self._selected  = selected

        # col 0: left accent strip (green when selected) — tk.Frame has no default min-height
        self._left_border = tk.Frame(
            self, width=3,
            bg=C["accent"] if selected else C["panel"],
        )
        self._left_border.grid(row=0, column=0, sticky="ns", padx=(4, 0), pady=6)

        # col 1: dot indicator
        self._dot = ctk.CTkLabel(
            self, text="●", font=ctk.CTkFont(size=8),
            text_color=C["accent"] if selected else C["text_muted"],
            width=18,
        )
        self._dot.grid(row=0, column=1, padx=(7, 3), pady=12)

        # col 2: city name (fills remaining width)
        self._lbl = ctk.CTkLabel(
            self, text=city, anchor="w",
            font=ctk.CTkFont(
                family=FONT, size=13,
                weight="bold" if selected else "normal",
            ),
            text_color=C["accent"] if selected else C["text_dim"],
        )
        self._lbl.grid(row=0, column=2, padx=(4, 4), pady=12, sticky="ew")
        self.columnconfigure(2, weight=1)

        # col 3: ··· menu button — invisible until hover
        self._menu_btn = ctk.CTkButton(
            self, text="···",
            width=28, height=24,
            fg_color="transparent",
            hover_color=C["card_hover"],
            text_color=C["panel"],
            font=ctk.CTkFont(family=FONT, size=14),
            corner_radius=6,
            command=self._open_menu,
        )
        self._menu_btn.grid(row=0, column=3, padx=(0, 8), pady=8)

        for w in (self, self._dot, self._lbl):
            w.bind("<Button-1>", self._click)
            w.bind("<Enter>",    self._hover_on)
            w.bind("<Leave>",    self._hover_off)

        self._menu_btn.bind("<Enter>", self._hover_on)
        self._menu_btn.bind("<Leave>", self._hover_off)

    def _click(self, _=None):
        self._on_click(self.city)

    def _hover_on(self, _=None):
        if not self._selected:
            self.configure(fg_color=C["card_hover"])
        self._menu_btn.configure(text_color=C["text_dim"])

    def _hover_off(self, event=None):
        if event:
            widget = event.widget.winfo_containing(event.x_root, event.y_root)
            if widget and (widget == self._menu_btn._canvas
                           or str(widget).startswith(str(self._menu_btn))):
                return
        if not self._selected:
            self.configure(fg_color="transparent")
        self._menu_btn.configure(text_color=C["panel"])

    def _open_menu(self):
        btn = self._menu_btn
        x = btn.winfo_rootx()
        y = btn.winfo_rooty() + btn.winfo_height() + 2
        CityContextMenu(
            self, x=x, y=y,
            on_edit=lambda: self._on_edit(self.city),
            on_delete=lambda: self._on_delete(self.city),
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Log panel — terminal style with macOS dots
# ─────────────────────────────────────────────────────────────────────────────
class LogPanel(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color=C["log_bg"], corner_radius=12, **kw)

        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=(12, 6))

        # macOS-style traffic light dots
        dots = ctk.CTkFrame(hdr, fg_color="transparent")
        dots.pack(side="left")
        for color in ("#ff5f57", "#febc2e", "#28c840"):
            ctk.CTkLabel(
                dots, text="●", font=ctk.CTkFont(size=11),
                text_color=color,
            ).pack(side="left", padx=(0, 3))

        ctk.CTkLabel(
            hdr, text="  REAL-TIME TERMINAL LOGS",
            font=ctk.CTkFont(family=FONT, size=9, weight="bold"),
            text_color=C["text_dim"],
        ).pack(side="left")

        ctk.CTkButton(
            hdr, text="clear", width=52, height=20,
            fg_color="transparent", hover_color=C["card_hover"],
            text_color=C["text_muted"],
            font=ctk.CTkFont(family=FONT, size=10),
            corner_radius=4, command=self.clear,
        ).pack(side="right")

        # Text area
        frame = ctk.CTkFrame(self, fg_color=C["log_bg"], corner_radius=0)
        frame.pack(fill="both", expand=True, padx=4, pady=(0, 8))

        self._txt = tk.Text(
            frame,
            bg=C["log_bg"], fg=C["log_info"],
            insertbackground=C["text"],
            font=(FONT_MONO, 11),
            wrap="word",
            relief="flat", bd=0,
            state="disabled",
            selectbackground=C["accent_dim"],
            selectforeground=C["text"],
        )
        scroll = tk.Scrollbar(
            frame, orient="vertical", command=self._txt.yview,
            bg=C["log_bg"], troughcolor=C["log_bg"],
            activebackground=C["accent_dim"],
        )
        self._txt.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self._txt.pack(side="left", fill="both", expand=True, padx=(8, 0))

        self._txt.tag_config("TIME",    foreground=C["log_time"])
        self._txt.tag_config("INFO",    foreground=C["log_info"])
        self._txt.tag_config("SUCCESS", foreground=C["log_success"])
        self._txt.tag_config("ERROR",   foreground=C["log_error"])
        self._txt.tag_config("WARNING", foreground=C["log_warning"])
        self._txt.tag_config("SEP",     foreground=C["log_sep"])

    def append(self, time_str: str, level: str, message: str):
        self._txt.configure(state="normal")
        self._txt.insert("end", f"[{time_str}] ", "TIME")
        tag = level.upper() if level.upper() in ("INFO", "SUCCESS", "ERROR", "WARNING") else "INFO"
        self._txt.insert("end", f"{level:<8} ", tag)
        self._txt.insert("end", message + "\n", tag)
        self._txt.see("end")
        self._txt.configure(state="disabled")

    def separator(self, label: str = ""):
        self._txt.configure(state="normal")
        if label:
            half = (56 - len(label)) // 2
            line = f"{'─' * half}  {label}  {'─' * half}"
        else:
            line = "─" * 62
        self._txt.insert("end", "\n" + line + "\n\n", "SEP")
        self._txt.see("end")
        self._txt.configure(state="disabled")

    def clear(self):
        self._txt.configure(state="normal")
        self._txt.delete("1.0", "end")
        self._txt.configure(state="disabled")


# ─────────────────────────────────────────────────────────────────────────────
#  Main application window
# ─────────────────────────────────────────────────────────────────────────────
class HotelScraperGUI(ctk.CTk):
    _URLS_PATH = PROJECT_ROOT / "config" / "booking_urls.json"

    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        super().__init__()
        self.withdraw()
        self.attributes('-alpha', 0.0)

        self._selected: str | None = None
        self._running              = False
        self._log_q: queue.Queue  = queue.Queue()
        self._cards: dict[str, CityCard] = {}
        self._headless_var         = tk.BooleanVar(value=False)
        self._breathe_active       = False
        self._breathe_step         = 0
        self._breathe_gen          = 0
        self._stop_event           = threading.Event()

        self._setup_window()
        self._setup_log_sink()
        self._build_ui()
        self._refresh_cities()
        self.after(80, self._drain_log_queue)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.update_idletasks()
        self.deiconify()
        self.after(10, self._fade_in)

    # ── Window fade-in / fade-out animations ─────────────────────────────────
    def _fade_in(self, alpha: float = 0.0):
        alpha = min(alpha + 0.08, 1.0)
        self.attributes('-alpha', alpha)
        if alpha < 1.0:
            self.after(16, self._fade_in, alpha)

    def _fade_out(self, alpha: float = 1.0):
        alpha = max(alpha - 0.1, 0.0)
        self.attributes('-alpha', alpha)
        if alpha > 0.0:
            self.after(16, self._fade_out, alpha)
        else:
            self.destroy()

    def _on_close(self):
        self._fade_out()

    # ── Window setup ──────────────────────────────────────────────────────────
    def _setup_window(self):
        self.title("Hotels Scraper")
        self.geometry("1200x820")
        self.minsize(960, 660)
        self.configure(fg_color=C["bg"])

    # ── Capture loguru INFO+ → queue → UI ────────────────────────────────────
    def _setup_log_sink(self):
        def _sink(msg):
            rec = msg.record
            self._log_q.put((
                rec["time"].strftime("%H:%M:%S"),
                rec["level"].name,
                rec["message"],
            ))
        logger.add(_sink, level="INFO", format="{message}")

    def _drain_log_queue(self):
        try:
            while True:
                t, lvl, msg = self._log_q.get_nowait()
                self._log.append(t, lvl, msg)
        except queue.Empty:
            pass
        self.after(80, self._drain_log_queue)

    # ── URL storage helpers ───────────────────────────────────────────────────
    def _load_urls(self) -> dict:
        with open(self._URLS_PATH, encoding="utf-8") as f:
            return json.load(f)

    def _save_urls(self, data: dict):
        with open(self._URLS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── City stats from local JSON base ──────────────────────────────────────
    def _load_city_stats(self, city: str) -> dict:
        base_path = PROJECT_ROOT / "base" / f"{city}_hotels.json"
        empty = {"total": 0, "avg_rating": 0.0, "last_scan": "—"}
        if not base_path.exists():
            return empty
        try:
            with open(base_path, encoding="utf-8") as f:
                data = json.load(f)
            if not data:
                return empty
            ratings = [h.get("rating", 0) for h in data if h.get("rating")]
            avg = sum(ratings) / len(ratings) if ratings else 0.0
            dates = []
            for h in data:
                if h.get("date_parsed"):
                    try:
                        dates.append(datetime.strptime(h["date_parsed"], "%d.%m.%Y"))
                    except Exception:
                        pass
            last = max(dates).strftime("%d.%m.%Y") if dates else "—"
            return {"total": len(data), "avg_rating": round(avg, 1), "last_scan": last}
        except Exception:
            return empty

    def _update_metrics(self, new_count: int | None = None):
        if not self._selected:
            self._m_total.configure(text="—")
            self._m_rating.configure(text="—")
            self._m_scan.configure(text="—")
            return
        stats = self._load_city_stats(self._selected)
        self._m_total.configure(text=str(stats["total"]) if stats["total"] else "0")
        self._m_rating.configure(
            text=f"{stats['avg_rating']:.1f}" if stats["avg_rating"] else "—"
        )
        self._m_scan.configure(text=stats["last_scan"])
        if new_count is not None:
            self._m_new.configure(text=str(new_count))

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        self._build_header()
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=18, pady=(0, 16))
        self._build_left(content)
        self._build_right(content)

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=C["panel"], height=56, corner_radius=0)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        # Logo
        logo = ctk.CTkFrame(hdr, fg_color="transparent")
        logo.pack(side="left", padx=22, pady=10)

        ctk.CTkLabel(
            logo, text="Hotel",
            font=ctk.CTkFont(family=FONT, size=17, weight="bold"),
            text_color=C["accent"],
        ).pack(side="left")

        ctk.CTkLabel(
            logo, text="Pulse",
            font=ctk.CTkFont(family=FONT, size=17, weight="bold"),
            text_color=C["text"],
        ).pack(side="left")

        ctk.CTkLabel(
            logo, text="  ·  booking.com",
            font=ctk.CTkFont(family=FONT, size=12),
            text_color=C["text_muted"],
        ).pack(side="left", pady=(2, 0))

        # Status indicator (right)
        self._status_lbl = ctk.CTkLabel(
            hdr, text="● Idle",
            font=ctk.CTkFont(family=FONT_MONO, size=11, weight="bold"),
            text_color=C["text_muted"],
        )
        self._status_lbl.pack(side="right", padx=22)

    def _build_left(self, parent):
        left = ctk.CTkFrame(parent, fg_color=C["panel"], corner_radius=14, width=256)
        left.pack(side="left", fill="y", padx=(0, 14), pady=16)
        left.pack_propagate(False)

        # Section header
        hdr = ctk.CTkFrame(left, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(18, 4))

        ctk.CTkLabel(
            hdr, text="ACTIVE CITIES",
            font=ctk.CTkFont(family=FONT, size=9, weight="bold"),
            text_color=C["accent"],
        ).pack(anchor="w")

        self._city_count_lbl = ctk.CTkLabel(
            hdr, text="",
            font=ctk.CTkFont(family=FONT, size=11),
            text_color=C["text_muted"],
        )
        self._city_count_lbl.pack(anchor="w", pady=(2, 0))

        # Scrollable city list
        self._cities_scroll = ctk.CTkScrollableFrame(
            left, fg_color="transparent",
            scrollbar_button_color=C["border"],
            scrollbar_button_hover_color=C["accent_dim"],
        )
        self._cities_scroll.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        ctk.CTkFrame(left, fg_color=C["border"], height=1).pack(
            fill="x", padx=16, pady=4
        )

        # Add city button
        ctk.CTkButton(
            left, text="＋  Add New City",
            height=40,
            fg_color=C["card_sel"], hover_color=C["card_hover"],
            text_color=C["accent"],
            font=ctk.CTkFont(family=FONT, size=12, weight="bold"),
            corner_radius=10, command=self._open_add_dialog,
        ).pack(fill="x", padx=14, pady=(4, 14))

    def _build_right(self, parent):
        right = ctk.CTkFrame(parent, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True, pady=16)

        # ── City header ───────────────────────────────────────────────────────
        city_hdr = ctk.CTkFrame(right, fg_color="transparent")
        city_hdr.pack(fill="x", pady=(0, 14))

        # Left: city info text
        info_left = ctk.CTkFrame(city_hdr, fg_color="transparent")
        info_left.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            info_left, text="CONTEXT ARCHITECTURE",
            font=ctk.CTkFont(family=FONT, size=9, weight="bold"),
            text_color=C["accent"], anchor="w",
        ).pack(anchor="w")

        self._city_name_lbl = ctk.CTkLabel(
            info_left,
            text="Select a city",
            font=ctk.CTkFont(family=FONT, size=28, weight="bold"),
            text_color=C["text_muted"],
            anchor="w",
        )
        self._city_name_lbl.pack(anchor="w")

        self._hotel_count_lbl = ctk.CTkLabel(
            info_left, text="",
            font=ctk.CTkFont(family=FONT, size=12),
            text_color=C["text_dim"],
            anchor="w",
        )
        self._hotel_count_lbl.pack(anchor="w", pady=(2, 0))

        # Right: controls (headless toggle + stop + run)
        ctrl = ctk.CTkFrame(city_hdr, fg_color="transparent")
        ctrl.pack(side="right", anchor="center")

        # Headless toggle row
        toggle_row = ctk.CTkFrame(ctrl, fg_color="transparent")
        toggle_row.pack(anchor="e", pady=(0, 10))

        # "Headless  [toggle]  Visible" — active mode is bright, inactive is dim
        self._headless_left_lbl = ctk.CTkLabel(
            toggle_row, text="Headless",
            font=ctk.CTkFont(family=FONT, size=12),
            text_color=C["text_muted"],   # dim by default (visible mode is on)
        )
        self._headless_left_lbl.pack(side="left", padx=(0, 8))

        self._headless_switch = ctk.CTkSwitch(
            toggle_row, text="",
            variable=self._headless_var,
            onvalue=True, offvalue=False,
            width=44, height=22,
            fg_color=C["toggle_off"],
            progress_color=C["toggle_on"],
            button_color=C["text"],
            button_hover_color=C["accent"],
            command=self._on_headless_toggle,
        )
        self._headless_switch.pack(side="left")

        self._headless_right_lbl = ctk.CTkLabel(
            toggle_row, text="Visible",
            font=ctk.CTkFont(family=FONT, size=12),
            text_color=C["text"],         # bright by default
        )
        self._headless_right_lbl.pack(side="left", padx=(8, 0))

        # Buttons row
        btns_row = ctk.CTkFrame(ctrl, fg_color="transparent")
        btns_row.pack(anchor="e")

        self._stop_btn = ctk.CTkButton(
            btns_row, text="◼  Stop",
            width=95, height=42,
            fg_color=C["card_hover"],
            hover_color="#4a1a2a",
            text_color=C["text_dim"],
            border_width=1, border_color=C["border"],
            font=ctk.CTkFont(family=FONT, size=13),
            corner_radius=10, state="disabled",
            command=self._stop_scraper,
        )
        self._stop_btn.pack(side="left", padx=(0, 10))

        self._run_btn = ctk.CTkButton(
            btns_row, text="▶  Start Scraper",
            width=148, height=42,
            fg_color=C["btn_run"],
            hover_color=C["btn_run_h"],
            text_color="#dfe2eb",
            font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
            corner_radius=10, state="disabled",
            command=self._run_scraper,
        )
        self._run_btn.pack(side="left")

        # ── Metric cards ──────────────────────────────────────────────────────
        metrics_row = ctk.CTkFrame(right, fg_color="transparent")
        metrics_row.pack(fill="x", pady=(0, 14))
        metrics_row.columnconfigure((0, 1, 2, 3), weight=1, uniform="metric")

        cards_cfg = [
            ("HOTELS IN DB",  "—", "· local database"),
            ("NEW FOUND",      "—", "· last scrape"),
            ("AVG RATING",     "—", "· booking.com"),
            ("LAST SCAN",      "—", "· date parsed"),
        ]
        val_labels = []
        for col, (title, val, sub) in enumerate(cards_cfg):
            padx = (0, 12) if col < 3 else (0, 0)
            lbl = self._make_metric_card(metrics_row, col, title, val, sub, padx)
            val_labels.append(lbl)

        self._m_total, self._m_new, self._m_rating, self._m_scan = val_labels

        # ── Progress bar ──────────────────────────────────────────────────────
        prog_hdr = ctk.CTkFrame(right, fg_color="transparent")
        prog_hdr.pack(fill="x")

        ctk.CTkLabel(
            prog_hdr, text="OPERATIONAL PROGRESS",
            font=ctk.CTkFont(family=FONT, size=9, weight="bold"),
            text_color=C["text_muted"],
        ).pack(side="left")

        self._scan_domain_lbl = ctk.CTkLabel(
            prog_hdr, text="",
            font=ctk.CTkFont(family=FONT_MONO, size=9),
            text_color=C["accent"],
        )
        self._scan_domain_lbl.pack(side="right")

        self._progress = ctk.CTkProgressBar(
            right, mode="indeterminate",
            fg_color=C["card_sel"],
            progress_color=C["accent"],
            height=4, corner_radius=2,
        )
        self._progress.pack(fill="x", pady=(4, 12))
        self._progress.set(0)

        # ── Log panel ─────────────────────────────────────────────────────────
        self._log = LogPanel(right)
        self._log.pack(fill="both", expand=True)

    def _make_metric_card(self, parent, col: int, title: str,
                          value: str, subtitle: str, padx) -> ctk.CTkLabel:
        card = ctk.CTkFrame(parent, fg_color=C["panel"], corner_radius=12)
        card.grid(row=0, column=col, sticky="ew", padx=padx, ipady=4)

        ctk.CTkLabel(
            card, text=title,
            font=ctk.CTkFont(family=FONT, size=9, weight="bold"),
            text_color=C["text_muted"],
            anchor="w",
        ).pack(anchor="w", padx=16, pady=(14, 2))

        val_lbl = ctk.CTkLabel(
            card, text=value,
            font=ctk.CTkFont(family=FONT, size=24, weight="bold"),
            text_color=C["text"],
            anchor="w",
        )
        val_lbl.pack(anchor="w", padx=16)

        ctk.CTkLabel(
            card, text=subtitle,
            font=ctk.CTkFont(family=FONT, size=10),
            text_color=C["text_dim"],
            anchor="w",
        ).pack(anchor="w", padx=16, pady=(2, 14))

        return val_lbl

    # ── City list ─────────────────────────────────────────────────────────────
    def _refresh_cities(self):
        for w in self._cities_scroll.winfo_children():
            w.destroy()
        self._cards.clear()

        urls = self._load_urls()

        # Update city count subtitle
        n = len(urls)
        self._city_count_lbl.configure(
            text=f"Monitoring {n} region{'s' if n != 1 else ''}" if n else ""
        )

        if not urls:
            ctk.CTkLabel(
                self._cities_scroll,
                text="No cities yet.\nAdd the first one!",
                text_color=C["text_muted"],
                font=ctk.CTkFont(family=FONT, size=13),
                justify="center",
            ).pack(pady=30)
            return

        for city in urls:
            card = CityCard(
                self._cities_scroll, city=city,
                selected=(city == self._selected),
                on_click=self._select_city,
                on_edit=self._edit_city,
                on_delete=self._delete_city,
            )
            card.pack(fill="x", pady=(0, 2))
            self._cards[city] = card

    def _select_city(self, city: str):
        if self._running:
            return
        self._selected = city

        for name, card in self._cards.items():
            sel = (name == city)
            card._selected = sel
            card.configure(fg_color=C["card_sel"] if sel else "transparent")
            card._left_border.configure(bg=C["accent"] if sel else C["panel"])
            card._dot.configure(text_color=C["accent"] if sel else C["text_muted"])
            card._lbl.configure(
                text_color=C["accent"] if sel else C["text_dim"],
                font=ctk.CTkFont(
                    family=FONT, size=13,
                    weight="bold" if sel else "normal",
                ),
            )

        self._city_name_lbl.configure(
            text=city,
            font=ctk.CTkFont(family=FONT, size=28, weight="bold"),
            text_color=C["text"],
        )
        self._update_metrics()

        # Update hotel count label
        stats = self._load_city_stats(city)
        if stats["total"]:
            self._hotel_count_lbl.configure(
                text=f"{stats['total']:,} hotels indexed in this region"
            )
        else:
            self._hotel_count_lbl.configure(text="No data yet — run the scraper")

        self._run_btn.configure(state="normal")
        self._start_breathe()

    # ── Add city dialog ───────────────────────────────────────────────────────
    def _open_add_dialog(self):
        def _on_save(name: str, url: str):
            urls = self._load_urls()
            if name in urls:
                self._log.append(
                    self._now(), "WARNING",
                    f"City '{name}' already exists in the list",
                )
                return
            urls[name] = url
            self._save_urls(urls)
            self._log.append(self._now(), "SUCCESS", f"City added: {name}")
            self._refresh_cities()
            self._select_city(name)

        AddCityDialog(self, on_save=_on_save)

    # ── Edit / delete city ────────────────────────────────────────────────────
    def _edit_city(self, city: str):
        if self._running:
            return
        urls = self._load_urls()
        current_url = urls.get(city, "")

        def _on_save(name: str, new_url: str):
            urls[name] = new_url
            self._save_urls(urls)
            self._log.append(self._now(), "SUCCESS", f"URL updated for: {name}")
            self._refresh_cities()

        EditCityDialog(self, city=city, current_url=current_url, on_save=_on_save)

    def _delete_city(self, city: str):
        if self._running:
            return
        ConfirmDeleteDialog(self, city=city, on_confirm=self._do_delete)

    def _do_delete(self, city: str):
        urls = self._load_urls()
        if city not in urls:
            return
        del urls[city]
        self._save_urls(urls)
        self._log.append(self._now(), "WARNING", f"City removed: {city}")
        if self._selected == city:
            self._selected = None
            self._city_name_lbl.configure(
                text="Select a city",
                font=ctk.CTkFont(family=FONT, size=28, weight="bold"),
                text_color=C["text_muted"],
            )
            self._hotel_count_lbl.configure(text="")
            self._run_btn.configure(state="disabled")
            self._m_total.configure(text="—")
            self._m_new.configure(text="—")
            self._m_rating.configure(text="—")
            self._m_scan.configure(text="—")
        self._refresh_cities()

    # ── Headless toggle ───────────────────────────────────────────────────────
    def _on_headless_toggle(self):
        if self._headless_var.get():
            # Headless ON — left label bright, right label dim
            self._headless_left_lbl.configure(text_color=C["accent"])
            self._headless_right_lbl.configure(text_color=C["text_muted"])
        else:
            # Visible ON — right label bright, left label dim
            self._headless_left_lbl.configure(text_color=C["text_muted"])
            self._headless_right_lbl.configure(text_color=C["text"])

    # ── Run button breathing animation ────────────────────────────────────────
    def _start_breathe(self):
        self._breathe_active = True
        self._breathe_step   = 0
        self._breathe_gen   += 1
        self._breathe_tick(self._breathe_gen)

    def _stop_breathe(self):
        self._breathe_active = False
        self._breathe_gen   += 1
        try:
            self._run_btn.configure(fg_color=C["btn_run"])
        except Exception:
            pass

    def _breathe_tick(self, gen: int):
        if gen != self._breathe_gen or not self._breathe_active or self._running:
            return
        t     = (math.sin(self._breathe_step * math.pi / 60) + 1) / 2
        color = _lerp_color(C["breathe_lo"], C["breathe_hi"], t)
        try:
            self._run_btn.configure(fg_color=color)
        except Exception:
            return
        self._breathe_step += 1
        self.after(20, self._breathe_tick, gen)

    # ── Status label ──────────────────────────────────────────────────────────
    def _set_status(self, text: str, color: str = None):
        self._status_lbl.configure(
            text=f"● {text}",
            text_color=color or C["text_muted"],
        )

    @staticmethod
    def _now() -> str:
        return datetime.now().strftime("%H:%M:%S")

    # ── Run scraper ───────────────────────────────────────────────────────────
    def _run_scraper(self):
        if not self._selected or self._running:
            return

        self._running = True
        self._stop_event.clear()
        self._stop_breathe()
        self._run_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._progress.start()
        self._set_status("RUNNING...", C["success"])
        self._scan_domain_lbl.configure(text="SCANNING DOMAIN: BOOKING.COM")
        self._log.separator(self._selected)

        headless = self._headless_var.get()
        self._thread = threading.Thread(
            target=self._worker,
            args=(self._selected, headless),
            daemon=True,
        )
        self._thread.start()

    def _make_filter_fail_callback(self) -> callable:
        def callback() -> bool:
            event  = threading.Event()
            result = [False]
            self.after(0, lambda: FilterWarningDialog(self, event, result))
            event.wait()
            return result[0]
        return callback

    def _worker(self, city: str, headless: bool):
        try:
            from scraper.storage import DataStorage
            from scraper.scraper import BookingScraper, ScraperConfig
            from scraper.parser import CardParser
            from scraper.sheets import GoogleSheetsManager

            storage  = DataStorage()
            url      = storage.get_booking_url(city)
            config   = ScraperConfig(
                page_load_timeout=40,
                element_timeout=15,
                retry_attempts=5,
                retry_delay=3.0,
            )
            old_data = storage.read_base(city, "hotels")

            mode_label = "headless" if headless else "visible"
            logger.info(f"Starting scraper for {city} ({mode_label} browser)")

            with BookingScraper(
                config,
                headless=headless,
                on_filter_fail=self._make_filter_fail_callback(),
                stop_event=self._stop_event,
            ) as scraper:
                cards = scraper.scrape(url=url, property_type="Hotels")
                if not cards:
                    if self._stop_event.is_set():
                        logger.info("Scraping stopped by user")
                        self.after(0, self._done, True, "Stopped by user", None)
                    else:
                        logger.info(f"No cards found for {city}")
                        self.after(0, self._done, False, "No cards found", None)
                    return
                updated_data, new_data = CardParser().parse(cards, old_data)

            storage.save_base(city, "hotels", updated_data)

            if new_data:
                logger.info(f"PROCESSED {len(new_data)} NEW properties")
                GoogleSheetsManager().update(new_data, city)
                self.after(0, self._done, True, f"New properties: {len(new_data)}", len(new_data))
            else:
                logger.info(f"No new properties found for {city}")
                self.after(0, self._done, True, "No new properties found", 0)

        except Exception as exc:
            logger.error(f"Scraper error: {exc}")
            self.after(0, self._done, False, str(exc), None)

    def _done(self, success: bool, message: str, new_count: int | None):
        self._running = False
        self._run_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._progress.stop()
        self._progress.set(0)
        self._scan_domain_lbl.configure(text="")
        self._start_breathe()
        self._update_metrics(new_count=new_count)

        # Refresh hotel count label
        if self._selected:
            stats = self._load_city_stats(self._selected)
            if stats["total"]:
                self._hotel_count_lbl.configure(
                    text=f"{stats['total']:,} hotels indexed in this region"
                )

        if success:
            self._set_status(f"Done — {message}", C["success"])
            self._log.append(self._now(), "SUCCESS", f"Finished: {message}")
        else:
            self._set_status("Error", C["error"])
            self._log.append(self._now(), "ERROR", f"Error: {message}")

        self._log.separator()

    def _stop_scraper(self):
        self._stop_event.set()
        self._log.append(self._now(), "WARNING", "Stop requested — finishing current operation...")
        self._set_status("Stopping...", C["warning"])
        self._stop_btn.configure(state="disabled")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    setup_loguru()
    app = HotelScraperGUI()
    app.mainloop()
