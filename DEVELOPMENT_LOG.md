# Neonatology Dashboard — Development Log

> This file tracks every change made to the dashboard and all planned enhancements.
> Keep it updated whenever new features are added or reverted.

---

## Current Version: v11

| Version | Feature | Date | Files Changed |
|---------|---------|------|---------------|
| v11 | Fix hIndex/citationCount wiped on admin sync | 2026-05-06 | `index.html` |
| v10 | Chronological sort for manually added papers | 2026-05-06 | `index.html` |
| v9 | PubMed API for PMID lookup (no API key needed) | 2026-05-06 | `index.html` |
| v8 | Cloudflare Worker sync proxy (admins need no PAT) | 2026-05-06 | `index.html`, `worker/index.js`, `worker/wrangler.toml` |
| v7 | Cloudflare Pages deployment + custom URL | 2026-05-06 | — (infra only) |
| v6 | GitHub repo, Pages, monthly schedule, first-name sort, password | 2026-05-06 | `index.html`, `.github/workflows/update-pubmed.yml`, `README.md` |
| v5 | Semantic Scholar API key support | 2026-05-01 | `fetch_pubmed.py`, `update-pubmed.yml` |
| v4 | Batch B: citations, OA badges, abstracts, h-index | 2026-05-01 | `fetch_pubmed.py`, `index.html` |
| v3 | GitHub Sync UI (one-click admin commit) | 2026-05-01 | `index.html` |
| v2 | Exclusion persistence fix (`_blocked` field) | 2026-05-01 | `fetch_pubmed.py`, `index.html` |
| v1 | Baseline — original project | — | — |

---

## Version History & Revert Instructions

---

### v11 — Fix hIndex/citationCount Wiped on Admin Sync *(current)*
**What it does:** The admin "↑ Sync to GitHub" button was rebuilding `publications.json` without preserving `hIndex` and `citationCount` at the faculty level, silently wiping them on every sync. Now those fields are carried through from the loaded `PUBS` data.

**Root cause:** `buildPublicationsPayload()` in `index.html` constructed each faculty entry with only `faculty_id`, `publications`, `total`, and `_blocked` — never copying `hIndex`/`citationCount` from `PUBS[f.id]`.

**Files changed:**
- `index.html`: `buildPublicationsPayload()` — added `if (fp.hIndex != null) entry.hIndex = fp.hIndex` and same for `citationCount`

**To revert v11:** Remove the two `fp.hIndex` / `fp.citationCount` lines from `buildPublicationsPayload()`.

---

### v10 — Chronological Sort for Manually Added Papers
**What it does:** Papers manually added via the "Add paper by PMID" feature were being appended to the end of the list regardless of year. All publications (auto-fetched + manually added) are now sorted newest-first together.

**Root cause:** `getEffectivePubs()` merged base + custom arrays but never sorted the result. The backend already sorts auto-fetched papers but the merged list was not re-sorted.

**Files changed:**
- `index.html`: `getEffectivePubs()` — replaced the bare `return filtered` with `return filtered.sort((a, b) => (parseInt(b.year)||0) - (parseInt(a.year)||0))`

**To revert v10:** Remove the `.sort(...)` from `getEffectivePubs()` and restore the original return.

---

### v9 — PubMed API for PMID Lookup (No API Key Needed)
**What it does:** The "Add paper by PMID" feature was routing all lookups through the Cloudflare Worker → Semantic Scholar. Semantic Scholar rate-limits unauthenticated requests by IP, and Cloudflare's shared IPs are frequently throttled, causing "Network error" in the browser.

Now: pure numeric IDs (PMIDs) are looked up directly against **PubMed E-utilities** (`esummary.fcgi`) from the browser — completely free, no key, no CORS issues. Non-numeric Semantic Scholar paper IDs still route through the Worker.

**New function:** `_parsePubMedRecord(pmid, rec)` — parses the PubMed esummary response into the same paper object shape as `_parsePaperForDashboard()`.

**Files changed:**
- `index.html`: `lookupPaper()` — branched on `isPmid`; added `_parsePubMedRecord()`; removed `SS_PAPER_FIELDS` constant

**To revert v9:** Replace the `isPmid` branch with the original single `fetch(SYNC_WORKER_URL/lookup?id=...)` call and restore `SS_PAPER_FIELDS` constant.

---

### v8 — Cloudflare Worker Sync Proxy
**What it does:** Replaces the admin "Sync to GitHub" PAT-token modal with a zero-config button. A Cloudflare Worker holds the GitHub token server-side; admins click sync and it just works — no GitHub account, no PAT, no modal.

Also adds a `/lookup` endpoint to the Worker for Semantic Scholar paper lookups (with retry on 429), used by the Add Paper feature for non-PMID Semantic Scholar IDs.

**Architecture:**
```
Admin clicks ↑ Sync to GitHub
    ↓
Browser POSTs publications.json content to Worker
(with X-Sync-Secret header for authentication)
    ↓
Worker fetches current SHA from GitHub API
    ↓
Worker commits updated publications.json to GitHub repo
    ↓
Cloudflare Pages detects push → redeploys (~1 min)
```

