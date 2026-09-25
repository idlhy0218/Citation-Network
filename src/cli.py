"""
src/cli.py
==========
Terminal interactive interface and CLI runner for Citation Network Builder.
"""
import os
import sys
from dotenv import load_dotenv

from src.core.zotero_client import ZoteroClient
from src.core.openalex_client import OpenAlexClient
from src.core.obsidian_writer import ObsidianWriter


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


def run_cli(args) -> None:
    """Runs the CLI processing pipeline."""
    load_dotenv()

    zotero_user_id      = os.getenv('ZOTERO_USER_ID', '')
    zotero_api_key      = os.getenv('ZOTERO_API_KEY', '')
    zotero_library_type = os.getenv('ZOTERO_LIBRARY_TYPE', 'user')
    obsidian_vault      = os.getenv('OBSIDIAN_VAULT_PATH', '')
    output_folder       = os.getenv('CITATION_NETWORK_FOLDER', 'Citation Network')
    openalex_email      = os.getenv('OPENALEX_EMAIL', '')
    
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cache_file = os.path.join(workspace_root, 'cache', 'openalex_cache.json')

    print("=" * 60)
    print("  Citation Network Builder (CLI Mode)")
    print("=" * 60)

    no_obsidian = getattr(args, 'no_obsidian', False) or (os.getenv('GENERATE_OBSIDIAN_NOTES', 'true').lower() in ('false', '0', 'no'))

    if not zotero_user_id or not zotero_api_key:
        print("Error: ZOTERO_USER_ID and ZOTERO_API_KEY must be configured in your .env file.")
        sys.exit(1)

    if not no_obsidian and not obsidian_vault:
        print("Error: OBSIDIAN_VAULT_PATH must be configured in your .env file (or run with --no-obsidian to skip note generation).")
        sys.exit(1)

    zotero   = ZoteroClient(zotero_user_id, zotero_api_key, library_type=zotero_library_type)
    openalex = OpenAlexClient(email=openalex_email, cache_file=cache_file)
    writer   = ObsidianWriter(obsidian_vault, output_folder) if not no_obsidian else None

    # -- Test Mode -----------------------------------------------------
    if getattr(args, 'test', False):
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
    if getattr(args, 'collection', None) is not None:
        tree, roots = zotero.get_collection_tree()
        matched = [k for k, v in tree.items() if v['name'] == args.collection]
        if not matched:
            print(f"Error: Collection '{args.collection}' not found.")
            sys.exit(1)
        collection_key = matched[0]
        print(f"\n  -> Processing collection: '{args.collection}' (includes subfolders)\n")
    else:
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
    if not no_obsidian and writer:
        print(f"\nGenerating Obsidian notes...\n")
        writer.write_all(papers, cites, cited_by, all_papers)
        print(f"\nCompleted! Open Obsidian and view the network in Graph View.")
        print(f"Output folder: {output_folder}")
    else:
        print(f"\nCompleted! Citation analysis mapped successfully (Obsidian notes skipped).")
        print(f"Connected papers: {linked}/{total} | Citation edges: {edges}")
