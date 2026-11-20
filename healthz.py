"""Health check for the running stack. Uses only the Python standard library.

Usage:
    python healthz.py                      # checks http://localhost:8010
    python healthz.py http://localhost:8000

Exit codes: 0 = API and database healthy, 1 = API unreachable or database down.
"""

import json
import sys
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "http://localhost:8010"
TIMEOUT_SECONDS = 5


def read_json(response_body: bytes) -> dict:
    try:
        return json.loads(response_body or b"{}")
    except json.JSONDecodeError:
        return {}


def check(base_url: str) -> int:
    url = f"{base_url.rstrip('/')}/api/health"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
            status, body = response.status, read_json(response.read())
    except urllib.error.HTTPError as error:
        status, body = error.code, read_json(error.read())
    except (urllib.error.URLError, OSError) as error:
        print(f"FAIL: cannot reach {url} ({error}). Is the backend running?")
        return 1

    message = body.get("message", "no message returned")
    if status == 200:
        print(f"OK: {message} ({url})")
        return 0
    print(f"FAIL: HTTP {status} from {url}: {message}")
    return 1


if __name__ == "__main__":
    sys.exit(check(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE_URL))
