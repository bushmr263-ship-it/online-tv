from http.server import BaseHTTPRequestHandler
import urllib.parse
import urllib.request

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # URL theke query parameters parse kora
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
            # Target link-e request pathanor jonno User-Agent set kora
            req = urllib.request.Request(
                target_url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            
            with urllib.request.urlopen(req) as response:
                content_type = response.headers.get('Content-Type', 'application/octet-stream')
                body = response.read()

                # Jodi response-ti m3u8 playlist hoy, tahobe vetor er chunk/ts link gulo rewrite korte hobe
                if 'mpegurl' in content_type.lower() or target_url.endswith('.m3u8') or '.m3u8' in target_url:
                    text_content = body.decode('utf-8', errors='ignore')
                    
                    # Target link-er base URL ber kora
                    base_url = target_url.rsplit('/', 1)[0] + '/'
                    
                    # Current Vercel host detect kora
                    host = self.headers.get('Host', 'online-tv-rho.vercel.app')
                    
                    lines = text_content.splitlines()
                    new_lines = []
                    for line in lines:
                        line_str = line.strip()
                        if line_str and not line_str.startswith('#'):
                            # Absolute URL toiri kora
                            if line_str.startswith('http://') or line_str.startswith('https://'):
                                abs_url = line_str
                            elif line_str.startswith('/'):
                                parsed_target = urllib.parse.urlparse(target_url)
                                abs_url = f"{parsed_target.scheme}://{parsed_target.netloc}{line_str}"
                            else:
                                abs_url = base_url + line_str
                            
                            # Proxy URL-er sathe wrap kora
                            proxy_wrapped_url = f"https://{host}/?url={urllib.parse.quote(abs_url, safe='')}"
                            new_lines.append(proxy_wrapped_url)
                        else:
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