**Worker secrets (set in Cloudflare dashboard):**
- `GITHUB_TOKEN` — repo-scoped PAT with `repo` + `workflow` scope
- `SYNC_SECRET` — random hex string shared with `index.html` (authenticates browser → Worker calls)
- `SS_API_KEY` — Semantic Scholar key (add when received; enables 10 req/s for lookups)

**Worker URL:** `https://utswneoresearch-sync.jawahar-jagarapu.workers.dev`

**Files changed:**
- `worker/index.js` — new file: Cloudflare Worker (POST `/` = sync, GET `/lookup` = SS paper lookup)
- `worker/wrangler.toml` — new file: Worker name + compatibility date
- `index.html`:
  - Removed GitHub sync modal HTML (`#gh-sync-modal`)
  - Removed `getGhConfig`, `saveGhConfig`, `detectGhRepo`, `showGhSyncModal`, `closeGhSyncModal`, `saveAndSync`, `doGitHubSync` functions
  - Added `SYNC_WORKER_URL` + `SYNC_SECRET` constants
  - Added `doWorkerSync()` — POSTs to Worker
  - `githubSync()` now calls `doWorkerSync()` directly

**To revert v8:** Restore the GitHub sync modal HTML and all removed JS functions from v3. Remove `SYNC_WORKER_URL`, `SYNC_SECRET`, `doWorkerSync()`. Delete `worker/` directory.

---

### v7 — Cloudflare Pages Deployment + Custom URL
**What it does:** Moves hosting from GitHub Pages (`jawaharjagarapu.github.io/Neonatology-Research-Dashboard`) to Cloudflare Pages (`utswneoresearch.pages.dev`). GitHub remains the source of truth — Cloudflare auto-deploys on every push to `main`.

**Live URLs:**
- **Dashboard:** https://utswneoresearch.pages.dev
- **Worker:** https://utswneoresearch-sync.jawahar-jagarapu.workers.dev

**Cloudflare account details:** Pages project `utswneoresearch`, Worker `utswneoresearch-sync`.
Account ID and API tokens stored in `CREDENTIALS.local.md` (local only).

**Files changed:** None (infrastructure change only — deployed via Cloudflare API)

**To revert v7:** The GitHub Pages site at `jawaharjagarapu.github.io/Neonatology-Research-Dashboard` remains active and can be used immediately. Just update `SYNC_WORKER_URL` in `index.html` to point to the Worker (or revert v8 to restore PAT-based sync).

---

### v6 — GitHub Repo, Monthly Schedule, First-Name Sort, Admin Password
**What it does:** Bundles several setup and polish changes made when the project was first published:

1. **GitHub repository created** — `jawaharjagarapu/Neonatology-Research-Dashboard` (public)
2. **GitHub Pages enabled** — served from `main` branch root
3. **Monthly auto-update** — cron changed from `0 2 * * 0` (weekly Sunday) to `0 2 1 * *` (1st of month)
4. **Faculty sorted by first name** — `FACULTY.sort()` key changed from `.split(' ').pop()` (last name) to `.split(' ')[0]` (first name); applied in 3 places: initial load, `mergeCustomFaculty()`, `confirmAddFaculty()`
5. **Admin password updated** — SHA-256 hash replaced; new password known to repo owner only
6. **README rewritten** — reflects current deployment, monthly schedule, Cloudflare sync workflow, manual trigger instructions

**Files changed:**
- `.github/workflows/update-pubmed.yml` — cron schedule
- `index.html` — faculty sort key (×3), `ADMIN_HASH`
- `README.md` — full rewrite

**To revert v6 schedule:** Change cron back to `0 2 * * 0` in `update-pubmed.yml`.
**To revert v6 sort:** Change `.split(' ')[0]` back to `.split(' ').pop()` in all 3 sort calls.
**To revert v6 password:** Compute SHA-256 of old password and update `ADMIN_HASH` in `index.html`.

---

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

### Batch A — Data Reliability ✅ DONE
- [x] **Retry + backoff** on 429/5xx errors — done in v4
- [x] **API key support** — done in v5 (SS_API_KEY); pending receipt for Worker lookup endpoint
- [ ] **Author ID fallback warning** — when name-search is used, log a WARNING showing matched author's institution + paper count so it's visible in GitHub Actions logs for review
- [ ] **Delta commit messages** — instead of generic "Auto-update publications 2026-05-01", show "+3 new papers (Chalak: +2, Mir: +1)"

### Batch B — Richer Data ✅ DONE in v4
- [x] Citation counts per paper and faculty
- [x] h-index per faculty
- [x] Open Access badges
- [x] Abstract expandable toggle

### Batch C — Workflow Polish
- [x] **Monthly runs** — changed from weekly Sunday to 1st of month (v6)
- [ ] **Stale data indicator** — if `last_updated.txt` > 45 days old, show a "Data may be outdated" pill in the header
- [ ] **SS_API_KEY in Worker** — once key is received, add as Cloudflare Worker secret (see deployment commands in `CREDENTIALS.local.md`)

