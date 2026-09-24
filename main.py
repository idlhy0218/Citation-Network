"""
Citation Network Builder
========================
Version: 1.2.0

python main.py                             -> Collection selection tree
python main.py --collection "Folder Name"  -> Process folder immediately (includes subfolders)
python main.py --test                      -> Test API connections
"""
import os
import sys
import argparse
from dotenv import load_dotenv

load_dotenv()

# -- Config (Loaded from .env) -----------------------------------------
ZOTERO_USER_ID      = os.getenv('ZOTERO_USER_ID', '')
ZOTERO_API_KEY      = os.getenv('ZOTERO_API_KEY', '')
ZOTERO_LIBRARY_TYPE = os.getenv('ZOTERO_LIBRARY_TYPE', 'user')
OBSIDIAN_VAULT      = os.getenv('OBSIDIAN_VAULT_PATH', '')
OUTPUT_FOLDER       = os.getenv('CITATION_NETWORK_FOLDER', 'Citation Network')
OPENALEX_EMAIL      = os.getenv('OPENALEX_EMAIL', '')
CACHE_FILE          = os.path.join(os.path.dirname(__file__), 'cache', 'openalex_cache.json')

sys.path.insert(0, os.path.dirname(__file__))
from src.zotero_client   import ZoteroClient
from src.openalex_client import OpenAlexClient
from src.obsidian_writer import ObsidianWriter


# --------------------------------------------------------------------
def _print_tree(tree: dict, keys: list, prefix: str, numbered: list) -> None:
    """Recursively prints the collection tree and appends keys to the numbered list."""
    for i, key in enumerate(keys):
        col       = tree[key]
        is_last   = (i == len(keys) - 1)
        connector = '└── ' if is_last else '├── '
        child_pre = '    ' if is_last else '│   '

        has_children = bool(col['children'])
        marker = '📁' if has_children else '📄'

        num = len(numbered) + 1
        numbered.append(key)
        print(f"  {prefix}{connector}{num:3d}. {marker} {col['name']}")

        if has_children:
            _print_tree(tree, col['children'], prefix + child_pre, numbered)


def pick_collection(zotero: ZoteroClient) -> tuple[str, bool]:
    """
    Selects a Zotero collection using the interactive tree terminal view.

    Returns:
        (collection_key, is_subtree)
    """
    print("\nFetching Zotero collection tree...")
    tree, roots = zotero.get_collection_tree()

    numbered: list[str] = []

    print("\n" + "=" * 60)
    print("  Select a Zotero Collection")
    print("  📁 = Has subfolders (processes all descendants)")
    print("  📄 = Single collection")
    print("=" * 60)


    _print_tree(tree, roots, '', numbered)

    print("-" * 60)
    print(f"   all.  Process all collections ({len(tree)} total)")
    print("=" * 60)

    while True:
        try:
            choice = input("\nEnter number (or 'all'): ").strip()

            if choice.lower() == 'all':
                print("  -> Processing all collections")
                return '', False

            idx = int(choice) - 1
            if 0 <= idx < len(numbered):
                key  = numbered[idx]
                name = tree[key]['name']
                has_children = bool(tree[key]['children'])
                if has_children:
                    print(f"  -> '{name}' selected along with all subfolders\n")
                else:
                    print(f"  -> '{name}' selected\n")
                return key, True
            print(f"  Warning: Please enter a number between 1 and {len(numbered)}.")

        except ValueError:
            print("  Warning: Please enter a valid number or 'all'.")
        except KeyboardInterrupt:
            print("\n\nCancelled.")
            sys.exit(0)


