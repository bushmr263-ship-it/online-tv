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

  // ১. রুট ডোমেইনে আসলে যাতে কোনোভাবেই ক্র্যাশ না করে
  if (requestUrl === '/' && !req.query.url) {
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
          <p>Backend proxy is active and ready.</p>
      </body>
      </html>
    `);
  }
