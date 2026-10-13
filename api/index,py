from http.server import BaseHTTPRequestHandler
import urllib.parse
import urllib.request

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # URL থেকে query parameters পার্স করা
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)
        
        target_url = query_params.get('url', [None])[0]

        if not target_url:
            self.send_response(400)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'URL parameter is missing')
            return

        try:
            # টার্গেট লিংকে রিকোয়েস্ট পাঠানোর জন্য ইউজার-এজেন্ট সেট করা
            req = urllib.request.Request(
                target_url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            
            with urllib.request.urlopen(req) as response:
                content_type = response.headers.get('Content-Type', 'application/octet-stream')
                body = response.read()

                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(body)
                
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f'Proxy Error: {str(e)}'.encode('utf-8'))
