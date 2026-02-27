"""
InFac P4 — Centralized Theme System
Dark industrial theme with blue accent colors.
"""

import tkinter as tk
from tkinter import ttk


# ─── Color Palette ───────────────────────────────────────────────────────────

class Colors:
    """Centralized color definitions for the entire application."""

    # Backgrounds
    BG_DARKEST      = "#0d1117"
    BG_DARK         = "#161b22"
    BG_MEDIUM       = "#1c2333"
    BG_CARD         = "#21283b"
    BG_CARD_HOVER   = "#2a3250"
    BG_SIDEBAR      = "#0d1117"
    BG_SIDEBAR_HOVER = "#1c2333"
    BG_INPUT        = "#0d1117"

    # Accent colors
    PRIMARY         = "#58a6ff"
    PRIMARY_HOVER   = "#79b8ff"
    PRIMARY_DIM     = "#1f6feb"
    SECONDARY       = "#8b949e"

    # Status colors
    SUCCESS         = "#3fb950"
    SUCCESS_DIM     = "#238636"
    WARNING         = "#d29922"
    WARNING_DIM     = "#9e6a03"
    DANGER          = "#f85149"
    DANGER_DIM      = "#da3633"
    INFO            = "#58a6ff"

    # Text
    TEXT_PRIMARY    = "#f0f6fc"
    TEXT_SECONDARY  = "#8b949e"
    TEXT_MUTED      = "#6e7681"
    TEXT_LINK       = "#58a6ff"

    # Borders
    BORDER          = "#30363d"
    BORDER_HOVER    = "#484f58"
    BORDER_ACTIVE   = "#58a6ff"

    # Chart colors
    CHART_1         = "#58a6ff"
    CHART_2         = "#3fb950"
    CHART_3         = "#d29922"
    CHART_4         = "#f85149"
    CHART_5         = "#bc8cff"
    CHART_6         = "#39d2c0"


# ─── Font Definitions ────────────────────────────────────────────────────────

class Fonts:
    """Font definitions used throughout the application."""

    FAMILY          = "Segoe UI"
    FAMILY_MONO     = "Cascadia Code"

    # Size definitions
    TITLE           = (FAMILY, 24, "bold")
    HEADING         = (FAMILY, 18, "bold")
    SUBHEADING      = (FAMILY, 14, "bold")
    BODY            = (FAMILY, 11)
    BODY_BOLD       = (FAMILY, 11, "bold")
    SMALL           = (FAMILY, 9)
    SMALL_BOLD      = (FAMILY, 9, "bold")
    TINY            = (FAMILY, 8)
    MONO            = (FAMILY_MONO, 10)
    MONO_SMALL      = (FAMILY_MONO, 9)

    # Stat card numbers
    STAT_VALUE      = (FAMILY, 28, "bold")
    STAT_LABEL      = (FAMILY, 10)

    # Sidebar
    SIDEBAR_ITEM    = (FAMILY, 11)
    SIDEBAR_HEADER  = (FAMILY, 8, "bold")

    # Button
    BUTTON          = (FAMILY, 10, "bold")
    BUTTON_SMALL    = (FAMILY, 9)


# ─── Dimensions ──────────────────────────────────────────────────────────────

class Dimensions:
    """Spacing, sizing, and layout constants."""

    SIDEBAR_WIDTH       = 220
    SIDEBAR_COLLAPSED   = 60
    TOPBAR_HEIGHT       = 50
    CARD_RADIUS         = 8
    BUTTON_RADIUS       = 6
    PADDING_XS          = 4
    PADDING_SM          = 8
    PADDING_MD          = 16
    PADDING_LG          = 24
    PADDING_XL          = 32
    MIN_WINDOW_W        = 1200
    MIN_WINDOW_H        = 750


# ─── TTK Style Configuration ─────────────────────────────────────────────────

