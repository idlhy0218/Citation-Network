"""
src/openalex_client.py
Fetches paper citation relationships using the OpenAlex API.
- DOI -> OpenAlex Work (includes referenced_works)
- Saves results to a JSON cache to avoid duplicate API requests.
"""
import json
import os
import time

import requests
from tqdm import tqdm


class OpenAlexClient:
    BASE_URL = "https://api.openalex.org"

    def __init__(self, email: str = '', cache_file: str = 'cache/openalex_cache.json'):
        self.email = email
        self.cache_file = cache_file
        self.cache: dict = self._load_cache()

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CitationNetworkBuilder/1.2.0 (https://github.com/idlhy0218/Citation-Network)',
        })
        # Polite pool: email registration grants higher rate limit
        if email:
            self.session.params = {'mailto': email}

    # ------------------------------------------------------------------ #
    # Cache
    # ------------------------------------------------------------------ #
    def _load_cache(self) -> dict:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_cache(self) -> None:
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------ #
    # HTTP
    # ------------------------------------------------------------------ #
    def _get(self, url: str, params: dict | None = None, retries: int = 3):
        for attempt in range(retries):
            try:
                resp = self.session.get(url, params=params, timeout=20)
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code == 404:
                    return None
                if resp.status_code == 429:
                    wait = 15 * (attempt + 1)
                    print(f"\n  Rate limit encountered (429). Waiting for {wait} seconds...")
                    time.sleep(wait)
                else:
                    print(f"\n  HTTP {resp.status_code} for {url}")
                    time.sleep(2)
            except requests.exceptions.Timeout:
                print(f"\n  Timeout (Attempt {attempt+1}/{retries})")
                time.sleep(3)
            except requests.exceptions.RequestException as e:
                print(f"\n  Request error: {e}")
                time.sleep(3)
        return None

    # ------------------------------------------------------------------ #
    # DOI -> OpenAlex Work
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalize_doi(doi: str) -> str:
        doi = doi.lower().strip()
        doi = doi.replace('https://doi.org/', '').replace('http://doi.org/', '').strip('/')
        return doi

    def get_work_by_doi(self, doi: str) -> dict | None:
        """Retrieves OpenAlex Work using DOI (utilizes cache)"""
        if not doi:
            return None

        doi_norm = self._normalize_doi(doi)
        cache_key = f"doi:{doi_norm}"

        if cache_key in self.cache:
            return self.cache[cache_key]

        data = self._get(f"{self.BASE_URL}/works/doi:{doi_norm}")
        self.cache[cache_key] = data     # Store None to prevent duplicate queries
        time.sleep(0.12)                 # limit rate to ~8 req/sec
        return data

    # ------------------------------------------------------------------ #
    # Abstract reconstruction (OpenAlex inverted index -> plain text)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _reconstruct_abstract(inverted_index: dict) -> str:
        if not inverted_index:
            return ''
        word_positions: list[tuple[int, str]] = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))
        word_positions.sort(key=lambda x: x[0])
        return ' '.join(w for _, w in word_positions)

    # ------------------------------------------------------------------ #
    # Build citation network
    # ------------------------------------------------------------------ #
    def build_citation_network(
        self,
        papers_by_collection: dict,
        progress_callback=None,
        log_callback=None
    ) -> tuple[dict, dict, dict]:
        """
        Builds citation relationships from paper data grouped by collection.

        Returns:
            cites      : {doi: [doi, ...]}   - Paper DOIs cited by this paper (within collections)
            cited_by   : {doi: [doi, ...]}   - Paper DOIs that cite this paper (within collections)
            all_papers : {doi: paper_meta}   - Aggregated paper metadata keyed by DOI
        """
        # Aggregate all papers: doi -> meta
        all_papers: dict[str, dict] = {}
        for col_data in papers_by_collection.values():
            for paper in col_data['papers']:
                doi = paper.get('doi', '')
                if doi:
                    all_papers[doi] = paper

        msg = f"Querying OpenAlex for {len(all_papers)} papers..."
        print(f"\n{msg}")
        if log_callback:
            log_callback(msg)

        # Step 1: Map each DOI to OpenAlex ID
        doi_to_oa_id: dict[str, str] = {}
        oa_id_to_doi: dict[str, str] = {}
        doi_to_referenced: dict[str, list[str]] = {}

        no_doi_papers = [p for col in papers_by_collection.values()
                         for p in col['papers'] if not p.get('doi')]
        if no_doi_papers:
            skip_msg = f"Skipped {len(no_doi_papers)} papers without a DOI"
            print(f"  {skip_msg}")
            if log_callback:
                log_callback(f"  - {skip_msg}")

        doi_list = list(all_papers.keys())
        total_doi = len(doi_list)
        iterator = tqdm(doi_list, desc="OpenAlex lookup") if not progress_callback else doi_list

        for idx, doi in enumerate(iterator):
            if progress_callback:
                progress_callback(idx + 1, total_doi, f"OpenAlex query [{idx+1}/{total_doi}]: {doi}")
            
            work = self.get_work_by_doi(doi)
            if not work:
                continue

            # OpenAlex ID (e.g. "https://openalex.org/W12345" -> "W12345")
            oa_id = work.get('id', '').split('/')[-1]
            if oa_id:
                doi_to_oa_id[doi] = oa_id
                oa_id_to_doi[oa_id] = doi

            # referenced_works: OpenAlex IDs of references cited by this paper
            doi_to_referenced[doi] = [
                ref_url.split('/')[-1]
                for ref_url in work.get('referenced_works', [])
            ]

            # Augment citation count from OpenAlex
            all_papers[doi]['citation_count'] = work.get('cited_by_count', 0)

            # Augment abstract from OpenAlex if missing in Zotero
            if not all_papers[doi].get('abstract'):
                abstract_idx = work.get('abstract_inverted_index')
                if abstract_idx:
                    all_papers[doi]['abstract'] = self._reconstruct_abstract(abstract_idx)

        self._save_cache()

        # Step 2: Create citation edges based on OpenAlex IDs
        cites: dict[str, list[str]] = {doi: [] for doi in all_papers}
        cited_by: dict[str, list[str]] = {doi: [] for doi in all_papers}

        for source_doi, referenced_ids in doi_to_referenced.items():
            for ref_oa_id in referenced_ids:
                target_doi = oa_id_to_doi.get(ref_oa_id)
                if target_doi and target_doi != source_doi and target_doi in all_papers:
                    if target_doi not in cites[source_doi]:
                        cites[source_doi].append(target_doi)
                    if source_doi not in cited_by[target_doi]:
                        cited_by[target_doi].append(source_doi)

        total_edges = sum(len(v) for v in cites.values())
        found = len(doi_to_oa_id)
        stat_msg = f"OpenAlex matches: {found}/{len(all_papers)} | Citation edges: {total_edges}"
        print(f"  {stat_msg}")
        if log_callback:
            log_callback(f"✓ {stat_msg}")

        return cites, cited_by, all_papers
