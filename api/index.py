from http.server import BaseHTTPRequestHandler
import urllib.parse
import urllib.request
import re

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

                # যদি রেসপন্সটি m3u8 প্লেলিস্ট হয়, তবে ভেতরের .ts বা চ্যাঙ্ক লিংকগুলো রিরাইট করতে হবে
                if 'mpegurl' in content_type.lower() or target_url.endswith('.m3u8'):
                    text_content = body.decode('utf-8', errors='ignore')
                    
                    # মূল লিংকের বেস ইউআরএল বের করা (যেমন: http://2756d46c.akciatv.ru/iptv/7FRNF6CY9A9TG3/9258/)
                    base_url = target_url.rsplit('/', 1)[0] + '/'
                    
                    # রিলেটিভ পাথগুলোকে অ্যাবসোলিউট (Absolute) লিংকে রূপান্তর করা
                    def rewrite_line(match):
                        line = match.group(0)
                        if line.startswith('http://') or line.startswith('https://'):
                            return line
                        elif line.startswith('/'):
                            # যদি রুট থেকে শুরু হয়
                            parsed_base = urllib.parse.urlparse(target_url)
                            return f"{parsed_base.scheme}://{parsed_base.netloc}{line}"
                        else:
                            return base_url + line

                    # এমথিউইট ফাইলের কমেন্ট বা ট্যাগ ছাড়া লাইনগুলোতে লিংক রিরাইট করা
                    lines = text_content.splitlines()
                    new_lines = []
                    for line in lines:
                        if line and not line.startswith('#'):
                            # লাইনটি যদি পূর্ণাঙ্গ লিংক না হয়, তবে বেস ইউআরএল যুক্ত করবে
                            if not line.startswith('http://') and not line.startswith('https://'):
                                line = base_url + line
                        new_lines.append(line)
                    
                    body = "\n".join(new_lines).encode('utf-8')
                    content_type = 'application/x-mpegURL'

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
