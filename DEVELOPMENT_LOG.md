# Neonatology Dashboard — Development Log

> This file tracks every change made to the dashboard and all planned enhancements.
> Keep it updated whenever new features are added or reverted.

---

## Current Version: v5

| Version | Feature | Date | Files Changed |
|---------|---------|------|---------------|
| v5 | Semantic Scholar API key support | 2026-05-01 | `fetch_pubmed.py`, `update-pubmed.yml` |
| v4 | Batch B: citations, OA badges, abstracts, h-index | 2026-05-01 | `fetch_pubmed.py`, `index.html` |
| v3 | GitHub Sync UI (one-click admin commit) | 2026-05-01 | `index.html` |
| v2 | Exclusion persistence fix (`_blocked` field) | 2026-05-01 | `fetch_pubmed.py`, `index.html` |
| v1 | Baseline — original project | — | — |

---

## Version History & Revert Instructions

### v5 — Semantic Scholar API Key *(current)*
**What it does:** Reads `SS_API_KEY` from environment variable and passes it as `x-api-key` header. Raises rate limit from ~1 req/s (unauthenticated) to 10 req/s. Optional — script still works without it.

**Setup (one-time):**
1. Request free key: https://www.semanticscholar.org/product/api
2. GitHub repo → Settings → Secrets and variables → Actions → New repository secret
3. Name: `SS_API_KEY` / Value: your key

**Files changed:**
- `scripts/fetch_pubmed.py`: added `SS_API_KEY = os.environ.get("SS_API_KEY", "")` after imports; added `if SS_API_KEY: headers["x-api-key"] = SS_API_KEY` in `ss_get()`
- `.github/workflows/update-pubmed.yml`: added `env: SS_API_KEY: ${{ secrets.SS_API_KEY }}` block under the fetch step

**To revert v5:** Remove those 3 additions. Everything else stays.

---

### v4 — Batch B Data Enrichment
**What it does:** Fetches and displays scholarly impact metrics per faculty and per paper.

**New data in `publications.json`:**
- Faculty level: `hIndex` (int), `citationCount` (int)
- Paper level: `abstract` (string), `openAccessUrl` (string URL or null), `citationCount` (int)

**New UI elements:**
- Faculty cards (division overview): teal `h-index N` badge
- Scholar profile stats row: 6 cells now (added **h-index** + **Citations**)
- Paper cards: green **Open Access** badge (links to PDF), **Cited N×** count, **▸ Abstract** expandable toggle

**Also fixed in v4:**
- Retry logic with exponential backoff (5s → 10s → 20s) on 429 rate-limit errors
- Safety fallback: if all API calls fail and cached data exists, keep cache instead of wiping
- UTF-8 encoding on all file reads/writes (was broken on Windows with accented author names)

**Files changed:**
- `scripts/fetch_pubmed.py`: `PAPER_FIELDS`, `get_author_stats()`, `parse_paper()`, author stats block in `main()`, output entry fields, encoding fixes, retry logic, fallback logic
- `index.html`: 5 new CSS classes, 2 new stats-row cells in HTML, faculty card JS, paper item templates (both admin/non-admin), `showScholar()` stats population, `escapeHtml()`, `toggleAbstract()`

**To revert v4 UI only** (keep backend data but remove UI elements):
- Remove `.pub-tag-oa`, `.pub-citations`, `.pub-abstract*`, `.card-hindex` CSS blocks from `index.html`
- Remove `<div id="sv-hindex">` and `<div id="sv-citations">` cells from scholar stats row HTML
- Remove `hIndex` line from faculty card in `renderDivisionView()`
- Remove `oaBadge`, `citeBadge`, `abstractBlock` from both paper item templates
- Remove the 2 `sv-hindex`/`sv-citations` lines from `showScholar()`
- Remove `escapeHtml()` and `toggleAbstract()` functions