# --------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Citation Network Builder")
    parser.add_argument('--collection', type=str, default=None,
                        help='Name of the collection to process')
    parser.add_argument('--test', action='store_true',
                        help='Test API connections')
    parser.add_argument('--cli', action='store_true',
                        help='Run in terminal CLI mode')
    parser.add_argument('--gui', action='store_true',
                        help='Run in Desktop GUI mode (default)')
    args, _ = parser.parse_known_args()

    # Launch GUI if no explicit CLI flag or collection/test arguments provided
    if not args.cli and not args.collection and not args.test:
        try:
            from gui import main as gui_main
            gui_main()
            return
        except Exception as e:
            print(f"Failed to start GUI mode ({e}). Falling back to CLI mode...")

    print("=" * 60)
    print("  Citation Network Builder (CLI Mode)")
    print("=" * 60)

    if not ZOTERO_USER_ID or not ZOTERO_API_KEY or not OBSIDIAN_VAULT:
        print("Error: ZOTERO_USER_ID, ZOTERO_API_KEY, and OBSIDIAN_VAULT_PATH must be configured in your .env file.")
        sys.exit(1)

    zotero   = ZoteroClient(ZOTERO_USER_ID, ZOTERO_API_KEY, library_type=ZOTERO_LIBRARY_TYPE)
    openalex = OpenAlexClient(email=OPENALEX_EMAIL, cache_file=CACHE_FILE)
    writer   = ObsidianWriter(OBSIDIAN_VAULT, OUTPUT_FOLDER)

    # -- Test Mode -----------------------------------------------------
    if args.test:
        print("\nTesting API connections...\n")
        try:
            cols = zotero.get_collections()
            print(f"  Zotero:    {len(cols)} collections found (Connection Successful)")
        except Exception as e:
            print(f"  Zotero:    Connection Failed: {e}")

        try:
            work = openalex.get_work_by_doi('10.1093/aje/kwu178')
            if work:
                print("  OpenAlex:  Connection Successful")
            else:
                print("  OpenAlex:  Failed to fetch test DOI (Network is OK)")
        except Exception as e:
            print(f"  OpenAlex:  Connection Failed: {e}")

        print("\nTest completed.")
        return

    # -- Collection Selection ------------------------------------------
    if args.collection is not None:
        tree, roots = zotero.get_collection_tree()
        matched = [k for k, v in tree.items() if v['name'] == args.collection]
        if not matched:
            print(f"Error: Collection '{args.collection}' not found.")
            sys.exit(1)
        collection_key = matched[0]
        print(f"\n  -> Processing collection: '{args.collection}' (includes subfolders)\n")
    else:
        tree, _ = None, None
        collection_key, _ = pick_collection(zotero)
        tree, _ = zotero.get_collection_tree()

    # -- Step 1: Collect papers from Zotero ----------------------------
    print("Fetching paper metadata from Zotero...")

    if collection_key == '':
        papers = zotero.get_all_collections_with_papers()
    else:
        papers = zotero.get_papers_in_subtree(collection_key, tree)

    if not papers:
        print("Error: No papers found in the selected collection.")
        sys.exit(1)

    total = sum(len(v['papers']) for v in papers.values())
    no_doi = sum(1 for v in papers.values() for p in v['papers'] if not p.get('doi'))
    print(f"Found {len(papers)} collections, {total} papers total")
    if no_doi:
        print(f"  Warning: {no_doi} papers without DOIs will be skipped in citation analysis.")

    # -- Step 2: Fetch OpenAlex citation network -----------------------
    cites, cited_by, all_papers = openalex.build_citation_network(papers)

    edges  = sum(len(v) for v in cites.values())
    linked = sum(1 for doi in all_papers if cites.get(doi) or cited_by.get(doi))
    print(f"\nCitation edges: {edges} | Connected papers: {linked}/{total}")

    # -- Step 3: Write Obsidian Notes ---------------------------------
    print(f"\nGenerating Obsidian notes...\n")
    writer.write_all(papers, cites, cited_by, all_papers)

    print(f"\nCompleted! Open Obsidian and view the network in Graph View.")
    print(f"Output folder: {OUTPUT_FOLDER}")


if __name__ == '__main__':
    main()
