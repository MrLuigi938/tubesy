import os
import sys
import urllib.request

try:
    urllib.request.urlopen(f"http://127.0.0.1:{os.environ.get('PORT', '8080')}/api/health", timeout=4)
except Exception as exc:
    print(exc)
    sys.exit(1)
