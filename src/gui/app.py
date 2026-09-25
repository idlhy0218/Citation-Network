"""
Citation Network Builder - Modern Desktop GUI
==============================================
A clean, matte, dry-styled GUI for Citation Network Builder using CustomTkinter.
"""
import os
import sys
import json
import threading
import subprocess
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Windows High-DPI Canvas Scaling Fix (Razor Sharp Resolution)
if sys.platform == "win32":
    import ctypes
    try:
        # 2 = PROCESS_PER_MONITOR_DPI_AWARE
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

from PIL import Image
import customtkinter as ctk
from dotenv import load_dotenv, set_key

# Import core clients and GUI components
from src.core.zotero_client import ZoteroClient
from src.core.openalex_client import OpenAlexClient
from src.core.obsidian_writer import ObsidianWriter
from src.gui.graph_view import GraphView


# ----------------------------------------------------------------------
# Theme & Color Palette (User Specified Matte / Dry Palette)
# ----------------------------------------------------------------------
THEME = {
    "bg_dark": "#F7F7FA",          # Main window background
    "card_bg": "#FFFFFF",          # Cards and section containers
    "card_border": "#E2E4EC",      # Subtle borders
    "input_bg": "#FFFFFF",         # Input fields and dropdowns
    "input_border": "#D5D8E4",     # Input border
    "text_primary": "#2D3140",     # Primary clean text (Dark slate)
    "text_muted": "#5C6378",       # Muted / secondary labels (Muted slate)
    "accent": "#8E7CC3",           # Accent lavender/purple primary button
    "accent_hover": "#7D6BB4",     # Hover state
    "secondary_btn": "#ECEEF4",    # Subdued utility buttons
    "secondary_hover": "#DFE2EC",  # Subdued utility button hover
    "success": "#3B8A68",          # Matte sage green for success/connected
    "error": "#B34B4B",            # Matte rust red for error/disconnected
    "warning": "#E0A84F",          # Warm amber
    "log_bg": "#F0F1F6",           # Terminal log background
    "log_text": "#2D3140",         # Terminal log text
}


class CitationNetworkGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Configuration (4-Column Capable Wide Layout)
        self.title("Citation Network Builder v1.2.0")
        self.geometry("1560x860")
        self.minsize(1100, 680)

        # Set default appearance to light matte
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        # Runtime State & Paths
        workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.assets_dir = os.path.join(workspace_root, 'assets')
        self.env_path = os.path.join(workspace_root, '.env')
        self.cache_file = os.path.join(workspace_root, 'cache', 'openalex_cache.json')
        load_dotenv(self.env_path)

        # Cross-platform window and taskbar icon
        self._setup_window_icon()

        self.generate_obsidian_notes = tk.BooleanVar(value=os.getenv("GENERATE_OBSIDIAN_NOTES", "true").lower() in ("true", "1", "yes"))
        self.tree_data = {}
        self.roots_data = []
        self.expanded_keys = {"__root__"}
        self.selected_collection_key = tk.StringVar(value="__root__")
        self.is_running = False
        self.stop_requested = False

        # Collapsible Panel Visibility States
        self.show_left_panel = True
        self.show_mid_panel = True
        self.show_right_panel = True
        self.show_detail_panel = False
        self.selected_doi_in_detail = None
        self.current_all_papers = {}
        self.current_cites = {}
        self.current_cited_by = {}
        self._meta_box_visible = False

        self._init_ui()
        self._load_config_to_inputs()
        
        # Initial check in background
        self.after(300, self._auto_load_tree)

    # ------------------------------------------------------------------
    # Cross-Platform Icon & Branding Setup
    # ------------------------------------------------------------------
    def _windows_set_titlebar_icon(self):
        """Override CustomTkinter's default 200ms timer callback so it NEVER overwrites
        our custom high-DPI logo with CustomTkinter's default blue circle icon."""
        pass

    def _setup_window_icon(self):
        """Cross-platform high-DPI window, taskbar, and dock icon setup (Windows, macOS, Linux)."""
        ico_path = os.path.join(self.assets_dir, "icon.ico")
        
        # 1. Prevent CustomTkinter from falling back to its blue circle icon
        self._iconbitmap_method_called = True

        # 2. Windows-specific: Explicit AppUserModelID for taskbar separation & iconbitmap
        if sys.platform.startswith("win"):
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "citationnetwork.desktop.builder.1.2"
                )
            except Exception:
                pass

            if os.path.exists(ico_path):
                try:
                    self.iconbitmap(ico_path)
                except Exception:
                    pass

        # 3. Multi-resolution sharp PhotoImages for wm_iconphoto
        # Providing multiple resolutions (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)
        # allows Windows/macOS/Linux window managers and high-DPI taskbars to pick
        # the crystal-clear native raster matching the exact monitor scaling without blur.
        self._app_icons = []
        icons_dir = os.path.join(self.assets_dir, "icons")
        sizes = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]

        if os.path.exists(icons_dir):
            for s in sizes:
                icon_file = os.path.join(icons_dir, f"icon_{s}.png")
                if os.path.exists(icon_file):
                    try:
                        self._app_icons.append(tk.PhotoImage(file=icon_file))
                    except Exception:
                        pass

        # Fallback to base logos if icons folder isn't populated
        if not self._app_icons:
            for fallback in ["logo_hi.png", "logo.png", "logo_icon.png"]:
                f_path = os.path.join(self.assets_dir, fallback)
                if os.path.exists(f_path):
                    try:
                        self._app_icons.append(tk.PhotoImage(file=f_path))
                    except Exception:
                        pass

        def _apply_iconphoto():
            if self._app_icons:
                try:
                    # wm_iconphoto accepts variable arguments of different sizes
                    self.wm_iconphoto(True, *self._app_icons)
                except Exception:
                    pass

        _apply_iconphoto()
        # Re-apply after 250ms to ensure window manager persists our razor-sharp icons
        self.after(250, _apply_iconphoto)

    # ------------------------------------------------------------------
    # UI Layout Initialization
    # ------------------------------------------------------------------
    def _init_ui(self):
        self.configure(fg_color=THEME["bg_dark"])

        # Main Grid Layout (Header / Content / Footer)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_body()
        self._build_footer()

    # 1. Minimal Header Area
    def _build_header(self):
        header_frame = ctk.CTkFrame(
            self,
            fg_color=THEME["card_bg"],
            corner_radius=0,
            height=46,
            border_width=1,
            border_color=THEME["card_border"]
        )
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 6))
        header_frame.grid_columnconfigure(1, weight=1)

        # Title & Subtitle (Left)
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.grid(row=0, column=0, padx=16, pady=6, sticky="w")

        # In-App Inline Logo Icon
        logo_icon_path = os.path.join(self.assets_dir, "logo_icon.png")
        if os.path.exists(logo_icon_path):
            try:
                pil_logo = Image.open(logo_icon_path)
                self._header_logo_img = ctk.CTkImage(
                    light_image=pil_logo,
                    dark_image=pil_logo,
                    size=(26, 26)
                )
                logo_label = ctk.CTkLabel(title_box, text="", image=self._header_logo_img)
                logo_label.pack(side="left", padx=(0, 8))
            except Exception:
                pass

        title_label = ctk.CTkLabel(
            title_box,
            text="Citation Network Builder",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=THEME["text_primary"]
        )
        title_label.pack(side="left", padx=(0, 8))

        ver_badge = ctk.CTkLabel(
            title_box,
            text="v1.2.0",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=THEME["input_bg"],
            text_color=THEME["text_muted"],
            corner_radius=4,
            padx=5,
            pady=1
        )
        ver_badge.pack(side="left")

        # Center: Panel View Toggles (Collapsible Panels - Calm, Clean, No Emojis)
        toggle_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        toggle_box.grid(row=0, column=1, padx=10, pady=6)

        self.btn_toggle_left = ctk.CTkButton(
            toggle_box,
            text="Collections",
            font=ctk.CTkFont(size=12),
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            text_color="#FFFFFF",
            width=100,
            height=28,
            corner_radius=6,
            command=self.toggle_left_panel
        )
        self.btn_toggle_left.pack(side="left", padx=4)

        self.btn_toggle_mid = ctk.CTkButton(
            toggle_box,
            text="Console & Run",
            font=ctk.CTkFont(size=12),
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            text_color="#FFFFFF",
            width=110,
            height=28,
            corner_radius=6,
            command=self.toggle_mid_panel
        )
        self.btn_toggle_mid.pack(side="left", padx=4)

        self.btn_toggle_right = ctk.CTkButton(
            toggle_box,
            text="Graph View",
            font=ctk.CTkFont(size=12),
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            text_color="#FFFFFF",
            width=100,
            height=28,
            corner_radius=6,
            command=self.toggle_right_panel
        )
        self.btn_toggle_right.pack(side="left", padx=4)

        self.btn_toggle_detail = ctk.CTkButton(
            toggle_box,
            text="Citation Index",
            font=ctk.CTkFont(size=12),
            fg_color=THEME["secondary_btn"],
            hover_color=THEME["secondary_hover"],
            text_color=THEME["text_primary"],
            width=110,
            height=28,
            corner_radius=6,
            command=self.toggle_detail_panel
        )
        self.btn_toggle_detail.pack(side="left", padx=4)

    # 2. Main Content Resizable Split View (macOS Finder / OneCommander Style)
    def _build_body(self):
        self.body_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.body_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 4))
        self.body_frame.grid_rowconfigure(0, weight=1)
        self.body_frame.grid_columnconfigure(0, weight=1)

        # PanedWindow for draggable dividers between panels
        self.paned = tk.PanedWindow(
            self.body_frame,
            orient=tk.HORIZONTAL,
            bd=0,
            sashwidth=6,
            sashpad=1,
            sashrelief=tk.FLAT,
            bg=THEME["bg_dark"],
            opaqueresize=True
        )
        self.paned.grid(row=0, column=0, sticky="nsew")

        self._build_left_panel(self.paned)
        self._build_mid_panel(self.paned)
        self._build_right_panel(self.paned)
        self._build_detail_panel(self.paned)

        self._update_panel_grid()

    def _update_panel_grid(self):
        current_panes = [str(p) for p in self.paned.panes()]

        # Remove all panes to maintain exact left-to-right order
        for card in [self.left_card, self.mid_card, self.right_card, self.detail_card]:
            if str(card) in current_panes:
                self.paned.forget(card)

        # Re-add in exact order with natural proportions
        if self.show_left_panel:
            self.paned.add(self.left_card, minsize=240, width=320)
            self.btn_toggle_left.configure(fg_color=THEME["accent"], hover_color=THEME["accent_hover"], text_color="#FFFFFF")
        else:
            self.btn_toggle_left.configure(fg_color=THEME["secondary_btn"], hover_color=THEME["secondary_hover"], text_color=THEME["text_primary"])

        if self.show_mid_panel:
            self.paned.add(self.mid_card, minsize=260, width=380)
            self.btn_toggle_mid.configure(fg_color=THEME["accent"], hover_color=THEME["accent_hover"], text_color="#FFFFFF")
        else:
            self.btn_toggle_mid.configure(fg_color=THEME["secondary_btn"], hover_color=THEME["secondary_hover"], text_color=THEME["text_primary"])

        if self.show_right_panel:
            self.paned.add(self.right_card, minsize=320, width=540)
            self.btn_toggle_right.configure(fg_color=THEME["accent"], hover_color=THEME["accent_hover"], text_color="#FFFFFF")
        else:
            self.btn_toggle_right.configure(fg_color=THEME["secondary_btn"], hover_color=THEME["secondary_hover"], text_color=THEME["text_primary"])

        if self.show_detail_panel:
            self.paned.add(self.detail_card, minsize=280, width=380)
            self.btn_toggle_detail.configure(fg_color=THEME["accent"], hover_color=THEME["accent_hover"], text_color="#FFFFFF")
        else:
            self.btn_toggle_detail.configure(fg_color=THEME["secondary_btn"], hover_color=THEME["secondary_hover"], text_color=THEME["text_primary"])

        if self.show_right_panel and hasattr(self, 'graph_view'):
            self.after(60, self.graph_view.redraw)

    def toggle_left_panel(self):
        active_count = sum([self.show_left_panel, self.show_mid_panel, self.show_right_panel, self.show_detail_panel])
        if self.show_left_panel and active_count <= 1:
            return
        self.show_left_panel = not self.show_left_panel
        self._update_panel_grid()

    def toggle_mid_panel(self):
        active_count = sum([self.show_left_panel, self.show_mid_panel, self.show_right_panel, self.show_detail_panel])
        if self.show_mid_panel and active_count <= 1:
            return
        self.show_mid_panel = not self.show_mid_panel
        self._update_panel_grid()

    def toggle_right_panel(self):
        active_count = sum([self.show_left_panel, self.show_mid_panel, self.show_right_panel, self.show_detail_panel])
        if self.show_right_panel and active_count <= 1:
            return
        self.show_right_panel = not self.show_right_panel
        self._update_panel_grid()

    def toggle_detail_panel(self):
        active_count = sum([self.show_left_panel, self.show_mid_panel, self.show_right_panel, self.show_detail_panel])
        if self.show_detail_panel and active_count <= 1:
            return
        self.show_detail_panel = not self.show_detail_panel
        self._update_panel_grid()
        if self.show_detail_panel:
            target_doi = self.selected_doi_in_detail
            if not target_doi and hasattr(self, 'graph_view'):
                target_doi = self.graph_view.selected_doi
            self.display_paper_detail(target_doi)

    def _build_left_panel(self, parent):
        self.left_card = ctk.CTkFrame(
            parent,
            fg_color=THEME["card_bg"],
            corner_radius=8,
            border_width=1,
            border_color=THEME["card_border"]
        )
        # Expand row 0 so tabview takes 100% vertical space!
        self.left_card.grid_rowconfigure(0, weight=1)
        self.left_card.grid_columnconfigure(0, weight=1)

        # Tabview for Collections vs Settings
        self.tabview = ctk.CTkTabview(
            self.left_card,
            fg_color=THEME["card_bg"],
            segmented_button_fg_color=THEME["input_bg"],
            segmented_button_selected_color=THEME["accent"],
            segmented_button_selected_hover_color=THEME["accent_hover"],
            segmented_button_unselected_color=THEME["input_bg"],
            segmented_button_unselected_hover_color=THEME["secondary_hover"],
            text_color=THEME["text_primary"]
        )
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=6, pady=4)
        
        tab_collections = self.tabview.add("  Collections  ")
        tab_settings = self.tabview.add("  Settings (.env)  ")

        self._build_collections_tab(tab_collections)
        self._build_settings_tab(tab_settings)

    def _build_collections_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        # Top Control Bar (Search, Expand, Collapse, Refresh)
        top_bar = ctk.CTkFrame(tab, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 6))
        top_bar.grid_columnconfigure(0, weight=1)

        self.collection_search_var = tk.StringVar()
        self.collection_search_var.trace_add("write", lambda *args: self._filter_collection_list())

        self.entry_search = ctk.CTkEntry(
            top_bar,
            textvariable=self.collection_search_var,
            placeholder_text="Search collection...",
            font=ctk.CTkFont(size=12),
            fg_color=THEME["input_bg"],
            border_color=THEME["input_border"],
            text_color=THEME["text_primary"],
            height=30
        )
        self.entry_search.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.btn_expand_all = ctk.CTkButton(
            top_bar,
            text="+",
            width=28,
            height=30,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=THEME["secondary_btn"],
            hover_color=THEME["secondary_hover"],
            text_color=THEME["text_primary"],
            command=self.expand_all_collections
        )
        self.btn_expand_all.grid(row=0, column=1, padx=(0, 4))

        self.btn_collapse_all = ctk.CTkButton(
            top_bar,
            text="-",
            width=28,
            height=30,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=THEME["secondary_btn"],
            hover_color=THEME["secondary_hover"],
            text_color=THEME["text_primary"],
            command=self.collapse_all_collections
        )
        self.btn_collapse_all.grid(row=0, column=2, padx=(0, 4))

        self.btn_refresh_tree = ctk.CTkButton(
            top_bar,
            text="Refresh",
            width=60,
            height=30,
            font=ctk.CTkFont(size=11),
            fg_color=THEME["secondary_btn"],
            hover_color=THEME["secondary_hover"],
            text_color=THEME["text_primary"],
            command=self.fetch_zotero_tree
        )
        self.btn_refresh_tree.grid(row=0, column=3)

        # Options Row
        opt_bar = ctk.CTkFrame(tab, fg_color="transparent")
        opt_bar.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 6))

        self.process_all_var = ctk.BooleanVar(value=False)
        self.chk_all = ctk.CTkCheckBox(
            opt_bar,
            text="Process All Collections",
            variable=self.process_all_var,
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_primary"],
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            command=self._on_process_all_toggled
        )
        self.chk_all.pack(side="left")

        # High-Performance Treeview Container (Zero Lag, Native C Rendering)
        tree_container = ctk.CTkFrame(
            tab,
            fg_color=THEME["input_bg"],
            corner_radius=6,
            border_width=1,
            border_color=THEME["input_border"]
        )
        tree_container.grid(row=2, column=0, sticky="nsew", padx=5, pady=(0, 5))
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        self.tree_scrollbar = ctk.CTkScrollbar(tree_container, orientation="vertical")
        self.tree_scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 3), pady=3)

        self.collection_tree = ttk.Treeview(
            tree_container,
            selectmode="browse",
            show="tree",
            yscrollcommand=self.tree_scrollbar.set
        )
        self.collection_tree.grid(row=0, column=0, sticky="nsew", padx=(4, 0), pady=4)
        self.tree_scrollbar.configure(command=self.collection_tree.yview)

        self._configure_treeview_style()
        self.collection_tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.collection_tree.bind("<<TreeviewOpen>>", self._on_tree_open)
        self.collection_tree.bind("<<TreeviewClose>>", self._on_tree_close)

    def _build_settings_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)

        # Form Scrollable
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=4, pady=4)
        scroll.grid_columnconfigure(1, weight=1)

        row = 0
        # Zotero User ID
        ctk.CTkLabel(scroll, text="Zotero User ID *", font=ctk.CTkFont(size=12), text_color=THEME["text_muted"]).grid(row=row, column=0, sticky="w", pady=(6, 2))
        row += 1
        self.entry_user_id = ctk.CTkEntry(scroll, fg_color=THEME["input_bg"], border_color=THEME["input_border"], height=30)
        self.entry_user_id.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        row += 1

        # Zotero API Key
        ctk.CTkLabel(scroll, text="Zotero API Key *", font=ctk.CTkFont(size=12), text_color=THEME["text_muted"]).grid(row=row, column=0, sticky="w", pady=(6, 2))
        row += 1
        self.entry_api_key = ctk.CTkEntry(scroll, fg_color=THEME["input_bg"], border_color=THEME["input_border"], height=30, show="•")
        self.entry_api_key.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        row += 1

        # Zotero Library Type
        ctk.CTkLabel(scroll, text="Library Type", font=ctk.CTkFont(size=12), text_color=THEME["text_muted"]).grid(row=row, column=0, sticky="w", pady=(6, 2))
        row += 1
        self.combo_lib_type = ctk.CTkComboBox(
            scroll,
            values=["user", "group"],
            fg_color=THEME["input_bg"],
            border_color=THEME["input_border"],
            button_color=THEME["secondary_btn"],
            height=30
        )
        self.combo_lib_type.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        row += 1

        # Generate Obsidian Notes Option
        self.chk_gen_notes_settings = ctk.CTkCheckBox(
            scroll,
            text="Generate Obsidian Notes (.md)",
            variable=self.generate_obsidian_notes,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME["text_primary"],
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            command=self._on_gen_notes_toggled
        )
        self.chk_gen_notes_settings.grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 4))
        row += 1

        # Obsidian Vault Path
        self.lbl_vault_path = ctk.CTkLabel(
            scroll,
            text="Obsidian Vault Path (Optional if notes disabled)",
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_muted"]
        )
        self.lbl_vault_path.grid(row=row, column=0, sticky="w", pady=(6, 2))
        row += 1
        vault_box = ctk.CTkFrame(scroll, fg_color="transparent")
        vault_box.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        vault_box.grid_columnconfigure(0, weight=1)

        self.entry_vault_path = ctk.CTkEntry(vault_box, fg_color=THEME["input_bg"], border_color=THEME["input_border"], text_color=THEME["text_primary"], height=30)
        self.entry_vault_path.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        btn_browse = ctk.CTkButton(
            vault_box,
            text="Browse...",
            width=70,
            height=30,
            fg_color=THEME["secondary_btn"],
            hover_color=THEME["secondary_hover"],
            text_color=THEME["text_primary"],
            command=self._browse_vault_path
        )
        btn_browse.grid(row=0, column=1)
        row += 1

        lbl_vault_note = ctk.CTkLabel(
            scroll,
            text="※ Notes are automatically saved inside a folder named after the selected Zotero collection.",
            font=ctk.CTkFont(size=11),
            text_color=THEME["text_muted"],
            wraplength=280,
            justify="left"
        )
        lbl_vault_note.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))
        row += 1

        # OpenAlex Email
        ctk.CTkLabel(scroll, text="OpenAlex Email (Optional for Faster Pool)", font=ctk.CTkFont(size=12), text_color=THEME["text_muted"]).grid(row=row, column=0, sticky="w", pady=(6, 2))
        row += 1
        self.entry_oa_email = ctk.CTkEntry(scroll, fg_color=THEME["input_bg"], border_color=THEME["input_border"], height=30)
        self.entry_oa_email.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        row += 1

        # Save Button
        self.btn_save_config = ctk.CTkButton(
            scroll,
            text="Save Configuration (.env)",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            text_color="#FFFFFF",
            height=34,
            command=self.save_config
        )
        self.btn_save_config.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        row += 1

        # Connection Testing Box in Settings
        test_box = ctk.CTkFrame(scroll, fg_color=THEME["input_bg"], corner_radius=6, border_width=1, border_color=THEME["input_border"])
        test_box.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(6, 10))
        test_box.grid_columnconfigure(0, weight=1)

        lbl_test_title = ctk.CTkLabel(test_box, text="API Connection Status", font=ctk.CTkFont(size=11, weight="bold"), text_color=THEME["text_primary"])
        lbl_test_title.pack(anchor="w", padx=10, pady=(8, 4))

        status_row = ctk.CTkFrame(test_box, fg_color="transparent")
        status_row.pack(fill="x", padx=10, pady=(0, 6))

        self.zotero_badge = ctk.CTkLabel(status_row, text="Zotero: Ready", font=ctk.CTkFont(size=11), text_color=THEME["text_muted"], fg_color=THEME["card_bg"], corner_radius=4, padx=8, pady=2)
        self.zotero_badge.pack(side="left", padx=(0, 6))

        self.openalex_badge = ctk.CTkLabel(status_row, text="OpenAlex: Ready", font=ctk.CTkFont(size=11), text_color=THEME["text_muted"], fg_color=THEME["card_bg"], corner_radius=4, padx=8, pady=2)
        self.openalex_badge.pack(side="left")

        self.btn_test_api = ctk.CTkButton(
            test_box,
            text="⚡ Test Connection",
            font=ctk.CTkFont(size=12),
            fg_color=THEME["secondary_btn"],
            hover_color=THEME["secondary_hover"],
            text_color=THEME["text_primary"],
            height=30,
            command=self.run_connection_test
        )
        self.btn_test_api.pack(fill="x", padx=10, pady=(0, 8))

    def _build_mid_panel(self, parent):
        self.mid_card = ctk.CTkFrame(
            parent,
            fg_color=THEME["card_bg"],
            corner_radius=8,
            border_width=1,
            border_color=THEME["card_border"]
        )
        self.mid_card.grid_rowconfigure(3, weight=1)
        self.mid_card.grid_columnconfigure(0, weight=1)

        # 1. Action Controls Header (Start / Cancel / Open Vault)
        ctrl_frame = ctk.CTkFrame(self.mid_card, fg_color="transparent")
        ctrl_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        ctrl_frame.grid_columnconfigure(0, weight=1)

        self.btn_start = ctk.CTkButton(
            ctrl_frame,
            text="Build Citation Network",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            text_color="#FFFFFF",
            height=38,
            corner_radius=6,
            command=self.start_build_process
        )
        self.btn_start.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.btn_stop = ctk.CTkButton(
            ctrl_frame,
            text="Stop",
            font=ctk.CTkFont(size=12),
            fg_color=THEME["secondary_btn"],
            hover_color=THEME["secondary_hover"],
            text_color=THEME["text_primary"],
            width=65,
            height=38,
            corner_radius=6,
            state="disabled",
            command=self.stop_build_process
        )
        self.btn_stop.grid(row=0, column=1, padx=(0, 6))

        self.btn_open_vault = ctk.CTkButton(
            ctrl_frame,
            text="Open Vault",
            font=ctk.CTkFont(size=12),
            fg_color=THEME["secondary_btn"],
            hover_color=THEME["secondary_hover"],
            text_color=THEME["text_primary"],
            width=90,
            height=38,
            corner_radius=6,
            command=self.open_obsidian_folder
        )
        self.btn_open_vault.grid(row=0, column=2)

        # 2. Option Checkbox (Generate Obsidian Notes)
        opt_box = ctk.CTkFrame(self.mid_card, fg_color="transparent")
        opt_box.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))

        self.chk_gen_notes_mid = ctk.CTkCheckBox(
            opt_box,
            text="Generate Obsidian Markdown Notes (.md)",
            variable=self.generate_obsidian_notes,
            font=ctk.CTkFont(size=11),
            text_color=THEME["text_muted"],
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            height=18,
            command=self._on_gen_notes_toggled
        )
        self.chk_gen_notes_mid.pack(side="left")

        # 3. Progress & Step Tracker
        prog_frame = ctk.CTkFrame(self.mid_card, fg_color="transparent")
        prog_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 6))
        prog_frame.grid_columnconfigure(0, weight=1)

        self.lbl_progress_step = ctk.CTkLabel(
            prog_frame,
            text="Ready to build citation network",
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_muted"]
        )
        self.lbl_progress_step.grid(row=0, column=0, sticky="w", pady=(0, 2))

        self.progress_bar = ctk.CTkProgressBar(
            prog_frame,
            height=6,
            corner_radius=3,
            fg_color=THEME["input_bg"],
            progress_color=THEME["accent"]
        )
        self.progress_bar.grid(row=1, column=0, sticky="ew")
        self.progress_bar.set(0.0)

        # 1-Line Inline Metrics Badge
        self._m_papers = "0"
        self._m_doi = "0"
        self._m_edges = "0"
        self._m_notes = "0"

        self.lbl_metrics = ctk.CTkLabel(
            prog_frame,
            text="Papers: 0  •  DOIs: 0  •  Links: 0  •  Notes: 0",
            font=ctk.CTkFont(size=11),
            text_color=THEME["text_muted"]
        )
        self.lbl_metrics.grid(row=2, column=0, sticky="w", pady=(4, 0))

        # 4. Live Log Console (Expands to fill all vertical space!)
        log_frame = ctk.CTkFrame(
            self.mid_card,
            fg_color=THEME["log_bg"],
            corner_radius=6,
            border_width=1,
            border_color=THEME["card_border"]
        )
        log_frame.grid(row=3, column=0, sticky="nsew", padx=12, pady=(2, 8))
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        # Log Top Bar
        log_bar = ctk.CTkFrame(log_frame, fg_color="transparent", height=22)
        log_bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 2))
        log_bar.grid_columnconfigure(0, weight=1)

        lbl_log_title = ctk.CTkLabel(
            log_bar,
            text="Execution Log",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=THEME["text_muted"]
        )
        lbl_log_title.grid(row=0, column=0, sticky="w")

        btn_clear_log = ctk.CTkButton(
            log_bar,
            text="Clear",
            font=ctk.CTkFont(size=10),
            fg_color="transparent",
            hover_color=THEME["secondary_hover"],
            text_color=THEME["text_muted"],
            width=40,
            height=18,
            command=self.clear_logs
        )
        btn_clear_log.grid(row=0, column=1, sticky="e")

        # Text View
        self.log_textbox = ctk.CTkTextbox(
            log_frame,
            fg_color="transparent",
            text_color=THEME["log_text"],
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word",
            activate_scrollbars=True
        )
        self.log_textbox.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))

    def _update_metrics(self, papers=None, doi=None, edges=None, notes=None):
        if papers is not None:
            self._m_papers = str(papers)
        if doi is not None:
            self._m_doi = str(doi)
        if edges is not None:
            self._m_edges = str(edges)
        if notes is not None:
            self._m_notes = str(notes)
        def _render():
            self.lbl_metrics.configure(
                text=f"Papers: {self._m_papers}  •  DOIs: {self._m_doi}  •  Links: {self._m_edges}  •  Notes: {self._m_notes}"
            )
        self.after(0, _render)

    def _build_right_panel(self, parent):
        self.right_card = ctk.CTkFrame(
            parent,
            fg_color=THEME["card_bg"],
            corner_radius=8,
            border_width=1,
            border_color=THEME["card_border"]
        )
        self.right_card.grid_rowconfigure(0, weight=1)
        self.right_card.grid_columnconfigure(0, weight=1)

        # Embed Obsidian-style Graph View
        self.graph_view = GraphView(self.right_card)
        self.graph_view.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self.graph_view.on_node_selected = self._on_graph_node_selected

    def _build_detail_panel(self, parent):
        self.detail_card = ctk.CTkFrame(
            parent,
            fg_color=THEME["card_bg"],
            corner_radius=8,
            border_width=1,
            border_color=THEME["card_border"]
        )
        self.detail_card.grid_rowconfigure(2, weight=1)
        self.detail_card.grid_columnconfigure(0, weight=1)

        # 1. Top Panel Title Bar
        header_bar = ctk.CTkFrame(self.detail_card, fg_color="transparent", height=36)
        header_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))
        header_bar.grid_columnconfigure(0, weight=1)

        self.lbl_detail_panel_title = ctk.CTkLabel(
            header_bar,
            text="Citation Index",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=THEME["text_primary"]
        )
        self.lbl_detail_panel_title.grid(row=0, column=0, sticky="w")

        btn_close_detail = ctk.CTkButton(
            header_bar,
            text="✕",
            width=26,
            height=26,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=THEME["secondary_hover"],
            text_color=THEME["text_muted"],
            command=self.toggle_detail_panel
        )
        btn_close_detail.grid(row=0, column=1, sticky="e")

        # 2. Selected Paper Header Card (Metadata & Actions) - Built Once for Zero Lag
        self.paper_meta_frame = ctk.CTkFrame(
            self.detail_card,
            fg_color=THEME["input_bg"],
            corner_radius=6,
            border_width=1,
            border_color=THEME["input_border"]
        )
        self.paper_meta_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))
        self.paper_meta_frame.grid_columnconfigure(0, weight=1)

        # 2A. Placeholder State (Shown when no paper is selected)
        self.meta_empty_box = ctk.CTkFrame(self.paper_meta_frame, fg_color="transparent")
        lbl_empty_title = ctk.CTkLabel(
            self.meta_empty_box,
            text="No Paper Selected",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=THEME["text_muted"]
        )
        lbl_empty_title.pack(anchor="w", padx=4, pady=(4, 2))

        lbl_empty_desc = ctk.CTkLabel(
            self.meta_empty_box,
            text="Click any node in the Graph View to inspect its outgoing references and incoming citations.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=THEME["text_muted"],
            wraplength=320,
            justify="left"
        )
        lbl_empty_desc.pack(anchor="w", padx=4, pady=(0, 4))

        # 2B. Metadata Content Box (Persistent Widgets Updated In-Place)
        self.meta_content_box = ctk.CTkFrame(self.paper_meta_frame, fg_color="transparent")

        top_tags = ctk.CTkFrame(self.meta_content_box, fg_color="transparent")
        top_tags.pack(fill="x", padx=4, pady=(4, 2))

        self.lbl_meta_citekey = ctk.CTkLabel(
            top_tags,
            text="[citekey]",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=THEME["accent"]
        )
        self.lbl_meta_citekey.pack(side="left")

        self.lbl_meta_year = ctk.CTkLabel(
            top_tags,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=THEME["text_muted"]
        )
        self.lbl_meta_year.pack(side="left")

        self.lbl_meta_title = ctk.CTkLabel(
            self.meta_content_box,
            text="Title",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=THEME["text_primary"],
            wraplength=330,
            justify="left"
        )
        self.lbl_meta_title.pack(anchor="w", padx=4, pady=(2, 4))

        self.lbl_meta_authors = ctk.CTkLabel(
            self.meta_content_box,
            text="Authors",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=THEME["text_muted"],
            wraplength=330,
            justify="left"
        )
        self.lbl_meta_authors.pack(anchor="w", padx=4, pady=(0, 4))

        self.lbl_meta_doi = ctk.CTkLabel(
            self.meta_content_box,
            text="DOI",
            font=ctk.CTkFont(family="Consolas", size=9),
            text_color=THEME["text_muted"],
            wraplength=330,
            justify="left"
        )
        self.lbl_meta_doi.pack(anchor="w", padx=4, pady=(0, 6))

        # Metrics Badges Row
        metrics_row = ctk.CTkFrame(self.meta_content_box, fg_color="transparent")
        metrics_row.pack(fill="x", padx=4, pady=(0, 8))

        def _make_meta_pill(parent, text):
            return ctk.CTkLabel(
                parent,
                text=text,
                font=ctk.CTkFont(family="Segoe UI", size=10),
                fg_color="#FFFFFF",
                text_color=THEME["text_primary"],
                corner_radius=4,
                padx=6,
                pady=1
            )

        self.lbl_pill_cites = _make_meta_pill(metrics_row, "Cites: 0")
        self.lbl_pill_cites.pack(side="left", padx=(0, 4))

        self.lbl_pill_cited_by = _make_meta_pill(metrics_row, "Cited By: 0")
        self.lbl_pill_cited_by.pack(side="left", padx=(0, 4))

        self.lbl_pill_global = _make_meta_pill(metrics_row, "Global: 0")
        self.lbl_pill_global.pack(side="left")

        # Action Buttons Row
        btn_row = ctk.CTkFrame(self.meta_content_box, fg_color="transparent")
        btn_row.pack(fill="x", padx=4, pady=(0, 6))

        self.btn_detail_zotero = ctk.CTkButton(
            btn_row,
            text="Open in Zotero",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            text_color="#FFFFFF",
            height=28,
            corner_radius=5
        )
        self.btn_detail_zotero.pack(side="left", padx=(0, 6))

        self.btn_detail_doi = ctk.CTkButton(
            btn_row,
            text="Open DOI",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=THEME["secondary_btn"],
            hover_color=THEME["secondary_hover"],
            text_color=THEME["text_primary"],
            height=28,
            corner_radius=5
        )
        self.btn_detail_doi.pack(side="left")

        # 3. High-Performance Native Scrollable Index Container (Zero Lag)
        self.index_scroll_frame = tk.Frame(self.detail_card, bg="#F7F7FA")
        self.index_scroll_frame.grid(row=2, column=0, sticky="nsew", padx=6, pady=(0, 6))
        self.index_scroll_frame.grid_rowconfigure(0, weight=1)
        self.index_scroll_frame.grid_columnconfigure(0, weight=1)

        self.index_canvas = tk.Canvas(self.index_scroll_frame, bg="#F7F7FA", highlightthickness=0, bd=0)
        self.index_scrollbar = ttk.Scrollbar(self.index_scroll_frame, orient="vertical", command=self.index_canvas.yview)
        self.index_canvas.configure(yscrollcommand=self.index_scrollbar.set)

        self.index_canvas.grid(row=0, column=0, sticky="nsew")
        self.index_scrollbar.grid(row=0, column=1, sticky="ns")

        self.index_container = tk.Frame(self.index_canvas, bg="#F7F7FA")
        self.index_canvas_win = self.index_canvas.create_window((0, 0), window=self.index_container, anchor="nw")

        self._last_index_canvas_w = 0
        self._scrollregion_timer_id = None
        self._card_wraplength = 270

        def _update_scrollregion():
            self._scrollregion_timer_id = None
            try:
                self.index_canvas.configure(scrollregion=self.index_canvas.bbox("all"))
            except Exception:
                pass

        def _on_index_container_configure(e):
            if self._scrollregion_timer_id is not None:
                self.after_cancel(self._scrollregion_timer_id)
            self._scrollregion_timer_id = self.after(25, _update_scrollregion)

        def _on_index_canvas_configure(e):
            if abs(e.width - self._last_index_canvas_w) >= 3:
                self._last_index_canvas_w = e.width
                self.index_canvas.itemconfig(self.index_canvas_win, width=e.width)
                new_wrap = max(180, e.width - 65)
                if abs(new_wrap - self._card_wraplength) >= 15:
                    self._card_wraplength = new_wrap
                    self._update_all_card_wraplengths(new_wrap)

        self.index_container.bind("<Configure>", _on_index_container_configure)
        self.index_canvas.bind("<Configure>", _on_index_canvas_configure)

        def _on_index_mousewheel(e):
            self.index_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            return "break"

        self.index_scroll_frame.bind("<Enter>", lambda e: self.index_canvas.bind_all("<MouseWheel>", _on_index_mousewheel))
        self.index_scroll_frame.bind("<Leave>", lambda e: self.index_canvas.unbind_all("<MouseWheel>"))

        # Persistent Section Layout inside index_container
        # 3A. Cites Section
        self.sec_cites_frame = tk.Frame(self.index_container, bg="#F7F7FA")
        self.sec_cites_hdr = tk.Frame(self.sec_cites_frame, bg="#F7F7FA")
        self.sec_cites_hdr.pack(fill="x", padx=4, pady=(4, 6))

        cites_title_box = tk.Frame(self.sec_cites_hdr, bg="#F7F7FA")
        cites_title_box.pack(side="left")
        tk.Label(cites_title_box, text="Cites", font=("Segoe UI", 11, "bold"), fg=THEME["text_primary"], bg="#F7F7FA").pack(side="left", padx=(0, 4))
        tk.Label(cites_title_box, text="(Outgoing References)", font=("Segoe UI", 9), fg=THEME["text_muted"], bg="#F7F7FA").pack(side="left")

        self.lbl_cites_cnt = tk.Label(self.sec_cites_hdr, text="0", font=("Segoe UI", 9, "bold"), fg=THEME["text_primary"], bg="#ECEEF4", padx=6, pady=1)
        self.lbl_cites_cnt.pack(side="right")

        self.lbl_cites_empty = tk.Label(self.sec_cites_frame, text="None found within this library.", font=("Segoe UI", 10), fg=THEME["text_muted"], bg="#F7F7FA")
        self.cites_cards_frame = tk.Frame(self.sec_cites_frame, bg="#F7F7FA")

        # Separator line
        self.sec_sep = tk.Frame(self.index_container, height=1, bg=THEME["card_border"])

        # 3B. Cited By Section
        self.sec_cited_by_frame = tk.Frame(self.index_container, bg="#F7F7FA")
        self.sec_cited_by_hdr = tk.Frame(self.sec_cited_by_frame, bg="#F7F7FA")
        self.sec_cited_by_hdr.pack(fill="x", padx=4, pady=(4, 6))

        cited_title_box = tk.Frame(self.sec_cited_by_hdr, bg="#F7F7FA")
        cited_title_box.pack(side="left")
        tk.Label(cited_title_box, text="Cited By", font=("Segoe UI", 11, "bold"), fg=THEME["text_primary"], bg="#F7F7FA").pack(side="left", padx=(0, 4))
        tk.Label(cited_title_box, text="(Incoming Citations)", font=("Segoe UI", 9), fg=THEME["text_muted"], bg="#F7F7FA").pack(side="left")

        self.lbl_cited_by_cnt = tk.Label(self.sec_cited_by_hdr, text="0", font=("Segoe UI", 9, "bold"), fg=THEME["text_primary"], bg="#ECEEF4", padx=6, pady=1)
        self.lbl_cited_by_cnt.pack(side="right")

        self.lbl_cited_by_empty = tk.Label(self.sec_cited_by_frame, text="None found within this library.", font=("Segoe UI", 10), fg=THEME["text_muted"], bg="#F7F7FA")
        self.cited_by_cards_frame = tk.Frame(self.sec_cited_by_frame, bg="#F7F7FA")

        # Card Pools for Reusable Memory
        self._cites_card_pool = []
        self._cited_by_card_pool = []

        self.display_paper_detail(None)

    def _on_graph_node_selected(self, doi: str | None):
        self.selected_doi_in_detail = doi
        # Only update if the panel is already open (do not auto-open)
        if self.show_detail_panel:
            self.display_paper_detail(doi)

    def display_paper_detail(self, doi: str | None):
        if not doi:
            self.selected_doi_in_detail = None
            if self._meta_box_visible:
                self.meta_content_box.pack_forget()
                self.meta_empty_box.pack(fill="x", padx=10, pady=8)
                self._meta_box_visible = False
            self.sec_cites_frame.pack_forget()
            self.sec_sep.pack_forget()
            self.sec_cited_by_frame.pack_forget()
            self.index_canvas.yview_moveto(0.0)
            return

        self.selected_doi_in_detail = doi

        # Fetch paper data
        paper = {}
        if hasattr(self, 'graph_view') and doi in self.graph_view.all_papers:
            paper = self.graph_view.all_papers[doi]
        elif hasattr(self, 'current_all_papers') and doi in self.current_all_papers:
            paper = self.current_all_papers[doi]

        title = paper.get('title', 'Untitled Paper')
        citekey = paper.get('citekey', '') or doi[:12]
        authors = paper.get('authors', [])
        year = str(paper.get('year', ''))
        journal = paper.get('journal', '')
        zotero_key = paper.get('zotero_key', '')
        cit_count = paper.get('citation_count', 0)

        cites_list = self.graph_view.cites.get(doi, []) if hasattr(self, 'graph_view') else []
        cited_by_list = self.graph_view.cited_by.get(doi, []) if hasattr(self, 'graph_view') else []

        author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "") if authors else "Unknown Authors"
        author_meta = f"{author_str}"
        if journal:
            author_meta += f" — {journal}"

        # 1. Update Persistent Header Widgets (Ultra-fast in-place)
        if not self._meta_box_visible:
            self.meta_empty_box.pack_forget()
            self.meta_content_box.pack(fill="x", padx=10, pady=8)
            self._meta_box_visible = True

        self.lbl_meta_citekey.configure(text=f"[{citekey}]")
        self.lbl_meta_year.configure(text=f"  •  {year}" if year else "")
        self.lbl_meta_title.configure(text=title)
        self.lbl_meta_authors.configure(text=author_meta)
        self.lbl_meta_doi.configure(text=f"DOI: {doi}")

        self.lbl_pill_cites.configure(text=f"Cites: {len(cites_list)}")
        self.lbl_pill_cited_by.configure(text=f"Cited By: {len(cited_by_list)}")
        self.lbl_pill_global.configure(text=f"Global: {cit_count}")

        self.btn_detail_zotero.configure(
            state="normal" if zotero_key else "disabled",
            command=lambda k=zotero_key: self._open_in_zotero(k)
        )
        self.btn_detail_doi.configure(
            state="normal" if doi else "disabled",
            command=lambda d=doi: self._open_doi_url(d)
        )

        # 2. Render Cites List
        if not self.sec_cites_frame.winfo_ismapped():
            self.sec_cites_frame.pack(fill="x", padx=4, pady=(4, 2))
        self._render_card_pool(
            container_frame=self.cites_cards_frame,
            pool=self._cites_card_pool,
            items=cites_list,
            badge_label=self.lbl_cites_cnt,
            empty_label=self.lbl_cites_empty
        )

        # 3. Separator
        if not self.sec_sep.winfo_ismapped():
            self.sec_sep.pack(fill="x", padx=4, pady=8)

        # 4. Render Cited By List
        if not self.sec_cited_by_frame.winfo_ismapped():
            self.sec_cited_by_frame.pack(fill="x", padx=4, pady=(2, 4))
        self._render_card_pool(
            container_frame=self.cited_by_cards_frame,
            pool=self._cited_by_card_pool,
            items=cited_by_list,
            badge_label=self.lbl_cited_by_cnt,
            empty_label=self.lbl_cited_by_empty
        )

        self.index_canvas.yview_moveto(0.0)

    def _update_all_card_wraplengths(self, new_wrap: int):
        for pool in (self._cites_card_pool, self._cited_by_card_pool):
            for card in pool:
                if card.get("packed", False):
                    card["title"].config(wraplength=new_wrap)

    def _render_card_pool(self, container_frame, pool, items, badge_label, empty_label):
        badge_label.config(text=str(len(items)))

        if not items:
            container_frame.pack_forget()
            empty_label.pack(anchor="w", padx=10, pady=4)
            for card in pool:
                if card.get("packed", False):
                    card["frame"].pack_forget()
                    card["packed"] = False
            return

        empty_label.pack_forget()
        container_frame.pack(fill="x")

        all_papers = self.graph_view.all_papers if hasattr(self, 'graph_view') else {}

        # Dynamically grow pool only if needed
        while len(pool) < len(items):
            card_frame = tk.Frame(
                container_frame,
                bg="#FFFFFF",
                highlightbackground="#E2E4EC",
                highlightthickness=1,
                bd=0
            )

            lbl_idx = tk.Label(
                card_frame,
                font=("Consolas", 10, "bold"),
                fg="#8E7CC3",
                bg="#FFFFFF",
                width=4,
                anchor="center"
            )
            lbl_idx.pack(side="left", padx=(6, 2), pady=6, anchor="n")

            text_box = tk.Frame(card_frame, bg="#FFFFFF")
            text_box.pack(side="left", fill="both", expand=True, padx=(2, 6), pady=4)

            lbl_title = tk.Label(
                text_box,
                font=("Segoe UI", 10, "bold"),
                fg="#2D3140",
                bg="#FFFFFF",
                anchor="w",
                justify="left",
                wraplength=self._card_wraplength
            )
            lbl_title.pack(fill="x", anchor="w")

            lbl_sub = tk.Label(
                text_box,
                font=("Segoe UI", 9),
                fg="#5C6378",
                bg="#FFFFFF",
                anchor="w",
                justify="left"
            )
            lbl_sub.pack(fill="x", anchor="w")

            card_data = {
                "frame": card_frame,
                "idx": lbl_idx,
                "box": text_box,
                "title": lbl_title,
                "sub": lbl_sub,
                "doi": None,
                "idx_text": None,
                "packed": False,
            }

            def _bind_card(cd):
                def _on_enter(e):
                    cd["frame"].config(bg="#F4F5F9", cursor="hand2")
                    cd["idx"].config(bg="#F4F5F9", cursor="hand2")
                    cd["box"].config(bg="#F4F5F9", cursor="hand2")
                    cd["title"].config(bg="#F4F5F9", cursor="hand2")
                    cd["sub"].config(bg="#F4F5F9", cursor="hand2")

                def _on_leave(e):
                    cd["frame"].config(bg="#FFFFFF", cursor="")
                    cd["idx"].config(bg="#FFFFFF", cursor="")
                    cd["box"].config(bg="#FFFFFF", cursor="")
                    cd["title"].config(bg="#FFFFFF", cursor="")
                    cd["sub"].config(bg="#FFFFFF", cursor="")

                def _on_click(e):
                    if cd["doi"]:
                        self._hop_to_paper(cd["doi"])

                for w in (cd["frame"], cd["idx"], cd["box"], cd["title"], cd["sub"]):
                    w.bind("<Button-1>", _on_click)

                cd["frame"].bind("<Enter>", _on_enter)
                cd["frame"].bind("<Leave>", _on_leave)

            _bind_card(card_data)
            pool.append(card_data)

        # Update and pack required cards (Only reconfigure text if target changed!)
        for i, target_doi in enumerate(items, 1):
            card = pool[i - 1]
            idx_str = f"[{i}]"

            if card["doi"] != target_doi or card["idx_text"] != idx_str:
                tp = all_papers.get(target_doi, {})
                tp_title = tp.get('title', target_doi)
                tp_authors = tp.get('authors', [])
                tp_year = str(tp.get('year', ''))

                author_str = tp_authors[0].split(',')[0] if tp_authors else ""
                if len(tp_authors) > 1:
                    author_str += " et al."
                author_year = f"{author_str} ({tp_year})" if (author_str and tp_year) else (author_str or tp_year or "")

                card["doi"] = target_doi
                card["idx_text"] = idx_str
                card["idx"].config(text=idx_str)
                card["title"].config(text=tp_title)
                card["sub"].config(text=author_year)

            if not card.get("packed", False):
                card["frame"].pack(fill="x", padx=4, pady=2)
                card["packed"] = True

        # Hide any excess cards without destroying
        for i in range(len(items), len(pool)):
            if pool[i].get("packed", False):
                pool[i]["frame"].pack_forget()
                pool[i]["packed"] = False

    def _hop_to_paper(self, doi: str):
        if not doi:
            return
        if hasattr(self, 'graph_view'):
            self.graph_view.select_and_focus_node(doi)
        self.display_paper_detail(doi)

    def _open_in_zotero(self, zotero_key: str):
        if not zotero_key:
            messagebox.showinfo("Zotero Item", "No Zotero key is associated with this paper.")
            return

        lib_type = self.combo_lib_type.get().strip() or os.getenv("ZOTERO_LIBRARY_TYPE", "user")
        user_id = self.entry_user_id.get().strip() or os.getenv("ZOTERO_USER_ID", "").strip()

        if lib_type.lower() == "group" and user_id:
            uri = f"zotero://select/groups/{user_id}/items/{zotero_key}"
        else:
            uri = f"zotero://select/library/items/{zotero_key}"

        self.log(f"Opening in Zotero: {uri}")
        try:
            if sys.platform == "win32":
                os.startfile(uri)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", uri])
            else:
                subprocess.Popen(["xdg-open", uri])
        except Exception as e:
            self.log(f"Failed to open in Zotero: {e}")
            messagebox.showerror("Zotero Launch Failed", f"Could not open Zotero with URI:\n{uri}\n\nError: {e}")

    def _open_doi_url(self, doi: str):
        if not doi:
            messagebox.showinfo("DOI URL", "No DOI is available for this paper.")
            return
        url = f"https://doi.org/{doi}"
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception as e:
            self.log(f"Failed to open DOI URL: {e}")

    # 3. Footer Area
    def _build_footer(self):
        footer_frame = ctk.CTkFrame(self, fg_color="transparent", height=24)
        footer_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(4, 8))
        footer_frame.grid_columnconfigure(0, weight=1)

        self.lbl_footer = ctk.CTkLabel(
            footer_frame,
            text="Citation Network Builder • Academic Research Graph Utility",
            font=ctk.CTkFont(size=11),
            text_color=THEME["text_muted"]
        )
        self.lbl_footer.grid(row=0, column=0, sticky="w")

    # ------------------------------------------------------------------
    # Config & State Helpers
    # ------------------------------------------------------------------
    def _load_config_to_inputs(self):
        self.entry_user_id.delete(0, "end")
        self.entry_user_id.insert(0, os.getenv("ZOTERO_USER_ID", ""))

        self.entry_api_key.delete(0, "end")
        self.entry_api_key.insert(0, os.getenv("ZOTERO_API_KEY", ""))

        lib_type = os.getenv("ZOTERO_LIBRARY_TYPE", "user")
        self.combo_lib_type.set(lib_type if lib_type in ["user", "group"] else "user")

        self.entry_vault_path.delete(0, "end")
        self.entry_vault_path.insert(0, os.getenv("OBSIDIAN_VAULT_PATH", ""))

        self.entry_oa_email.delete(0, "end")
        self.entry_oa_email.insert(0, os.getenv("OPENALEX_EMAIL", ""))

        gen_notes = os.getenv("GENERATE_OBSIDIAN_NOTES", "true").lower() in ("true", "1", "yes")
        self.generate_obsidian_notes.set(gen_notes)

    def save_config(self):
        user_id = self.entry_user_id.get().strip()
        api_key = self.entry_api_key.get().strip()
        lib_type = self.combo_lib_type.get().strip()
        vault_path = self.entry_vault_path.get().strip()
        oa_email = self.entry_oa_email.get().strip()
        gen_notes_str = "true" if self.generate_obsidian_notes.get() else "false"

        if not os.path.exists(self.env_path):
            with open(self.env_path, "w", encoding="utf-8") as f:
                f.write("")

        set_key(self.env_path, "ZOTERO_USER_ID", user_id)
        set_key(self.env_path, "ZOTERO_API_KEY", api_key)
        set_key(self.env_path, "ZOTERO_LIBRARY_TYPE", lib_type)
        set_key(self.env_path, "OBSIDIAN_VAULT_PATH", vault_path)
        set_key(self.env_path, "OPENALEX_EMAIL", oa_email)
        set_key(self.env_path, "GENERATE_OBSIDIAN_NOTES", gen_notes_str)

        # Reload into environment
        load_dotenv(self.env_path, override=True)
        self.log("Configuration saved to .env successfully.")
        messagebox.showinfo("Saved", "Settings successfully saved to .env")

    def _on_gen_notes_toggled(self):
        if self.generate_obsidian_notes.get():
            self.log("Obsidian note export enabled.")
        else:
            self.log("Obsidian note export disabled (Standalone Graph View mode).")

    def _browse_vault_path(self):
        chosen = filedialog.askdirectory(title="Select Obsidian Vault Directory")
        if chosen:
            self.entry_vault_path.delete(0, "end")
            self.entry_vault_path.insert(0, os.path.normpath(chosen))

    # ------------------------------------------------------------------
    # Logging & Console Helpers
    # ------------------------------------------------------------------
    def log(self, message: str):
        def _append():
            ts = datetime.now().strftime("%H:%M:%S")
            self.log_textbox.insert("end", f"[{ts}] {message}\n")
            self.log_textbox.see("end")
        self.after(0, _append)

    def clear_logs(self):
        self.log_textbox.delete("1.0", "end")

    def set_progress(self, current: int, total: int, step_desc: str):
        def _update():
            if total > 0:
                pct = min(max(current / total, 0.0), 1.0)
                self.progress_bar.set(pct)
                self.lbl_progress_step.configure(text=f"{step_desc} ({int(pct*100)}%)")
            else:
                self.lbl_progress_step.configure(text=step_desc)
        self.after(0, _update)

    # ------------------------------------------------------------------
    # Zotero Collection Tree Management
    # ------------------------------------------------------------------
    def _auto_load_tree(self):
        user_id = os.getenv("ZOTERO_USER_ID", "").strip()
        api_key = os.getenv("ZOTERO_API_KEY", "").strip()
        if user_id and api_key:
            self.fetch_zotero_tree()
        else:
            self.log("Zotero credentials not set. Please configure in the Settings tab.")

    def fetch_zotero_tree(self):
        user_id = self.entry_user_id.get().strip() or os.getenv("ZOTERO_USER_ID", "").strip()
        api_key = self.entry_api_key.get().strip() or os.getenv("ZOTERO_API_KEY", "").strip()
        lib_type = self.combo_lib_type.get().strip() or os.getenv("ZOTERO_LIBRARY_TYPE", "user")

        if not user_id or not api_key:
            self.log("Cannot fetch collections: Zotero User ID or API Key is missing.")
            self.tabview.set("  Settings (.env)  ")
            return

        def _worker():
            self.log("Connecting to Zotero API and retrieving collection tree...")
            self.after(0, lambda: self.btn_refresh_tree.configure(state="disabled"))
            try:
                client = ZoteroClient(user_id, api_key, library_type=lib_type)
                tree, roots = client.get_collection_tree()
                self.tree_data = tree
                self.roots_data = roots
                # Default expansion: expand My Library and roots
                self.expanded_keys = {"__root__"} | set(roots)

                if not self.selected_collection_key.get() or self.selected_collection_key.get() not in tree:
                    self.selected_collection_key.set(roots[0] if roots else "__root__")

                self.after(0, self._render_tree)
                self.after(0, lambda: self.zotero_badge.configure(
                    text=f"Zotero: {len(tree)} cols",
                    fg_color=THEME["card_bg"],
                    text_color=THEME["success"]
                ))
                self.log(f"Successfully loaded {len(tree)} collections from Zotero.")

            except Exception as e:
                self.log(f"Zotero fetch error: {e}")
                self.after(0, lambda: self.zotero_badge.configure(
                    text="Zotero: Failed",
                    fg_color=THEME["card_bg"],
                    text_color=THEME["error"]
                ))
            finally:
                self.after(0, lambda: self.btn_refresh_tree.configure(state="normal"))

        threading.Thread(target=_worker, daemon=True).start()

    def _configure_treeview_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "Treeview",
            background="#FFFFFF",
            foreground=THEME["text_primary"],
            fieldbackground="#FFFFFF",
            rowheight=26,
            font=("Segoe UI", 10),
            borderwidth=0
        )
        style.map(
            "Treeview",
            background=[("selected", THEME["accent"])],
            foreground=[("selected", "#FFFFFF")]
        )

    def _on_tree_select(self, event=None):
        selected = self.collection_tree.selection()
        if not selected:
            return
        key = selected[0]
        self.selected_collection_key.set(key)
        self._on_collection_selected()

    def _on_tree_open(self, event=None):
        item = self.collection_tree.focus()
        if item:
            self.expanded_keys.add(item)

    def _on_tree_close(self, event=None):
        item = self.collection_tree.focus()
        if item:
            self.expanded_keys.discard(item)

    def toggle_folder_expansion(self, key: str):
        if not self.collection_tree.exists(key):
            return
        is_open = self.collection_tree.item(key, "open")
        self.collection_tree.item(key, open=not is_open)
        if not is_open:
            self.expanded_keys.add(key)
        else:
            self.expanded_keys.discard(key)

    def expand_all_collections(self):
        def _open(item):
            self.collection_tree.item(item, open=True)
            for c in self.collection_tree.get_children(item):
                _open(c)
        for r in self.collection_tree.get_children(""):
            _open(r)
        if self.tree_data:
            self.expanded_keys = {"__root__"} | set(self.tree_data.keys())

    def collapse_all_collections(self):
        def _close(item):
            for c in self.collection_tree.get_children(item):
                _close(c)
            if item != "__root__":
                self.collection_tree.item(item, open=False)
        for r in self.collection_tree.get_children(""):
            _close(r)
        self.expanded_keys = {"__root__"}

    def _on_collection_selected(self):
        key = self.selected_collection_key.get()
        if key == "__root__":
            self.process_all_var.set(True)
            self.log("Selected: My Library (All Collections)")
        else:
            self.process_all_var.set(False)
            name = self.tree_data.get(key, {}).get("name", key)
            self.log(f"Selected collection: '{name}'")

    def _on_process_all_toggled(self):
        if self.process_all_var.get():
            self.selected_collection_key.set("__root__")
            if self.collection_tree.exists("__root__"):
                self.collection_tree.selection_set("__root__")
                self.collection_tree.see("__root__")
            self.log("Option selected: Process ALL collections (My Library)")
        else:
            if self.roots_data:
                rk = self.roots_data[0]
                self.selected_collection_key.set(rk)
                if self.collection_tree.exists(rk):
                    self.collection_tree.selection_set(rk)
                    self.collection_tree.see(rk)
            self.log("Option selected: Single collection subtree mode")

    def _filter_collection_list(self):
        self._render_tree()

    def _render_tree(self, query: str = ""):
        # Clear existing items instantly in C
        self.collection_tree.delete(*self.collection_tree.get_children())

        if not self.tree_data:
            return

        query = (query or self.collection_search_var.get()).strip().lower()

        # Find matching keys and auto-expand ancestors during search
        matching_keys = set()
        active_expanded = set(self.expanded_keys)
        if query:
            for k, col in self.tree_data.items():
                if query in col["name"].lower():
                    matching_keys.add(k)
                    pk = col.get("parent_key")
                    while pk and pk in self.tree_data:
                        active_expanded.add(pk)
                        pk = self.tree_data[pk].get("parent_key")
                    active_expanded.add("__root__")

        # 1. Top Root: "My Library" (Selects all collections)
        root_open = ("__root__" in active_expanded) or bool(query)
        self.collection_tree.insert(
            "",
            "end",
            iid="__root__",
            text="My Library (All Collections)",
            open=root_open
        )

        # 2. Render children recursively
        sorted_roots = sorted(self.roots_data, key=lambda k: self.tree_data[k]["name"].lower())
        for rk in sorted_roots:
            self._render_tree_item(rk, parent_id="__root__", query=query, matching_keys=matching_keys, active_expanded=active_expanded)

        # Restore selection
        sel = self.selected_collection_key.get()
        if sel and self.collection_tree.exists(sel):
            self.collection_tree.selection_set(sel)
            self.collection_tree.see(sel)
        else:
            self.collection_tree.selection_set("__root__")

    def _render_tree_item(self, key: str, parent_id: str, query: str, matching_keys: set, active_expanded: set):
        col = self.tree_data.get(key)
        if not col:
            return

        has_children = bool(col.get("children"))

        # When searching, only render if this node or any descendant matches
        if query:
            def _has_match(k):
                if k in matching_keys:
                    return True
                for ch in self.tree_data.get(k, {}).get("children", []):
                    if _has_match(ch):
                        return True
                return False

            if not _has_match(key):
                return

        is_open = (key in active_expanded) or bool(query)

        self.collection_tree.insert(
            parent_id,
            "end",
            iid=key,
            text=col['name'],
            open=is_open
        )

        if has_children:
            sorted_children = sorted(col["children"], key=lambda k: self.tree_data[k]["name"].lower())
            for ck in sorted_children:
                self._render_tree_item(ck, parent_id=key, query=query, matching_keys=matching_keys, active_expanded=active_expanded)

    # ------------------------------------------------------------------
    # Connection Testing
    # ------------------------------------------------------------------
    def run_connection_test(self):
        user_id = self.entry_user_id.get().strip() or os.getenv("ZOTERO_USER_ID", "").strip()
        api_key = self.entry_api_key.get().strip() or os.getenv("ZOTERO_API_KEY", "").strip()
        lib_type = self.combo_lib_type.get().strip() or os.getenv("ZOTERO_LIBRARY_TYPE", "user")
        oa_email = self.entry_oa_email.get().strip() or os.getenv("OPENALEX_EMAIL", "").strip()

        self.btn_test_api.configure(state="disabled", text="Testing...")
        self.log("\n--- Starting API Connection Test ---")

        def _test_worker():
            # 1. Zotero Test
            zot_ok = False
            try:
                zotero = ZoteroClient(user_id, api_key, library_type=lib_type)
                cols = zotero.get_collections()
                zot_ok = True
                self.log(f"✓ Zotero connection successful! ({len(cols)} collections found)")
                self.after(0, lambda: self.zotero_badge.configure(
                    text="Zotero: Connected",
                    fg_color=THEME["card_bg"],
                    text_color=THEME["success"]
                ))
            except Exception as e:
                self.log(f"✗ Zotero connection failed: {e}")
                self.after(0, lambda: self.zotero_badge.configure(
                    text="Zotero: Error",
                    fg_color=THEME["card_bg"],
                    text_color=THEME["error"]
                ))

            # 2. OpenAlex Test
            oa_ok = False
            try:
                openalex = OpenAlexClient(email=oa_email, cache_file=self.cache_file)
                work = openalex.get_work_by_doi("10.1093/aje/kwu178")
                if work:
                    oa_ok = True
                    self.log("✓ OpenAlex connection successful! (Test DOI fetched)")
                    self.after(0, lambda: self.openalex_badge.configure(
                        text="OpenAlex: Connected",
                        fg_color=THEME["card_bg"],
                        text_color=THEME["success"]
                    ))
                else:
                    self.log("⚠ OpenAlex reachable but test DOI returned empty.")
            except Exception as e:
                self.log(f"✗ OpenAlex connection failed: {e}")
                self.after(0, lambda: self.openalex_badge.configure(
                    text="OpenAlex: Error",
                    fg_color=THEME["card_bg"],
                    text_color=THEME["error"]
                ))

            self.log("--- Connection Test Completed ---\n")
            self.after(0, lambda: self.btn_test_api.configure(state="normal", text="Test Connection"))

        threading.Thread(target=_test_worker, daemon=True).start()

    # ------------------------------------------------------------------
    # Main Build Pipeline Execution
    # ------------------------------------------------------------------
    def start_build_process(self):
        if self.is_running:
            return

        # Read Current Inputs
        user_id = self.entry_user_id.get().strip() or os.getenv("ZOTERO_USER_ID", "").strip()
        api_key = self.entry_api_key.get().strip() or os.getenv("ZOTERO_API_KEY", "").strip()
        lib_type = self.combo_lib_type.get().strip() or os.getenv("ZOTERO_LIBRARY_TYPE", "user")
        vault_path = self.entry_vault_path.get().strip() or os.getenv("OBSIDIAN_VAULT_PATH", "").strip()
        oa_email = self.entry_oa_email.get().strip() or os.getenv("OPENALEX_EMAIL", "").strip()
        gen_notes = self.generate_obsidian_notes.get()

        if not user_id or not api_key:
            messagebox.showwarning("Missing Credentials", "Please enter your Zotero User ID and API Key in Settings.")
            self.tabview.set("  Settings (.env)  ")
            return

        if gen_notes and (not vault_path or not os.path.exists(vault_path)):
            messagebox.showwarning(
                "Invalid Vault Path",
                "Obsidian Vault directory path is required when note generation is enabled.\n\n"
                "Please configure a valid folder in Settings or uncheck 'Generate Obsidian Markdown Notes'."
            )
            self.tabview.set("  Settings (.env)  ")
            return

        selected_key = self.selected_collection_key.get()
        is_all = self.process_all_var.get() or (selected_key == "__root__")

        if not is_all and not selected_key:
            messagebox.showwarning("No Collection Selected", "Please select a collection from the list or check 'Process All Collections'.")
            self.tabview.set("  Collections  ")
            return

        # Prepare UI State
        self.is_running = True
        self.stop_requested = False
        self.btn_start.configure(state="disabled", text="Processing Network...")
        self.btn_stop.configure(state="normal")
        self.progress_bar.set(0.0)
        self.lbl_progress_step.configure(text="Initializing pipeline...")

        # Reset Metrics
        self._update_metrics(papers="0", doi="0", edges="0", notes="0")

        self.log("\n=======================================================")
        mode_str = "With Obsidian Notes" if gen_notes else "Standalone GUI Graph Mode"
        self.log(f"Starting Citation Network Build ({mode_str}) [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
        self.log("=======================================================")

        def _pipeline_worker():
            try:
                # 1. Initialize Clients
                zotero = ZoteroClient(user_id, api_key, library_type=lib_type)
                openalex = OpenAlexClient(email=oa_email, cache_file=self.cache_file)

                # Ensure tree structure is available
                if not self.tree_data:
                    self.log("Fetching collection tree structure...")
                    tree, roots = zotero.get_collection_tree()
                    self.tree_data = tree
                else:
                    tree = self.tree_data

                # --- STEP 1: Fetch Papers from Zotero ---
                total_steps = 3 if gen_notes else 2
                self.set_progress(0, 100, f"Step 1/{total_steps}: Fetching papers from Zotero...")
                self.log(f"Step 1/{total_steps}: Fetching papers from Zotero...")

                if is_all:
                    target_name = "All Collections"
                    papers = zotero.get_all_collections_with_papers(
                        progress=False,
                        log_callback=self.log,
                        progress_callback=lambda c, t, m: self.set_progress(int((c/t)*30), 100, f"Zotero: {m}")
                    )
                else:
                    target_name = tree.get(selected_key, {}).get('name', selected_key)
                    self.log(f"Processing subtree for collection: '{target_name}'")
                    papers = zotero.get_papers_in_subtree(
                        selected_key,
                        tree,
                        log_callback=self.log
                    )

                if self.stop_requested:
                    self.log("Process cancelled by user.")
                    return

                if not papers:
                    self.log("Warning: No paper items found in the selected collection.")
                    self.set_progress(100, 100, "Completed (No papers found)")
                    return

                total_papers = sum(len(v['papers']) for v in papers.values())
                doi_papers = sum(1 for v in papers.values() for p in v['papers'] if p.get('doi'))
                self._update_metrics(papers=total_papers, doi=doi_papers)

                self.log(f"Step 1 Complete: Found {len(papers)} collections, {total_papers} papers ({doi_papers} with DOI)")
                self.set_progress(35, 100, f"Step 1 Complete: {total_papers} papers collected")

                # --- STEP 2: OpenAlex Citation Network Analysis ---
                self.log(f"\nStep 2/{total_steps}: Querying OpenAlex and mapping citation network...")
                cites, cited_by, all_papers = openalex.build_citation_network(
                    papers,
                    log_callback=self.log,
                    progress_callback=lambda c, t, m: self.set_progress(35 + int((c/t)*(45 if gen_notes else 60)), 100, m)
                )

                if self.stop_requested:
                    self.log("Process cancelled by user.")
                    return

                edges = sum(len(v) for v in cites.values())
                connected = sum(1 for d in all_papers if cites.get(d) or cited_by.get(d))

                self._update_metrics(edges=edges)
                self.log(f"Step 2 Complete: {edges} citation links mapped ({connected}/{total_papers} papers connected)")
                self.set_progress(80 if gen_notes else 100, 100, f"Step 2 Complete: {edges} citation edges")

                self.current_cites = cites
                self.current_cited_by = cited_by
                self.current_all_papers = all_papers

                # Update Graph View in real time
                self.after(0, lambda c=cites, cb=cited_by, ap=all_papers: self.graph_view.load_graph_data(c, cb, ap))

                if gen_notes:
                    # --- STEP 3: Generate Obsidian Markdown Notes ---
                    self.log(f"\nStep 3/{total_steps}: Writing Obsidian markdown notes...")
                    writer = ObsidianWriter(vault_path, citation_folder="")
                    created, updated = writer.write_all(
                        papers,
                        cites,
                        cited_by,
                        all_papers,
                        log_callback=self.log,
                        progress_callback=lambda c, t, m: self.set_progress(80 + int((c/t)*20), 100, m)
                    )

                    total_notes = created + updated
                    self._update_metrics(notes=total_notes)

                    dest_folder = vault_path if is_all else os.path.join(vault_path, ObsidianWriter.sanitize_filename(target_name))

                    self.set_progress(100, 100, "✓ Citation Network successfully built!")
                    self.log("\n=======================================================")
                    self.log("✓ SUCCESS: Citation network notes generated!")
                    self.log(f"  • Notes Written: {total_notes} (Created: {created}, Updated: {updated})")
                    self.log(f"  • Citation Edges: {edges}")
                    self.log(f"  • Destination Folder: {dest_folder}")
                    self.log("=======================================================")

                    messagebox.showinfo(
                        "Network Build Complete",
                        f"Successfully generated {total_notes} Obsidian notes!\n"
                        f"Citation Links: {edges}\n"
                        f"Folder: {dest_folder}\n\n"
                        f"You can now explore the citation graph in Obsidian and Graph View."
                    )
                else:
                    self.set_progress(100, 100, "✓ Citation Network mapped (Obsidian notes skipped)!")
                    self.log("\n=======================================================")
                    self.log("✓ SUCCESS: Citation network mapped successfully!")
                    self.log(f"  • Connected Papers: {connected}/{total_papers}")
                    self.log(f"  • Citation Edges: {edges}")
                    self.log("  • Obsidian Notes: Skipped (Standalone Mode)")
                    self.log("=======================================================")

                    messagebox.showinfo(
                        "Network Build Complete",
                        f"Citation network successfully mapped in Graph View!\n\n"
                        f"• Connected Papers: {connected}/{total_papers}\n"
                        f"• Citation Links: {edges}\n\n"
                        f"Explore the interactive graph in the Graph View panel."
                    )

            except Exception as e:
                self.log(f"\n✗ ERROR during pipeline execution: {e}")
                self.set_progress(0, 100, "Failed with error")
                messagebox.showerror("Execution Error", f"An error occurred:\n{e}")
            finally:
                self.is_running = False
                self.after(0, lambda: self.btn_start.configure(state="normal", text="Build Citation Network"))
                self.after(0, lambda: self.btn_stop.configure(state="disabled"))

        threading.Thread(target=_pipeline_worker, daemon=True).start()

    def stop_build_process(self):
        if self.is_running:
            self.stop_requested = True
            self.log("Cancellation requested. Stopping after current task...")
            self.btn_stop.configure(state="disabled")

    def open_obsidian_folder(self):
        vault_path = self.entry_vault_path.get().strip() or os.getenv("OBSIDIAN_VAULT_PATH", "").strip()
        selected_key = self.selected_collection_key.get()
        if selected_key == "__root__" or self.process_all_var.get():
            target_name = ""
        else:
            target_name = self.tree_data.get(selected_key, {}).get('name', '') if self.tree_data else ''
        target = os.path.join(vault_path, ObsidianWriter.sanitize_filename(target_name)) if (vault_path and target_name) else vault_path

        if target and os.path.exists(target):
            if sys.platform == "win32":
                os.startfile(target)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", target])
            else:
                subprocess.Popen(["xdg-open", target])
        elif vault_path and os.path.exists(vault_path):
            if sys.platform == "win32":
                os.startfile(vault_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", vault_path])
            else:
                subprocess.Popen(["xdg-open", vault_path])
        else:
            messagebox.showinfo(
                "Vault Directory",
                "Obsidian Vault directory path is not configured or does not exist.\n"
                "Please configure a valid Obsidian Vault Path in Settings."
            )


# ----------------------------------------------------------------------
# Application Entry Point
# ----------------------------------------------------------------------
def main():
    app = CitationNetworkGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
