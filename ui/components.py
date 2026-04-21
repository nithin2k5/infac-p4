"""
Infac P4 — Reusable UI Components
Custom widgets for the industrial inspection application.
"""

import tkinter as tk
from tkinter import ttk
from ui.theme import Colors, Fonts, Dimensions


class RoundedFrame(tk.Canvas):
    """A frame with rounded corners drawn on a Canvas."""

    def __init__(self, parent, bg_color=Colors.BG_CARD, corner_radius=12,
                 border_color=Colors.BORDER, border_width=1, **kwargs):
        super().__init__(parent, highlightthickness=0, bg=Colors.BG_DARK, **kwargs)
        self.bg_color = bg_color
        self.corner_radius = corner_radius
        self.border_color = border_color
        self.border_width = border_width
        self._inner_frame = tk.Frame(self, bg=bg_color)
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        self.delete("rounded_bg")
        w, h = event.width, event.height
        r = self.corner_radius
        # Draw rounded rectangle
        self._round_rect(2, 2, w - 2, h - 2, r, fill=self.bg_color,
                         outline=self.border_color, width=self.border_width,
                         tags="rounded_bg")
        # Place inner frame
        pad = self.corner_radius // 2
        self.create_window(pad + 4, pad + 4, window=self._inner_frame,
                           anchor="nw", width=w - 2 * (pad + 4),
                           height=h - 2 * (pad + 4), tags="inner")
        self.tag_lower("rounded_bg")

    def _round_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1,
            x2, y1, x2, y1 + r, x2, y1 + r, x2, y2 - r,
            x2, y2 - r, x2, y2, x2 - r, y2, x2 - r, y2,
            x1 + r, y2, x1 + r, y2, x1, y2, x1, y2 - r,
            x1, y2 - r, x1, y1 + r, x1, y1 + r, x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    @property
    def inner(self):
        return self._inner_frame


class StatCard(tk.Frame):
    """A statistics card showing a value, label, and trend indicator."""

    def __init__(self, parent, icon="📊", label="Metric", value="0",
                 trend=None, trend_positive=True, accent_color=Colors.PRIMARY, **kwargs):
        super().__init__(parent, bg=Colors.BG_CARD, **kwargs)

        self.accent_color = accent_color
        self.configure(padx=0, pady=0)

        # Outer container with padding
        container = tk.Frame(self, bg=Colors.BG_CARD, padx=20, pady=16)
        container.pack(fill="both", expand=True)

        # Top row: icon + label
        top_row = tk.Frame(container, bg=Colors.BG_CARD)
        top_row.pack(fill="x", anchor="w")

        icon_label = tk.Label(top_row, text=icon, font=("Segoe UI", 16),
                              bg=Colors.BG_CARD, fg=accent_color)
        icon_label.pack(side="left", padx=(0, 8))

        name_label = tk.Label(top_row, text=label, font=Fonts.STAT_LABEL,
                              bg=Colors.BG_CARD, fg=Colors.TEXT_SECONDARY)
        name_label.pack(side="left", anchor="s", pady=(0, 2))

        # Accent line
        accent_line = tk.Frame(container, bg=accent_color, height=2)
        accent_line.pack(fill="x", pady=(10, 8))

        # Value row
        value_row = tk.Frame(container, bg=Colors.BG_CARD)
        value_row.pack(fill="x", anchor="w")

        self.value_label = tk.Label(value_row, text=value, font=Fonts.STAT_VALUE,
                                    bg=Colors.BG_CARD, fg=Colors.TEXT_PRIMARY)
        self.value_label.pack(side="left")

        # Trend indicator
        if trend is not None:
            trend_color = Colors.SUCCESS if trend_positive else Colors.DANGER
            trend_arrow = "▲" if trend_positive else "▼"
            trend_text = f" {trend_arrow} {trend}"
            trend_label = tk.Label(value_row, text=trend_text, font=Fonts.SMALL_BOLD,
                                   bg=Colors.BG_CARD, fg=trend_color)
            trend_label.pack(side="left", padx=(12, 0), anchor="s", pady=(0, 6))

        # Hover effects
        self._all_widgets = [self, container, top_row, icon_label, name_label,
                             accent_line, value_row, self.value_label]
        if trend is not None:
            self._all_widgets.append(trend_label)

        for w in self._all_widgets:
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

    def _on_enter(self, event):
        for w in self._all_widgets:
            try:
                w.configure(bg=Colors.BG_CARD_HOVER)
            except tk.TclError:
                pass

    def _on_leave(self, event):
        for w in self._all_widgets:
            try:
                w.configure(bg=Colors.BG_CARD)
            except tk.TclError:
                pass

    def update_value(self, new_value):
        self.value_label.configure(text=str(new_value))


