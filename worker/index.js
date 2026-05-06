const REPO = 'jawaharjagarapu/Neonatology-Research-Dashboard';
const FILE = 'data/publications.json';
const GH_API = `https://api.github.com/repos/${REPO}/contents/${FILE}`;

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, X-Sync-Secret',
};

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS });
    }

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

      // Get current file SHA (required by GitHub API to update an existing file)
      const getRes = await fetch(GH_API, { headers: ghHeaders });
      if (!getRes.ok) {
        const e = await getRes.json().catch(() => ({}));
        return json({ error: e.message || `GitHub GET ${getRes.status}` }, 502);
      }
      const { sha } = await getRes.json();

      // Commit updated file
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
