const REPO = 'jawaharjagarapu/Neonatology-Research-Dashboard';
const FILE = 'data/publications.json';
const GH_API = `https://api.github.com/repos/${REPO}/contents/${FILE}`;
const SS_API = 'https://api.semanticscholar.org/graph/v1/paper';
const SS_FIELDS = 'paperId,title,authors,year,venue,journal,externalIds,publicationTypes,publicationDate';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, X-Sync-Secret',
};

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS });
    }

    const url = new URL(request.url);

    // ── GET /lookup?id=PMID:39284927  ────────────────────────────────────────
    if (request.method === 'GET' && url.pathname === '/lookup') {
      const id = url.searchParams.get('id');
      if (!id) return json({ error: 'Missing id parameter' }, 400);

      const ssHeaders = { 'Accept': 'application/json' };
      if (env.SS_API_KEY) ssHeaders['x-api-key'] = env.SS_API_KEY;

      const ssUrl = `${SS_API}/${encodeURIComponent(id)}?fields=${encodeURIComponent(SS_FIELDS)}`;
      let ssRes;
      // Retry up to 3 times on 429 rate-limit
      for (let attempt = 0; attempt < 3; attempt++) {
        if (attempt > 0) await new Promise(r => setTimeout(r, attempt * 5000));
        ssRes = await fetch(ssUrl, { headers: ssHeaders });
        if (ssRes.status !== 429) break;
      }

      if (!ssRes.ok) {
        const msg = ssRes.status === 404
          ? 'Paper not found. Check the PMID or Semantic Scholar ID.'
          : ssRes.status === 429
            ? 'Rate limited by Semantic Scholar — please try again in 30 seconds.'
            : `Semantic Scholar error ${ssRes.status}`;
        return json({ error: msg }, ssRes.status);
      }

      const paper = await ssRes.json();
      return json(paper);
    }

    // ── POST /  — sync publications.json to GitHub ────────────────────────────
    if (request.method !== 'POST') {
      return json({ error: 'Method not allowed' }, 405);
    }

    if (request.headers.get('X-Sync-Secret') !== env.SYNC_SECRET) {
      return json({ error: 'Unauthorized' }, 401);
    }

    try {
      const { content } = await request.json();
      if (!content) return json({ error: 'Missing content' }, 400);

      const ghHeaders = {
        'Authorization': `token ${env.GITHUB_TOKEN}`,
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'UTSWNeoSync/1.0',
        'Content-Type': 'application/json',
      };

      const getRes = await fetch(GH_API, { headers: ghHeaders });
      if (!getRes.ok) {
        const e = await getRes.json().catch(() => ({}));
        return json({ error: e.message || `GitHub GET ${getRes.status}` }, 502);
      }
      const { sha } = await getRes.json();

      const today = new Date().toISOString().split('T')[0];
      const putRes = await fetch(GH_API, {
        method: 'PUT',
        headers: ghHeaders,
        body: JSON.stringify({
          message: `Admin sync: update publications.json ${today}`,
          content: btoa(unescape(encodeURIComponent(content))),
          sha,
        }),
      });

      if (!putRes.ok) {
        const e = await putRes.json().catch(() => ({}));
        return json({ error: e.message || `GitHub PUT ${putRes.status}` }, 502);
      }

      return json({ ok: true });

    } catch (err) {
      return json({ error: err.message }, 500);
    }
  },
};

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...CORS, 'Content-Type': 'application/json' },
  });
}
