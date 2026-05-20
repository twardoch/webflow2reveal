# this_file: dev_server.py

import http.server
import socketserver
import urllib.request
import urllib.parse
import ssl
import sys

PORT = 8080

# Create unverified SSL context to bypass potential local SSL verification errors during proxying
ssl_context = ssl._create_unverified_context()

class DevProxyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/proxy/'):
            # Extract target URL
            target_url = self.path[7:]
            target_url = urllib.parse.unquote(target_url)
            
            print(f"[Proxy] Fetching: {target_url}")
            
            try:
                # Add headers to emulate a browser request
                req = urllib.request.Request(
                    target_url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
                    }
                )
                
                with urllib.request.urlopen(req, context=ssl_context) as response:
                    content = response.read()
                    
                    self.send_response(200)
                    # Enable CORS
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Headers', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
                    
                    # Forward content type
                    content_type = response.headers.get('Content-Type', 'text/html')
                    self.send_header('Content-Type', content_type)
                    self.end_headers()
                    
                    self.wfile.write(content)
                    
            except Exception as e:
                print(f"[Proxy Error] {e}")
                self.send_response(500)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Proxy error: {str(e)}".encode())
        else:
            # Fallback to serving files
            super().do_GET()

def main():
    # Allow port to be configurable
    port = PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
            
    # Fix protocol version to enable HTTP/1.1 if needed
    DevProxyHandler.protocol_version = 'HTTP/1.1'
    
    # Enable socket re-use to prevent "Address already in use" errors on restarts
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.ThreadingTCPServer(("", port), DevProxyHandler) as httpd:
        print(f"==================================================")
        print(f"  Webflow2Reveal Development Server")
        print(f"  Running on: http://localhost:{port}")
        print(f"  Serving docs at: http://localhost:{port}/docs/index.html")
        print(f"==================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")

if __name__ == '__main__':
    main()
