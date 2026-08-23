"""
Citation Network Builder - Modern Desktop GUI
==============================================
A clean, subdued dark-themed GUI for Citation Network Builder using CustomTkinter.
"""
import os
import sys
import json
import threading
import subprocess
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
from dotenv import load_dotenv, set_key

# Import core clients
sys.path.insert(0, os.path.dirname(__file__))
from src.zotero_client import ZoteroClient
from src.openalex_client import OpenAlexClient
from src.obsidian_writer import ObsidianWriter


# ----------------------------------------------------------------------
# Theme & Color Palette (Subdued, Muted Slate/Charcoal Dark Theme)
# ----------------------------------------------------------------------
THEME = {
    "bg_dark": "#16171B",          # Main window background
    "card_bg": "#202228",          # Cards and section containers
    "card_border": "#2C2E37",      # Subtle borders
    "input_bg": "#1A1B20",         # Input fields and dropdowns
    "input_border": "#353844",     # Input border
    "text_primary": "#E1E4EA",     # Primary clean text
    "text_muted": "#8C92A4",       # Muted / secondary labels
    "accent": "#3E5C76",           # Muted slate blue primary button
    "accent_hover": "#4B6E8D",     # Hover state
    "secondary_btn": "#2A2C34",    # Subdued utility buttons
    "secondary_hover": "#363943",  # Subdued utility button hover
    "success": "#4D7C66",          # Muted sage green for success/connected
    "error": "#934B4B",            # Muted rust red for error/disconnected
    "warning": "#9B7E48",          # Muted warm amber
    "log_bg": "#121316",           # Terminal log background
    "log_text": "#C8CDD8",         # Terminal log text
}


class CitationNetworkGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Configuration
        self.title("Citation Network Builder v1.1.0")
        self.geometry("1100x740")
        self.minsize(980, 680)

        # Set default appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Runtime State
        self.env_path = os.path.join(os.path.dirname(__file__), '.env')
        self.cache_file = os.path.join(os.path.dirname(__file__), 'cache', 'openalex_cache.json')
        load_dotenv(self.env_path)

        self.tree_data = {}
        self.roots_data = []
        self.collection_list = []  # [(key, display_name, is_folder)]
        self.is_running = False
        self.stop_requested = False

        self._init_ui()
        self._load_config_to_inputs()
        
        # Initial check in background
        self.after(300, self._auto_load_tree)

    # ------------------------------------------------------------------
    # UI Layout Initialization
    # ------------------------------------------------------------------
    def _init_ui(self):
        self.configure(fg_color=THEME["bg_dark"])

        # Main Grid Layout (Header / Content / Status)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_body()
        self._build_footer()

    # 1. Header Area
    def _build_header(self):
        header_frame = ctk.CTkFrame(
            self,
            fg_color=THEME["card_bg"],
            corner_radius=0,
            height=60,
            border_width=1,
            border_color=THEME["card_border"]
        )
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 10))
        header_frame.grid_columnconfigure(1, weight=1)

        # Title & Subtitle
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        title_label = ctk.CTkLabel(
            title_box,
            text="Citation Network Builder",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=THEME["text_primary"]
        )
        title_label.pack(side="left", padx=(0, 10))

        ver_badge = ctk.CTkLabel(
            title_box,
            text="v1.1.0",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=THEME["input_bg"],
            text_color=THEME["text_muted"],
            corner_radius=4,
            padx=6,
            pady=2
        )
        ver_badge.pack(side="left")

        # Status Badges and Quick Test
        status_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        status_box.grid(row=0, column=2, padx=20, pady=10, sticky="e")

        self.zotero_badge = ctk.CTkLabel(
            status_box,
            text="Zotero: Ready",
            font=ctk.CTkFont(size=12),
            fg_color=THEME["input_bg"],
            text_color=THEME["text_muted"],
            corner_radius=6,
            padx=10,
            pady=4
        )
        self.zotero_badge.pack(side="left", padx=5)

        self.openalex_badge = ctk.CTkLabel(
            status_box,
            text="OpenAlex: Ready",
            font=ctk.CTkFont(size=12),
            fg_color=THEME["input_bg"],
            text_color=THEME["text_muted"],
            corner_radius=6,
            padx=10,
            pady=4
        )
        self.openalex_badge.pack(side="left", padx=5)

        self.btn_test_api = ctk.CTkButton(
            status_box,
            text="Test Connection",
            font=ctk.CTkFont(size=12),
            fg_color=THEME["secondary_btn"],
            hover_color=THEME["secondary_hover"],
            text_color=THEME["text_primary"],
            width=115,
            height=30,
            corner_radius=6,
            command=self.run_connection_test
        )
        self.btn_test_api.pack(side="left", padx=(10, 0))

    # 2. Main Content Split View (Left: Settings/Tree, Right: Action/Log/Stats)
    def _build_body(self):
        body_frame = ctk.CTkFrame(self, fg_color="transparent")
        body_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=0)
        body_frame.grid_rowconfigure(0, weight=1)
        body_frame.grid_columnconfigure(0, weight=4, minsize=380)  # Left Panel
        body_frame.grid_columnconfigure(1, weight=6, minsize=520)  # Right Panel

        self._build_left_panel(body_frame)
        self._build_right_panel(body_frame)

    def _build_left_panel(self, parent):
        left_card = ctk.CTkFrame(
            parent,
            fg_color=THEME["card_bg"],
            corner_radius=8,
            border_width=1,
            border_color=THEME["card_border"]
        )
        left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)
        left_card.grid_rowconfigure(1, weight=1)
        left_card.grid_columnconfigure(0, weight=1)

        # Tabview for Collections vs Settings
        self.tabview = ctk.CTkTabview(
            left_card,
            fg_color=THEME["card_bg"],
            segmented_button_fg_color=THEME["input_bg"],
            segmented_button_selected_color=THEME["accent"],
            segmented_button_selected_hover_color=THEME["accent_hover"],
            segmented_button_unselected_color=THEME["input_bg"],
            segmented_button_unselected_hover_color=THEME["secondary_hover"],
            text_color=THEME["text_primary"]
        )
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
        
        tab_collections = self.tabview.add("  Collections  ")
        tab_settings = self.tabview.add("  Settings (.env)  ")

        self._build_collections_tab(tab_collections)
        self._build_settings_tab(tab_settings)

    def _build_collections_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        # Top Control Bar (Search & Refresh)
        top_bar = ctk.CTkFrame(tab, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 8))
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
            height=32
        )
        self.entry_search.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.btn_refresh_tree = ctk.CTkButton(
            top_bar,
            text="↻ Refresh",
            width=75,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=THEME["secondary_btn"],
            hover_color=THEME["secondary_hover"],
            text_color=THEME["text_primary"],
            command=self.fetch_zotero_tree
        )
        self.btn_refresh_tree.grid(row=0, column=1)

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

        # Scrollable Collection Tree / List View
        self.tree_scroll = ctk.CTkScrollableFrame(
            tab,
            fg_color=THEME["input_bg"],
            corner_radius=6,
            border_width=1,
            border_color=THEME["input_border"]
        )
        self.tree_scroll.grid(row=2, column=0, sticky="nsew", padx=5, pady=(0, 5))
        self.tree_scroll.grid_columnconfigure(0, weight=1)

        self.selected_collection_key = tk.StringVar(value="")
        self.tree_radio_buttons = []

        # Info Note at Bottom of Tab
        lbl_info = ctk.CTkLabel(
            tab,
            text="Selecting a folder includes all subcollections automatically.",
            font=ctk.CTkFont(size=11),
            text_color=THEME["text_muted"]
        )
        lbl_info.grid(row=3, column=0, sticky="w", padx=8, pady=(4, 2))

    def _build_settings_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)

        # Form Scrollable
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)
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

        # Obsidian Vault Path
        ctk.CTkLabel(scroll, text="Obsidian Vault Path *", font=ctk.CTkFont(size=12), text_color=THEME["text_muted"]).grid(row=row, column=0, sticky="w", pady=(6, 2))
        row += 1
        vault_box = ctk.CTkFrame(scroll, fg_color="transparent")
        vault_box.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        vault_box.grid_columnconfigure(0, weight=1)

        self.entry_vault_path = ctk.CTkEntry(vault_box, fg_color=THEME["input_bg"], border_color=THEME["input_border"], height=30)
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

        # Citation Folder Name
        ctk.CTkLabel(scroll, text="Output Folder Name in Vault", font=ctk.CTkFont(size=12), text_color=THEME["text_muted"]).grid(row=row, column=0, sticky="w", pady=(6, 2))
        row += 1
        self.entry_folder_name = ctk.CTkEntry(scroll, fg_color=THEME["input_bg"], border_color=THEME["input_border"], height=30)
        self.entry_folder_name.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        row += 1

        # OpenAlex Email
        ctk.CTkLabel(scroll, text="OpenAlex Email (Optional for Faster Pool)", font=ctk.CTkFont(size=12), text_color=THEME["text_muted"]).grid(row=row, column=0, sticky="w", pady=(6, 2))
        row += 1
        self.entry_oa_email = ctk.CTkEntry(scroll, fg_color=THEME["input_bg"], border_color=THEME["input_border"], height=30)
        self.entry_oa_email.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        row += 1

        # Save Button
        self.btn_save_config = ctk.CTkButton(
            scroll,
            text="Save Configuration (.env)",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            text_color=THEME["text_primary"],
            height=34,
            command=self.save_config
        )
        self.btn_save_config.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 10))

    def _build_right_panel(self, parent):
        right_card = ctk.CTkFrame(
            parent,
            fg_color=THEME["card_bg"],
            corner_radius=8,
            border_width=1,
            border_color=THEME["card_border"]
        )
        right_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)
        right_card.grid_rowconfigure(2, weight=1)
        right_card.grid_columnconfigure(0, weight=1)

        # 1. Action Controls Header (Start / Cancel / Open Vault)
        ctrl_frame = ctk.CTkFrame(right_card, fg_color="transparent")
        ctrl_frame.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 8))
        ctrl_frame.grid_columnconfigure(0, weight=1)

        self.btn_start = ctk.CTkButton(
            ctrl_frame,
            text="▶  Build Citation Network",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            text_color=THEME["text_primary"],
            height=42,
            corner_radius=6,
            command=self.start_build_process
        )
        self.btn_start.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.btn_stop = ctk.CTkButton(
            ctrl_frame,
            text="■ Stop",
            font=ctk.CTkFont(size=12),
            fg_color=THEME["secondary_btn"],
            hover_color=THEME["secondary_hover"],
            text_color=THEME["text_primary"],
            width=70,
            height=42,
            corner_radius=6,
            state="disabled",
            command=self.stop_build_process
        )
        self.btn_stop.grid(row=0, column=1, padx=(0, 8))

        self.btn_open_vault = ctk.CTkButton(
            ctrl_frame,
            text="Open Vault ↗",
            font=ctk.CTkFont(size=12),
            fg_color=THEME["secondary_btn"],
            hover_color=THEME["secondary_hover"],
            text_color=THEME["text_primary"],
            width=95,
            height=42,
            corner_radius=6,
            command=self.open_obsidian_folder
        )
        self.btn_open_vault.grid(row=0, column=2)

        # 2. Progress & Step Tracker
        prog_frame = ctk.CTkFrame(right_card, fg_color="transparent")
        prog_frame.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))
        prog_frame.grid_columnconfigure(0, weight=1)

        self.lbl_progress_step = ctk.CTkLabel(
            prog_frame,
            text="Ready to build citation network",
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_muted"]
        )
        self.lbl_progress_step.grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.progress_bar = ctk.CTkProgressBar(
            prog_frame,
            height=8,
            corner_radius=4,
            fg_color=THEME["input_bg"],
            progress_color=THEME["accent"]
        )
        self.progress_bar.grid(row=1, column=0, sticky="ew")
        self.progress_bar.set(0.0)

        # 3. Live Log Console
        log_frame = ctk.CTkFrame(
            right_card,
            fg_color=THEME["log_bg"],
            corner_radius=6,
            border_width=1,
            border_color=THEME["card_border"]
        )
        log_frame.grid(row=2, column=0, sticky="nsew", padx=14, pady=(4, 10))
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        # Log Top Bar
        log_bar = ctk.CTkFrame(log_frame, fg_color="transparent", height=24)
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
            width=45,
            height=20,
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

        # 4. Result Metrics / Stats Cards
        stats_frame = ctk.CTkFrame(right_card, fg_color="transparent")
        stats_frame.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 12))
        for col_idx in range(4):
            stats_frame.grid_columnconfigure(col_idx, weight=1)

        self.stat_papers = self._create_stat_card(stats_frame, 0, "Papers", "0")
        self.stat_doi = self._create_stat_card(stats_frame, 1, "DOI Matched", "0")
        self.stat_edges = self._create_stat_card(stats_frame, 2, "Citation Links", "0")
        self.stat_notes = self._create_stat_card(stats_frame, 3, "Notes Generated", "0")

    def _create_stat_card(self, parent, col, title, initial_val):
        card = ctk.CTkFrame(
            parent,
            fg_color=THEME["input_bg"],
            corner_radius=6,
            border_width=1,
            border_color=THEME["input_border"]
        )
        card.grid(row=0, column=col, sticky="ew", padx=3 if col in (1, 2) else (0 if col == 0 else 0))

        lbl_title = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=11), text_color=THEME["text_muted"])
        lbl_title.pack(anchor="center", pady=(6, 0))

        lbl_val = ctk.CTkLabel(card, text=initial_val, font=ctk.CTkFont(size=16, weight="bold"), text_color=THEME["text_primary"])
        lbl_val.pack(anchor="center", pady=(0, 6))

        return lbl_val

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

        self.entry_folder_name.delete(0, "end")
        self.entry_folder_name.insert(0, os.getenv("CITATION_NETWORK_FOLDER", "Citation Network"))

        self.entry_oa_email.delete(0, "end")
        self.entry_oa_email.insert(0, os.getenv("OPENALEX_EMAIL", ""))

    def save_config(self):
        user_id = self.entry_user_id.get().strip()
        api_key = self.entry_api_key.get().strip()
        lib_type = self.combo_lib_type.get().strip()
        vault_path = self.entry_vault_path.get().strip()
        folder_name = self.entry_folder_name.get().strip() or "Citation Network"
        oa_email = self.entry_oa_email.get().strip()

        if not os.path.exists(self.env_path):
            with open(self.env_path, "w", encoding="utf-8") as f:
                f.write("")

        set_key(self.env_path, "ZOTERO_USER_ID", user_id)
        set_key(self.env_path, "ZOTERO_API_KEY", api_key)
        set_key(self.env_path, "ZOTERO_LIBRARY_TYPE", lib_type)
        set_key(self.env_path, "OBSIDIAN_VAULT_PATH", vault_path)
        set_key(self.env_path, "CITATION_NETWORK_FOLDER", folder_name)
        set_key(self.env_path, "OPENALEX_EMAIL", oa_email)

        # Reload into environment
        load_dotenv(self.env_path, override=True)
        self.log("Configuration saved to .env successfully.")
        messagebox.showinfo("Saved", "Settings successfully saved to .env")

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
            self.after(0, lambda: self.btn_refresh_tree.configure(state="disabled", text="Loading..."))
            try:
                client = ZoteroClient(user_id, api_key, library_type=lib_type)
                tree, roots = client.get_collection_tree()
                self.tree_data = tree
                self.roots_data = roots

                # Flatten tree into hierarchical list
                flat_list = []
                def _flatten(keys, depth=0):
                    for k in keys:
                        col = tree[k]
                        indent = "    " * depth
                        has_children = bool(col['children'])
                        prefix = "📁 " if has_children else "📄 "
                        display_name = f"{indent}{prefix}{col['name']}"
                        flat_list.append((k, display_name, col['name']))
                        if has_children:
                            _flatten(col['children'], depth + 1)

                _flatten(roots)
                self.collection_list = flat_list

                self.after(0, lambda: self._update_tree_ui(flat_list))
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
                self.after(0, lambda: self.btn_refresh_tree.configure(state="normal", text="↻ Refresh"))

        threading.Thread(target=_worker, daemon=True).start()

    def _update_tree_ui(self, items):
        # Clear existing
        for widget in self.tree_scroll.winfo_children():
            widget.destroy()
        self.tree_radio_buttons = []

        if not items:
            lbl_empty = ctk.CTkLabel(
                self.tree_scroll,
                text="No collections found in Zotero library.",
                font=ctk.CTkFont(size=12),
                text_color=THEME["text_muted"]
            )
            lbl_empty.pack(pady=20)
            return

        for key, display_name, raw_name in items:
            rb = ctk.CTkRadioButton(
                self.tree_scroll,
                text=display_name,
                value=key,
                variable=self.selected_collection_key,
                font=ctk.CTkFont(size=12),
                text_color=THEME["text_primary"],
                fg_color=THEME["accent"],
                hover_color=THEME["accent_hover"],
                border_color=THEME["input_border"]
            )
            rb.pack(anchor="w", padx=8, pady=3, fill="x")
            self.tree_radio_buttons.append((key, display_name, raw_name, rb))

        # Select first by default if nothing selected
        if not self.selected_collection_key.get() and items:
            self.selected_collection_key.set(items[0][0])

    def _filter_collection_list(self):
        query = self.collection_search_var.get().strip().lower()
        for key, display_name, raw_name, rb in self.tree_radio_buttons:
            if not query or query in raw_name.lower():
                rb.pack(anchor="w", padx=8, pady=3, fill="x")
            else:
                rb.pack_forget()

    def _on_process_all_toggled(self):
        if self.process_all_var.get():
            self.log("Option selected: Process ALL collections")
        else:
            self.log(f"Option selected: Single collection subtree mode")

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
        folder_name = self.entry_folder_name.get().strip() or os.getenv("CITATION_NETWORK_FOLDER", "Citation Network")
        oa_email = self.entry_oa_email.get().strip() or os.getenv("OPENALEX_EMAIL", "").strip()

        if not user_id or not api_key:
            messagebox.showwarning("Missing Credentials", "Please enter your Zotero User ID and API Key in Settings.")
            self.tabview.set("  Settings (.env)  ")
            return

        if not vault_path or not os.path.exists(vault_path):
            messagebox.showwarning("Invalid Vault Path", "Please provide a valid Obsidian Vault directory path.")
            self.tabview.set("  Settings (.env)  ")
            return

        is_all = self.process_all_var.get()
        selected_key = self.selected_collection_key.get()

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

        # Reset Stats
        self.stat_papers.configure(text="0")
        self.stat_doi.configure(text="0")
        self.stat_edges.configure(text="0")
        self.stat_notes.configure(text="0")

        self.log("\n=======================================================")
        self.log(f"Starting Citation Network Build [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
        self.log("=======================================================")

        def _pipeline_worker():
            try:
                # 1. Initialize Clients
                zotero = ZoteroClient(user_id, api_key, library_type=lib_type)
                openalex = OpenAlexClient(email=oa_email, cache_file=self.cache_file)
                writer = ObsidianWriter(vault_path, folder_name)

                # Ensure tree structure is available
                if not self.tree_data:
                    self.log("Fetching collection tree structure...")
                    tree, roots = zotero.get_collection_tree()
                    self.tree_data = tree
                else:
                    tree = self.tree_data

                # --- STEP 1: Fetch Papers from Zotero ---
                self.set_progress(0, 100, "Step 1/3: Fetching papers from Zotero...")
                self.log("Step 1/3: Fetching papers from Zotero...")

                if is_all:
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
                self.after(0, lambda: self.stat_papers.configure(text=str(total_papers)))
                self.after(0, lambda: self.stat_doi.configure(text=str(doi_papers)))

                self.log(f"Step 1 Complete: Found {len(papers)} collections, {total_papers} papers ({doi_papers} with DOI)")
                self.set_progress(35, 100, f"Step 1 Complete: {total_papers} papers collected")

                # --- STEP 2: OpenAlex Citation Network Analysis ---
                self.log("\nStep 2/3: Querying OpenAlex and mapping citation network...")
                cites, cited_by, all_papers = openalex.build_citation_network(
                    papers,
                    log_callback=self.log,
                    progress_callback=lambda c, t, m: self.set_progress(35 + int((c/t)*45), 100, m)
                )

                if self.stop_requested:
                    self.log("Process cancelled by user.")
                    return

                edges = sum(len(v) for v in cites.values())
                connected = sum(1 for d in all_papers if cites.get(d) or cited_by.get(d))

                self.after(0, lambda: self.stat_edges.configure(text=str(edges)))
                self.log(f"Step 2 Complete: {edges} citation links mapped ({connected}/{total_papers} papers connected)")
                self.set_progress(80, 100, f"Step 2 Complete: {edges} citation edges")

                # --- STEP 3: Generate Obsidian Markdown Notes ---
                self.log("\nStep 3/3: Writing Obsidian markdown notes...")
                created, updated = writer.write_all(
                    papers,
                    cites,
                    cited_by,
                    all_papers,
                    log_callback=self.log,
                    progress_callback=lambda c, t, m: self.set_progress(80 + int((c/t)*20), 100, m)
                )

                total_notes = created + updated
                self.after(0, lambda: self.stat_notes.configure(text=str(total_notes)))

                self.set_progress(100, 100, "✓ Citation Network successfully built!")
                self.log("\n=======================================================")
                self.log("✓ SUCCESS: Citation network notes generated!")
                self.log(f"  • Notes Written: {total_notes} (Created: {created}, Updated: {updated})")
                self.log(f"  • Citation Edges: {edges}")
                self.log(f"  • Vault Folder: {os.path.join(vault_path, folder_name)}")
                self.log("=======================================================")

                messagebox.showinfo(
                    "Network Build Complete",
                    f"Successfully generated {total_notes} Obsidian notes!\n"
                    f"Citation Links: {edges}\n\n"
                    f"You can now explore the citation graph in Obsidian."
                )

            except Exception as e:
                self.log(f"\n✗ ERROR during pipeline execution: {e}")
                self.set_progress(0, 100, "Failed with error")
                messagebox.showerror("Execution Error", f"An error occurred:\n{e}")
            finally:
                self.is_running = False
                self.after(0, lambda: self.btn_start.configure(state="normal", text="▶  Build Citation Network"))
                self.after(0, lambda: self.btn_stop.configure(state="disabled"))

        threading.Thread(target=_pipeline_worker, daemon=True).start()

    def stop_build_process(self):
        if self.is_running:
            self.stop_requested = True
            self.log("Cancellation requested. Stopping after current task...")
            self.btn_stop.configure(state="disabled")

    def open_obsidian_folder(self):
        vault_path = self.entry_vault_path.get().strip() or os.getenv("OBSIDIAN_VAULT_PATH", "").strip()
        folder_name = self.entry_folder_name.get().strip() or os.getenv("CITATION_NETWORK_FOLDER", "Citation Network")
        target = os.path.join(vault_path, folder_name) if vault_path else ""

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
            messagebox.showinfo("Vault Directory", "Obsidian Vault directory path not found.")


# ----------------------------------------------------------------------
# Application Entry Point
# ----------------------------------------------------------------------
def main():
    app = CitationNetworkGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
