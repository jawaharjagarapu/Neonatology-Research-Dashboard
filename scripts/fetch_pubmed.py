#!/usr/bin/env python3
"""
Semantic Scholar Faculty Publications Fetcher
Runs weekly via GitHub Actions to auto-update publications.json

Author disambiguation strategy (in priority order):
  1. semantic_scholar_id in faculty.json — direct, exact author lookup.
     Find it at semanticscholar.org: search the faculty member, open their
     profile, and copy the numeric ID from the URL.
     e.g. semanticscholar.org/author/J.-Smith/1234567 → ID is "1234567"
  2. Fallback: Semantic Scholar author name search — picks the top result.

Blocked paper IDs (faculty.blocked_pmids in faculty.json) are always excluded.
Values can be PubMed PMIDs or Semantic Scholar paper IDs (both are checked).

Manually added papers (faculty.manual_pmids / faculty.manual_ss_ids) are always
fetched individually and merged in, regardless of author-ID settings.
These fields are populated automatically when the admin uses "Export JSON" after
adding papers via the dashboard's "Add paper by PMID" feature.
"""

import json
import time
import datetime
import urllib.request
import urllib.parse
import os

# Optional API key — set SS_API_KEY env var (or GitHub Actions secret) for 10× rate limit.
# Get a free key at: https://www.semanticscholar.org/product/api
SS_API_KEY   = os.environ.get("SS_API_KEY", "")

SS_BASE      = "https://api.semanticscholar.org/graph/v1"
MAX_RESULTS  = 200
PAPER_FIELDS = (
    "paperId,title,authors,year,venue,journal,"
    "externalIds,publicationTypes,publicationDate,"
    "abstract,openAccessPdf,citationCount"
)


# ─── SEMANTIC SCHOLAR API ─────────────────────────────────────────────────────

def ss_get(url: str) -> dict | None:
    """GET a Semantic Scholar API URL with exponential-backoff retry on 429."""
    headers = {"Accept": "application/json"}
    if SS_API_KEY:
        headers["x-api-key"] = SS_API_KEY
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 5 * (2 ** attempt)   # 5 s, 10 s, 20 s
                print(f"  Rate limited (429) — retrying in {wait}s…")
                time.sleep(wait)
            else:
                print(f"  API error: HTTP {e.code}")
                return None
        except Exception as e:
            print(f"  API error: {e}")
            return None
    print(f"  API error: rate limit persists after 3 attempts")
    return None


def get_papers_by_author_id(author_id: str) -> list[dict]:
    """Fetch all papers for a known Semantic Scholar author ID (paginated)."""
    all_papers = []
    offset     = 0
    limit      = 100

    while len(all_papers) < MAX_RESULTS:
        params = urllib.parse.urlencode({
            "fields": PAPER_FIELDS,
            "limit":  limit,
            "offset": offset,
        })
        data = ss_get(f"{SS_BASE}/author/{author_id}/papers?{params}")
        if not data:
            break
        page = data.get("data", [])
        all_papers.extend(page)
        if len(page) < limit:   # last page
            break
        offset += limit
        time.sleep(0.5)

    return all_papers[:MAX_RESULTS]


def search_author_id(name: str) -> str | None:
    """Search by name; return the best-match Semantic Scholar author ID or None."""
    params = urllib.parse.urlencode({
        "query":  name,
        "fields": "authorId,name,affiliations,paperCount",
        "limit":  5,
    })
    data = ss_get(f"{SS_BASE}/author/search?{params}")
    if not data:
        return None
    results = data.get("data", [])
    if not results:
        return None
    # First result is the closest match
    found = results[0]
    matched_name = found.get('name', '').encode('ascii', 'replace').decode('ascii')
    print(f"  Name search matched: {matched_name} "
          f"(ID: {found.get('authorId')}, {found.get('paperCount', '?')} papers)")
    return found.get("authorId")


def get_author_stats(author_id: str) -> dict:
    """Fetch h-index and total citation count for a Semantic Scholar author ID."""
    data = ss_get(f"{SS_BASE}/author/{author_id}?fields=hIndex,citationCount")
    if not data:
        return {}
    return {
        "hIndex":        data.get("hIndex"),
        "citationCount": data.get("citationCount"),
    }


def get_paper_by_id(paper_id: str) -> dict | None:
    """Fetch a single paper by PMID (prefix PMID:) or Semantic Scholar paper ID."""
    # Bare digits → treat as PMID
    lookup_id = f"PMID:{paper_id}" if paper_id.isdigit() else paper_id
    data = ss_get(f"{SS_BASE}/paper/{urllib.parse.quote(lookup_id, safe='')}?fields={PAPER_FIELDS}")
    return data  # None on error


# ─── ARTICLE PARSING ─────────────────────────────────────────────────────────

