import os
import sys
import time
import socket
import threading
import urllib.request
import webbrowser
from pathlib import Path
from waitress import serve
from config.wsgi import application
from django.conf import settings
from django.core.management import call_command

SPLASH_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {
    margin: 0;
    background: #0f172a;
    color: #f8fafc;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100vh;
    overflow: hidden;
    user-select: none;
  }
  .box {
    text-align: center;
    width: 380px;
    max-width: 85%;
  }
  .logo-icon {
    font-size: 42px;
    margin-bottom: 12px;
  }
  .title {
    font-size: 24px;
    font-weight: 700;
    margin-bottom: 6px;
    letter-spacing: -0.02em;
    color: #38bdf8;
  }
  .sub {
    font-size: 13px;
    color: #94a3b8;
    margin-bottom: 28px;
  }
  .progress-bar {
    width: 100%;
    height: 6px;
    background: #1e293b;
    border-radius: 9999px;
    overflow: hidden;
    position: relative;
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.4);
  }
  .progress-inner {
    position: absolute;
    height: 100%;
    background: linear-gradient(90deg, #0284c7, #38bdf8);
    border-radius: 9999px;
    width: 35%;
    animation: load 1.2s infinite ease-in-out;
  }
  @keyframes load {
    0% { left: -35%; }
    50% { left: 45%; width: 45%; }
    100% { left: 100%; width: 25%; }
  }
</style>
</head>
<body>
<div class="box">
  <div class="logo-icon">📊</div>
  <div class="title">Finanzplan Desktop</div>
  <div class="sub">Wird gestartet und vorbereitet...</div>
  <div class="progress-bar"><div class="progress-inner"></div></div>
</div>
</body>
</html>"""

def find_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def start_server(port):
    serve(application, host='127.0.0.1', port=port, threads=6, _quiet=True)

def wait_for_server(port, timeout=15.0):
    url = f"http://127.0.0.1:{port}"
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=0.5):
                return True
        except Exception:
            time.sleep(0.05)
    return False

def init_django_database():
    """Initializes migrations and cache table quietly."""
    try:
        call_command('migrate', interactive=False)
    except Exception as e:
        print(f"Migration error: {e}")

    try:
        call_command('createcachetable')
    except Exception as e:
        print(f"Cache table error: {e}")

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

    # CLI Support: Allow executing Django management commands via the desktop executable
    # e.g.: FinanzplanDesktop.exe --seed  or  FinanzplanDesktop.exe --manage seed_demo_family
    if len(sys.argv) > 1:
        import django
        django.setup()
        arg = sys.argv[1].strip()
        if arg in ('--seed', '--seed-demo'):
            call_command('seed_demo_data')
            sys.exit(0)
        elif arg in ('--seed-family', '--seed-demo-family'):
            call_command('seed_demo_family')
            sys.exit(0)
        elif arg == '--manage' and len(sys.argv) > 2:
            cmd_name = sys.argv[2]
            cmd_args = sys.argv[3:]
            call_command(cmd_name, *cmd_args)
            sys.exit(0)

    # Initialize Django app registry and configuration
    import django
    django.setup()

    ui_mode = os.getenv('DESKTOP_UI_MODE', 'window').strip().lower()
    port = find_free_port()
    url = f"http://127.0.0.1:{port}"

    # Register dynamic local ports in trusted CSRF origins to prevent sporadic login CSRF errors
    for host in ('127.0.0.1', 'localhost'):
        origin = f"http://{host}:{port}"
        if origin not in settings.CSRF_TRUSTED_ORIGINS:
            settings.CSRF_TRUSTED_ORIGINS.append(origin)

    if ui_mode == 'browser':
        init_django_database()
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

        # Allow text selection for copying figures, account numbers and notes
        # Start immediately with a clean loading splash screen
        window = webview.create_window(
            "Finanzplan Desktop",
            html=SPLASH_HTML,
            width=1280,
            height=850,
            min_size=(900, 600),
            text_select=True
        )

        def bootstrap_and_navigate():
            # Run migrations and cache table creation in the background while user sees splash
            init_django_database()
            server_thread = threading.Thread(target=start_server, args=(port,), daemon=True)
            server_thread.start()
            if wait_for_server(port):
                window.load_url(url)

        # Persist WebView cookies and session data in LocalAppData to avoid CSRF & session dropouts
        storage_dir = Path(os.getenv('LOCALAPPDATA', str(Path.home()))) / 'Finanzplan Desktop' / 'webview_data'
        try:
            storage_dir.mkdir(parents=True, exist_ok=True)
            webview.start(bootstrap_and_navigate, private_mode=False, storage_path=str(storage_dir))
        except Exception:
            webview.start(bootstrap_and_navigate)
        sys.exit(0)
