"""
src/core/zotero_client.py
Fetches collection and paper metadata from Zotero Web API.
"""
import re
from pyzotero import zotero
from tqdm import tqdm


class ZoteroClient:
    """Zotero API client"""

    PAPER_TYPES = {
        'journalArticle', 'conferencePaper', 'book',
        'bookSection', 'preprint', 'thesis', 'report', 'manuscript',
    }

    def __init__(self, library_id: str, api_key: str, library_type: str = 'user'):
        self.zot = zotero.Zotero(library_id, library_type, api_key)

    # ------------------------------------------------------------------ #
    # Collections
    # ------------------------------------------------------------------ #
    def get_collections(self) -> list[dict]:
        """Returns all collections across all pages: [{key, name, parent_key}]"""
        try:
            raw = self.zot.everything(self.zot.collections())
        except Exception:
            raw = self.zot.collections()
        return [
            {
                'key': c['key'],
                'name': c['data']['name'],
                'parent_key': c['data'].get('parentCollection') or None,
            }
            for c in raw
        ]

    def get_collection_tree(self) -> tuple[dict, list]:
        """
        Returns the collection tree structure.

        Returns:
            tree  : {key: {name, parent_key, children: [key, ...]}}
            roots : List of root collection keys (those without parents)
        """
        cols = self.get_collections()
        tree = {c['key']: {**c, 'children': []} for c in cols}

        roots = []
        for key, col in tree.items():
            pk = col['parent_key']
            if pk and pk in tree:
                tree[pk]['children'].append(key)
            else:
                roots.append(key)

        # Sort alphabetically A-Z (case-insensitive)
        roots.sort(key=lambda k: tree[k]['name'].lower())
        for col in tree.values():
            col['children'].sort(key=lambda k: tree[k]['name'].lower())

        return tree, roots

    def get_papers_in_subtree(
        self,
        collection_key: str,
        tree: dict,
        progress_callback=None,
        log_callback=None
    ) -> dict:
        """
        Recursively collects papers from the selected collection and all its subcollections.

        Returns:
            {col_name: {key, parent_key, papers: [...]}, ...}
        """
        result = {}
        col = tree[collection_key]

        if log_callback:
            log_callback(f"Fetching Zotero collection: {col['name']}")

        # Papers in the current collection
        papers = self.get_items_in_collection(collection_key)
        if papers:
            result[col['name']] = {
                'key': collection_key,
                'parent_key': col['parent_key'],
                'papers': papers,
            }
            if log_callback:
                log_callback(f"  - Found {len(papers)} papers in '{col['name']}'")

        # Recursively fetch subcollections
        for child_key in col['children']:
            result.update(
                self.get_papers_in_subtree(
                    child_key,
                    tree,
                    progress_callback=progress_callback,
                    log_callback=log_callback
                )
            )

        return result

    # ------------------------------------------------------------------ #
    # Item Retrieval
    # ------------------------------------------------------------------ #
    def get_items_in_collection(self, collection_key: str) -> list[dict]:
        """Returns a list of metadata for paper items in a collection"""
        raw_items = self.zot.everything(self.zot.collection_items(collection_key))
        papers = []
        for item in raw_items:
            if item['data'].get('itemType') in self.PAPER_TYPES:
                meta = self._extract_metadata(item)
                if meta:
                    papers.append(meta)
        return papers

    def get_all_collections_with_papers(
        self,
        progress: bool = True,
        key_filter: str = '',
        progress_callback=None,
        log_callback=None
    ) -> dict:
        """
        Returns all collections (or a specific collection by key) and their papers.
        key_filter: Collection key ('' to fetch all)
        """
        collections = self.get_collections()

        if key_filter:
            collections = [c for c in collections if c['key'] == key_filter]
            if not collections:
                return {}

        result = {}
        total = len(collections)
        iterator = tqdm(collections, desc="Fetching collections") if (progress and not progress_callback) else collections
        for i, col in enumerate(iterator):
            if log_callback:
                log_callback(f"Fetching Zotero collection [{i+1}/{total}]: {col['name']}")
            if progress_callback:
                progress_callback(i + 1, total, f"Fetching collection: {col['name']}")

            papers = self.get_items_in_collection(col['key'])
            if papers:
                result[col['name']] = {
                    'key': col['key'],
                    'parent_key': col['parent_key'],
                    'papers': papers,
                }
                if log_callback:
                    log_callback(f"  - Found {len(papers)} papers in '{col['name']}'")

        return result

    # ------------------------------------------------------------------ #
    # Metadata Extraction
    # ------------------------------------------------------------------ #
    def _extract_metadata(self, item: dict) -> dict | None:
        data = item['data']

        title = data.get('title', '').strip()
        if not title:
            return None

        # Normalize DOI
        doi = data.get('DOI', '').strip().lower()
        doi = doi.replace('https://doi.org/', '').replace('http://doi.org/', '').strip('/')

        # citekey (Better BibTeX Extra field)
        citekey = self._parse_citekey(data.get('extra', ''))

        # Auto-generate citekey if not present
        if not citekey:
            citekey = self._generate_citekey(data)

        # Authors
        creators = data.get('creators', [])
        authors = []
        for c in creators:
            if c.get('creatorType') in ('author', 'editor'):
                last = c.get('lastName', '').strip()
                first = c.get('firstName', '').strip()
                name = f"{last}, {first}".strip(', ')
                if name:
                    authors.append(name)

        # Year
        date_str = data.get('date', '')
        year = re.search(r'\d{4}', date_str)
        year = year.group(0) if year else ''

        # Journal/Publisher
        journal = (
            data.get('publicationTitle')
            or data.get('bookTitle')
            or data.get('publisher')
            or ''
        ).strip()

        return {
            'zotero_key': item['key'],
            'title': title,
            'authors': authors,
            'year': year,
            'journal': journal,
            'doi': doi,
            'citekey': citekey,
            'abstract': data.get('abstractNote', '').strip(),
            'tags': [t['tag'] for t in data.get('tags', [])],
            'item_type': data.get('itemType', ''),
            'volume': data.get('volume', ''),
            'issue': data.get('issue', ''),
            'pages': data.get('pages', ''),
        }

    @staticmethod
    def _parse_citekey(extra: str) -> str | None:
        """Parses Better BibTeX Citation Key from the Extra field"""
        for line in extra.splitlines():
            line = line.strip()
            lower = line.lower()
            if lower.startswith('citation key:'):
                return line.split(':', 1)[1].strip()
            if lower.startswith('citekey:'):
                return line.split(':', 1)[1].strip()
        return None

    @staticmethod
    def _generate_citekey(data: dict) -> str:
        """Generates citekey if missing: lastname_year_journalabbrev"""
        creators = data.get('creators', [])
        last_name = ''
        for c in creators:
            if c.get('creatorType') == 'author':
                last_name = re.sub(r'[^a-zA-Z]', '', c.get('lastName', '')).lower()
                break

        date_str = data.get('date', '')
        year_match = re.search(r'\d{4}', date_str)
        year = year_match.group(0) if year_match else 'xxxx'

        journal = re.sub(r'[^a-zA-Z]', '', data.get('publicationTitle', ''))[:8].lower()

        parts = [p for p in [last_name, year, journal] if p]
        return '_'.join(parts) if parts else 'unknown'
