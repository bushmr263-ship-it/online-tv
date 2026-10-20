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
    const parsedTarget = new URL(targetUrl);
    const originHeader = `${parsedTarget.protocol}//${parsedTarget.hostname}`;

    // ১. সঠিক Header Spoofing (যাতে সোর্স সার্ভার স্পিড কম না করে)
    const customHeaders = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
      'Accept': '*/*',
      'Referer': originHeader,
      'Origin': originHeader,
    };

    const response = await fetch(targetUrl, {
      method: req.method,
      headers: customHeaders,
      redirect: 'follow',
    });

    const contentType = response.headers.get('content-type') || '';
    const finalUrl = response.url;

    // ২. M3U8 Playlist Rewriting
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

    // ৩. TS Video Chunk / Raw Stream Handling (বাফারিং দূর করার জন্য)
    const responseHeaders = new Headers(response.headers);
    Object.keys(corsHeaders).forEach((key) => {
      responseHeaders.set(key, corsHeaders[key]);
    });

    // সঠিক কন্টেন্ট টাইপ নিশ্চিত করা
    if (targetUrl.includes('.ts')) {
      responseHeaders.set('Content-Type', 'video/mp2t');
    }

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
