"""
src/obsidian_writer.py
Writes paper metadata + citation relationships as Obsidian markdown notes.
"""
import os
import re
from datetime import datetime


class ObsidianWriter:

    def __init__(self, vault_path: str, citation_folder: str = ''):
        self.vault_path      = vault_path
        self.citation_folder = citation_folder or ''
        self.base_path       = os.path.join(vault_path, self.citation_folder) if self.citation_folder else vault_path
        self.today           = datetime.now().strftime('%Y-%m-%d')

    # ------------------------------------------------------------------ #
    # Filename / link utilities
    # ------------------------------------------------------------------ #
    @staticmethod
    def sanitize_filename(name: str) -> str:
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', name)
        name = name.strip('. ')
        return name[:200] or 'untitled'

    def get_paper_filename(self, paper: dict) -> str:
        citekey = paper.get('citekey', '').strip()
        if citekey:
            return self.sanitize_filename(citekey) + '.md'
        return self.sanitize_filename(paper.get('title', 'untitled')[:60]) + '.md'

    def _wiki_link(self, paper: dict, for_table: bool = False) -> str:
        r"""
        Returns a wiki-link.
        for_table=True escapes the alias separator as \| to prevent
        breaking markdown table columns.
        """
        filename = self.get_paper_filename(paper).replace('.md', '')
        authors  = paper.get('authors', [])
        year     = paper.get('year', '')

        if authors:
            last  = authors[0].split(',')[0].strip()
            et_al = ' et al.' if len(authors) > 1 else ''
            label = f"{last}{et_al} ({year})" if year else last
        else:
            label = filename

        sep = r'\|' if for_table else '|'
        return f"[[{filename}{sep}{label}]]"

    @staticmethod
    def _plain_text_reference(paper: dict) -> str:
        """Returns a plain text representation of the paper (no wiki-link)"""
        authors = paper.get('authors', [])
        year    = paper.get('year', '')
        title   = paper.get('title', 'Untitled')
        citekey = paper.get('citekey', '')

        if authors:
            last  = authors[0].split(',')[0].strip()
            et_al = ' et al.' if len(authors) > 1 else ''
            author_year = f"{last}{et_al} ({year})" if year else last
        else:
            author_year = year or 'Unknown'

        ref = f"{author_year} - {title}"
        if citekey:
            ref += f" (`{citekey}`)"
        return ref

    # ------------------------------------------------------------------ #
    # YAML helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _ys(val: str) -> str:
        return val.replace('"', "'")

    def _fmt_authors(self, authors: list[str]) -> str:
        if not authors:
            return '  - "Unknown"'
        return '\n'.join(f'  - "{self._ys(a)}"' for a in authors)

    def _fmt_tags(self, collection_name: str, tags: list[str]) -> str:
        lines = [f'  - zotero/{self.sanitize_filename(collection_name).replace(" ", "-")}']
        for tag in tags:
            clean = re.sub(r'[^a-zA-Z0-9_\-/]', '_', tag).strip('_')
            if clean:
                lines.append(f'  - {clean}')
        return '\n'.join(lines)

    # ------------------------------------------------------------------ #
    # Paper note
    # ------------------------------------------------------------------ #
    def create_paper_note(
        self,
        paper: dict,
        collection_name: str,
        cites_papers: list[dict],
        cited_by_papers: list[dict],
    ) -> tuple[str, str]:

        title          = paper.get('title', 'Untitled')
        authors        = paper.get('authors', [])
        year           = paper.get('year', '')
        journal        = paper.get('journal', '')
        doi            = paper.get('doi', '')
        citekey        = paper.get('citekey', '')
        abstract       = paper.get('abstract', '')
        tags           = paper.get('tags', [])
        citation_count = paper.get('citation_count', '')
        zotero_key     = paper.get('zotero_key', '')

        doi_url     = f"https://doi.org/{doi}" if doi else ''
        authors_str = '; '.join(authors) if authors else ''
        filename    = self.get_paper_filename(paper)

        # -- YAML frontmatter ------------------------------------------
        yaml_block = '\n'.join([
            '---',
            f'title: "{self._ys(title)}"',
            'authors:',
            self._fmt_authors(authors),
            f'year: {year or "null"}',
            f'journal: "{self._ys(journal)}"',
            f'doi: "{doi}"',
            f'doi_url: "{doi_url}"',
            f'citekey: "{citekey}"',
            'tags:',
            self._fmt_tags(collection_name, tags),
            f'citation_count: {citation_count if citation_count != "" else "null"}',
            f'zotero_key: "{zotero_key}"',
            f'collection: "{self._ys(collection_name)}"',
            'type: paper',
            f'created: {self.today}',
            '---',
        ])

        # -- Citation relationship section -----------------------------
        if cites_papers:
            cites_section = "### Cites (within collection)\n" + \
                '\n'.join(f"- {self._wiki_link(p)}" for p in cites_papers)
        else:
            cites_section = "### Cites (within collection)\nNone"

        if cited_by_papers:
            cited_by_section = "### Cited by (within collection)\n" + \
                '\n'.join(f"- {self._plain_text_reference(p)}" for p in cited_by_papers)
        else:
            cited_by_section = "### Cited by (within collection)\nNone"

        # -- Abstract --------------------------------------------------
        abstract_section = f"\n## Abstract\n{abstract}\n" if abstract else ''

        # -- Footer links ----------------------------------------------
        links = []
        if doi_url:
            links.append(f"[DOI]({doi_url})")
        if zotero_key:
            links.append(f"[Open in Zotero](zotero://select/library/items/{zotero_key})")
        links_str = ' | '.join(links)

        content = f"""{yaml_block}

# {title}

## Bibliography

| Field | Value |
|-------|-------|
| **Authors** | {authors_str} |
| **Year** | {year} |
| **Journal** | {journal} |
| **DOI** | {f'[{doi}]({doi_url})' if doi else 'N/A'} |
| **Citation Count** | {citation_count if citation_count != '' else 'N/A'} |
| **Citekey** | `{citekey}` |

## Citation Network
> [!info] Auto-generated on {self.today} via OpenAlex

{cites_section}

{cited_by_section}
{abstract_section}
---
{links_str}
"""
        return filename, content

    # ------------------------------------------------------------------ #
    # Collection index (_Index.md, created inside the collection folder only)
    # ------------------------------------------------------------------ #
    def _create_collection_index(
        self,
        collection_name: str,
        papers: list[dict],
        cites: dict,
        cited_by: dict,
    ) -> str:

        sorted_papers = sorted(papers, key=lambda p: p.get('year', ''), reverse=True)

        rows = []
        for p in sorted_papers:
            doi        = p.get('doi', '')
            link       = self._wiki_link(p, for_table=True)
            year       = p.get('year', '')
            journal    = p.get('journal', '')[:35]
            n_cites    = len(cites.get(doi, []))
            n_cited_by = len(cited_by.get(doi, []))
            cc         = p.get('citation_count', 'N/A')
            if cc == '' or cc is None:
                cc = 'N/A'
            rows.append(f"| {link} | {year} | {journal} | {n_cites} | {n_cited_by} | {cc} |")

        table = (
            "| Paper | Year | Journal | Cites | Cited by | Citation Count |\n"
            "|-------|:----:|---------|:-----:|:--------:|:--------------:|\n"
            + '\n'.join(rows)
        )

        return f"""---
type: collection-index
collection: "{self._ys(collection_name)}"
paper_count: {len(papers)}
updated: {self.today}
---

# {collection_name}

> **Papers**: {len(papers)} | **Updated**: {self.today}
> Cites: papers within this collection cited by this paper | Cited by: papers within this collection that cite this paper

## Papers

{table}

---
*Auto-generated by Citation Network script*
"""

    # ------------------------------------------------------------------ #
    # Main write entry point
    # ------------------------------------------------------------------ #
    def write_all(
        self,
        papers_by_collection: dict,
        cites: dict,
        cited_by: dict,
        all_papers_by_doi: dict,
        progress_callback=None,
        log_callback=None
    ) -> tuple[int, int]:

        os.makedirs(self.base_path, exist_ok=True)
        created = updated = 0
        total_papers = sum(len(col_data['papers']) for col_data in papers_by_collection.values())
        processed_count = 0

        for col_name, col_data in papers_by_collection.items():
            papers     = col_data['papers']
            col_folder = os.path.join(self.base_path, self.sanitize_filename(col_name))
            os.makedirs(col_folder, exist_ok=True)

            print(f"\n[{col_name}]  ({len(papers)} papers)")
            if log_callback:
                log_callback(f"Writing collection notes: [{col_name}] ({len(papers)} papers)")

            for paper in papers:
                processed_count += 1
                if progress_callback:
                    progress_callback(processed_count, total_papers, f"Writing note [{processed_count}/{total_papers}]")

                doi = paper.get('doi', '')
                cites_papers    = [all_papers_by_doi[d] for d in cites.get(doi, [])    if d in all_papers_by_doi]
                cited_by_papers = [all_papers_by_doi[d] for d in cited_by.get(doi, []) if d in all_papers_by_doi]

                filename, content = self.create_paper_note(
                    paper, col_name, cites_papers, cited_by_papers
                )

                filepath = os.path.join(col_folder, filename)
                exists   = os.path.exists(filepath)

                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)

                if exists:
                    updated += 1
                    print(f"  updated: {filename}")
                else:
                    created += 1
                    print(f"  created: {filename}")

            # Collection index
            idx_content = self._create_collection_index(col_name, papers, cites, cited_by)
            idx_path    = os.path.join(col_folder, '_Index.md')
            with open(idx_path, 'w', encoding='utf-8') as f:
                f.write(idx_content)
            print(f"  index:   _Index.md")

        done_msg = f"Done. Created: {created} | Updated: {updated} notes in Obsidian"
        print(f"\n{'='*50}\n{done_msg}\nPath: {self.base_path}")
        if log_callback:
            log_callback(f"✓ {done_msg}")
            log_callback(f"  Vault path: {self.base_path}")

        return created, updated