def parse_paper(paper: dict) -> dict:
    """Map a Semantic Scholar paper record to the canonical article dict."""
    external_ids = paper.get("externalIds") or {}
    pmid         = str(external_ids.get("PubMed", ""))
    doi          = external_ids.get("DOI", "") or ""
    paper_id     = paper.get("paperId", "")

    # Primary display ID: PMID when available (dashboard links to PubMed), else SS ID
    record_id = pmid if pmid else paper_id

    authors_raw  = paper.get("authors", [])
    author_names = [a.get("name", "") for a in authors_raw[:6]]
    if len(authors_raw) > 6:
        author_names.append("et al.")

    year = str(paper.get("year") or "") or "Unknown"

    # Journal: prefer structured journal.name, fall back to venue string
    journal_obj = paper.get("journal") or {}
    journal     = journal_obj.get("name", "") or paper.get("venue", "") or ""

    title     = (paper.get("title") or "").rstrip(".")
    pub_types = paper.get("publicationTypes") or []

    joined = " ".join(t.lower() for t in pub_types)
    tags   = []
    if "review" in joined:
        tags.append("Review")
    if any(k in joined for k in ("clinicaltrial", "clinical trial", "randomizedcontrolledtrial")):
        tags.append("Clinical Trial")

    abstract  = (paper.get("abstract") or "").strip() or None
    oa_data   = paper.get("openAccessPdf") or {}
    oa_url    = (oa_data.get("url") or None) if isinstance(oa_data, dict) else None
    cite_cnt  = paper.get("citationCount")  # int or None

    return {
        "pmid":          record_id,   # kept as "pmid" for dashboard compatibility
        "paper_id":      paper_id,    # SS paper ID (used for blocklist matching)
        "title":         title,
        "authors":       author_names,
        "journal":       journal,
        "year":          year,
        "doi":           doi,
        "tags":          tags,
        "pub_types":     pub_types,
        "abstract":      abstract,
        "openAccessUrl": oa_url,
        "citationCount": cite_cnt,
    }


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def load_existing(root_dir: str) -> dict:
    """Load publications.json if it exists; return empty dict otherwise."""
    path = os.path.join(root_dir, "data/publications.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_persisted_blocked(existing: dict) -> dict[str, set]:
    """Extract per-faculty blocked-ID sets from the _blocked field in publications.json.

    The admin UI writes this field on Export JSON so that exclusions made in the
    browser survive a full re-fetch even when faculty.json has not been updated.
    """
    return {
        fid: set(str(p) for p in entry.get("_blocked", []))
        for fid, entry in existing.items()
    }


def main():
    print("Loading faculty roster…")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir   = os.path.dirname(script_dir)

    with open(os.path.join(root_dir, "data/faculty.json"), encoding="utf-8") as f:
        faculty = json.load(f)

    # Load what we already have so this run only adds new papers
    existing = load_existing(root_dir)

    # Per-faculty blocked sets persisted by the admin UI inside publications.json.
    # These accumulate exclusions made in the browser without requiring faculty.json
    # to be manually updated and committed.
    persisted_blocked = load_persisted_blocked(existing)

    output = {}

    for member in faculty:
        fid           = member["id"]
        name          = member["name"]
        ss_id_raw     = member.get("semantic_scholar_id", "").strip()
        ss_author_ids = [i.strip() for i in ss_id_raw.split(",") if i.strip()]

        # Merge two blocklist sources:
        #   1. faculty.json blocked_pmids  — managed via repo commits
        #   2. publications.json _blocked  — written by admin UI Export JSON
        blocked = set(str(p) for p in member.get("blocked_pmids", []))
        blocked |= persisted_blocked.get(fid, set())

        print(f"\nFetching: {name}")

        existing_articles = existing.get(fid, {}).get("publications", [])

        papers = []

        # ── Step 1: use known Semantic Scholar author ID(s) ──────────────────
        if ss_author_ids:
            # IDs are authoritative → full re-fetch so wrong/stale papers are cleared
            print(f"  Full re-fetch (authoritative SS ID set — discarding old cache)")
            for ss_author_id in ss_author_ids:
                print(f"  Using Semantic Scholar author ID: {ss_author_id}")
                fetched = get_papers_by_author_id(ss_author_id)
                print(f"  Retrieved {len(fetched)} papers from SS")
                papers.extend(fetched)
                time.sleep(0.5)

        # ── Step 2: fallback — search by name (only when no IDs configured) ───
        else:
            print(f"  Falling back to name search: {name}")
            found_id = search_author_id(name)
            if found_id:
                time.sleep(0.5)
                papers = get_papers_by_author_id(found_id)
                print(f"  Retrieved {len(papers)} papers from SS")
                time.sleep(0.5)
            else:
                print(f"  No author found via name search")

        # ── Step 3: parse papers ──────────────────────────────────────────────
        if ss_author_ids:
            # Full re-fetch: parse all, deduplicate by ID within this run only
            seen = set()
            new_articles = []
            for p in papers:
                article = parse_paper(p)
                uid = article["pmid"] or article["paper_id"]
                if uid and uid not in seen:
                    seen.add(uid)
                    new_articles.append(article)
            print(f"  {len(new_articles)} paper(s) after dedup")

            # Safety: if every API call failed and we have cached data, keep it
            # rather than overwriting with an empty list due to transient 429s.
            if not new_articles and existing_articles:
                print(f"  WARNING: all API calls failed — keeping {len(existing_articles)} cached paper(s)")
                merged = existing_articles
            else:
                merged = new_articles
        else:
            # Incremental: only add papers not already stored
            seen = set()
            for a in existing_articles:
                if a.get("pmid"):     seen.add(a["pmid"])
                if a.get("paper_id"): seen.add(a["paper_id"])

            new_articles = []
            for p in papers:
                article = parse_paper(p)
                uid = article["pmid"] or article["paper_id"]
                if uid and uid not in seen:
                    seen.add(uid)
                    new_articles.append(article)

            if new_articles:
                print(f"  +{len(new_articles)} new paper(s) found")
            else:
                print(f"  No new papers since last run")

            # Merge: existing first (preserves any manual edits), then new
            merged = existing_articles + new_articles

        # ── Step 4: fetch manually pinned papers (manual_pmids / manual_ss_ids) ─
        manual_ids = (
            [str(p) for p in member.get("manual_pmids", [])] +
            [str(p) for p in member.get("manual_ss_ids", [])]
        )
        if manual_ids:
            # Build seen set from what we already have
            seen_for_manual = set()
            for a in merged:
                if a.get("pmid"):     seen_for_manual.add(a["pmid"])
                if a.get("paper_id"): seen_for_manual.add(a["paper_id"])
            print(f"  Fetching {len(manual_ids)} manually pinned paper(s)…")
            for mid in manual_ids:
                if mid in seen_for_manual:
                    continue  # already in the list
                paper = get_paper_by_id(mid)
                if not paper or "paperId" not in paper:
                    print(f"    Could not fetch manual ID: {mid}")
                    continue
                article = parse_paper(paper)
                article["_manual"] = True
                uid = article["pmid"] or article["paper_id"]
                if uid and uid not in seen_for_manual:
                    seen_for_manual.add(uid)
                    merged.append(article)
                    print(f"    + Manually added: {article['title'][:60]}")
                time.sleep(0.3)

        if not merged:
            entry = {"faculty_id": fid, "publications": [], "total": 0}
            if blocked:
                entry["_blocked"] = sorted(blocked)
            output[fid] = entry
            continue

        # ── Step 5: apply blocklist (PMID or SS paper_id) ────────────────────
        if blocked:
            before = len(merged)
            merged = [
                a for a in merged
                if a.get("pmid") not in blocked and a.get("paper_id", "") not in blocked
            ]
            removed = before - len(merged)
            if removed:
                print(f"  Removed {removed} blocked paper(s)")

        # Sort newest first
        merged.sort(key=lambda x: x.get("year", "0"), reverse=True)

        # Fetch h-index and citation count from Semantic Scholar author endpoint.
        # For multi-ID faculty (papers split across profiles) take the best h-index
        # found across all IDs — h-index is not additive so we never sum it.
        h_index       = None
        citation_count = None
        if ss_author_ids:
            print(f"  Fetching author impact stats…")
            best_h = -1
            for aid in ss_author_ids:
                s = get_author_stats(aid)
                h = s.get("hIndex")
                if h is not None and h > best_h:
                    best_h      = h
                    citation_count = s.get("citationCount")
                time.sleep(0.3)
            h_index = best_h if best_h >= 0 else None
            if h_index is not None:
                print(f"  h-index: {h_index}, citations: {citation_count}")

        entry: dict = {
            "faculty_id":    fid,
            "hIndex":        h_index,
            "citationCount": citation_count,
            "publications":  merged,
            "total":         len(merged),
        }
        # Persist the merged blocklist so the next re-fetch can re-apply it even
        # if faculty.json was never updated after an admin Export JSON.
        if blocked:
            entry["_blocked"] = sorted(blocked)

        output[fid] = entry
        print(f"  Total stored: {len(merged)} articles for {name}")

    # ── Write outputs ─────────────────────────────────────────────────────────
    out_path = os.path.join(root_dir, "data/publications.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {out_path}")

    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(os.path.join(root_dir, "data/last_updated.txt"), "w", encoding="utf-8") as f:
        f.write(ts)
    print(f"Last updated: {ts}")


if __name__ == "__main__":
    main()
