"""HTTP 服务：提供经营页面静态资源和指标 JSON 接口。"""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from pathlib import Path
import importlib
import json
import os

os.chdir(Path(__file__).parent)


class Handler(SimpleHTTPRequestHandler):
    def _send_json(self, status, payload):
        data = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        if urlparse(self.path).path == "/metrics.json":
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Content-Length", "0")
            self.end_headers()
        else:
            self.send_error(404)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path != "/metrics.json":
            return super().do_GET()

        try:
            import metrics
            importlib.reload(metrics)
            query = parse_qs(url.query)
            market = query.get("market", [None])[0] or None
            sku = query.get("sku", [None])[0] or None
            result = metrics.build_metrics(market=market, sku=sku)
            self._send_json(200, result)
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})


ThreadingHTTPServer(("0.0.0.0", 3000), Handler).serve_forever()

