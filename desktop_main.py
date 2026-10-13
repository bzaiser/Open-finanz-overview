import os
import sys
import time
import socket
import threading
import webbrowser
from waitress import serve
from config.wsgi import application
from django.conf import settings

def find_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def start_server(port):
    serve(application, host='127.0.0.1', port=port, threads=6, _quiet=True)

def wait_for_server(port, timeout=10.0):
    url = f"http://127.0.0.1:{port}"
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=0.5):
                return True
        except Exception:
            time.sleep(0.05)
    return False

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    
    # Force settings load to read .env
    _ = settings.BASE_DIR
    
    ui_mode = os.getenv('DESKTOP_UI_MODE', 'window').strip().lower()
    port = find_free_port()
    url = f"http://127.0.0.1:{port}"
    
    if ui_mode == 'browser':
        server_thread = threading.Thread(target=start_server, args=(port,), daemon=True)
        server_thread.start()
        wait_for_server(port)
        webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            sys.exit(0)
    else:
        import webview
        server_thread = threading.Thread(target=start_server, args=(port,), daemon=True)
        server_thread.start()
        webview.create_window("Finanzplan Desktop", url, width=1280, height=850, min_size=(900, 600))
        webview.start()
        sys.exit(0)
