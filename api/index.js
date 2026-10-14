export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', '*');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  const { url: targetUrl } = req.query;

  // যদি সরাসরি ডোমেইন ভিজিট করা হয় (কোনো url param না থাকে), তবে ক্র্যাশ না করে শুধু মেসেজ দেখাবে
  if (!targetUrl) {
    return res.status(200).json({ error: "No URL provided. Use ?url=STREAM_LINK" });
  }

  try {
    const parsedTarget = new URL(targetUrl);

    const headers = {
      'User-Agent': 'VLC/3.0.18 LibVLC/3.0.18',
      'Referer': parsedTarget.origin + '/',
      'Origin': parsedTarget.origin,
      'Accept': '*/*'
    };

    const response = await fetch(targetUrl, {
      method: 'GET',
      headers: headers
    });

    if (!response.ok) {
      return res.status(response.status).json({ error: `Stream HTTP ${response.status}` });
    }

    const contentType = response.headers.get('content-type'] || '';

    if (targetUrl.includes('.m3u8') || contentType.includes('mpegurl') || contentType.includes('m3u8')) {
      const text = await response.text();
      const host = req.headers['x-forwarded-host'] || req.headers.host;
      const protocol = req.headers['x-forwarded-proto'] || 'https';

      const lines = text.split('\n');
      const rewritten = lines.map(line => {
        const trimmed = line.trim();
        if (!trimmed) return line;

        if (trimmed.startsWith('#')) {
          if (trimmed.includes('URI=')) {
            return trimmed.replace(/URI=["']([^"']+)["']/g, (m, uri) => {
              try {
                const abs = new URL(uri, targetUrl).href;
                return `URI="${protocol}://${host}/?url=${encodeURIComponent(abs)}"`;
              } catch (e) {
                return m;
              }
            });
          }
          return line;
        }

        try {
          const abs = new URL(trimmed, targetUrl).href;
          return `${protocol}://${host}/?url=${encodeURIComponent(abs)}`;
        } catch (e) {
          return line;
        }
      });

      res.setHeader('Content-Type', 'application/vnd.apple.mpegurl; charset=utf-8');
      return res.status(200).send(rewritten.join('\n'));
    }

    res.setHeader('Content-Type', contentType || 'video/mp2t');
    const arrayBuffer = await response.arrayBuffer();
    return res.status(200).send(Buffer.from(arrayBuffer));

  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
}
