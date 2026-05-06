# UT Southwestern Neonatology Research Dashboard

A free, auto-updating scholarly research dashboard for your division — powered by PubMed and hosted on GitHub Pages. Zero servers, zero cost, zero maintenance after initial setup.

---

## What this is

- A **static website** that reads from `data/publications.json`
- A **GitHub Action** that runs every Sunday, queries PubMed for each faculty member using author disambiguation, and commits fresh data
- An **admin mode** (password-protected) for managing faculty and curating publications directly in the browser

---

## Deployment in 5 steps (~30 minutes)

### Step 1 — Create a GitHub repository

1. Go to [github.com](https://github.com) and sign in (free account is fine)
2. Click **New repository**
3. Name it: `neonatology-research-dashboard`
4. Set to **Public** (required for free GitHub Pages)
5. Click **Create repository**

### Step 2 — Upload this folder

Drag and drop all files into the new repo, or use:
```bash
git init
git remote add origin https://github.com/YOUR_USERNAME/neonatology-research-dashboard.git
git add .
git commit -m "Initial commit"
git push -u origin main
```

### Step 3 — Enable GitHub Pages

1. Go to your repo → **Settings** → **Pages**
2. Under "Source", select **Deploy from a branch**
3. Select **main** branch, **/ (root)** folder
4. Click **Save**
5. Your site will be live at: `https://YOUR_USERNAME.github.io/neonatology-research-dashboard`

### Step 4 — Add your faculty to `data/faculty.json`

Each faculty member entry:
```json
{
  "id": "lastname-firstname",
  "name": "First Last",
  "pubmed_query": "Last F[Author] AND (Neonatal OR NICU)",
  "seed_pmid": "12345678",
  "blocked_pmids": [],
  "title": "Professor",
  "photo": "",
  "email": "email@utsouthwestern.edu",
  "focus": ["Area 1", "Area 2"]
}
```

| Field | Required | Description |
|---|---|---|
| `id` | Yes | Unique slug: `lastname-firstname` |
| `name` | Yes | Full display name |
| `seed_pmid` | **Strongly recommended** | Any PubMed ID from a paper by this person. Used by the author disambiguation API for precise results. Without it, falls back to text search. |
| `pubmed_query` | Fallback | Used only when `seed_pmid` is absent or disambiguation returns nothing |
| `blocked_pmids` | No | Array of PMID strings to permanently exclude from this faculty member's list |
| `title`, `photo`, `email`, `focus` | No | Display metadata |

**Finding a seed PMID:** Search the faculty member's name on [pubmed.ncbi.nlm.nih.gov](https://pubmed.ncbi.nlm.nih.gov), open any of their papers, and copy the number from the URL (e.g., `pubmed.ncbi.nlm.nih.gov/38901234/` → seed PMID is `38901234`).

### Step 5 — Trigger the first data fetch

1. Go to your repo → **Actions** tab
2. Click **Auto-Update PubMed Data**
3. Click **Run workflow** → **Run workflow**
4. Wait ~5–10 minutes
5. Refresh your GitHub Pages URL — data will appear

After this, the fetch runs automatically every Sunday at 2am UTC.

---

## Author Disambiguation

Instead of relying solely on text-based PubMed queries (which match anyone with the same name), the fetch script uses the [NCBI BioNLP Author Disambiguation API](https://www.ncbi.nlm.nih.gov/research/bionlp/APIs/authors/). Given a seed PMID and author name, the API returns a machine-learning-curated list of PubMed IDs attributed to that specific person.

**Fetch pipeline per faculty member:**
1. If `seed_pmid` is set → query disambiguation API → get exact PMID list
2. Else → fall back to `pubmed_query` text search
3. Remove any PMIDs listed in `blocked_pmids`
4. Fetch full article metadata for remaining PMIDs

---

## Admin Mode

The dashboard includes a password-protected admin mode for managing content without editing files.

### Logging in

Click the **Admin** button in the top-right of the header. The default password is `admin`. **Change it before deploying** (see below).

### Changing the admin password

Open your browser's developer console and run:
```javascript
crypto.subtle.digest('SHA-256', new TextEncoder().encode('yourpassword'))
  .then(b => console.log([...new Uint8Array(b)].map(x => x.toString(16).padStart(2,'0')).join('')))
```
Copy the output and replace the `ADMIN_HASH` constant near the top of the `<script>` section in `index.html`.

### What admin mode can do

| Feature | How |
|---|---|
| **Exclude a paper** | In any faculty's Papers tab, hover a paper → click the **✕** button |
| **Add a faculty member** | Click **+ Add Faculty** in the admin bar → enter name + seed PMID → preview → confirm |
| **Remove a custom faculty member** | In the sidebar, hover the faculty row → click **✕** |
| **View / restore excluded papers** | Click **Excluded Papers** in the admin bar |
| **Export data to files** | Click **Export JSON** — downloads updated `faculty.json` and `publications.json` |

### How exclusions work

Exclusions are **immediate but local** — they are stored in your browser's `localStorage` and take effect right away. To make them permanent for all users:

1. In admin mode, click **Export JSON**
2. This downloads updated `faculty.json` and `publications.json`
3. Commit both files to your GitHub repo
4. GitHub Pages redeploys automatically

For `faculty.json` exclusions only, you can also manually add PMIDs to the `blocked_pmids` array for that faculty member and commit. The next GitHub Action run will respect the list.

### How added faculty work

Faculty added via **+ Add Faculty** are stored in `localStorage`. They persist across page refreshes on the same browser. To make them permanent:

1. Click **Export JSON** after adding the faculty member
2. Commit the downloaded `faculty.json` and `publications.json` to GitHub
3. The GitHub Action will re-fetch their publications on the next weekly run

---

## Adding faculty photos

**Option A — Upload in the dashboard** (easiest, browser-local)
Click a faculty member → **Photo** tab → upload image. Stored in `localStorage`.

**Option B — GitHub repo** (permanent, visible to all users)
1. Add `.jpg` files to the `/photos/` folder: `photos/lastname-firstname.jpg`
2. Update `data/faculty.json` with the path: `"photo": "photos/lastname-firstname.jpg"`
3. Commit and push

---

## How auto-updating works

```
Every Sunday 2am UTC
       ↓
GitHub Action runs scripts/fetch_pubmed.py
       ↓
For each faculty member with seed_pmid:
  → Queries NCBI Author Disambiguation API
  → Gets ML-curated list of their PubMed IDs
  → Falls back to text search if no seed_pmid
  → Removes any blocked_pmids
       ↓
Fetches full article metadata from PubMed
       ↓
Writes data/publications.json + data/last_updated.txt
       ↓
Commits to repo → GitHub Pages auto-deploys
       ↓
Dashboard shows fresh, accurate data ✓
```

No API keys needed. All APIs used (PubMed E-utilities and NCBI BioNLP) are free and open.

---

## Customizing

**Change update frequency:** Edit `.github/workflows/update-pubmed.yml`
```yaml
# Daily at midnight:
- cron: '0 0 * * *'
# Monthly on 1st:
- cron: '0 2 1 * *'
```

**Change the institution name:** Edit the `<title>` tag and `<h1>` in `index.html`.

**Add a custom domain:** In GitHub Pages settings, add a CNAME. Your IT team can point a subdomain like `research.neonatology.utsouthwestern.edu` to GitHub Pages.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| "Error loading data" | Open from a web server, not `file://` — run `python -m http.server 8080` locally |
| No publications showing | Run the GitHub Action manually (Step 5 above) |
| Wrong papers for a faculty member | Add a `seed_pmid` to their entry in `faculty.json` and re-run the Action. For one-off bad papers, use admin mode to exclude them. |
| GitHub Action failing | Go to **Actions** tab → click the failed run → read the error log |
| Admin password forgotten | Open `index.html`, find `ADMIN_HASH`, replace with a new hash generated from the browser console (see above) |
| Custom faculty missing after refresh | They are in `localStorage` — export and commit `faculty.json` to make permanent |

---

## Files

```
/
├── index.html                    ← The entire dashboard (single file)
├── data/
│   ├── faculty.json              ← Faculty roster with seed PMIDs and blocked lists
│   ├── publications.json         ← Auto-generated by GitHub Action (do not edit manually)
│   └── last_updated.txt          ← Timestamp of last fetch
├── photos/
│   └── (add faculty photos here)
├── scripts/
│   └── fetch_pubmed.py           ← PubMed fetcher (runs in GitHub Actions)
└── .github/
    └── workflows/
        └── update-pubmed.yml     ← Schedule and CI config
```
