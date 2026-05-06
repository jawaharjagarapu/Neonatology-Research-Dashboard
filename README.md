# UT Southwestern Neonatology Research Dashboard

A live, auto-updating scholarly research dashboard for the UTSW Division of Neonatology — powered by Semantic Scholar and hosted on GitHub Pages. Zero servers, zero cost.

**Live site:** https://jawaharjagarapu.github.io/Neonatology-Research-Dashboard/

---

## What this is

- A **static website** (`index.html`) that reads from `data/publications.json`
- A **GitHub Action** that runs on the 1st of every month, queries Semantic Scholar for each faculty member, and commits fresh data automatically
- An **admin mode** (password-protected) for curating publications and syncing changes directly to GitHub from the browser

---

## Repository structure

```
/
├── index.html                    ← Entire dashboard (HTML + CSS + JS, single file)
├── data/
│   ├── faculty.json              ← Faculty roster with Semantic Scholar IDs and blocked lists
│   ├── publications.json         ← Auto-generated monthly (do not hand-edit)
│   └── last_updated.txt          ← Timestamp of last successful fetch
├── scripts/
│   └── fetch_pubmed.py           ← Data fetcher (runs in GitHub Actions)
└── .github/
    └── workflows/
        └── update-pubmed.yml     ← Monthly cron schedule and CI config
```

---

## Auto-update schedule

Publications refresh automatically on the **1st of every month at 2am UTC** via GitHub Actions.

### How it works

```
1st of month, 2am UTC
       ↓
GitHub Action runs scripts/fetch_pubmed.py
       ↓
For each faculty member:
  → Queries Semantic Scholar API (using semantic_scholar_id if set)
  → Falls back to name-based text search if no ID
  → Removes any blocked_pmids + admin-deleted papers
  → Fetches citations, h-index, open-access URLs, abstracts
       ↓
Writes data/publications.json + data/last_updated.txt
       ↓
Commits to repo → GitHub Pages redeploys (~5 min)
       ↓
Dashboard shows fresh data ✓
```

### Trigger a manual update

You can run the fetch at any time without waiting for the monthly schedule:

1. Go to the repo → **Actions** tab
2. Click **Auto-Update Publications (Semantic Scholar)** in the left sidebar
3. Click **Run workflow** → **Run workflow**
4. Wait ~5–10 minutes for the run to complete
5. Refresh the live site — new data will appear

### Change the update frequency

Edit the cron line in `.github/workflows/update-pubmed.yml`:

```yaml
# Monthly on the 1st (current setting):
- cron: '0 2 1 * *'

# Weekly every Sunday:
- cron: '0 2 * * 0'

# Daily at midnight:
- cron: '0 0 * * *'
```

---

## Admin mode

### Logging in

Click the lock icon / **Admin** button in the top-right of the dashboard header and enter the admin password.

### What admin mode can do

| Feature | How |
|---|---|
| **Exclude a paper** | In a faculty member's Papers tab, hover a paper → click **✕** |
| **Add a faculty member** | Click **+ Add Faculty** in the admin bar → enter name + Semantic Scholar ID → confirm |
| **Remove a faculty member** | Hover the faculty row in the sidebar → click **✕** |
| **View / restore excluded papers** | Click **Excluded Papers** in the admin bar |
| **Sync changes to GitHub** | Click **↑ Sync to GitHub** in the admin bar (see below) |
| **Export data as files** | Click **Export JSON** — downloads `faculty.json` and `publications.json` |

### Syncing changes to GitHub

Admin deletions and additions are initially **browser-local** (stored in `localStorage`). To make them permanent for all users:

1. In admin mode, click **↑ Sync to GitHub** in the admin bar
2. Enter your **GitHub Personal Access Token** (needs `repo` + `workflow` scope)
   - Create one at: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
3. The **Repository** field auto-detects from the URL (`jawaharjagarapu/Neonatology-Research-Dashboard`)
4. Click **Save & Sync Now**
5. The button shows `✓ Synced` on success — GitHub Pages redeploys in ~2 minutes

> The token is stored in `sessionStorage` only and is cleared when the browser tab closes.

### Changing the admin password

**Option A — Via Claude Code (recommended)**
Share your new password with Claude Code and it will compute the SHA-256 hash and push the update automatically.

**Option B — Manually via browser console**
1. Open browser DevTools → **Console** tab
2. Run (replace `yourpassword`):
   ```javascript
   crypto.subtle.digest('SHA-256', new TextEncoder().encode('yourpassword'))
     .then(b => console.log([...new Uint8Array(b)].map(x => x.toString(16).padStart(2,'0')).join('')))
   ```
3. Copy the 64-character hash output
4. Open `index.html`, find the `ADMIN_HASH` constant, and replace the hash string
5. Commit and push to GitHub

---

## Managing faculty

### faculty.json entry structure

```json
{
  "id": "lastname-firstname",
  "name": "First Last",
  "semantic_scholar_id": "1234567",
  "pubmed_query": "Last F[Author] AND Neonatal",
  "seed_pmid": "38901234",
  "blocked_pmids": [],
  "title": "Associate Professor",
  "photo": "",
  "email": "email@utsouthwestern.edu",
  "focus": ["Research Area 1", "Research Area 2"]
}
```

| Field | Required | Description |
|---|---|---|
| `id` | Yes | Unique slug: `lastname-firstname` |
| `name` | Yes | Full display name |
| `semantic_scholar_id` | **Strongly recommended** | Found in the URL at semanticscholar.org/author/Name/**123456**. Enables precise author matching. |
| `seed_pmid` | Fallback | Any PubMed ID by this person — used for NCBI author disambiguation if no Semantic Scholar ID |
| `pubmed_query` | Fallback | Text search used only when both above are absent |
| `blocked_pmids` | No | PMIDs to permanently exclude (wrong-author papers, etc.) |
| `title`, `photo`, `email`, `focus` | No | Display metadata |

Faculty are displayed **alphabetically by last name** throughout the dashboard.

### Adding faculty photos

**Option A — In the dashboard** (browser-local)
Click a faculty member → **Photo** tab → upload image.

**Option B — Via GitHub repo** (permanent, visible to all users)
1. Add image to `/photos/` folder: `photos/lastname-firstname.jpg`
2. Set `"photo": "photos/lastname-firstname.jpg"` in `faculty.json`
3. Commit and push

---

## Semantic Scholar API key (optional)

An API key raises the rate limit from ~1 req/s to 10 req/s, significantly speeding up monthly fetches.

1. Request a free key at: https://www.semanticscholar.org/product/api
2. Go to repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
3. Name: `SS_API_KEY` / Value: your key

The fetch script works without it — the key is optional.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Dashboard shows "Error loading data" | Open from a web server, not `file://` — run `python -m http.server 8080` locally |
| No publications showing | Trigger the GitHub Action manually (see above) |
| Wrong papers for a faculty member | Add their `semantic_scholar_id` to `faculty.json` and re-run the Action. For individual bad papers, use admin mode to exclude them and sync. |
| GitHub Action failing | Go to **Actions** tab → click the failed run → read the error log |
| Admin password forgotten | Open `index.html`, find `ADMIN_HASH`, replace with a new hash (see Changing the admin password above) |
| Sync to GitHub fails | Verify the PAT has `repo` + `workflow` scopes and hasn't expired |
| Excluded papers reappear after monthly update | Make sure you clicked **↑ Sync to GitHub** after deleting — the `_blocked` list in `publications.json` must be committed to survive the next fetch |