**To revert v4 backend** (stop fetching new fields):
- Remove `,abstract,openAccessPdf,citationCount` from `PAPER_FIELDS`
- Remove `get_author_stats()` function
- Remove `abstract`, `openAccessUrl`, `citationCount` from `parse_paper()` return dict
- Remove the h-index/citationCount stats block from `main()` loop
- Remove `hIndex`/`citationCount` from output entry

---

### v3 — GitHub Sync UI
**What it does:** Adds a teal "↑ Sync to GitHub" button to the admin bar. One click commits `publications.json` (with `_blocked` exclusions) directly to the GitHub repo via the GitHub Contents API. No more download-and-commit workflow.

**How to use:**
1. Log in as admin
2. Delete wrong papers
3. Click **↑ Sync to GitHub**
4. First time: enter GitHub PAT (`repo` or `public_repo` scope) + repo name (auto-detected from URL)
5. Token is stored in `sessionStorage` only (cleared when tab closes)
6. Button shows `✓ Synced` on success, `✗ Sync failed` with console error on failure
7. GitHub Pages redeploys automatically (~2 min after sync)

**Files changed:** `index.html` only
- CSS: `.admin-bar-sync`, `.admin-bar-sync:hover`, `.admin-bar-sync:disabled`
- HTML admin bar: `<button id="gh-sync-bar-btn">`
- HTML modal: `<div id="gh-sync-modal">` with PAT + repo inputs
- JS functions: `getGhConfig`, `saveGhConfig`, `detectGhRepo`, `showGhSyncModal`, `closeGhSyncModal`, `githubSync`, `saveAndSync`, `buildPublicationsPayload`, `utf8ToBase64`, `doGitHubSync`
- Exclusions modal sub-text updated to reference sync button

**To revert v3:**
- Remove 3 CSS lines (`.admin-bar-sync` block)
- Remove `<button id="gh-sync-bar-btn">` from admin bar
- Remove `<div id="gh-sync-modal">` modal
- Remove all 10 GitHub sync JS functions
- Restore exclusions modal text: *"To make them permanent for all users, copy the JSON below into `data/faculty.json` → `blocked_pmids` and commit."*

---

### v2 — Exclusion Persistence Fix
**What it does:** Admin-deleted papers were re-appearing after every weekly re-fetch because exclusions only lived in browser localStorage and `faculty.json` was rarely updated. Fixed by storing a `_blocked` array inside `publications.json` itself — which IS committed weekly.

**How the fix works:**
1. Admin deletes paper → goes to `localStorage`
2. Admin clicks **↑ Sync to GitHub** (v3) or **Export JSON** → `_blocked` written to `publications.json`
3. Weekly `fetch_pubmed.py` run reads `_blocked` from existing `publications.json`
4. Merges with `faculty.blocked_pmids` from `faculty.json`
5. Applies combined blocklist → deleted papers stay gone
6. Writes `_blocked` back to new `publications.json` → persists forever

**Files changed:**
- `scripts/fetch_pubmed.py`: `load_persisted_blocked()` function, `blocked |= persisted_blocked.get(fid, set())`, `_blocked` in both output entry locations
- `index.html`: `exportAdminData()` now uses `allFaculty.forEach` (not `FACULTY.forEach`), adds `_blocked` to publications.json export

**To revert v2:**
- Remove `load_persisted_blocked()` from `fetch_pubmed.py`
- Remove `blocked |= persisted_blocked.get(fid, set())`
- Remove `_blocked` from both output entry locations
- In `exportAdminData()`: change `allFaculty.forEach` back to `FACULTY.forEach`, remove `_blocked` logic

---

## Planned Enhancements

### Batch A — Data Reliability (fetch_pubmed.py + GitHub Actions) ✅ PARTIALLY DONE
- [x] **Retry + backoff** on 429/5xx errors — done in v4
- [x] **API key support** — done in v5
- [ ] **Author ID fallback warning** — when name-search is used, log a WARNING showing matched author's institution + paper count so it's visible in GitHub Actions logs for review
- [ ] **Delta commit messages** — instead of generic "Auto-update publications 2026-04-21", show "+3 new papers (Chalak: +2, Mir: +1)"

