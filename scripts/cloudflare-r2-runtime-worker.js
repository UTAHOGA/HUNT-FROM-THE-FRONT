const CONTENT_TYPES = {
  '.csv': 'text/csv; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.geojson': 'application/geo+json; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.md': 'text/markdown; charset=utf-8',
};

function contentTypeFor(pathname) {
  const lower = pathname.toLowerCase();
  const extension = Object.keys(CONTENT_TYPES).find((suffix) => lower.endsWith(suffix));
  return extension ? CONTENT_TYPES[extension] : 'application/octet-stream';
}

function withCors(headers = new Headers()) {
  headers.set('Access-Control-Allow-Origin', '*');
  headers.set('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS');
  headers.set('Access-Control-Allow-Headers', 'Range, Content-Type, If-None-Match, If-Modified-Since');
  headers.set('Access-Control-Expose-Headers', 'Content-Length, Content-Range, ETag');
  return headers;
}

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: withCors() });
    }

    if (!['GET', 'HEAD'].includes(request.method)) {
      return new Response('Method not allowed', { status: 405, headers: withCors() });
    }

    const url = new URL(request.url);
    const key = decodeURIComponent(url.pathname.replace(/^\/+/, ''));
    if (!key || key.includes('..')) {
      return new Response('Not found', { status: 404, headers: withCors() });
    }

    const object = await env.DATA.get(key);
    if (!object) {
      return new Response('Not found', { status: 404, headers: withCors() });
    }

    const headers = withCors(new Headers());
    object.writeHttpMetadata(headers);
    headers.set('Content-Type', headers.get('Content-Type') || contentTypeFor(key));
    headers.set('Cache-Control', headers.get('Cache-Control') || 'public, max-age=300');
    headers.set('ETag', object.httpEtag);
    headers.set('Content-Length', object.size.toString());

    return new Response(request.method === 'HEAD' ? null : object.body, {
      status: 200,
      headers,
    });
  },
};
