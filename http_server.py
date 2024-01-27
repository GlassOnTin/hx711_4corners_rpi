import os
import configparser
import http.server
import socket
import socketserver
import urllib
from urllib.parse import urlparse, parse_qs
from scale import Scale
from states import STATE_TARING, STATE_CALIBRATING, STATE_MEASURING

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, scale=None, state_q=None, config_file='scale_config.ini',**kwargs):
        self.scale = scale
        self.state_q = state_q
        
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.config.read(self.config_file)
        
        super().__init__(*args, **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def do_GET(self):       
        parsed_path = urlparse(self.path)
        self.path = parsed_path.path

        if self.path == '/':
            self.path = '/index.html'
            return super().do_GET()
        
        else:
            return super().do_GET()

    def do_POST(self):
        if self.path == '/tare':
            print("Taring")
            while not self.state_q.empty(): self.state_q.get()
            self.state_q.put(STATE_TARING)
            
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Taring complete.")

        elif self.path == '/calibrate':
            print("Calibrating")

            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = urllib.parse.parse_qs(post_data.decode('utf-8'))
            known_weight = float(data.get('weight', [1])[0])  # Default weight 1 unit
            self.config['DEFAULT']['KnownWeight'] = str(known_weight)
            with open(self.config_file, 'w') as configfile:
                self.config.write(configfile)

            while not self.state_q.empty(): self.state_q.get()
            self.state_q.put(STATE_CALIBRATING)
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Calibration complete.")
        
        else:
            self.send_error(404, "Unsupported operation")

def start_http_server(host, port, directory, scale, state_q):
    def handler(*args, **kwargs):
        return CustomHandler(*args, scale=scale, state_q=state_q, **kwargs)

    with socketserver.TCPServer((host, port), handler) as httpd:
        httpd.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print(f"Serving at http://{host}:{port}")
        os.chdir(directory)
        httpd.serve_forever()
