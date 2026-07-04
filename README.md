# Citation Network Builder

This tool analyzes citation relationships between papers stored in Zotero using the free OpenAlex academic database API, and automatically converts them into linked Obsidian notes.

### Workflow

1. Zotero: Retrieves paper metadata and collection (folder) structures from your Zotero library.
2. OpenAlex: Queries the OpenAlex database using paper DOIs to determine citation relationships within the selected collections.
3. Obsidian: Generates or updates individual paper notes in your vault, complete with wiki-links. You can visualize the citation network using Obsidian's built-in Graph View.



## Prerequisites

- Python 3.9 or higher (https://python.org)
- Zotero account and API Key
- Obsidian (https://obsidian.md)


## Installation

### Step 0 - Fork & Clone the Repository

1. Click the Fork button at the top-right of this GitHub repository page to copy it to your own GitHub account.
2. Clone the repository to your local computer:
   - Using Git command:
     git clone https://github.com/idlhy0218/Citation-Network.git
   - Or open it using GitHub Desktop.


### Step 1 - Install Dependencies

Open Command Prompt or PowerShell, navigate to this folder, and run:

    python -m pip install -r requirements.txt


### Step 2 - Configure API Keys

Open the `.env` file with a text editor and update the following settings:

    ZOTERO_USER_ID=Your Zotero User ID
    ZOTERO_API_KEY=Your Zotero API Key
    OBSIDIAN_VAULT_PATH=C:\Users\YourUsername\Path\To\Obsidian\Vault

You can find or generate your Zotero User ID and API Key at https://www.zotero.org/settings/keys.

OBSIDIAN_VAULT_PATH is the absolute path to your Obsidian vault folder.

### Step 3 - Test the Connection

To verify if everything is set up correctly, run:

    python main.py --test

If you see "Zotero connection successful" and "OpenAlex connection successful", you are ready to go.


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

Notes are generated under the folder specified by `CITATION_NETWORK_FOLDER` in your `.env` file (defaults to `13. Citation Network`) inside your Obsidian Vault.

Inside each collection folder, you will find:

- `citekey.md`: Individual paper notes containing references to other papers.
- `_Index.md`: A summary table of all papers in that folder.

Open Graph View in Obsidian to see the network. You can filter the graph by entering `path:"Your Folder Name"` (e.g. `path:"13. Citation Network"`) in the graph filter bar to show only these citation notes.


## Good to Know

- Papers must have a DOI to fetch citation data. Adding DOIs in Zotero yields more connections.
- OpenAlex is a free scholastic database and does not require registration or API keys.
- Re-running the script on the same folder will update the notes. Custom comments or notes added by you will be preserved as long as you write them below the auto-generated section.
- The `.env` file contains your private API keys. It is added to `.gitignore` so it will not be uploaded to GitHub.