### Batch B — Richer Data ✅ DONE in v4
- [x] Citation counts per paper and faculty
- [x] h-index per faculty
- [x] Open Access badges
- [x] Abstract expandable toggle

### Batch C — Workflow Polish (low effort)
- [ ] **Twice-weekly runs** — change cron from `0 2 * * 0` to `0 2 * * 0,3` (add Wednesday). Zero additional cost.
- [ ] **Stale data indicator** — if `last_updated.txt` > 14 days old, show a red "Data may be outdated" pill in the header

### Batch D — User Features (index.html, high value)
- [ ] **Global publication search** — search by title/keyword/author across ALL faculty simultaneously. Client-side, zero infra. Add search box to header area.
- [ ] **CSV / Excel export** — one-click export of publication list for grants, reports, annual reviews. Add button to division view and individual faculty view.

### Batch E — Admin UX
- [ ] **Change password from UI** — currently requires manual SHA-256 computation in browser console. Add "Change password" dialog that computes the hash client-side.
- [ ] **Post-edit reminder** — show a subtle banner "Changes are browser-local — sync to GitHub to make them permanent" after any admin deletion/addition.

### Lower Priority
- [ ] **Collaboration network** — co-authorship heatmap or force-directed graph from `authors` arrays in `publications.json`
- [ ] **Mobile layout** — optimized bottom-nav for phones; current layout collapses but isn't mobile-first
- [ ] **Light mode toggle** — CSS variable swap; currently dark-only
- [ ] **Per-faculty lazy loading** — split `publications.json` into per-faculty files (~40KB each instead of one ~2MB file) to speed up initial load

---

## Known Issues / Watch List

| Issue | Status | Notes |
|-------|--------|-------|
| Semantic Scholar author ID mismatches (wrong papers from same-name authors) | **Active** | Use admin Delete + Sync to GitHub to exclude wrong papers. Consider adding SS author ID for affected faculty. |
| Rate limiting without API key | **Mitigated** | Retry logic added in v4. API key (v5) eliminates this. |
| `publications.json` file size | **Monitor** | ~700KB before abstracts; ~1.5–2MB with abstracts. GitHub Pages serves gzip-compressed (~400–600KB on wire). |
| localStorage not shared across browsers | **By design** | Admin exclusions/photos are browser-local until synced via GitHub Sync (v3). |
| Admin password is SHA-256 of "admin" | **Change before going public** | Use browser console: `crypto.subtle.digest('SHA-256', new TextEncoder().encode('yourpassword')).then(b => console.log([...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,'0')).join('')))` — paste result into `ADMIN_HASH` in `index.html` |

---

## Architecture Quick Reference

```
data/faculty.json          ← roster config (edit to add/remove faculty)
data/publications.json     ← AUTO-GENERATED weekly (do not hand-edit)
data/last_updated.txt      ← ISO timestamp of last successful run
scripts/fetch_pubmed.py    ← data fetcher (Python 3, stdlib only)
.github/workflows/
  update-pubmed.yml        ← GitHub Actions cron (weekly Sun 2am UTC)
index.html                 ← entire frontend: HTML + CSS + JS (single file)
```

**Weekly update cycle:**
1. GitHub Actions triggers (Sunday 2am UTC, or manual dispatch)
2. `fetch_pubmed.py` reads `faculty.json`, calls Semantic Scholar API
3. Writes `publications.json` + `last_updated.txt`
4. Auto-commits and pushes → GitHub Pages redeploys (~5–15 min total)

**faculty.json key fields:**
```json
{
  "id": "lastname-firstname",
  "semantic_scholar_id": "123456",        // find at semanticscholar.org/author/...
  "blocked_pmids": ["11111", "22222"],    // permanent exclusions
  "manual_pmids": [],                     // manually pinned papers
  "focus": ["Tag1", "Tag2"]              // shown in division themes widget
}
```