class StatusBadge(tk.Frame):
    """A small colored badge indicating status (online, offline, etc.)."""

    STATUS_COLORS = {
        "online":       (Colors.SUCCESS, "● Online"),
        "offline":      (Colors.DANGER, "● Offline"),
        "connecting":   (Colors.WARNING, "● Connecting"),
        "ready":        (Colors.SUCCESS, "● Ready"),
        "error":        (Colors.DANGER, "● Error"),
        "idle":         (Colors.TEXT_MUTED, "● Idle"),
    }

    def __init__(self, parent, status="offline", bg=Colors.BG_DARK, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        color, text = self.STATUS_COLORS.get(status, (Colors.TEXT_MUTED, "● Unknown"))
        self.label = tk.Label(self, text=text, font=Fonts.SMALL_BOLD,
                              fg=color, bg=bg)
        self.label.pack()

    def set_status(self, status):
        color, text = self.STATUS_COLORS.get(status, (Colors.TEXT_MUTED, "● Unknown"))
        self.label.configure(text=text, fg=color)


class StyledButton(tk.Canvas):
    """A modern-looking button with rounded corners and hover animation."""

    def __init__(self, parent, text="Button", command=None,
                 bg_color=Colors.PRIMARY_DIM, fg_color=Colors.TEXT_PRIMARY,
                 hover_color=Colors.PRIMARY, icon=None, width=140, height=38,
                 font=Fonts.BUTTON, corner_radius=8, **kwargs):
        super().__init__(parent, width=width, height=height,
                         highlightthickness=0, bg=Colors.BG_DARK,
                         cursor="hand2", **kwargs)

        self.bg_color = bg_color
        self.fg_color = fg_color
        self.hover_color = hover_color
        self.command = command
        self.corner_radius = corner_radius
        self._width = width
        self._height = height

        # Draw the button
        self._bg_id = self._round_rect(1, 1, width - 1, height - 1,
                                        corner_radius, fill=bg_color,
                                        outline="", width=0)

        display_text = f"{icon}  {text}" if icon else text
        self._text_id = self.create_text(width // 2, height // 2,
                                          text=display_text, fill=fg_color,
                                          font=font)

        # Bind events
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _round_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1,
            x2, y1, x2, y1 + r, x2, y1 + r, x2, y2 - r,
            x2, y2 - r, x2, y2, x2 - r, y2, x2 - r, y2,
            x1 + r, y2, x1 + r, y2, x1, y2, x1, y2 - r,
            x1, y2 - r, x1, y1 + r, x1, y1 + r, x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _on_enter(self, event):
        self.itemconfig(self._bg_id, fill=self.hover_color)

    def _on_leave(self, event):
        self.itemconfig(self._bg_id, fill=self.bg_color)

    def _on_press(self, event):
        self.move(self._text_id, 0, 1)

    def _on_release(self, event):
        self.move(self._text_id, 0, -1)
        if self.command:
            self.command()


class SectionHeader(tk.Frame):
    """A section header with title and optional action button."""

    def __init__(self, parent, title="Section", subtitle=None,
                 action_text=None, action_command=None, bg=Colors.BG_DARK, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)

        left = tk.Frame(self, bg=bg)
        left.pack(side="left", fill="x", expand=True)

        title_label = tk.Label(left, text=title, font=Fonts.SUBHEADING,
                               fg=Colors.TEXT_PRIMARY, bg=bg)
        title_label.pack(anchor="w")

        if subtitle:
            sub_label = tk.Label(left, text=subtitle, font=Fonts.SMALL,
                                 fg=Colors.TEXT_SECONDARY, bg=bg)
            sub_label.pack(anchor="w", pady=(2, 0))

        if action_text:
            action_btn = StyledButton(self, text=action_text,
                                       command=action_command,
                                       bg_color=Colors.BG_CARD,
                                       hover_color=Colors.BG_CARD_HOVER,
                                       width=100, height=32,
                                       font=Fonts.BUTTON_SMALL,
                                       corner_radius=6)
            action_btn.pack(side="right", padx=(8, 0))


class DetectionLogTable(tk.Frame):
    """A styled table for showing detection log entries."""

    def __init__(self, parent, columns=None, **kwargs):
        super().__init__(parent, bg=Colors.BG_CARD, **kwargs)

        if columns is None:
            columns = ("ID", "Timestamp", "Type", "Confidence", "Status")

        # Create Treeview
        self.tree = ttk.Treeview(self, columns=columns, show="headings",
                                 selectmode="browse")

        # Configure columns
        col_widths = {"ID": 60, "Timestamp": 160, "Type": 120,
                      "Confidence": 100, "Status": 100}
        for col in columns:
            width = col_widths.get(col, 120)
            self.tree.heading(col, text=col, anchor="w")
            self.tree.column(col, width=width, anchor="w", minwidth=60)

        # Scrollbar
        scrollbar = ttk.Scrollbar(self, orient="vertical",
                                  command=self.tree.yview,
                                  style="Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Pack
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def insert_row(self, values, index="end"):
        self.tree.insert("", index, values=values)

    def clear(self):
        for item in self.tree.get_children():
            self.tree.delete(item)


class SearchBar(tk.Frame):
    """A styled search bar with icon and placeholder text."""

    def __init__(self, parent, placeholder="Search...", command=None,
                 bg=Colors.BG_DARK, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)

        container = tk.Frame(self, bg=Colors.BG_INPUT,
                             highlightbackground=Colors.BORDER,
                             highlightthickness=1, highlightcolor=Colors.PRIMARY)
        container.pack(fill="x", expand=True)

        icon = tk.Label(container, text="🔍", font=("Segoe UI", 12),
                        bg=Colors.BG_INPUT, fg=Colors.TEXT_MUTED)
        icon.pack(side="left", padx=(10, 4), pady=6)

        self.entry = tk.Entry(container, bg=Colors.BG_INPUT,
                              fg=Colors.TEXT_PRIMARY,
                              insertbackground=Colors.TEXT_PRIMARY,
                              font=Fonts.BODY, relief="flat",
                              highlightthickness=0)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=6)

        # Placeholder
        self.placeholder = placeholder
        self.entry.insert(0, placeholder)
        self.entry.configure(fg=Colors.TEXT_MUTED)
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)

        if command:
            self.entry.bind("<Return>", lambda e: command(self.get()))

    def _on_focus_in(self, event):
        if self.entry.get() == self.placeholder:
            self.entry.delete(0, "end")
            self.entry.configure(fg=Colors.TEXT_PRIMARY)

    def _on_focus_out(self, event):
        if not self.entry.get():
            self.entry.insert(0, self.placeholder)
            self.entry.configure(fg=Colors.TEXT_MUTED)

    def get(self):
        value = self.entry.get()
        return "" if value == self.placeholder else value


