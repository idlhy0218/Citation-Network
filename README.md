<div align="center">
  <img src="assets/logo.png" width="160" alt="Citation Network Logo" />
  <h1>Citation Network Builder</h1>
  <p>
    <img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/version-1.2.0-8E7CC3?style=flat-square" alt="Version">
    <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square" alt="Platform">
  </p>
  <p>
    <b>Analyze citation relationships in your Zotero library with OpenAlex, generate linked Obsidian notes,<br>and explore an interactive 2D citation graph with deep links back to desktop Zotero.</b>
  </p>
</div>

---

## Quick Start (3 Steps)

### Step 1: Install Python & Dependencies
1. Download and install **Python 3.9+** from [python.org](https://python.org).
   > [!IMPORTANT]
   > On Windows, check the box **"Add python.exe to PATH"** at the bottom of the installer.
2. Open your terminal in the project folder and run:
   ```bash
   pip install -r requirements.txt
   ```

### Step 2: Configure `.env` (Only 3 Settings)
Duplicate `.env.example` and rename it to `.env`. Fill in these 3 lines:

```ini
ZOTERO_USER_ID=1234567                   # Your numeric ID from https://www.zotero.org/settings/keys
ZOTERO_API_KEY=your_private_key_here     # Create a key at https://www.zotero.org/settings/keys
OBSIDIAN_VAULT_PATH=C:\Users\Name\Vault  # Absolute path to your Obsidian Vault
```

### Step 3: Run the App
- **Windows**: Double-click **`run.bat`**
- **Or via Terminal**:
  ```bash
  python main.py
  ```

---

## How to Use the GUI (4 Panels)

The app features a wide 4-column layout where each panel can be resized or collapsed using the top header buttons:

```
[Collections]          [Console & Run]       [Graph View]            [Citation Index]
+--------------------+---------------------+-----------------------+---------------------+
| 1. Select Folder   | 2. Click Build      | 3. Explore Graph      | 4. Inspect & Zotero |
|                    |                     |                       |                     |
| - My Library       | [Build Network]     | - Drag nodes (spring) | - Paper details     |
|   ├─ AI Papers     | - Real-time logs    | - Zoom & pan          | - Cites [1], [2]... |
|   └─ Biology       | - Progress bar      | - Settings & Palette  | - [Open in Zotero]  |
+--------------------+---------------------+-----------------------+---------------------+
```

1. **Panel 1: Collections (Left)**
   - Click to select the Zotero folder you want to analyze (or choose **`My Library`** for all papers).
2. **Panel 2: Console & Run (Center-Left)**
   - Click **`Build Citation Network`**. Watch the real-time progress bar and log terminal.
3. **Panel 3: Graph View (Center-Right)**
   - View your citation network rendered in high definition.
   - **Navigate**: Mouse wheel to zoom, drag background to pan.
   - **Interact**: Drag any node to pull connected papers via elastic physics springs.
   - **Customize**: Click **`Settings & Palette`** to adjust Node Size, Link Distance, Repel Force, or pick custom colors from the 2D spectrum picker.
4. **Panel 4: Citation Index (Right)**
   - Click the **`Citation Index`** button in the top header to toggle this panel.
   - Displays the selected paper's outgoing references (**Cites**) and incoming citations (**Cited By**) in numbered cards (`[1]`, `[2]`, ...).
   - Click any card to hop directly to that paper in the graph.
   - Click **`Open in Zotero`** to immediately focus and highlight the paper in desktop Zotero!

---

## Viewing in Obsidian

Notes are automatically organized inside your vault under a folder matching your Zotero collection name:

1. Open your vault in **Obsidian**.
2. Press `Ctrl + G` (or `Cmd + G` on Mac) to open **Graph View**.
3. In Graph View settings, set the filter to `path:"[Your Collection Name]"`.
4. Turn on **Arrows** under Display settings to see citation flow (`A ──> B` means paper A cites paper B).
5. Inside each note, click `[Open in Zotero]` to jump back to the desktop reference.

---

## Helpful Tips & FAQ

- **Don't use Obsidian?** No problem! Uncheck **`Generate Obsidian Notes`** in the GUI (or run `python main.py --cli --no-obsidian` in terminal) to use the app as a standalone 2D citation graph visualizer without writing any markdown files.
- **Do papers need DOIs?** Yes, OpenAlex matches citations via DOIs. Papers with DOIs in Zotero will automatically connect.
- **Can I re-run on the same folder?** Yes! Re-running safely updates citations. Any personal notes written below the auto-generated section in Obsidian are preserved.
- **Is my data safe?** Yes. Your `.env` API keys stay entirely on your local machine and are never shared.
- **Prefer the command line?** Run `python main.py --cli` for interactive terminal mode.

---

## License

MIT License. Free for academic and personal research use.
