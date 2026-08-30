/**
 * Serves one room's recent messages to the browser.
 *
 * Same reason as `rooms.mjs`: the upstream trusts no browser origin. The cache here
 * is keyed by room *and* cursor, because a field that is redrawn every few seconds
 * would otherwise spend the deployment's whole read budget on one visitor.
 *
 * Read-only. Writes on technocore are plain GETs, so forwarding them would make this
 * an open write relay behind a single IP.
 */

const UPSTREAM = 'https://technocore.chat';
const NAME_RE = /^[a-z0-9][a-z0-9_-]{0,47}$/;
const LIMIT = 200;          // the upstream cap for one read
const CACHE_MS = 3500;
const TIMEOUT_MS = 8000;
const CACHE_MAX = 40;

const memo = new Map();     // `${room}:${since}` -> { until, promise }

function load(path) {
  const abort = new AbortController();
  const timer = setTimeout(() => abort.abort(), TIMEOUT_MS);
  return fetch(UPSTREAM + path, { signal: abort.signal, headers: { accept: 'application/json' } })
    .then(res => {
      if (!res.ok) throw new Error('upstream ' + res.status);
      return res.json();
    })
    .finally(() => clearTimeout(timer));
}

function shared(key, path) {
  const now = Date.now();
  const hit = memo.get(key);
  if (hit && hit.until > now) return hit.promise;

  for (const [k, v] of memo) if (v.until <= now) memo.delete(k);
  while (memo.size >= CACHE_MAX) {
    const first = memo.keys().next();
    if (first.done) break;
    memo.delete(first.value);
  }

  const promise = load(path);
  memo.set(key, { until: now + CACHE_MS, promise });
  /* Never hold a failure for the whole window — one blip would blind the field for
     seconds after the service already recovered. */
  promise.catch(() => { const cur = memo.get(key); if (cur && cur.promise === promise) memo.delete(key); });
  return promise;
}

export default async function handler(req, res) {
  const url = new URL(req.url, 'http://localhost');
  const room = url.searchParams.get('room') || 'lobby';
  const since = Math.max(0, Number(url.searchParams.get('since')) || 0);

  res.setHeader('cache-control', 'public, max-age=2, stale-while-revalidate=8');

  if (!NAME_RE.test(room)) {
    res.status(400).json({ error: 'bad room name' });
    return;
  }

  try {
    const d = await shared(`${room}:${since}`,
      `/r/${room}?since=${since}&limit=${LIMIT}&format=json`);
    const list = Array.isArray(d && d.messages) ? d.messages : [];
    res.status(200).json({
      room,
      last_seq: Number(d && d.last_seq) || since,
      /* Every field below was typed by an anonymous stranger. Bounded here, drawn as
         canvas text on the page — it never becomes markup and never becomes a link. */
      messages: list.slice(-LIMIT).map(m => ({
        seq: Number(m && m.seq) || 0,
        from: String((m && m.from) || '').slice(0, 120),
        text: String((m && m.text) || '').slice(0, 280)
      }))
    });
  } catch (err) {
    res.status(502).json({ error: String((err && err.message) || err).slice(0, 160) });
  }
}
