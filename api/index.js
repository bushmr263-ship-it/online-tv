// ===================================================
// সিক্রেট আইডি (প্রয়োজনে পরিবর্তন করুন)
// ===================================================
const EXPIRE_CODE = "48436844"; 

// মূল M3U প্লেলিস্ট URL
const PLAYLIST_URL = 'https://raw.githubusercontent.com/bushmr263-ship-it/online-tv/refs/heads/main/playlist.m3u';
// ===================================================

export default async function handler(req, res) {
  // CORS হেডার
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', '*');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  const host = req.headers.host;
  const protocol = req.headers['x-forwarded-proto'] || 'https';
  const requestUrl = req.url || '';

  // যদি শুধু রুট ডোমেইন ভিজিট করা হয় (কোনো প্যারামিটার বা পাথ ছাড়া)
  if (!req.query.url && requestUrl === '/') {
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    return res.status(200).send(`
      <!DOCTYPE html>
      <html lang="bn">
      <head>
          <meta charset="UTF-8">
          <title>SHAWON TV Proxy</title>
          <style>
              body { background: #121212; color: #fff; font-family: Arial, sans-serif; text-align: center; padding-top: 100px; }
              h1 { color: #f39c12; }
          </style>
      </head>
      <body>
          <h1>SHAWON TV Proxy Server is Running!</h1>
          <p>Use your playlist link or stream URL parameter to watch.</p>
      </body>
      </html>
    `);
  }

  // ---------------------------------------------------------
  // ১. M3U প্লেলিস্ট রিকোয়েস্ট 
  // ---------------------------------------------------------
  if (!req.query.url && (requestUrl.includes('.m3u') || requestUrl.includes('playlist-expire'))) {
    
    // সিকিউরিটি কোড যাচাইকরণ
    if (EXPIRE_CODE && !requestUrl.includes(EXPIRE_CODE)) {
      return res.status(403).json({ error: 'Access Denied: Invalid or Expired ID' });
    }

    try {
      const response = await fetch(PLAYLIST_URL, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
      });

      if (!response.ok) {
        return res.status(response.status).json({ error: 'Failed to fetch playlist' });
      }

      const content = await response.text();
      const baseUrl = response.url; 

      const lines = content.split('\n');
      const rewrittenLines = lines.map(line => {
        const trimmed = line.trim();
        if (trimmed && !trimmed.startsWith('#')) {
          try {
            const absUrl = new URL(trimmed, baseUrl).href;
            return `${protocol}://${host}/?url=${encodeURIComponent(absUrl)}`;
          } catch (e) {
            return line;
          }
        }
        return line;
      });

      res.setHeader('Content-Type', 'application/vnd.apple.mpegurl; charset=utf-8');
      return res.status(200).send(rewrittenLines.join('\n'));

    } catch (error) {
      return res.status(500).json({ error: error.message });
    }
  }

  // ---------------------------------------------------------
  // ২. নির্দিষ্ট চ্যানেল ও ভিডিও স্ট্রিম ফেচিং
  // ---------------------------------------------------------
  const targetUrl = req.query.url;
  if (!targetUrl) {
    return res.status(400).json({ error: 'No URL provided' });
  }

  try {
    let reqOrigin = 'https://tv.moviemasti.net';
    let reqReferer = 'https://tv.moviemasti.net/';

    if (!targetUrl.includes('moviemasti.net')) {
      const parsedTarget = new URL(targetUrl);
      reqOrigin = parsedTarget.origin;
      reqReferer = parsedTarget.origin + '/';
    }

    const response = await fetch(targetUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36',
        'Origin': reqOrigin,
        'Referer': reqReferer,
        'Accept': '*/*'
      }
    });

    if (!response.ok) {
      return res.status(response.status).json({ error: `Stream failed (${response.status})` });
    }

    const contentType = response.headers.get('content-type') || '';
    const finalUrl = response.url; 

    const isPlaylist = targetUrl.includes('.m3u') || 
                       contentType.includes('mpegurl') || 
                       contentType.includes('m3u') || 
                       contentType.includes('text/plain');

    if (isPlaylist) {
      const text = await response.text();

      if (text.trim().startsWith('#EXTM3U') || targetUrl.includes('.m3u8')) {
        const lines = text.split('\n');
        const rewrittenLines = lines.map(line => {
          const trimmed = line.trim();
          if (!trimmed) return line;

          if (trimmed.startsWith('#')) {
            if (trimmed.includes('URI=')) {
              return trimmed.replace(/URI=["']([^"']+)["']/g, (match, uri) => {
                try {
                  const abs = new URL(uri, finalUrl).href;
                  return `URI="${protocol}://${host}/?url=${encodeURIComponent(abs)}"`;
                } catch (e) {
                  return match;
                }
              });
            }
            return line;
          }

          try {
            const abs = new URL(trimmed, finalUrl).href;
            return `${protocol}://${host}/?url=${encodeURIComponent(abs)}`;
          } catch (e) {
            return line;
          }
        });

        res.setHeader('Content-Type', 'application/vnd.apple.mpegurl; charset=utf-8');
        return res.status(200).send(rewrittenLines.join('\n'));
      }

      res.setHeader('Content-Type', contentType || 'text/plain');
      return res.status(200).send(text);
    }

    const arrayBuffer = await response.arrayBuffer();
    res.setHeader('Content-Type', contentType || 'video/mp2t');
    res.setHeader('Cache-Control', 'public, max-age=3600');
    return res.status(200).send(Buffer.from(arrayBuffer));

  } catch (error) {
    return res.status(500).json({ error: error.message });
  }
}
