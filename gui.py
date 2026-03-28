#!/usr/bin/env python3
"""Hotels Scraper GUI — modern dark interface for Booking.com scraper."""

import tkinter as tk
import customtkinter as ctk
import json
import sys
import threading
import queue
from pathlib import Path
from typing import Optional
from loguru import logger

# ── Project root ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.logging_config import setup_loguru

# ── Color palette (dark purple-grey theme) ────────────────────────────────────
C = {
    "bg":           "#0e0e1c",
    "panel":        "#13132a",
    "card":         "#1b1b38",
    "card_hover":   "#22224a",
    "card_sel":     "#2a1f52",
    "border":       "#2e2e55",
    "border_sel":   "#7b5ea7",
    "accent":       "#7b5ea7",
    "accent_h":     "#9d7fd4",
    "accent_dim":   "#3d2d72",
    "text":         "#dcdcf8",
    "text_dim":     "#9090b8",
    "text_muted":   "#4a4a70",
    "success":      "#4ec9a0",
    "error":        "#e05468",
    "warning":      "#e0a844",
    "log_bg":       "#080814",
    "log_time":     "#4a4a6a",
    "log_info":     "#7878c0",
    "log_success":  "#4ec9a0",
    "log_error":    "#e05468",
    "log_warning":  "#e0a844",
    "log_sep":      "#2a2a50",
    "toggle_off":   "#2e2e55",
    "toggle_on":    "#7b5ea7",
}

FONT      = "Segoe UI"
FONT_MONO = "Consolas"


