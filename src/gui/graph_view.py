"""
src/graph_view.py
=================
Interactive, Obsidian-style Citation Graph View widget for CustomTkinter.
Supports:
- Live 60FPS Force-Directed Physics Animation Loop with Elastic Spring Dragging
  (Dragging a node actively pulls connected neighbors with smooth spring physics)
- Obsidian Dark Aesthetic with glowing node halos and subtle dark palette
- Smooth Zoom (centered at mouse cursor) & Pan (click-and-drag)
- Hover Focus (fades unrelated nodes/edges) & Clean Tooltip Card
- Node Search / Filter
- Minimal, decluttered toolbar (No Load Cache, on-demand build rendering only)
"""
import os
import math
import time
import random
import colorsys
import textwrap
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk
import customtkinter as ctk

from src.gui.graph_render import GraphRenderer

GRAPH_THEME = {
    "canvas_bg": "#F7F7FA",
    "dot_grid": "#D8DCE8",          # Crisp subtle grid
    "node_regular": "#3A4052",      # Dark solid slate (High contrast!)
    "node_hub": "#8E7CC3",          # Accent lavender/purple
    "node_highlight": "#E0A84F",    # Warm amber for focus/selection
    "node_search": "#E0A84F",       # Warm amber for search matches
    "node_dimmed": "#969EB2",       # Noticeable matte gray for non-connected
    "edge_default": "#6B7285",      # Crisp dark slate hairline edge (High contrast!)
    "edge_highlight": "#8E7CC3",    # Active edge purple
    "edge_dimmed": "#C2C6D4",       # Subdued faded edge
    "text_primary": "#2D3140",      # Dark slate
    "text_muted": "#474E61",        # Muted slate (darker for high readability)
    "tooltip_bg": "#2D3140",        # Dark slate matte card
    "tooltip_border": "#3E4354",
    "badge_bg": "#F0F1F6",
}


