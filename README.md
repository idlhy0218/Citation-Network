# Citation Network Builder
![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) [![Stars](https://img.shields.io/github/stars/idlhy0218/Citation-Network?style=flat-square)](https://github.com/idlhy0218/Citation-Network/stargazers) ![Version](https://img.shields.io/badge/version-1.0.0-blue?style=flat-square)

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

### Step 0 - Fork & Clone the Repository

1. Click the **Fork** button at the top-right of this GitHub repository page to copy it to your own GitHub account.
2. Clone the repository to your local computer:
   - Using Git command:
     ```bash
     git clone https://github.com/idlhy0218/Citation-Network.git
     ```
   - Or open it using **GitHub Desktop**.


### Step 1 - Open Terminal & Install Dependencies

Open Command Prompt or PowerShell, navigate to this project folder, and install the dependencies.

> [!TIP]
> **Easy way to open terminal at the current folder (Windows)**:
> 1. Open File Explorer and navigate to this project folder (`Citation Network`).
> 2. Click the address bar at the top, clear the text, type **`cmd`**, and press **Enter**.
> 3. A Command Prompt window will open directly in this directory.

Once the terminal is open, run:

```bash
python -m pip install -r requirements.txt
```


### Step 2 - Create Config File and Set API Keys

When you first clone this repository, you only have the template config file. You need to create a `.env` file and insert your credentials.

1. In the terminal, run the following command to duplicate `.env.example` as a new `.env` file:
   - **Command Prompt (cmd)**:
     ```cmd
     copy .env.example .env
     ```
   - **PowerShell**:
     ```powershell
     cp .env.example .env
     ```
   *(Or copy `.env.example` in File Explorer and rename it to `.env`. Make sure it is not named `.env.txt`)*

2. Open the newly created `.env` file with a text editor (like Notepad) and fill in your details:

   * **ZOTERO_USER_ID**: Go to [Zotero API Settings](https://www.zotero.org/settings/keys). At the top, copy the number next to **"Your userID for API calls is XXXXXX"**.
   * **ZOTERO_API_KEY**: On the same page, click **"Create new private key"** to generate an API key.
   * **OBSIDIAN_VAULT_PATH**: The absolute path to your Obsidian Vault folder (e.g. `C:\Users\YourName\Documents\MyVault`).

```ini
# [Required] Zotero API credentials & Obsidian path
ZOTERO_USER_ID=Your Zotero User ID (digits)
ZOTERO_API_KEY=Your Zotero API Key
OBSIDIAN_VAULT_PATH=C:\Users\YourUsername\Path\To\Obsidian\Vault

# [Optional] Personalize folder name & increase request speed
CITATION_NETWORK_FOLDER=Citation Network
OPENALEX_EMAIL=your_email@domain.com
```

3. **Personalizing Your Configuration (Optional)**:
   * **Change Output Folder Name**: If you want the notes to be saved in a folder other than the default `Citation Network`, modify `CITATION_NETWORK_FOLDER` to your preferred folder name (e.g., `My Citations`).
   * **Improve OpenAlex API Speed**: If you have a large library (dozens of papers or more), add your email address in `OPENALEX_EMAIL`. OpenAlex offers a faster rate limit ("Polite Pool") for users who identify themselves via email.


### Step 3 - Test the Connection

To verify if everything is set up correctly, run:

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


## Good to Know

- Papers must have a DOI to fetch citation data. Adding DOIs in Zotero yields more connections.
- OpenAlex is a free scholastic database and does not require registration or API keys.
- Re-running the script on the same folder will update the notes. Custom comments or notes added by you will be preserved as long as you write them below the auto-generated section.
- The `.env` file contains your private API keys. It is added to `.gitignore` so it will not be uploaded to GitHub.