### Batch D — User Features (high value)
- [ ] **Global publication search** — search by title/keyword/author across ALL faculty simultaneously. Client-side, zero infra.
- [ ] **CSV / Excel export** — one-click export for grants, reports, annual reviews.

### Batch E — Admin UX
- [ ] **Change password from UI** — add "Change password" dialog that computes SHA-256 hash client-side and writes to `ADMIN_HASH` via Worker sync
- [ ] **Post-edit reminder** — subtle banner "Changes are browser-local — sync to GitHub to make them permanent" after any admin deletion/addition
- [ ] **Add SS_API_KEY to Worker** — waiting on key approval from Semantic Scholar (applied 2026-05-06); will fix rate-limited SS ID lookups in Add Paper feature

### Lower Priority
- [ ] **Collaboration network** — co-authorship heatmap or force-directed graph from `authors` arrays in `publications.json`
- [ ] **Mobile layout** — optimized bottom-nav for phones; current layout collapses but isn't mobile-first
- [ ] **Light mode toggle** — CSS variable swap; currently dark-only
- [ ] **Per-faculty lazy loading** — split `publications.json` into per-faculty files to speed up initial load
- [ ] **Add `semantic_scholar_id` for remaining 25 faculty** — h-index/citations will not populate for faculty without this field

---

## Known Issues / Watch List

| Issue | Status | Notes |
|-------|--------|-------|
| Semantic Scholar author ID mismatches (wrong papers from same-name authors) | **Active** | Use admin Delete + Sync to GitHub to exclude wrong papers. Add `semantic_scholar_id` to `faculty.json` for permanent fix. |
| SS ID paper lookup rate-limited | **Pending fix** | Worker `/lookup` endpoint hits 429 on Cloudflare's shared IPs without SS API key. PMID lookup works fine via PubMed. Fix: add `SS_API_KEY` secret to Worker once key arrives. |
| 25 faculty missing h-index/citations | **Active** | Faculty without `semantic_scholar_id` in `faculty.json` will always show `—`. Find their IDs at semanticscholar.org and add to `faculty.json`. |
| `publications.json` file size | **Monitor** | ~1.5–2MB with abstracts. Cloudflare Pages serves gzip-compressed. |
| Admin sync previously wiped h-index data | **Fixed in v11** | `buildPublicationsPayload()` now preserves `hIndex`/`citationCount`. |
| Admin password | **Changed** | Password updated 2026-05-06. SHA-256 hash stored in `ADMIN_HASH` in `index.html`. |

---

## Architecture Quick Reference

```
data/faculty.json          ← roster config (edit to add/remove faculty)
data/publications.json     ← AUTO-GENERATED monthly (do not hand-edit)
data/last_updated.txt      ← ISO timestamp of last successful run
scripts/fetch_pubmed.py    ← data fetcher (Python 3, stdlib only)
worker/
  index.js                 ← Cloudflare Worker (sync proxy + SS lookup)
  wrangler.toml            ← Worker deployment config
.github/workflows/
  update-pubmed.yml        ← GitHub Actions cron (1st of month, 2am UTC)
index.html                 ← entire frontend: HTML + CSS + JS (single file)
```

**Live URLs:**
- Dashboard: https://utswneoresearch.pages.dev
- Cloudflare Worker: see `CREDENTIALS.local.md` (local only, not in repo)

**Monthly update cycle:**
1. GitHub Actions triggers (1st of month 2am UTC, or manual dispatch)
2. `fetch_pubmed.py` reads `faculty.json`, calls Semantic Scholar API
3. Fetches papers, h-index, citation counts, abstracts, open-access URLs
4. Writes `publications.json` + `last_updated.txt`
5. Auto-commits and pushes → Cloudflare Pages auto-redeploys (~1–2 min)

**Admin sync cycle (v8+):**
1. Admin deletes/adds papers in browser
2. Clicks **↑ Sync to GitHub**
3. Browser POSTs to Cloudflare Worker with `X-Sync-Secret` header
4. Worker commits `publications.json` to GitHub via Contents API
5. Cloudflare Pages detects push → redeploys

**Cloudflare infrastructure:** Pages project `utswneoresearch`, Worker `utswneoresearch-sync`.
Worker secrets: `GITHUB_TOKEN`, `SYNC_SECRET`, `SS_API_KEY` (pending).
See `CREDENTIALS.local.md` for account IDs, tokens, and deployment commands.

**faculty.json key fields:**
```json
{
  "id": "lastname-firstname",
  "name": "First Last",
  "semantic_scholar_id": "123456",        // find at semanticscholar.org/author/...
  "blocked_pmids": ["11111", "22222"],    // permanent exclusions
  "manual_pmids": [],                     // manually pinned papers (fetched monthly)
  "focus": ["Tag1", "Tag2"]              // shown in division themes widget
}
```
