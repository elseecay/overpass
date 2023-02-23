import http.server

from urllib.parse import urlparse, parse_qs


# pylint: disable=f-string-without-interpolation
# pylint: disable=invalid-name
# pylint: disable=global-variable-undefined


PORT = 36698
SITE = f"http://localhost:{PORT}"
CLIENT_ID = "4eb86ca86ee841c3ade52e269bb4dc3d"


REDIRECT_PAGE_CONTENT = \
"""
<html>
<head><meta charset="utf-8"></head>
<script>
    const hash = window.location.hash.substr(1);
    window.location.replace(`http://localhost:PORT/token?${hash}`);
</script>
</html>
""".replace("PORT", str(PORT))


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
<h4>YOUR TOKEN:$TOKEN</h4>
</html>
"""


class Handler(http.server.BaseHTTPRequestHandler):

    # pylint: disable-next=invalid-name
    def do_GET(self):
        global token
        parse_result = urlparse(f"{SITE}{self.path}")
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        if parse_result.path == "/":
            self.wfile.write(REDIRECT_PAGE_CONTENT.encode("utf-8"))
            return
        if not parse_result.path == "/token":
            self.wfile.write(ERROR_PAGE_CONTENT.replace("$ERR_CODE", f"Bad path requested {self.path}").encode("utf-8"))
            return
        params = {k: v[0] for k, v in parse_qs(parse_result.query).items()}
        if "access_token" in params:
            token = params["access_token"]
            self.wfile.write(TOKEN_PAGE_CONTENT.replace("$TOKEN", params["access_token"]).encode("utf-8"))
        elif "error" in params:
            self.wfile.write(ERROR_PAGE_CONTENT.replace("$ERR_CODE", params["error"]).encode("utf-8"))
        else:
            self.wfile.write(ERROR_PAGE_CONTENT.replace("$ERR_CODE", f"No 'error' or 'access_token' parameters in url {self.path}").encode("utf-8"))

    # pylint: disable-next=redefined-builtin
    def log_message(self, format, *args):
        pass


def get():
    global token
    token = None

    url = "https://oauth.yandex.ru/authorize"
    url += f"?response_type=token"
    url += f"&client_id={CLIENT_ID}"
    url += f"&force_confirm=true"
    print("Follow this link:", url)

    server = http.server.HTTPServer(("localhost", PORT), Handler)
    while not token:
        server.handle_request()
    server.server_close()

    print("Your token:", token)
