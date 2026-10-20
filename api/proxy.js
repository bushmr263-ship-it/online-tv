avascript
export const config = {
  runtime: 'edge',
};

export default async function handler(req) {
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, HEAD, POST, OPTIONS',
    'Access-Control-Allow-Headers': '*',
  };

  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  const reqUrl = new URL(req.url);
  const targetUrl = reqUrl.searchParams.get('url');

  if (!targetUrl) {
    return new Response('Missing "url" parameter', { 
      status: 400, 
      headers: corsHeaders 
    });
  }

  try {
    const response = await fetch(targetUrl, {
      method: req.method,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': '*/*',
      },
      redirect: 'follow',
    });

    const contentType = response.headers.get('content-type') || '';
    const finalUrl = response.url;

    if (contentType.includes('mpegurl') || contentType.includes('m3u8') || targetUrl.includes('.m3u8')) {
      let text = await response.text();
      const baseUrl = finalUrl.substring(0, finalUrl.lastIndexOf('/') + 1);
      const proxyPrefix = `${reqUrl.origin}${reqUrl.pathname}?url=`;

      const rewrittenText = text.split('\n').map(line => {
        const trimmed = line.trim();
        if (trimmed && !trimmed.startsWith('#')) {
          if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
            return `${proxyPrefix}${encodeURIComponent(trimmed)}`;
          } else {
            return `${proxyPrefix}${encodeURIComponent(baseUrl + trimmed)}`;
          }
        }
        return line;
      }).join('\n');

      const responseHeaders = new Headers(corsHeaders);
      responseHeaders.set('Content-Type', 'application/vnd.apple.mpegurl');

      return new Response(rewrittenText, {
        status: 200,
        headers: responseHeaders,
      });
    }

    const responseHeaders = new Headers(response.headers);
    Object.keys(corsHeaders).forEach((key) => {
      responseHeaders.set(key, corsHeaders[key]);
    });

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });

  } catch (err) {
    return new Response('Proxy Error: ' + err.message, { 
      status: 500, 
      headers: corsHeaders 
    });
  }
}   