# ─────────────────────────────────────────────────────────────────────────────
#  Filter Warning Dialog
# ─────────────────────────────────────────────────────────────────────────────
class FilterWarningDialog(ctk.CTkToplevel):
    """Shown when the property-type filter fails to apply.
    Blocks the scraper thread via the provided threading.Event until the user decides.
    """

    def __init__(self, parent, event: threading.Event, result: list):
        super().__init__(parent)
        self._event  = event
        self._result = result  # mutable list; result[0] = True (continue) / False (abort)

        self.title("Filter Warning")
        self.geometry("500x310")
        self.configure(fg_color=C["card"])
        self.resizable(False, False)
        self.transient(parent)
        # Prevent closing via [X] without choosing
        self.protocol("WM_DELETE_WINDOW", self._on_abort)

        # Defer build — CTkToplevel needs one event-loop tick to fully initialize
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
        # Warning badge row
        badge_row = ctk.CTkFrame(self, fg_color="transparent")
        badge_row.pack(fill="x", padx=28, pady=(24, 0))

        badge = ctk.CTkFrame(
            badge_row,
            fg_color="#3a1f10", corner_radius=10,
            border_width=1, border_color="#b05020",
        )
        badge.pack(anchor="w")

        ctk.CTkLabel(
            badge, text="  ⚠  Filter not applied  ",
            font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
            text_color="#e08040",
        ).pack(padx=4, pady=6)

        # Main message
        ctk.CTkLabel(
            self,
            text=(
                "The Hotels filter could not be activated after\n"
                "all retry attempts."
            ),
            font=ctk.CTkFont(family=FONT, size=14),
            text_color=C["text"],
            justify="left",
        ).pack(anchor="w", padx=28, pady=(16, 4))

        ctk.CTkLabel(
            self,
            text=(
                "Without this filter, apartments, guesthouses, and\n"
                "other property types may be included in the results."
            ),
            font=ctk.CTkFont(family=FONT, size=13),
            text_color=C["text_dim"],
            justify="left",
        ).pack(anchor="w", padx=28, pady=(0, 0))

        # Divider
        ctk.CTkFrame(self, fg_color=C["border"], height=1).pack(
            fill="x", padx=24, pady=(20, 20)
        )

        # Buttons
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=28, pady=(0, 24))

        ctk.CTkButton(
            btns, text="Stop scraper",
            width=140, height=42,
            fg_color=C["card_hover"], hover_color=C["error"],
            text_color=C["text_dim"],
            font=ctk.CTkFont(family=FONT, size=14),
            corner_radius=9,
            command=self._on_abort,
        ).pack(side="right", padx=(10, 0))

        ctk.CTkButton(
            btns, text="Continue without filter",
            width=190, height=42,
            fg_color="#5a3500", hover_color="#7a4800",
            text_color="#e0a844",
            border_width=1, border_color="#7a4800",
            font=ctk.CTkFont(family=FONT, size=14, weight="bold"),
            corner_radius=9,
            command=self._on_continue,
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

        # Defer build — CTkToplevel needs one event-loop tick to fully initialize
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
            self, text="Add new city / filter",
            font=ctk.CTkFont(family=FONT, size=17, weight="bold"),
            text_color=C["text"], anchor="w",
        ).pack(fill="x", pady=(26, 0), **pad)

        ctk.CTkFrame(self, fg_color=C["border"], height=1).pack(
            fill="x", padx=24, pady=(14, 20)
        )

        ctk.CTkLabel(
            self, text="City name or filter label",
            font=ctk.CTkFont(family=FONT, size=12),
            text_color=C["text_dim"], anchor="w",
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
            self, text="Booking.com search URL",
            font=ctk.CTkFont(family=FONT, size=12),
            text_color=C["text_dim"], anchor="w",
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
            fg_color=C["accent"], hover_color=C["accent_h"],
            text_color="white",
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
    """Frameless dropdown that appears next to the ··· button.

    Closes when the user clicks anywhere outside the menu in the main window.
    Uses a <ButtonPress> binding on the parent root (no global grab needed),
    so item click handlers still fire normally.
    """

    def __init__(self, parent, x: int, y: int, on_edit, on_delete):
        self._parent_root = parent.winfo_toplevel()
        self._bind_id     = None

        super().__init__(parent)
        self.overrideredirect(True)
        self.configure(bg=C["card_hover"])
        self.geometry(f"160x76+{x}+{y}")
        self.resizable(False, False)

        # Thin border frame
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
                w.bind("<Enter>",    lambda _, fw=f, lw=lbl: (
                    fw.configure(bg=C["card"]), lw.configure(bg=C["card"])
                ))
                w.bind("<Leave>",    lambda _, fw=f, lw=lbl: (
                    fw.configure(bg=C["card_hover"]), lw.configure(bg=C["card_hover"])
                ))

        _item("  ✏  Edit URL",     C["text_dim"], on_edit)
        tk.Frame(inner, bg=C["border"], height=1).pack(fill="x", padx=8)
        _item("  ✕  Remove city",  C["error"],    on_delete)

        # Wait one tick so the opening click doesn't immediately close the menu
        self.after(50, self._bind_outside_click)

    def _bind_outside_click(self):
        """Attach a <ButtonPress> handler to the main window to detect outside clicks."""
        self._bind_id = self._parent_root.bind("<ButtonPress>", self._on_outside_click, "+")

    def _on_outside_click(self, event):
        """Close if the click landed outside this window's area."""
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
    """Pre-filled dialog for updating a city's Booking.com URL."""

    def __init__(self, parent, city: str, current_url: str, on_save):
        super().__init__(parent)
        self._city      = city
        self._cur_url   = current_url
        self._on_save   = on_save

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

        # City name (read-only header)
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
            text_color=C["accent_h"],
        ).pack(side="left")

        ctk.CTkFrame(self, fg_color=C["border"], height=1).pack(
            fill="x", padx=24, pady=(14, 20)
        )

        ctk.CTkLabel(
            self, text="Booking.com search URL",
            font=ctk.CTkFont(family=FONT, size=12),
            text_color=C["text_dim"], anchor="w",
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
            fg_color=C["accent"], hover_color=C["accent_h"],
            text_color="white",
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
    """Small confirmation dialog before removing a city."""

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
            text_color=C["text_dim"],
            justify="left", anchor="w",
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
            fg_color="#3a1010", hover_color="#b03040",
            text_color="#ffb0b8",
            border_width=1, border_color="#6a2020",
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
    def __init__(self, parent, city: str, selected: bool, on_click, on_edit, on_delete, **kw):
        fg = C["card_sel"] if selected else C["card"]
        bc = C["border_sel"] if selected else C["border"]
        super().__init__(
            parent, fg_color=fg, corner_radius=10,
            border_width=1, border_color=bc, cursor="hand2", **kw,
        )
        self.city      = city
        self._on_click = on_click
        self._on_edit  = on_edit
        self._on_delete = on_delete
        self._selected = selected

        dot_col = C["accent_h"]  if selected else C["text_muted"]
        txt_col = C["text"]      if selected else C["text_dim"]
        txt_w   = "bold"         if selected else "normal"

        self._dot = ctk.CTkLabel(
            self, text="●", font=ctk.CTkFont(size=9),
            text_color=dot_col, width=22,
        )
        self._dot.grid(row=0, column=0, padx=(12, 0), pady=13)

        self._lbl = ctk.CTkLabel(
            self, text=city, anchor="w",
            font=ctk.CTkFont(family=FONT, size=14, weight=txt_w),
            text_color=txt_col,
        )
        self._lbl.grid(row=0, column=1, padx=(7, 4), pady=13, sticky="ew")
        self.columnconfigure(1, weight=1)

        # ··· menu button — hidden until hover
        self._menu_btn = ctk.CTkButton(
            self, text="···",
            width=28, height=26,
            fg_color="transparent",
            hover_color=C["border"],
            text_color=C["text_muted"],   # starts invisible against card bg
            font=ctk.CTkFont(family=FONT, size=15),
            corner_radius=6,
            command=self._open_menu,
        )
        self._menu_btn.grid(row=0, column=2, padx=(0, 8), pady=8)
        # Hide by default — reveal on hover
        self._menu_btn.configure(text_color=C["card"])

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
        self._menu_btn.configure(text_color=C["text_muted"])

    def _hover_off(self, event=None):
        # Don't hide if mouse moved to the menu button itself
        if event:
            widget = event.widget.winfo_containing(event.x_root, event.y_root)
            if widget and (widget == self._menu_btn._canvas
                           or str(widget).startswith(str(self._menu_btn))):
                return
        if not self._selected:
            self.configure(fg_color=C["card"])
        self._menu_btn.configure(text_color=C["card"])

    def _open_menu(self):
        # Position dropdown below the ··· button
        btn = self._menu_btn
        x = btn.winfo_rootx()
        y = btn.winfo_rooty() + btn.winfo_height() + 2
        CityContextMenu(
            self,
            x=x, y=y,
            on_edit=lambda: self._on_edit(self.city),
            on_delete=lambda: self._on_delete(self.city),
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Log panel
# ─────────────────────────────────────────────────────────────────────────────
class LogPanel(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color=C["log_bg"], corner_radius=12, **kw)

        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(
            hdr, text="LOGS",
            font=ctk.CTkFont(family=FONT, size=10, weight="bold"),
            text_color=C["accent_h"],
        ).pack(side="left")

        ctk.CTkButton(
            hdr, text="clear", width=60, height=22,
            fg_color="transparent", hover_color=C["card"],
            text_color=C["text_muted"],
            font=ctk.CTkFont(family=FONT, size=11),
            corner_radius=6, command=self.clear,
        ).pack(side="right")

        frame = ctk.CTkFrame(self, fg_color=C["log_bg"], corner_radius=0)
        frame.pack(fill="both", expand=True, padx=4, pady=(0, 8))

        self._txt = tk.Text(
            frame,
            bg=C["log_bg"], fg=C["log_info"],
            insertbackground=C["text"],
            font=(FONT_MONO, 12),
            wrap="word",
            relief="flat",
            bd=0,
            state="disabled",
            selectbackground=C["accent_dim"],
            selectforeground=C["text"],
        )
        scroll = tk.Scrollbar(
            frame, orient="vertical", command=self._txt.yview,
            bg=C["panel"], troughcolor=C["log_bg"],
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

        self._selected: str | None = None
        self._running              = False
        self._log_q: queue.Queue  = queue.Queue()
        self._cards: dict[str, CityCard] = {}
        self._headless_var         = tk.BooleanVar(value=False)

        self._setup_window()
        self._setup_log_sink()
        self._build_ui()
        self._refresh_cities()
        self.after(80, self._drain_log_queue)

    # ── Window setup ──────────────────────────────────────────────────────────
    def _setup_window(self):
        self.title("Hotels Scraper")
        self.geometry("1140x780")
        self.minsize(920, 620)
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
        # INFO level — no debug output in UI
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

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        self._build_header()
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=18, pady=(0, 16))
        self._build_left(content)
        self._build_right(content)

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=C["panel"], height=66, corner_radius=0)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        left = ctk.CTkFrame(hdr, fg_color="transparent")
        left.pack(side="left", padx=22, pady=10)

        ctk.CTkLabel(
            left, text="🏨",
            font=ctk.CTkFont(size=28), text_color=C["accent_h"],
        ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            left, text="Hotels Scraper",
            font=ctk.CTkFont(family=FONT, size=20, weight="bold"),
            text_color=C["text"],
        ).pack(side="left")

        ctk.CTkLabel(
            left, text="  ·  booking.com",
            font=ctk.CTkFont(family=FONT, size=13),
            text_color=C["text_muted"],
        ).pack(side="left", pady=(3, 0))

        self._status_lbl = ctk.CTkLabel(
            hdr, text="● Idle",
            font=ctk.CTkFont(family=FONT, size=13),
            text_color=C["text_muted"],
        )
        self._status_lbl.pack(side="right", padx=24)

    def _build_left(self, parent):
        left = ctk.CTkFrame(parent, fg_color=C["panel"], corner_radius=14, width=265)
        left.pack(side="left", fill="y", padx=(0, 14), pady=16)
        left.pack_propagate(False)

        ctk.CTkLabel(
            left, text="CITIES",
            font=ctk.CTkFont(family=FONT, size=10, weight="bold"),
            text_color=C["text_muted"],
        ).pack(anchor="w", padx=18, pady=(18, 6))

        self._cities_scroll = ctk.CTkScrollableFrame(
            left, fg_color="transparent",
            scrollbar_button_color=C["border"],
            scrollbar_button_hover_color=C["accent_dim"],
        )
        self._cities_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        ctk.CTkFrame(left, fg_color=C["border"], height=1).pack(
            fill="x", padx=16, pady=4
        )

        ctk.CTkButton(
            left, text="＋  Add city",
            height=40,
            fg_color="transparent", hover_color=C["card"],
            text_color=C["accent_h"],
            border_color=C["accent_dim"], border_width=1,
            font=ctk.CTkFont(family=FONT, size=13),
            corner_radius=10, command=self._open_add_dialog,
        ).pack(fill="x", padx=14, pady=(4, 14))

    def _build_right(self, parent):
        right = ctk.CTkFrame(parent, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True, pady=16)

        # ── Top row: city info card + control panel ───────────────────────────
        top = ctk.CTkFrame(right, fg_color="transparent")
        top.pack(fill="x", pady=(0, 12))

        # Selected city display
        self._city_card = ctk.CTkFrame(top, fg_color=C["panel"], corner_radius=14)
        self._city_card.pack(side="left", fill="both", expand=True, padx=(0, 12))

        self._city_name_lbl = ctk.CTkLabel(
            self._city_card,
            text="Select a city from the list",
            font=ctk.CTkFont(family=FONT, size=15),
            text_color=C["text_muted"],
        )
        self._city_name_lbl.pack(expand=True, pady=22, padx=24)

        # Control panel (run/stop + headless toggle)
        ctrl = ctk.CTkFrame(top, fg_color=C["panel"], corner_radius=14, width=210)
        ctrl.pack(side="right", fill="y")
        ctrl.pack_propagate(False)

        self._run_btn = ctk.CTkButton(
            ctrl, text="▶   Run scraper",
            height=52,
            fg_color=C["accent"], hover_color=C["accent_h"],
            text_color="white",
            font=ctk.CTkFont(family=FONT, size=15, weight="bold"),
            corner_radius=10, state="disabled",
            command=self._run_scraper,
        )
        self._run_btn.pack(fill="x", padx=16, pady=(16, 8))

        self._stop_btn = ctk.CTkButton(
            ctrl, text="■   Stop",
            height=36,
            fg_color=C["card_hover"], hover_color=C["error"],
            text_color=C["text_dim"],
            font=ctk.CTkFont(family=FONT, size=13),
            corner_radius=10, state="disabled",
            command=self._stop_scraper,
        )
        self._stop_btn.pack(fill="x", padx=16, pady=(0, 12))

        # Divider
        ctk.CTkFrame(ctrl, fg_color=C["border"], height=1).pack(
            fill="x", padx=16, pady=(0, 10)
        )

        # Headless mode toggle
        toggle_row = ctk.CTkFrame(ctrl, fg_color="transparent")
        toggle_row.pack(fill="x", padx=16, pady=(0, 16))

        ctk.CTkLabel(
            toggle_row, text="Headless mode",
            font=ctk.CTkFont(family=FONT, size=12),
            text_color=C["text_dim"], anchor="w",
        ).pack(side="left", expand=True, fill="x")

        self._headless_switch = ctk.CTkSwitch(
            toggle_row,
            text="",
            variable=self._headless_var,
            onvalue=True, offvalue=False,
            width=44, height=22,
            fg_color=C["toggle_off"],
            progress_color=C["toggle_on"],
            button_color=C["text"],
            button_hover_color=C["accent_h"],
            command=self._on_headless_toggle,
        )
        self._headless_switch.pack(side="right")

        self._headless_lbl = ctk.CTkLabel(
            ctrl, text="Browser: visible",
            font=ctk.CTkFont(family=FONT, size=11),
            text_color=C["text_muted"],
        )
        self._headless_lbl.pack(pady=(0, 14))

        # ── Progress bar ──────────────────────────────────────────────────────
        self._progress = ctk.CTkProgressBar(
            right, mode="indeterminate",
            fg_color=C["card"], progress_color=C["accent"],
            height=3, corner_radius=2,
        )
        self._progress.pack(fill="x", pady=(0, 12))
        self._progress.set(0)

        # ── Log panel ─────────────────────────────────────────────────────────
        self._log = LogPanel(right)
        self._log.pack(fill="both", expand=True)

    # ── City list ─────────────────────────────────────────────────────────────
    def _refresh_cities(self):
        for w in self._cities_scroll.winfo_children():
            w.destroy()
        self._cards.clear()

        urls = self._load_urls()
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
            card.pack(fill="x", pady=(0, 6))
            self._cards[city] = card

    def _select_city(self, city: str):
        if self._running:
            return
        self._selected = city

        for name, card in self._cards.items():
            sel = (name == city)
            card._selected = sel
            card.configure(
                fg_color=C["card_sel"] if sel else C["card"],
                border_color=C["border_sel"] if sel else C["border"],
            )
            card._dot.configure(text_color=C["accent_h"] if sel else C["text_muted"])
            card._lbl.configure(
                text_color=C["text"] if sel else C["text_dim"],
                font=ctk.CTkFont(
                    family=FONT, size=14,
                    weight="bold" if sel else "normal",
                ),
            )

        self._city_name_lbl.configure(
            text=f"🌍  {city}",
            font=ctk.CTkFont(family=FONT, size=19, weight="bold"),
            text_color=C["text"],
        )
        self._run_btn.configure(state="normal")

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
                text="Select a city from the list",
                font=ctk.CTkFont(family=FONT, size=15),
                text_color=C["text_muted"],
            )
            self._run_btn.configure(state="disabled")
        self._refresh_cities()

    # ── Headless toggle ───────────────────────────────────────────────────────
    def _on_headless_toggle(self):
        if self._headless_var.get():
            self._headless_lbl.configure(text="Browser: headless", text_color=C["accent_h"])
        else:
            self._headless_lbl.configure(text="Browser: visible",  text_color=C["text_muted"])

    # ── Status label ──────────────────────────────────────────────────────────
    def _set_status(self, text: str, color: str = None):
        self._status_lbl.configure(
            text=f"● {text}",
            text_color=color or C["text_muted"],
        )

    @staticmethod
    def _now() -> str:
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")

    # ── Run scraper ───────────────────────────────────────────────────────────
    def _run_scraper(self):
        if not self._selected or self._running:
            return

        self._running = True
        self._run_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._progress.start()
        self._set_status("Running...", C["success"])
        self._log.separator(self._selected)

        headless = self._headless_var.get()
        self._thread = threading.Thread(
            target=self._worker,
            args=(self._selected, headless),
            daemon=True,
        )
        self._thread.start()

    def _make_filter_fail_callback(self) -> callable:
        """Return a thread-safe callback for BookingScraper.
        Called from the scraper thread when filter cannot be applied.
        Blocks the thread, shows a warning dialog on the main thread,
        and returns True (continue) or False (abort) once the user decides.
        """
        def callback() -> bool:
            event  = threading.Event()
            result = [False]  # mutable container for dialog's choice

            # Schedule dialog creation on the main (GUI) thread
            self.after(0, lambda: FilterWarningDialog(self, event, result))

            # Block the scraper thread until the user clicks a button
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
            ) as scraper:
                cards = scraper.scrape(url=url, property_type="Hotels")
                if not cards:
                    logger.info(f"No cards found for {city}")
                    self.after(0, self._done, False, "No cards found")
                    return
                updated_data, new_data = CardParser().parse(cards, old_data)

            storage.save_base(city, "hotels", updated_data)

            if new_data:
                logger.info(f"PROCESSED {len(new_data)} NEW properties")
                GoogleSheetsManager().update(new_data, city)
                self.after(0, self._done, True, f"New properties: {len(new_data)}")
            else:
                logger.info(f"No new properties found for {city}")
                self.after(0, self._done, True, "No new properties found")

        except Exception as exc:
            logger.error(f"Scraper error: {exc}")
            self.after(0, self._done, False, str(exc))

    def _done(self, success: bool, message: str):
        self._running = False
        self._run_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._progress.stop()
        self._progress.set(0)

        if success:
            self._set_status(f"Done — {message}", C["success"])
            self._log.append(self._now(), "SUCCESS", f"Finished: {message}")
        else:
            self._set_status("Error", C["error"])
            self._log.append(self._now(), "ERROR", f"Error: {message}")

        self._log.separator()

    def _stop_scraper(self):
        self._log.append(
            self._now(), "WARNING",
            "Stop requested — will finish after current operation",
        )
        self._set_status("Stopping...", C["warning"])


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    setup_loguru()
    app = HotelScraperGUI()
    app.mainloop()
