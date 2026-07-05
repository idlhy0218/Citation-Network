# Citation Network Builder v1.0.1
![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) [![Stars](https://img.shields.io/github/stars/idlhy0218/Citation-Network?style=flat-square)](https://github.com/idlhy0218/Citation-Network/stargazers) ![Version](https://img.shields.io/badge/version-1.0.1-blue?style=flat-square)

This tool analyzes citation relationships between papers stored in Zotero using the free OpenAlex academic database API, and automatically converts them into linked Obsidian notes.

### Workflow

1. Zotero: Retrieves paper metadata and collection (folder) structures from your Zotero library.
2. OpenAlex: Queries the OpenAlex database using paper DOIs to determine citation relationships within the selected collections.
3. Obsidian: Generates or updates individual paper notes in your vault, complete with wiki-links. You can visualize the citation network using Obsidian's built-in Graph View.



## Prerequisites

- **Python 3.9 or higher** (https://python.org)
  - > [!IMPORTANT]
  > During Python installation, make sure to check the box **"Add python.exe to PATH"** at the bottom. If you skip this, your terminal will fail to recognize the `python` command.
- **Zotero account and API Key**
- **Obsidian** (https://obsidian.md)


## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/idlhy0218/Citation-Network.git
   cd Citation-Network
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   Duplicate `.env.example` as `.env` and configure the following required fields:
   * **ZOTERO_USER_ID**: Find your ID at [Zotero API Settings](https://www.zotero.org/settings/keys) under "Your userID for API calls".
   * **ZOTERO_API_KEY**: Create a private key at [Zotero API Settings](https://www.zotero.org/settings/keys).
   * **OBSIDIAN_VAULT_PATH**: Absolute path to your Obsidian vault.

   ```ini
   # Required Settings
   ZOTERO_USER_ID=Your_Zotero_User_ID
   ZOTERO_API_KEY=Your_Zotero_API_Key
   OBSIDIAN_VAULT_PATH=C:\Users\Username\Documents\MyVault

   # Optional Settings
   ZOTERO_LIBRARY_TYPE=user                 # Change to 'group' for group libraries
   CITATION_NETWORK_FOLDER=Citation Network  # Folder name in Obsidian Vault
   OPENALEX_EMAIL=your_email@domain.com      # Improves OpenAlex query speed
   ```

4. **Test the connection**:
   ```bash
   python main.py --test
   ```

If you see `"Zotero connection successful"` and `"OpenAlex connection successful"`, you are ready to go.


## How to Use

### Run Interactively (Recommended)

Double-click `run.bat` or run the following command in your terminal:

    python main.py

The program will display your Zotero folders in a tree structure:

    ============================================================
      Select a Zotero folder
      (Tree) = Has subfolders / (Single) = No subfolders
    ============================================================
      1.  (Single) Introduction
      2.  (Tree)   Machine Learning
          3.  (Single) Supervised Learning
          4.  (Single) Unsupervised Learning
      ...

Enter the number of the folder you want to process. Selecting a parent folder will automatically process all its subfolders.

### Run with a Specific Folder Name

    python main.py --collection "Machine Learning"

Wrap the collection name in quotation marks. Subfolders will be automatically included.

### Test Connection

    python main.py --test


## File Structure and Roles

    Citation Network/
    │
    ├── run.bat                   Execution file. Double-click to start quickly.
    │
    ├── main.py                   Entry point of the program. Handles folder selection.
    │
    ├── .env                      Configuration file for API keys and paths.
    │                             Never share this file or upload it to GitHub.
    │
    ├── requirements.txt          List of required Python libraries.
    │                             Only needs to be run once during installation.
    │
    ├── cache/
    │   └── openalex_cache.json   Cache file for OpenAlex query results.
    │                             Makes subsequent runs significantly faster.
    │
    └── src/
        ├── zotero_client.py      Retrieves paper lists and metadata from Zotero.
        ├── openalex_client.py    Fetches citation connections using OpenAlex.
        └── obsidian_writer.py    Writes paper data as markdown files to Obsidian.


## Viewing the Output

Notes are generated under the folder specified by `CITATION_NETWORK_FOLDER` in your `.env` file (defaults to `Citation Network`) inside your Obsidian Vault.

Inside each collection folder, you will find:

- `citekey.md`: Individual paper notes containing references to other papers.
- `_Index.md`: A summary table of all papers in that folder.

Open Graph View in Obsidian to see the network. You can filter the graph by entering `path:"Your Folder Name"` (e.g. `path:"Citation Network"`) in the graph filter bar to show only these citation notes.

> [!TIP]
> **Directional Citation Arrows (v1.0.1+)**: Under Obsidian Graph View settings, enable **Arrows**. The arrows point from the citing paper to the cited paper (A ──> B means paper A cites paper B). The "Cited by" section inside each note lists citing papers as plain text to prevent cluttering the graph with bidirectional arrows.


## Good to Know

- Papers must have a DOI to fetch citation data. Adding DOIs in Zotero yields more connections.
- OpenAlex is a free scholastic database and does not require registration or API keys.
- Re-running the script on the same folder will update the notes. Custom comments or notes added by you will be preserved as long as you write them below the auto-generated section.
- The `.env` file contains your private API keys. It is added to `.gitignore` so it will not be uploaded to GitHub.