class ToggleSwitch(tk.Canvas):
    """A modern toggle switch widget."""

    def __init__(self, parent, command=None, initial=False, bg=Colors.BG_DARK, **kwargs):
        super().__init__(parent, width=48, height=26, highlightthickness=0,
                         bg=bg, cursor="hand2", **kwargs)
        self.command = command
        self._state = initial
        self._draw()
        self.bind("<Button-1>", self._toggle)

    def _draw(self):
        self.delete("all")
        if self._state:
            # On state
            self._round_rect(2, 2, 46, 24, 12, fill=Colors.PRIMARY,
                              outline="", tags="bg")
            self.create_oval(26, 4, 44, 22, fill="white", outline="", tags="knob")
        else:
            # Off state
            self._round_rect(2, 2, 46, 24, 12, fill=Colors.BG_CARD,
                              outline=Colors.BORDER, width=1, tags="bg")
            self.create_oval(4, 4, 22, 22, fill=Colors.TEXT_MUTED, outline="", tags="knob")

    def _round_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1,
            x2, y1, x2, y1 + r, x2, y1 + r, x2, y2 - r,
            x2, y2 - r, x2, y2, x2 - r, y2, x2 - r, y2,
            x1 + r, y2, x1 + r, y2, x1, y2, x1, y2 - r,
            x1, y2 - r, x1, y1 + r, x1, y1 + r, x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _toggle(self, event=None):
        self._state = not self._state
        self._draw()
        if self.command:
            self.command(self._state)

    @property
    def state(self):
        return self._state
