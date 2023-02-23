import http.server
import random
import string
import base64
import hashlib
import json

from urllib.parse import urlparse, parse_qs

import requests

# pylint: disable=f-string-without-interpolation
# pylint: disable=invalid-name
# pylint: disable=global-variable-undefined


PORT = 36698
SITE = f"http://localhost:{PORT}"
CLIENT_ID = "70lb3xbyjwf04ly"


ERROR_PAGE_CONTENT = \
"""
<html>
<head><meta charset="utf-8"></head>
<h4>ERROR:$ERR_CODE</h4>
</html>
"""


TOKEN_PAGE_CONTENT = \
"""
<html>
<head><meta charset="utf-8"></head>
<h4>YOUR REFRESH TOKEN:$TOKEN</h4>
</html>
"""


class Handler(http.server.BaseHTTPRequestHandler):

    # pylint: disable-next=invalid-name
    def do_GET(self):
        global refresh_token
        parse_result = urlparse(f"{SITE}{self.path}")
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        if parse_result.path != "/":
            self.wfile.write(ERROR_PAGE_CONTENT.replace("$ERR_CODE", f"Bad path requested {self.path}").encode("utf-8"))
            return
        params = {k: v[0] for k, v in parse_qs(parse_result.query).items()}
        if "code" not in params:
            self.wfile.write(ERROR_PAGE_CONTENT.replace("$ERR_CODE", f"No 'code' parameter").encode("utf-8"))
            return
        request_params = {
            "code": params["code"],
            "code_verifier": code_verifier,
            "client_id": CLIENT_ID,
            "redirect_uri": f"http://localhost:{PORT}",
            "grant_type": "authorization_code",
        }
        try:
            response = requests.post("https://api.dropbox.com/oauth2/token", params=request_params, timeout=10)
        except requests.RequestException as e:
            self.wfile.write(ERROR_PAGE_CONTENT.replace("$ERR_CODE", str(e)).encode("utf-8"))
            return
        if response.status_code != 200:
            self.wfile.write(ERROR_PAGE_CONTENT.replace("$ERR_CODE", response.text).encode("utf-8"))
            return
        js = json.loads(response.text)
        if "refresh_token" not in js:
            self.wfile.write(ERROR_PAGE_CONTENT.replace("$ERR_CODE", "dropbox return 200 but without refresh_token").encode("utf-8"))
            return
        refresh_token = js["refresh_token"]
        self.wfile.write(TOKEN_PAGE_CONTENT.replace("$TOKEN", js["refresh_token"]).encode("utf-8"))

    # pylint: disable-next=redefined-builtin
    def log_message(self, format, *args):
        pass


def get():
    global code_verifier, code_challenge, refresh_token
    refresh_token = None
    code_verifier = "".join(random.choice(string.ascii_lowercase) for _ in range(50))
    code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("utf-8")).digest()).decode("utf-8").rstrip("=")

    url = "https://www.dropbox.com/oauth2/authorize"
    url += f"?client_id={CLIENT_ID}"
    url += f"&redirect_uri=http://localhost:{PORT}"
    url += f"&code_challenge={code_challenge}"
    url += f"&code_challenge_method=S256"
    url += f"&response_type=code"
    url += f"&token_access_type=offline"
    print("Follow this link:", url)

    server = http.server.HTTPServer(("localhost", PORT), Handler)
    while not refresh_token:
        server.handle_request()
    server.server_close()

    print("Your refresh token:", refresh_token)
