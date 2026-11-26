const express = require('express');
const { Readable } = require('stream');

const app = express();

// ===================================================
// সিক্রেট আইডি (প্রয়োজনে পরিবর্তন করুন)
// ===================================================
const EXPIRE_CODE = "48436844";

// মূল M3U প্লেলিস্ট URL
const PLAYLIST_URL = 'https://raw.githubusercontent.com/bushmr263-ship-it/online-tv/refs/heads/main/playlist.m3u';

const DEFAULT_UA =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';
// ===================================================

// সব রাউটের জন্য CORS হেডার যুক্ত করা
app.use((req, res, next) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, HEAD, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', '*');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }
  next();
});

// হোম রুট (হেলথ চেক ও টেস্টিংয়ের জন্য)
app.get('/', (req, res) => {
  res.send('SHAWON TV Proxy Server is Running!');
});

function buildProxyUrl(protocol, host, targetUrl, referrer) {
  let proxyUrl = `${protocol}://${host}/api/proxy?url=${encodeURIComponent(targetUrl)}`;
  if (referrer) {
    proxyUrl += `&ref=${encodeURIComponent(referrer)}`;
  }
  return proxyUrl;
}

// প্রক্সি প্রসেসর ফাংশন
async function handleProxy(req, res) {
  const host = req.headers.host;
  const protocol = req.headers['x-forwarded-proto'] || req.protocol || 'https';
  const requestUrl = req.originalUrl || req.url || '';

  // ---------------------------------------------------------
  // ১. M3U প্লেলিস্ট রিকোয়েস্ট (যেমন: /api/proxy/playlist-expire=48436844.m3u)
  // ---------------------------------------------------------
  if (!req.query.url && (requestUrl.includes('.m3u') || requestUrl.includes('playlist-expire'))) {
    if (EXPIRE_CODE && !requestUrl.includes(EXPIRE_CODE)) {
      return res.status(403).json({ error: 'Access Denied: Invalid or Expired ID' });
    }

    try {
      const response = await fetch(PLAYLIST_URL, {
        headers: { 'User-Agent': DEFAULT_UA }
      });

      if (!response.ok) {
        return res.status(response.status).json({ error: 'Failed to fetch playlist' });
      }

      const content = await response.text();
      const baseUrl = response.url;
      let pendingReferrer = '';

      const lines = content.split('\n');
      const rewrittenLines = lines.map((line) => {
        const trimmed = line.trim();

        // #EXTVLCOPT:http-referrer=... থেকে রেফারার সংগ্রহ
        if (trimmed.startsWith('#EXTVLCOPT:')) {
          const match = trimmed.match(/http-referrer=(.+)$/i);
          if (match && match[1]) {
            pendingReferrer = match[1].trim();
          }
          return line;
        }

        if (trimmed && !trimmed.startsWith('#')) {
          try {
            const absUrl = new URL(trimmed, baseUrl).href;
            const out = buildProxyUrl(protocol, host, absUrl, pendingReferrer);
            pendingReferrer = ''; // পরবর্তী চ্যানেলের জন্য রিসেট
            return out;
          } catch (e) {
            pendingReferrer = '';
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
  const customRef = typeof req.query.ref === 'string' ? req.query.ref.trim() : '';

  if (!targetUrl) {
    return res.status(400).json({ error: 'No URL provided' });
  }

  try {
    const parsedTarget = new URL(targetUrl);
    const effectiveRef = customRef || `${parsedTarget.origin}/`;

    let effectiveOrigin = `${parsedTarget.origin}`;
    try {
      effectiveOrigin = new URL(effectiveRef).origin;
    } catch (_) {
      effectiveOrigin = parsedTarget.origin;
    }

    const response = await fetch(targetUrl, {
      headers: {
        'User-Agent': DEFAULT_UA,
        'Origin': effectiveOrigin,
        'Referer': effectiveRef,
        'Accept': '*/*'
      }
    });

    if (!response.ok) {
      return res.status(response.status).json({ error: `Stream failed (${response.status})` });
    }

    const contentType = response.headers.get('content-type') || '';
    const finalUrl = response.url;

    const isPlaylist =
      targetUrl.includes('.m3u') ||
      contentType.includes('mpegurl') ||
      contentType.includes('m3u') ||
      contentType.includes('text/plain');

    if (isPlaylist) {
      const text = await response.text();

      if (text.trim().startsWith('#EXTM3U') || targetUrl.includes('.m3u8')) {
        const lines = text.split('\n');
        const rewrittenLines = lines.map((line) => {
          const trimmed = line.trim();
          if (!trimmed) return line;

          if (trimmed.startsWith('#')) {
            if (trimmed.includes('URI=')) {
              return trimmed.replace(/URI=["']([^"']+)["']/g, (match, uri) => {
                try {
                  const abs = new URL(uri, finalUrl).href;
                  return `URI="${buildProxyUrl(protocol, host, abs, customRef)}"`;
                } catch (e) {
                  return match;
                }
              });
            }
            return line;
          }

          try {
            const abs = new URL(trimmed, finalUrl).href;
            return buildProxyUrl(protocol, host, abs, customRef);
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

    // TS/AAC/MP4 সেগমেন্ট স্ট্রিম করে পাঠানো
    res.setHeader('Content-Type', contentType || 'video/mp2t');
    res.setHeader('Cache-Control', 'public, max-age=3600');

    if (response.body) {
      Readable.fromWeb(response.body).pipe(res);
    } else {
      const arrayBuffer = await response.arrayBuffer();
      return res.status(200).send(Buffer.from(arrayBuffer));
    }
  } catch (error) {
    return res.status(500).json({ error: error.message });
  }
}

// প্রক্সি রাউট
app.use('/api/proxy', handleProxy);

const PORT = process.env.PORT || 10000;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
