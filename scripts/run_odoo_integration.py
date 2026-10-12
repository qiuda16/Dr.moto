"""Run BFF tests against an isolated Odoo through an SSH tunnel."""

import argparse
import ast
import os
from pathlib import Path
import select
import socketserver
import subprocess
import sys
import tempfile
import threading

import paramiko


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-config-script", required=True,
                        help="Local file containing literal host, username and password assignments; never executed")
    parser.add_argument("--odoo-port", type=int, default=18069)
    parser.add_argument("--all-tests", action="store_true")
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
                   username=values["username"], password=values["password"],
                   timeout=10, auth_timeout=10, banner_timeout=10)

    class Forward(socketserver.BaseRequestHandler):
        def handle(self):
            channel = client.get_transport().open_channel(
                "direct-tcpip", ("127.0.0.1", args.odoo_port), self.request.getpeername())
            try:
                while True:
                    ready, _, _ = select.select([self.request, channel], [], [], 20)
                    for source in ready:
                        data = source.recv(65536)
                        if not data:
                            return
                        (channel if source is self.request else self.request).sendall(data)
            finally:
                channel.close()

    class Tunnel(socketserver.ThreadingTCPServer):
        daemon_threads = True

    tunnel = Tunnel(("127.0.0.1", 0), Forward)
    threading.Thread(target=tunnel.serve_forever, daemon=True).start()
    root = Path(__file__).resolve().parents[1]
    try:
        with tempfile.TemporaryDirectory(prefix="drmoto-integration-") as directory:
            env = dict(os.environ)
            env.update(
                ODOO_URL=f"http://127.0.0.1:{tunnel.server_address[1]}",
                ODOO_DB="odoo", ODOO_USER="admin", ODOO_PASSWORD="admin",
                DATABASE_URL=f"sqlite:///{directory}/bff.db",
            )
            tests = ["bff/tests"] if args.all_tests else [
                "bff/tests/test_api.py", "-k",
                "customer_create_with_vehicle_and_query or customer_summary_endpoint or "
                "customer_with_vehicle_search_prioritizes_exact_name or wechat_intent_requires_configuration",
            ]
            return subprocess.run([sys.executable, "-m", "pytest", "-q", *tests],
                                  cwd=root, env=env, timeout=180).returncode
    finally:
        tunnel.shutdown()
        tunnel.server_close()
        client.close()


if __name__ == "__main__":
    sys.exit(main())
