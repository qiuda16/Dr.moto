"""Serve the staff build and proxy its API to isolated BFF through SSH."""

import argparse
import ast
import http.client
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import paramiko


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-config-script", required=True)
    parser.add_argument("--port", type=int, default=5179)
    parser.add_argument("--client", choices=["web_staff", "landing_site"], default="web_staff")
    args = parser.parse_args()
    values = {}
    for node in ast.walk(ast.parse(Path(args.ssh_config_script).read_text())):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"host", "port", "username", "password"}:
                    values[target.id] = ast.literal_eval(node.value)
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect(values["host"], port=values.get("port", 22),
                   username=values["username"], password=values["password"], timeout=10)
    root = Path(__file__).resolve().parents[1] / "clients" / args.client / "dist"

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

        def proxy(self):
            connection = http.client.HTTPConnection("127.0.0.1", 28080, timeout=30)
            connection.sock = client.get_transport().open_channel(
                "direct-tcpip", ("127.0.0.1", 28080), self.client_address)
            connection.sock.settimeout(30)
            try:
                body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                headers = {key: value for key, value in self.headers.items()
                           if key.lower() not in {"host", "connection", "transfer-encoding"}}
                connection.request(self.command, self.path[4:] or "/", body=body, headers=headers)
                response = connection.getresponse()
                data = response.read()
                self.send_response(response.status)
                self.send_header("Content-Type", response.getheader("Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            finally:
                connection.close()

        def do_GET(self):
            if self.path.startswith("/api/"):
                return self.proxy()
            if not Path(self.translate_path(urlsplit(self.path).path)).exists():
                self.path = "/index.html"
            super().do_GET()

        do_POST = proxy
        do_PUT = proxy
        do_DELETE = proxy
        do_PATCH = proxy

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Staff acceptance: http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        client.close()


if __name__ == "__main__":
    main()