class GraphView(ctk.CTkFrame):
    """
    An interactive, organic Obsidian-style Graph View widget.
    """
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=GRAPH_THEME["canvas_bg"], corner_radius=8, **kwargs)

        self.cites: dict[str, list[str]] = {}
        self.cited_by: dict[str, list[str]] = {}
        self.all_papers: dict[str, dict] = {}

        # Graph node data: {doi: {x, y, vx, vy, radius, citekey, title, authors, year, ...}}
        self.nodes: dict[str, dict] = {}
        self.edges: list[tuple[str, str]] = []

        # Offscreen Vector Renderer & Canvas Image State
        self.renderer = GraphRenderer()
        self._bg_image_id = None
        self._current_photo = None
        self._frame_times: list[float] = []
        self.anim_tick_ms = 16

        # Vectorized NumPy Physics Arrays
        self.doi_list: list[str] = []
        self.doi_to_idx: dict[str, int] = {}
        self.pos = None        # shape (n, 2)
        self.vel = None        # shape (n, 2)
        self.radii = None      # shape (n,)
        self.pinned = None     # shape (n,)
        self.edge_indices = None  # shape (E, 2)

        # Viewport transformation
        self.zoom = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0

        # Interaction state
        self.hovered_doi: str | None = None
        self.selected_doi: str | None = None
        self.dragged_doi: str | None = None
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.is_panning = False
        self.search_query = ""
        self.on_node_selected = None  # Callback signature: fn(doi: str | None)

        # Obsidian Graph Settings Parameters
        self.show_settings = False
        self.setting_node_size = 9.0     # Base radius (slider 4-22)
        self.setting_distance = 170.0    # Spring rest length (slider 80-320)
        self.setting_repel = 14000.0     # Repulsion (slider 4000-35000)
        self.setting_gravity = 0.0008    # Center pull (slider 0.0001-0.0050)

        # Live Physics Engine Parameters
        self.alpha = 0.0                 # Physics activity/temperature
        self.is_animating = False
        self._anim_timer_id = None
        self.k_repulse = self.setting_repel
        self.k_spring = 0.045
        self.spring_len = self.setting_distance
        self.k_gravity = self.setting_gravity
        self.damping = 0.82

        # Interactive Spectrum Color Palette State
        self.target_color_mode = "node"  # "node" | "hub" | "link"
        self.spec_w = 260
        self.spec_h = 24
        self.spec_img = self._generate_spectrum_image(self.spec_w, self.spec_h)
        self.spec_photo = ImageTk.PhotoImage(self.spec_img)

        # Smooth resize debouncing state
        self._last_canvas_w = 0
        self._last_canvas_h = 0
        self._resize_redraw_id = None

        self._init_ui()

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------
    def _init_ui(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # 1. Sleek Top Toolbar
        self.toolbar = ctk.CTkFrame(self, fg_color="#FFFFFF", height=38, corner_radius=6, border_width=1, border_color="#E2E4EC")
        self.toolbar.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 2))
        self.toolbar.grid_columnconfigure(1, weight=1)

        # Title & Count Badge
        left_box = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        left_box.grid(row=0, column=0, padx=8, pady=4, sticky="w")

        lbl_title = ctk.CTkLabel(
            left_box,
            text="Graph View",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=GRAPH_THEME["text_primary"]
        )
        lbl_title.pack(side="left", padx=(0, 6))

        self.lbl_stats = ctk.CTkLabel(
            left_box,
            text="Ready",
            font=ctk.CTkFont(size=11),
            fg_color=GRAPH_THEME["badge_bg"],
            text_color=GRAPH_THEME["text_muted"],
            corner_radius=4,
            padx=6,
            pady=1
        )
        self.lbl_stats.pack(side="left")

        # Minimal Controls on Right
        btn_box = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        btn_box.grid(row=0, column=2, padx=6, pady=4, sticky="e")

        self.btn_zoom_in = ctk.CTkButton(
            btn_box,
            text="+",
            width=26,
            height=26,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#ECEEF4",
            hover_color="#DFE2EC",
            text_color=GRAPH_THEME["text_primary"],
            command=lambda: self._zoom_step(1.25)
        )
        self.btn_zoom_in.pack(side="left", padx=2)

        self.btn_zoom_out = ctk.CTkButton(
            btn_box,
            text="-",
            width=26,
            height=26,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#ECEEF4",
            hover_color="#DFE2EC",
            text_color=GRAPH_THEME["text_primary"],
            command=lambda: self._zoom_step(0.8)
        )
        self.btn_zoom_out.pack(side="left", padx=2)

        self.btn_reset = ctk.CTkButton(
            btn_box,
            text="Fit",
            width=32,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color="#ECEEF4",
            hover_color="#DFE2EC",
            text_color=GRAPH_THEME["text_primary"],
            command=self.fit_view
        )
        self.btn_reset.pack(side="left", padx=2)

        self.btn_relayout = ctk.CTkButton(
            btn_box,
            text="Layout",
            width=46,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color="#ECEEF4",
            hover_color="#DFE2EC",
            text_color=GRAPH_THEME["text_primary"],
            command=self.recompute_layout
        )
        self.btn_relayout.pack(side="left", padx=2)

        self.btn_settings = ctk.CTkButton(
            btn_box,
            text="Settings & Palette",
            width=115,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color="#ECEEF4",
            hover_color="#DFE2EC",
            text_color=GRAPH_THEME["text_primary"],
            command=self.toggle_settings_panel
        )
        self.btn_settings.pack(side="left", padx=(2, 0))

        # 2. Obsidian-Style Sliders & Spectrum Palette Panel (Collapsible)
        self.settings_card = ctk.CTkFrame(
            self,
            fg_color="#FFFFFF",
            corner_radius=6,
            border_width=1,
            border_color="#E2E4EC"
        )
        self.settings_card.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Slider 1: Node Size
        box_size = ctk.CTkFrame(self.settings_card, fg_color="transparent")
        box_size.grid(row=0, column=0, padx=6, pady=4, sticky="ew")
        self.lbl_size = ctk.CTkLabel(box_size, text="Node Size: 9px", font=ctk.CTkFont(size=11), text_color=GRAPH_THEME["text_muted"])
        self.lbl_size.pack(anchor="w")
        self.slider_size = ctk.CTkSlider(box_size, from_=4, to=22, number_of_steps=18, fg_color="#ECEEF4", progress_color="#8E7CC3", button_color="#8E7CC3", button_hover_color="#7B68B3", height=14, command=self._on_size_slider)
        self.slider_size.set(self.setting_node_size)
        self.slider_size.pack(fill="x", pady=(2, 0))

        # Slider 2: Link Distance
        box_dist = ctk.CTkFrame(self.settings_card, fg_color="transparent")
        box_dist.grid(row=0, column=1, padx=6, pady=4, sticky="ew")
        self.lbl_dist = ctk.CTkLabel(box_dist, text="Distance: 170", font=ctk.CTkFont(size=11), text_color=GRAPH_THEME["text_muted"])
        self.lbl_dist.pack(anchor="w")
        self.slider_dist = ctk.CTkSlider(box_dist, from_=80, to=320, number_of_steps=24, fg_color="#ECEEF4", progress_color="#8E7CC3", button_color="#8E7CC3", button_hover_color="#7B68B3", height=14, command=self._on_dist_slider)
        self.slider_dist.set(self.setting_distance)
        self.slider_dist.pack(fill="x", pady=(2, 0))

        # Slider 3: Repel Force
        box_rep = ctk.CTkFrame(self.settings_card, fg_color="transparent")
        box_rep.grid(row=0, column=2, padx=6, pady=4, sticky="ew")
        self.lbl_repel = ctk.CTkLabel(box_rep, text="Repel: 14.0k", font=ctk.CTkFont(size=11), text_color=GRAPH_THEME["text_muted"])
        self.lbl_repel.pack(anchor="w")
        self.slider_repel = ctk.CTkSlider(box_rep, from_=4000, to=35000, number_of_steps=31, fg_color="#ECEEF4", progress_color="#8E7CC3", button_color="#8E7CC3", button_hover_color="#7B68B3", height=14, command=self._on_repel_slider)
        self.slider_repel.set(self.setting_repel)
        self.slider_repel.pack(fill="x", pady=(2, 0))

        # Slider 4: Center Force
        box_grav = ctk.CTkFrame(self.settings_card, fg_color="transparent")
        box_grav.grid(row=0, column=3, padx=6, pady=4, sticky="ew")
        self.lbl_grav = ctk.CTkLabel(box_grav, text="Center: 0.0008", font=ctk.CTkFont(size=11), text_color=GRAPH_THEME["text_muted"])
        self.lbl_grav.pack(anchor="w")
        self.slider_grav = ctk.CTkSlider(box_grav, from_=0.0001, to=0.0050, number_of_steps=25, fg_color="#ECEEF4", progress_color="#8E7CC3", button_color="#8E7CC3", button_hover_color="#7B68B3", height=14, command=self._on_grav_slider)
        self.slider_grav.set(self.setting_gravity)
        self.slider_grav.pack(fill="x", pady=(2, 0))

        # Row 1: Interactive Spectrum Color Palette Bar
        palette_frame = ctk.CTkFrame(self.settings_card, fg_color="transparent")
        palette_frame.grid(row=1, column=0, columnspan=4, padx=6, pady=(3, 6), sticky="ew")

        lbl_target = ctk.CTkLabel(
            palette_frame,
            text="Palette:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=GRAPH_THEME["text_muted"]
        )
        lbl_target.pack(side="left", padx=(2, 6))

        self.btn_color_node = ctk.CTkButton(
            palette_frame,
            text="Node",
            width=54,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color="#8E7CC3",
            text_color="#FFFFFF",
            hover_color="#7D6BB4",
            command=lambda: self._set_target_color_mode("node")
        )
        self.btn_color_node.pack(side="left", padx=2)

        self.btn_color_hub = ctk.CTkButton(
            palette_frame,
            text="Hub",
            width=50,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color="#ECEEF4",
            text_color=GRAPH_THEME["text_primary"],
            hover_color="#DFE2EC",
            command=lambda: self._set_target_color_mode("hub")
        )
        self.btn_color_hub.pack(side="left", padx=2)

        self.btn_color_link = ctk.CTkButton(
            palette_frame,
            text="Link",
            width=50,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color="#ECEEF4",
            text_color=GRAPH_THEME["text_primary"],
            hover_color="#DFE2EC",
            command=lambda: self._set_target_color_mode("link")
        )
        self.btn_color_link.pack(side="left", padx=2)

        # Interactive Spectrum Canvas
        self.canvas_spectrum = tk.Canvas(
            palette_frame,
            width=self.spec_w,
            height=self.spec_h,
            highlightthickness=1,
            highlightbackground="#D5D8E4",
            cursor="crosshair"
        )
        self.canvas_spectrum.create_image(0, 0, image=self.spec_photo, anchor="nw")
        self.canvas_spectrum.pack(side="left", padx=(10, 6))
        self.canvas_spectrum.bind("<Button-1>", self._on_spectrum_click)
        self.canvas_spectrum.bind("<B1-Motion>", self._on_spectrum_click)

        # Preview Swatch & Hex Label
        self.swatch_preview = ctk.CTkLabel(
            palette_frame,
            text="",
            width=22,
            height=22,
            fg_color=GRAPH_THEME["node_regular"],
            corner_radius=4
        )
        self.swatch_preview.pack(side="left", padx=4)

        self.lbl_color_hex = ctk.CTkLabel(
            palette_frame,
            text=GRAPH_THEME["node_regular"],
            font=ctk.CTkFont(size=11, family="Consolas"),
            text_color=GRAPH_THEME["text_primary"]
        )
        self.lbl_color_hex.pack(side="left", padx=4)

        # Reset Palette Button
        self.btn_reset_palette = ctk.CTkButton(
            palette_frame,
            text="↺ Reset",
            width=56,
            height=24,
            font=ctk.CTkFont(size=10),
            fg_color="#ECEEF4",
            text_color=GRAPH_THEME["text_muted"],
            hover_color="#DFE2EC",
            command=self._reset_palette_colors
        )
        self.btn_reset_palette.pack(side="left", padx=(8, 2))

        # 3. Main Interactive Canvas
        self.canvas = tk.Canvas(
            self,
            bg=GRAPH_THEME["canvas_bg"],
            highlightthickness=0,
            bd=0
        )
        self.canvas.grid(row=2, column=0, sticky="nsew", padx=6, pady=2)

        # Mouse event bindings
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<ButtonPress-3>", self._on_right_mouse_down)
        self.canvas.bind("<B3-Motion>", self._on_right_mouse_drag)
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-4>", lambda e: self._zoom_step(1.2, e.x, e.y))
        self.canvas.bind("<Button-5>", lambda e: self._zoom_step(0.8, e.x, e.y))

        # 4. Bottom Filter Bar
        bottom_bar = ctk.CTkFrame(self, fg_color="#FFFFFF", height=32, corner_radius=6, border_width=1, border_color="#E2E4EC")
        bottom_bar.grid(row=3, column=0, sticky="ew", padx=6, pady=(2, 6))
        bottom_bar.grid_columnconfigure(0, weight=1)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self._on_search_changed())

        self.entry_search = ctk.CTkEntry(
            bottom_bar,
            textvariable=self.search_var,
            placeholder_text="Filter nodes by citekey, title, author...",
            font=ctk.CTkFont(size=11),
            fg_color="#F7F7FA",
            border_color="#D5D8E4",
            text_color=GRAPH_THEME["text_primary"],
            height=26
        )
        self.entry_search.grid(row=0, column=0, sticky="ew", padx=6, pady=3)

    def toggle_settings_panel(self):
        self.show_settings = not self.show_settings
        if self.show_settings:
            self.settings_card.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 4))
            self.btn_settings.configure(fg_color="#8E7CC3", hover_color="#7B68B3", text_color="#FFFFFF")
        else:
            self.settings_card.grid_remove()
            self.btn_settings.configure(fg_color="#ECEEF4", hover_color="#DFE2EC", text_color=GRAPH_THEME["text_primary"])

    def _on_size_slider(self, val):
        self.setting_node_size = float(val)
        self.lbl_size.configure(text=f"Node Size: {int(val)}px")
        for i, doi in enumerate(self.doi_list):
            n = self.nodes[doi]
            local_degree = n["in_deg"] * 2.5 + n["out_deg"] * 1.0
            r = self.setting_node_size + min(local_degree * 1.8, 22.0)
            n["radius"] = r
            if self.radii is not None and i < len(self.radii):
                self.radii[i] = r
        self.redraw()

    def _on_dist_slider(self, val):
        self.setting_distance = float(val)
        self.spring_len = self.setting_distance
        self.lbl_dist.configure(text=f"Distance: {int(val)}")
        self.wake_simulation(energy=0.45)

    def _on_repel_slider(self, val):
        self.setting_repel = float(val)
        self.k_repulse = self.setting_repel
        self.lbl_repel.configure(text=f"Repel: {val/1000:.1f}k")
        self.wake_simulation(energy=0.45)

    def _on_grav_slider(self, val):
        self.setting_gravity = float(val)
        self.k_gravity = self.setting_gravity
        self.lbl_grav.configure(text=f"Center: {val:.4f}")
        self.wake_simulation(energy=0.45)

    # ------------------------------------------------------------------
    # Spectrum Color Palette Helpers
    # ------------------------------------------------------------------
    def _generate_spectrum_image(self, width: int, height: int):
        img = Image.new("RGB", (width, height))
        pixels = []
        gray_w = 36
        rainbow_w = max(width - gray_w, 1)

        for y in range(height):
            # Top row is lighter/vivid, bottom row is deeper/darker
            val = 1.0 - (y / max(height - 1, 1)) * 0.70
            sat = 0.35 + (y / max(height - 1, 1)) * 0.55

            for x in range(width):
                if x < gray_w:
                    ratio = x / float(gray_w)
                    gray = int(255 * (1.0 - ratio * 0.85 * (1.0 - (y / height) * 0.4)))
                    pixels.append((gray, gray, gray))
                else:
                    hue = (x - gray_w) / float(rainbow_w)
                    r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
                    pixels.append((int(r * 255), int(g * 255), int(b * 255)))

        img.putdata(pixels)
        return img

    def _set_target_color_mode(self, mode: str):
        self.target_color_mode = mode
        self.btn_color_node.configure(
            fg_color="#8E7CC3" if mode == "node" else "#ECEEF4",
            text_color="#FFFFFF" if mode == "node" else GRAPH_THEME["text_primary"]
        )
        self.btn_color_hub.configure(
            fg_color="#8E7CC3" if mode == "hub" else "#ECEEF4",
            text_color="#FFFFFF" if mode == "hub" else GRAPH_THEME["text_primary"]
        )
        self.btn_color_link.configure(
            fg_color="#8E7CC3" if mode == "link" else "#ECEEF4",
            text_color="#FFFFFF" if mode == "link" else GRAPH_THEME["text_primary"]
        )

        curr_hex = GRAPH_THEME["node_regular"] if mode == "node" else (
            GRAPH_THEME["node_hub"] if mode == "hub" else GRAPH_THEME["edge_default"]
        )
        self.swatch_preview.configure(fg_color=curr_hex)
        self.lbl_color_hex.configure(text=curr_hex)

    def _on_spectrum_click(self, event):
        x = max(0, min(event.x, self.spec_w - 1))
        y = max(0, min(event.y, self.spec_h - 1))
        r, g, b = self.spec_img.getpixel((x, y))
        hex_code = f"#{r:02X}{g:02X}{b:02X}"

        # Draw reticle on spectrum canvas
        self.canvas_spectrum.delete("reticle")
        self.canvas_spectrum.create_oval(
            x - 3, y - 3, x + 3, y + 3,
            outline="#FFFFFF", width=1.5, tags="reticle"
        )
        self.canvas_spectrum.create_oval(
            x - 4, y - 4, x + 4, y + 4,
            outline="#000000", width=0.8, tags="reticle"
        )

        # Update swatch & label
        self.swatch_preview.configure(fg_color=hex_code)
        self.lbl_color_hex.configure(text=hex_code)

        # Apply to target and update nodes/links
        if self.target_color_mode == "node":
            GRAPH_THEME["node_regular"] = hex_code
            for n in self.nodes.values():
                if not n.get("is_hub", False):
                    n["base_color"] = hex_code
        elif self.target_color_mode == "hub":
            GRAPH_THEME["node_hub"] = hex_code
            for n in self.nodes.values():
                if n.get("is_hub", False):
                    n["base_color"] = hex_code
        elif self.target_color_mode == "link":
            GRAPH_THEME["edge_default"] = hex_code

        self.redraw()

    def _reset_palette_colors(self):
        GRAPH_THEME["node_regular"] = "#3A4052"
        GRAPH_THEME["node_hub"] = "#8E7CC3"
        GRAPH_THEME["edge_default"] = "#6B7285"
        for n in self.nodes.values():
            n["base_color"] = GRAPH_THEME["node_hub"] if n.get("is_hub", False) else GRAPH_THEME["node_regular"]
        self._set_target_color_mode(self.target_color_mode)
        self.canvas_spectrum.delete("reticle")
        self.redraw()

    # ------------------------------------------------------------------
    # Data Loading & Component Layout
    # ------------------------------------------------------------------
    def _apply_component_layout(self):
        """
        Discovers connected components (citation chunks) and positions them in distinct
        radial sectors so individual research clusters are visually separated rather
        than collapsing into an overcrowded center.
        """
        n = len(self.doi_list)
        if n == 0:
            return

        # Build adjacency graph (undirected components)
        adj = {i: [] for i in range(n)}
        if len(self.edge_indices) > 0:
            for u, v in self.edge_indices:
                adj[u].append(v)
                adj[v].append(u)

        visited = set()
        components = []
        for i in range(n):
            if i not in visited:
                comp = []
                queue = [i]
                visited.add(i)
                while queue:
                    curr = queue.pop(0)
                    comp.append(curr)
                    for neighbor in adj[curr]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
                components.append(comp)

        # Separate multi-node clusters from isolated singletons
        clusters = [c for c in components if len(c) > 1]
        singletons = [c[0] for c in components if len(c) == 1]

        # Sort clusters by size (descending)
        clusters.sort(key=len, reverse=True)

        new_pos = np.zeros((n, 2), dtype=np.float32)

        # 1. Position multi-node clusters in distinct radial sectors
        num_clusters = len(clusters)
        if num_clusters == 1:
            # Single main cluster: center around (0, 0) with gentle dispersion
            comp = clusters[0]
            m = len(comp)
            for idx_in_c, node_idx in enumerate(comp):
                theta = (2.0 * math.pi * idx_in_c) / max(m, 1)
                r = 60.0 + (idx_in_c * 8.0) if m > 10 else 50.0 + random.uniform(-15.0, 15.0)
                new_pos[node_idx] = [math.cos(theta) * r, math.sin(theta) * r]
        elif num_clusters > 1:
            # Spread cluster centers evenly across 360 degrees
            cluster_radius = max(280.0, 130.0 + num_clusters * 45.0)
            for c_idx, comp in enumerate(clusters):
                cluster_angle = (2.0 * math.pi * c_idx) / num_clusters
                cx = math.cos(cluster_angle) * cluster_radius
                cy = math.sin(cluster_angle) * cluster_radius
                m = len(comp)
                for idx_in_c, node_idx in enumerate(comp):
                    theta = (2.0 * math.pi * idx_in_c) / max(m, 1)
                    local_r = 40.0 + min(m * 6.0, 80.0) + random.uniform(-10.0, 10.0)
                    new_pos[node_idx] = [
                        cx + math.cos(theta) * local_r,
                        cy + math.sin(theta) * local_r
                    ]

        # 2. Position isolated singletons in an outer orbital ring
        num_singles = len(singletons)
        if num_singles > 0:
            orbit_radius = (max(280.0, 130.0 + num_clusters * 45.0) + 160.0) if num_clusters > 0 else 220.0
            for s_idx, node_idx in enumerate(singletons):
                angle = (2.0 * math.pi * s_idx) / max(num_singles, 1)
                r = orbit_radius + random.uniform(-25.0, 25.0)
                new_pos[node_idx] = [math.cos(angle) * r, math.sin(angle) * r]

        self.pos = new_pos
        self.vel = np.zeros((n, 2), dtype=np.float32)

        # Synchronize back to self.nodes dict
        for i, doi in enumerate(self.doi_list):
            self.nodes[doi]["x"] = float(self.pos[i, 0])
            self.nodes[doi]["y"] = float(self.pos[i, 1])
            self.nodes[doi]["vx"] = 0.0
            self.nodes[doi]["vy"] = 0.0

    def load_graph_data(
        self,
        cites: dict[str, list[str]],
        cited_by: dict[str, list[str]],
        all_papers: dict[str, dict]
    ):
        """
        Populates graph data on build completion and starts the live physics simulation.
        """
        self.cites = cites
        self.cited_by = cited_by
        self.all_papers = all_papers

        self.nodes = {}
        self.edges = []

        all_dois = list(all_papers.keys())
        if not all_dois:
            self.lbl_stats.configure(text="0 nodes")
            self.pos = None
            self.vel = None
            self.radii = None
            self.pinned = None
            self.edge_indices = None
            self.doi_list = []
            self.doi_to_idx = {}
            self.redraw()
            return

        # Prepare Nodes
        for i, doi in enumerate(all_dois):
            p = all_papers[doi]
            citekey = p.get('citekey', '') or doi[:10]
            title = p.get('title', 'Untitled')
            authors = p.get('authors', [])
            year = str(p.get('year', ''))
            citation_count = p.get('citation_count', 0)
            if not isinstance(citation_count, (int, float)):
                try:
                    citation_count = int(citation_count)
                except (ValueError, TypeError):
                    citation_count = 0

            in_deg = len(cited_by.get(doi, []))
            out_deg = len(cites.get(doi, []))

            # Dynamic node radius based strictly on local connectivity within this folder/collection
            local_degree = (in_deg * 2.5) + (out_deg * 1.0)
            radius = self.setting_node_size + min(local_degree * 1.8, 22.0)

            # Hub nodes: papers with high local connections in this folder
            is_hub = (in_deg >= 2) or (local_degree >= 5)
            base_color = GRAPH_THEME["node_hub"] if is_hub else GRAPH_THEME["node_regular"]

            self.nodes[doi] = {
                "doi": doi,
                "citekey": citekey,
                "title": title,
                "authors": authors,
                "year": year,
                "citation_count": citation_count,
                "in_deg": in_deg,
                "out_deg": out_deg,
                "radius": radius,
                "is_hub": is_hub,
                "base_color": base_color,
                "x": 0.0,
                "y": 0.0,
                "vx": 0.0,
                "vy": 0.0,
                "is_pinned": False,
            }

        # Prepare Edges: (source_doi, target_doi)
        for src_doi, targets in cites.items():
            if src_doi not in self.nodes:
                continue
            for tgt_doi in targets:
                if tgt_doi in self.nodes and tgt_doi != src_doi:
                    self.edges.append((src_doi, tgt_doi))

        self.lbl_stats.configure(text=f"{len(self.nodes)} nodes • {len(self.edges)} links")

        # Initialize NumPy Vectorized State
        self.doi_list = list(self.nodes.keys())
        self.doi_to_idx = {doi: i for i, doi in enumerate(self.doi_list)}
        n = len(self.doi_list)

        self.pos = np.zeros((n, 2), dtype=np.float32)
        self.vel = np.zeros((n, 2), dtype=np.float32)
        self.radii = np.array([self.nodes[d]["radius"] for d in self.doi_list], dtype=np.float32)
        self.pinned = np.zeros(n, dtype=bool)

        edge_list = []
        for s, t in self.edges:
            if s in self.doi_to_idx and t in self.doi_to_idx:
                edge_list.append((self.doi_to_idx[s], self.doi_to_idx[t]))
        self.edge_indices = np.array(edge_list, dtype=np.int32) if edge_list else np.empty((0, 2), dtype=np.int32)

        # Apply component-aware radial layout
        self._apply_component_layout()

        # Fast initial relaxation
        self._simulate_step(dt=0.35, steps=50)
        self.fit_view()

        # Wake up live simulation loop to breathe and settle
        self.wake_simulation(energy=0.8)

    # ------------------------------------------------------------------
    # Live Interactive Physics Loop (Elastic, Spring-like Motion)
    # ------------------------------------------------------------------
    def wake_simulation(self, energy: float = 0.5):
        """Wakes up the physics simulation loop with given energy level."""
        self.alpha = max(self.alpha, energy)
        if not self.is_animating:
            self.is_animating = True
            self._physics_loop_tick()

    def _physics_loop_tick(self):
        """Dynamic 60FPS/40FPS animation tick with quick stabilization to conserve CPU."""
        if not self.nodes or self.pos is None:
            self.is_animating = False
            return

        is_dragging = (self.dragged_doi is not None)

        if self.alpha > 0.015 or is_dragging:
            t_start = time.perf_counter()

            step_alpha = max(self.alpha, 0.35) if is_dragging else self.alpha
            self._simulate_step(dt=0.32, steps=1, alpha_scale=step_alpha)

            if not is_dragging:
                self.alpha *= 0.93

            self.redraw()

            # Dynamic frame interval: 16ms target, fallback to 25ms if render exceeds 16ms
            t_render = (time.perf_counter() - t_start) * 1000.0
            self._frame_times.append(t_render)
            if len(self._frame_times) > 10:
                self._frame_times.pop(0)
            avg_t = sum(self._frame_times) / len(self._frame_times)
            self.anim_tick_ms = 25 if avg_t > 16.0 else 16

            self._anim_timer_id = self.after(self.anim_tick_ms, self._physics_loop_tick)
        else:
            self.is_animating = False
            self.alpha = 0.0
            self.redraw()

    def _simulate_step(self, dt: float = 0.32, steps: int = 1, alpha_scale: float = 1.0):
        """
        Vectorized NumPy Physics Engine:
        Calculates Coulomb repulsion, edge spring tension, collision prevention,
        and center gravity in sub-millisecond C speeds.
        """
        n = len(self.doi_list)
        if n <= 1 or self.pos is None or len(self.pos) != n:
            return

        effective_rep = self.k_repulse * alpha_scale
        effective_spring = self.k_spring * alpha_scale

        for _ in range(steps):
            # Pairwise differences: diff[i, j] = pos[i] - pos[j]
            diff = self.pos[:, np.newaxis, :] - self.pos[np.newaxis, :, :]  # (n, n, 2)
            dist_sq = np.sum(diff ** 2, axis=-1) + 0.1  # (n, n)
            dist = np.sqrt(dist_sq)

            # Avoid division by zero on diagonal
            np.fill_diagonal(dist, 1.0)
            np.fill_diagonal(dist_sq, 1.0)

            dir_vec = diff / dist[:, :, np.newaxis]

            # 1. Coulomb Repulsion (expanded to 800px cutoff so distinct chunks continue repelling)
            rep_mask = (dist_sq < 640000.0)
            np.fill_diagonal(rep_mask, False)
            rep_mag = np.where(rep_mask, effective_rep / dist_sq, 0.0)

            # 2. Hard Collision Prevention (prevents node overlap with generous spacing)
            min_dist_matrix = self.radii[:, np.newaxis] + self.radii[np.newaxis, :] + 22.0
            col_mask = (dist < min_dist_matrix)
            np.fill_diagonal(col_mask, False)
            overlap_mag = np.where(col_mask, (min_dist_matrix - dist) * (12.0 * alpha_scale), 0.0)

            total_pairwise_mag = rep_mag + overlap_mag
            total_forces = np.sum(dir_vec * total_pairwise_mag[:, :, np.newaxis], axis=1)  # (n, 2)

            # 3. Center Gravity
            total_forces -= self.pos * (self.k_gravity * alpha_scale)

            # 4. Attraction along edges (Elastic Springs)
            if len(self.edge_indices) > 0:
                src_idx = self.edge_indices[:, 0]
                tgt_idx = self.edge_indices[:, 1]

                edge_diff = self.pos[tgt_idx] - self.pos[src_idx]  # (E, 2)
                edge_dist = np.linalg.norm(edge_diff, axis=1, keepdims=True) + 0.01  # (E, 1)
                edge_disp = edge_dist - self.spring_len
                edge_force_mag = edge_disp * effective_spring
                edge_forces = (edge_diff / edge_dist) * edge_force_mag  # (E, 2)

                np.add.at(total_forces, src_idx, edge_forces)
                np.add.at(total_forces, tgt_idx, -edge_forces)

            # 5. Integrate velocity and position
            unpinned = ~self.pinned
            self.vel[unpinned] = (self.vel[unpinned] + total_forces[unpinned] * dt) * self.damping
            self.pos[unpinned] += self.vel[unpinned] * dt

        # Synchronize positions to self.nodes dict for full compatibility
        for i, doi in enumerate(self.doi_list):
            self.nodes[doi]["x"] = float(self.pos[i, 0])
            self.nodes[doi]["y"] = float(self.pos[i, 1])
            self.nodes[doi]["vx"] = float(self.vel[i, 0])
            self.nodes[doi]["vy"] = float(self.vel[i, 1])
            self.nodes[doi]["is_pinned"] = bool(self.pinned[i])

    def recompute_layout(self):
        """Unpins nodes, reapplies component layout, and shakes layout to find optimal equilibrium."""
        if self.pinned is not None:
            self.pinned[:] = False
        for n in self.nodes.values():
            n["is_pinned"] = False
        self._apply_component_layout()
        self._simulate_step(dt=0.35, steps=50)
        self.fit_view()
        self.wake_simulation(energy=0.9)

    # ------------------------------------------------------------------
    # Viewport & Coordinate Utilities
    # ------------------------------------------------------------------
    def fit_view(self):
        """Centers and scales the graph to fit comfortably in view."""
        w = max(self.canvas.winfo_width(), 350)
        h = max(self.canvas.winfo_height(), 250)

        if not self.nodes:
            self.zoom = 1.0
            self.offset_x = 0.0
            self.offset_y = 0.0
            self.redraw()
            return

        xs = [n["x"] for n in self.nodes.values()]
        ys = [n["y"] for n in self.nodes.values()]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        span_x = max(max_x - min_x + 90.0, 100.0)
        span_y = max(max_y - min_y + 90.0, 100.0)

        zoom_x = (w * 0.82) / span_x
        zoom_y = (h * 0.82) / span_y
        self.zoom = min(max(min(zoom_x, zoom_y), 0.15), 2.0)

        mid_x = (min_x + max_x) / 2.0
        mid_y = (min_y + max_y) / 2.0

        self.offset_x = -mid_x * self.zoom
        self.offset_y = -mid_y * self.zoom

        self.redraw()

    def _world_to_screen(self, wx: float, wy: float) -> tuple[float, float]:
        cx = self.canvas.winfo_width() / 2.0
        cy = self.canvas.winfo_height() / 2.0
        return cx + self.offset_x + (wx * self.zoom), cy + self.offset_y + (wy * self.zoom)

    def _screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        cx = self.canvas.winfo_width() / 2.0
        cy = self.canvas.winfo_height() / 2.0
        return (sx - cx - self.offset_x) / self.zoom, (sy - cy - self.offset_y) / self.zoom

    def _zoom_step(self, factor: float, center_x=None, center_y=None):
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if center_x is None:
            center_x = cw / 2.0
        if center_y is None:
            center_y = ch / 2.0

        old_zoom = self.zoom
        new_zoom = min(max(old_zoom * factor, 0.15), 5.0)
        if new_zoom == old_zoom:
            return

        cx = cw / 2.0
        cy = ch / 2.0
        wx = (center_x - cx - self.offset_x) / old_zoom
        wy = (center_y - cy - self.offset_y) / old_zoom

        self.zoom = new_zoom
        self.offset_x = center_x - cx - (wx * self.zoom)
        self.offset_y = center_y - cy - (wy * self.zoom)

        self.redraw()

    # ------------------------------------------------------------------
    # Rendering (Offscreen Anti-Aliased Vector Rasterization + Canvas Overlays)
    # ------------------------------------------------------------------
    def redraw(self):
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw <= 10 or ch <= 10:
            return

        # Placeholder when no data loaded yet
        if not self.nodes:
            if self._bg_image_id:
                self.canvas.itemconfigure(self._bg_image_id, state="hidden")
            self.canvas.delete("overlay")
            self._draw_empty_placeholder(cw, ch)
            return

        # Active / highlighted set
        active_node = self.hovered_doi or self.selected_doi
        connected_dois = set()
        if active_node and active_node in self.nodes:
            connected_dois.add(active_node)
            connected_dois.update(self.cites.get(active_node, []))
            connected_dois.update(self.cited_by.get(active_node, []))

        scene = {
            "bg_color": GRAPH_THEME["canvas_bg"],
            "edges": [],
            "rings": [],
            "nodes": [],
        }

        # 1. Build Edges in Scene
        for src_doi, tgt_doi in self.edges:
            ns = self.nodes.get(src_doi)
            nt = self.nodes.get(tgt_doi)
            if not ns or not nt:
                continue

            sx, sy = self._world_to_screen(ns["x"], ns["y"])
            tx, ty = self._world_to_screen(nt["x"], nt["y"])

            # Cull offscreen edges
            if (sx < -80 and tx < -80) or (sx > cw + 80 and tx > cw + 80) or \
               (sy < -80 and ty < -80) or (sy > ch + 80 and ty > ch + 80):
                continue

            if active_node:
                if src_doi == active_node or tgt_doi == active_node:
                    edge_color = GRAPH_THEME["edge_highlight"]
                    edge_width = 2.0
                else:
                    edge_color = GRAPH_THEME["edge_dimmed"]
                    edge_width = 1.0
            else:
                edge_color = GRAPH_THEME["edge_default"]
                edge_width = 1.3

            # Trim edge to node border
            dx = tx - sx
            dy = ty - sy
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < 0.001:
                continue

            if dist > (ns["radius"] + nt["radius"]) * self.zoom:
                target_r = nt["radius"] * self.zoom + 1.0
                trimmed_tx = tx - (dx / dist) * target_r
                trimmed_ty = ty - (dy / dist) * target_r
                trimmed_sx = sx + (dx / dist) * (ns["radius"] * self.zoom)
                trimmed_sy = sy + (dy / dist) * (ns["radius"] * self.zoom)
            else:
                trimmed_sx, trimmed_sy = sx, sy
                trimmed_tx, trimmed_ty = tx, ty

            # Arrowhead vector triangle
            arrow_points = None
            line_ex, line_ey = trimmed_tx, trimmed_ty
            if dist > 32.0:
                arrow_len = min(8.0 * max(self.zoom, 0.7), 12.0)
                arrow_w = min(4.5 * max(self.zoom, 0.7), 7.0)
                ux = dx / dist
                uy = dy / dist
                px = -uy
                py = ux
                bx = trimmed_tx - ux * arrow_len
                by = trimmed_ty - uy * arrow_len
                w1 = (bx + px * arrow_w, by + py * arrow_w)
                w2 = (bx - px * arrow_w, by - py * arrow_w)
                arrow_points = [(trimmed_tx, trimmed_ty), w1, w2]
                line_ex, line_ey = bx, by

            scene["edges"].append({
                "sx": trimmed_sx,
                "sy": trimmed_sy,
                "ex": line_ex,
                "ey": line_ey,
                "color": edge_color,
                "width": edge_width,
                "arrow_points": arrow_points,
            })

        # 2. Build Focus Ring in Scene
        if active_node and active_node in self.nodes:
            an = self.nodes[active_node]
            asx, asy = self._world_to_screen(an["x"], an["y"])
            ar = max(an["radius"] * self.zoom, 4.0)
            scene["rings"].append({
                "x": asx,
                "y": asy,
                "radius": ar + 3.5,
                "color": "#E0A84F",
                "width": 2.0,
            })

        # 3. Build Nodes in Scene
        query = self.search_query.strip().lower()

        for doi, n in self.nodes.items():
            sx, sy = self._world_to_screen(n["x"], n["y"])
            r = max(n["radius"] * self.zoom, 4.0)

            if sx < -50 or sx > cw + 50 or sy < -50 or sy > ch + 50:
                continue

            matches_search = bool(query and (
                query in n["citekey"].lower() or
                query in n["title"].lower() or
                any(query in a.lower() for a in n["authors"])
            ))

            is_focus = (doi == active_node)
            is_connected = (doi in connected_dois)

            if matches_search:
                core_fill = GRAPH_THEME["node_search"]
                border_color = "#C7923E"
                border_w = 2.0
            elif active_node:
                if is_focus:
                    core_fill = GRAPH_THEME["node_highlight"]
                    border_color = GRAPH_THEME["text_primary"]
                    border_w = 2.0
                elif is_connected:
                    core_fill = n["base_color"]
                    border_color = core_fill
                    border_w = 1.4
                else:
                    core_fill = GRAPH_THEME["node_dimmed"]
                    border_color = core_fill
                    border_w = 1.0
            else:
                core_fill = n["base_color"]
                border_color = core_fill
                border_w = 1.2

            scene["nodes"].append({
                "x": sx,
                "y": sy,
                "radius": r,
                "fill": core_fill,
                "outline": border_color,
                "outline_width": border_w,
            })

        # 4. Offscreen Vector Rasterization (Skia / Pillow Fallback)
        photo = self.renderer.render(cw, ch, scene, is_animating=self.is_animating, existing_photo=self._current_photo)
        self._current_photo = photo

        # 5. Canvas Image Update (Single Image Item Reused via itemconfigure)
        if self._bg_image_id is None:
            self._bg_image_id = self.canvas.create_image(0, 0, anchor="nw", image=photo, tags="graph_bg")
            self.canvas.tag_lower(self._bg_image_id)
        else:
            self.canvas.itemconfigure(self._bg_image_id, image=photo, state="normal")
            self.canvas.tag_lower(self._bg_image_id)

        # 6. Clear Overlays (Labels & Tooltips Only)
        self.canvas.delete("overlay")

        # 7. Draw Citekey Text Labels (Native Subpixel Font Rendering)
        for doi, n in self.nodes.items():
            sx, sy = self._world_to_screen(n["x"], n["y"])
            r = max(n["radius"] * self.zoom, 4.0)

            if sx < -50 or sx > cw + 50 or sy < -50 or sy > ch + 50:
                continue

            matches_search = bool(query and (
                query in n["citekey"].lower() or
                query in n["title"].lower() or
                any(query in a.lower() for a in n["authors"])
            ))

            is_focus = (doi == active_node)
            is_connected = (doi in connected_dois)

            show_label = (self.zoom >= 0.70) or is_connected or matches_search or is_focus
            if show_label:
                text_col = GRAPH_THEME["text_primary"] if (is_connected or matches_search or not active_node or is_focus) else GRAPH_THEME["text_muted"]
                font_sz = max(int(9 * min(self.zoom, 1.2)), 8)
                self.canvas.create_text(
                    sx, sy + r + 6,
                    text=n["citekey"],
                    font=("Segoe UI", font_sz, "bold" if (is_focus or matches_search) else "normal"),
                    fill=text_col,
                    tags="overlay"
                )

        # 8. Draw Hover Tooltip on Top
        if self.hovered_doi and self.hovered_doi in self.nodes:
            self._draw_tooltip(self.hovered_doi, cw, ch)

    def _draw_empty_placeholder(self, cw: float, ch: float):
        self.canvas.create_text(
            cw / 2, ch / 2 - 8,
            text="No Graph Data",
            font=("Segoe UI", 13, "bold"),
            fill=GRAPH_THEME["text_muted"],
            justify="center",
            tags="overlay"
        )
        self.canvas.create_text(
            cw / 2, ch / 2 + 16,
            text="Select a collection and run 'Build Citation Network' to explore the graph.",
            font=("Segoe UI", 11),
            fill=GRAPH_THEME["text_muted"],
            justify="center",
            tags="overlay"
        )

    def _draw_tooltip(self, doi: str, cw: float, ch: float):
        n = self.nodes[doi]
        sx, sy = self._world_to_screen(n["x"], n["y"])

        # Dynamically wrap title to maximum 42 chars per line (up to 2 lines)
        raw_title = n["title"].strip() or "Untitled"
        title_lines = textwrap.wrap(raw_title, width=42)
        if len(title_lines) > 2:
            title_lines = title_lines[:2]
            if not title_lines[1].endswith("..."):
                title_lines[1] = title_lines[1][:38] + "..."
        if not title_lines:
            title_lines = ["Untitled"]

        author_str = n["authors"][0] if n["authors"] else "Unknown"
        if len(n["authors"]) > 1:
            author_str += " et al."
        year_str = f" ({n['year']})" if n['year'] else ""

        stats_str = f"In-Folder Cites: {n['out_deg']}  |  Cited By: {n['in_deg']}  |  Total Cites: {n['citation_count']}"

        card_w = 380
        title_h = len(title_lines) * 17
        card_h = 24 + title_h + 17 + 18
        tx = sx + 16
        ty = sy - 34

        if tx + card_w > cw - 10:
            tx = sx - card_w - 16
        if tx < 10:
            tx = 10
        if ty + card_h > ch - 10:
            ty = ch - card_h - 10
        if ty < 10:
            ty = 10

        self.canvas.create_rectangle(
            tx, ty, tx + card_w, ty + card_h,
            fill=GRAPH_THEME["tooltip_bg"],
            outline=GRAPH_THEME["tooltip_border"],
            width=1.0,
            tags="overlay"
        )

        offset_y = ty + 12
        for t_line in title_lines:
            self.canvas.create_text(
                tx + 12, offset_y,
                text=t_line,
                font=("Segoe UI", 10, "bold"),
                fill="#FFFFFF",
                anchor="w",
                width=356,
                tags="overlay"
            )
            offset_y += 17

        self.canvas.create_text(
            tx + 12, offset_y,
            text=f"{author_str}{year_str}  •  [{n['citekey']}]",
            font=("Segoe UI", 9),
            fill="#D1D5E2",
            anchor="w",
            width=356,
            tags="overlay"
        )
        offset_y += 17

        self.canvas.create_text(
            tx + 12, offset_y,
            text=stats_str,
            font=("Segoe UI", 9),
            fill=GRAPH_THEME["node_search"],
            anchor="w",
            width=356,
            tags="overlay"
        )

    # ------------------------------------------------------------------
    # Mouse & Event Handlers (Active Dragging with Spring Physics)
    # ------------------------------------------------------------------
    def _find_node_at(self, sx: float, sy: float) -> str | None:
        if not self.doi_list or self.pos is None:
            return None
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        cx = cw / 2.0
        cy = ch / 2.0
        screen_pos = np.array([cx + self.offset_x, cy + self.offset_y], dtype=np.float32) + (self.pos * self.zoom)
        diff = screen_pos - np.array([sx, sy], dtype=np.float32)
        dist_sq = np.sum(diff ** 2, axis=1)

        r = np.maximum(self.radii * self.zoom, 8.0)
        hits = np.where(dist_sq <= (r ** 2))[0]
        if len(hits) > 0:
            return self.doi_list[hits[-1]]
        return None

    def _on_mouse_down(self, event):
        hit_doi = self._find_node_at(event.x, event.y)
        if hit_doi:
            self.dragged_doi = hit_doi
            self.selected_doi = hit_doi
            idx = self.doi_to_idx.get(hit_doi)
            if idx is not None and self.pinned is not None:
                self.pinned[idx] = True
            self.nodes[hit_doi]["is_pinned"] = True
            # Wake up live simulation so neighbors actively respond
            self.wake_simulation(energy=0.7)
            if callable(self.on_node_selected):
                self.on_node_selected(hit_doi)
        else:
            self.is_panning = True
            self.selected_doi = None
            if callable(self.on_node_selected):
                self.on_node_selected(None)

        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.redraw()

    def select_and_focus_node(self, doi: str):
        """Focuses and highlights a specific node programmatically, centering viewport."""
        if doi not in self.nodes:
            return
        self.selected_doi = doi
        n = self.nodes[doi]
        self.offset_x = -n["x"] * self.zoom
        self.offset_y = -n["y"] * self.zoom
        self.wake_simulation(energy=0.35)
        if not self.is_animating:
            self.redraw()

    def _on_mouse_drag(self, event):
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y

        if self.dragged_doi and self.dragged_doi in self.nodes:
            # Set pinned position directly to mouse world coordinates
            wx, wy = self._screen_to_world(event.x, event.y)
            idx = self.doi_to_idx.get(self.dragged_doi)
            if idx is not None and self.pos is not None:
                self.pos[idx, 0] = wx
                self.pos[idx, 1] = wy
                self.vel[idx, 0] = 0.0
                self.vel[idx, 1] = 0.0
            n = self.nodes[self.dragged_doi]
            n["x"] = wx
            n["y"] = wy
            n["vx"] = 0.0
            n["vy"] = 0.0

            # Actively inject energy into physics so springs pull connected neighbors!
            self.wake_simulation(energy=0.55)
            self.drag_start_x = event.x
            self.drag_start_y = event.y
        elif self.is_panning:
            self.offset_x += dx
            self.offset_y += dy
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            self.redraw()

    def _on_mouse_up(self, event):
        if self.dragged_doi and self.dragged_doi in self.nodes:
            idx = self.doi_to_idx.get(self.dragged_doi)
            if idx is not None and self.pinned is not None:
                self.pinned[idx] = False
            self.nodes[self.dragged_doi]["is_pinned"] = False
            # Allow gentle spring wobble to settle naturally
            self.wake_simulation(energy=0.4)
        self.dragged_doi = None
        self.is_panning = False
        self.redraw()

    def _on_right_mouse_down(self, event):
        self.is_panning = True
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def _on_right_mouse_drag(self, event):
        if self.is_panning:
            self.offset_x += (event.x - self.drag_start_x)
            self.offset_y += (event.y - self.drag_start_y)
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            self.redraw()

    def _on_mouse_move(self, event):
        if self.is_panning or self.dragged_doi:
            return

        hit_doi = self._find_node_at(event.x, event.y)
        if hit_doi != self.hovered_doi:
            self.hovered_doi = hit_doi
            self.canvas.configure(cursor="hand2" if hit_doi else "")
            self.redraw()

    def _on_mouse_wheel(self, event):
        factor = 1.15 if event.delta > 0 else 0.87
        self._zoom_step(factor, event.x, event.y)

    def _on_search_changed(self):
        self.search_query = self.search_var.get()
        self.redraw()

    def _on_canvas_configure(self, event):
        w = event.width
        h = event.height
        if abs(w - self._last_canvas_w) < 2 and abs(h - self._last_canvas_h) < 2:
            return
        self._last_canvas_w = w
        self._last_canvas_h = h
        if self._resize_redraw_id is not None:
            self.after_cancel(self._resize_redraw_id)
        # Throttled at 16ms for buttery 60fps divider resizing
        self._resize_redraw_id = self.after(16, self._do_resize_redraw)

    def _do_resize_redraw(self):
        self._resize_redraw_id = None
        self.redraw()