def configure_styles(root: tk.Tk):
    """Apply the dark industrial theme to all ttk widgets."""

    style = ttk.Style(root)
    style.theme_use("clam")

    # ── TFrame ───────────────────────────────────────────
    style.configure("TFrame", background=Colors.BG_DARK)
    style.configure("Dark.TFrame", background=Colors.BG_DARKEST)
    style.configure("Card.TFrame", background=Colors.BG_CARD)
    style.configure("Sidebar.TFrame", background=Colors.BG_SIDEBAR)

    # ── TLabel ───────────────────────────────────────────
    style.configure("TLabel",
                    background=Colors.BG_DARK,
                    foreground=Colors.TEXT_PRIMARY,
                    font=Fonts.BODY)
    style.configure("Title.TLabel",
                    font=Fonts.TITLE,
                    foreground=Colors.TEXT_PRIMARY,
                    background=Colors.BG_DARK)
    style.configure("Heading.TLabel",
                    font=Fonts.HEADING,
                    foreground=Colors.TEXT_PRIMARY,
                    background=Colors.BG_DARK)
    style.configure("Subheading.TLabel",
                    font=Fonts.SUBHEADING,
                    foreground=Colors.TEXT_PRIMARY,
                    background=Colors.BG_DARK)
    style.configure("Secondary.TLabel",
                    foreground=Colors.TEXT_SECONDARY,
                    background=Colors.BG_DARK,
                    font=Fonts.SMALL)
    style.configure("Muted.TLabel",
                    foreground=Colors.TEXT_MUTED,
                    background=Colors.BG_DARK,
                    font=Fonts.TINY)
    style.configure("Card.TLabel",
                    background=Colors.BG_CARD,
                    foreground=Colors.TEXT_PRIMARY)
    style.configure("CardSecondary.TLabel",
                    background=Colors.BG_CARD,
                    foreground=Colors.TEXT_SECONDARY,
                    font=Fonts.SMALL)
    style.configure("Success.TLabel",
                    foreground=Colors.SUCCESS,
                    background=Colors.BG_CARD)
    style.configure("Danger.TLabel",
                    foreground=Colors.DANGER,
                    background=Colors.BG_CARD)
    style.configure("Warning.TLabel",
                    foreground=Colors.WARNING,
                    background=Colors.BG_CARD)

    # ── TButton ──────────────────────────────────────────
    style.configure("TButton",
                    background=Colors.PRIMARY_DIM,
                    foreground=Colors.TEXT_PRIMARY,
                    font=Fonts.BUTTON,
                    padding=(16, 8),
                    borderwidth=0)
    style.map("TButton",
              background=[("active", Colors.PRIMARY),
                          ("pressed", Colors.PRIMARY_DIM)])

    style.configure("Accent.TButton",
                    background=Colors.PRIMARY,
                    foreground=Colors.BG_DARKEST,
                    font=Fonts.BUTTON,
                    padding=(20, 10))
    style.map("Accent.TButton",
              background=[("active", Colors.PRIMARY_HOVER)])

    style.configure("Danger.TButton",
                    background=Colors.DANGER_DIM,
                    foreground=Colors.TEXT_PRIMARY,
                    font=Fonts.BUTTON,
                    padding=(16, 8))
    style.map("Danger.TButton",
              background=[("active", Colors.DANGER)])

    style.configure("Success.TButton",
                    background=Colors.SUCCESS_DIM,
                    foreground=Colors.TEXT_PRIMARY,
                    font=Fonts.BUTTON,
                    padding=(16, 8))
    style.map("Success.TButton",
              background=[("active", Colors.SUCCESS)])

    style.configure("Ghost.TButton",
                    background=Colors.BG_DARK,
                    foreground=Colors.TEXT_SECONDARY,
                    font=Fonts.BUTTON,
                    padding=(12, 6),
                    borderwidth=1)
    style.map("Ghost.TButton",
              background=[("active", Colors.BG_CARD)],
              foreground=[("active", Colors.TEXT_PRIMARY)])

    # ── TEntry ───────────────────────────────────────────
    style.configure("TEntry",
                    fieldbackground=Colors.BG_INPUT,
                    foreground=Colors.TEXT_PRIMARY,
                    insertcolor=Colors.TEXT_PRIMARY,
                    borderwidth=1,
                    padding=(8, 6))
    style.map("TEntry",
              bordercolor=[("focus", Colors.BORDER_ACTIVE),
                           ("!focus", Colors.BORDER)])

    # ── TCombobox ────────────────────────────────────────
    style.configure("TCombobox",
                    fieldbackground=Colors.BG_INPUT,
                    background=Colors.BG_CARD,
                    foreground=Colors.TEXT_PRIMARY,
                    arrowcolor=Colors.TEXT_SECONDARY,
                    borderwidth=1,
                    padding=(8, 6))

    # ── Horizontal.TScale ────────────────────────────────
    style.configure("Horizontal.TScale",
                    background=Colors.BG_DARK,
                    troughcolor=Colors.BG_CARD,
                    sliderthickness=16)

    # ── TProgressbar ─────────────────────────────────────
    style.configure("Horizontal.TProgressbar",
                    background=Colors.PRIMARY,
                    troughcolor=Colors.BG_CARD,
                    borderwidth=0,
                    thickness=6)
    style.configure("Success.Horizontal.TProgressbar",
                    background=Colors.SUCCESS)
    style.configure("Warning.Horizontal.TProgressbar",
                    background=Colors.WARNING)
    style.configure("Danger.Horizontal.TProgressbar",
                    background=Colors.DANGER)

    # ── Treeview ─────────────────────────────────────────
    style.configure("Treeview",
                    background=Colors.BG_CARD,
                    foreground=Colors.TEXT_PRIMARY,
                    fieldbackground=Colors.BG_CARD,
                    borderwidth=0,
                    rowheight=36,
                    font=Fonts.SMALL)
    style.configure("Treeview.Heading",
                    background=Colors.BG_MEDIUM,
                    foreground=Colors.TEXT_SECONDARY,
                    borderwidth=0,
                    font=Fonts.SMALL_BOLD)
    style.map("Treeview",
              background=[("selected", Colors.PRIMARY_DIM)],
              foreground=[("selected", Colors.TEXT_PRIMARY)])

    # ── TNotebook ────────────────────────────────────────
    style.configure("TNotebook",
                    background=Colors.BG_DARK,
                    borderwidth=0)
    style.configure("TNotebook.Tab",
                    background=Colors.BG_CARD,
                    foreground=Colors.TEXT_SECONDARY,
                    padding=(16, 8),
                    font=Fonts.SMALL_BOLD)
    style.map("TNotebook.Tab",
              background=[("selected", Colors.BG_DARK)],
              foreground=[("selected", Colors.TEXT_PRIMARY)])

    # ── TSeparator ───────────────────────────────────────
    style.configure("TSeparator", background=Colors.BORDER)

    # ── TScrollbar ───────────────────────────────────────
    style.configure("Vertical.TScrollbar",
                    background=Colors.BG_CARD,
                    troughcolor=Colors.BG_DARK,
                    borderwidth=0,
                    arrowsize=0)
    style.map("Vertical.TScrollbar",
              background=[("active", Colors.BORDER_HOVER)])

    return style
