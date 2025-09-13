# ota_server.py — mini serveur OTA local (GET /update/<imei>, POST /report, /files/*)
import json, os, re, mimetypes
from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# Servez explicitement depuis ota_local/
FILES_DIR = os.path.join(BASE_DIR, "ota_local", "files")
UPDATE_DIR = os.path.join(BASE_DIR, "ota_local", "update")

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        # petit log pour debug
        print("GET:", parsed.path)
        if parsed.path == "/healthz":
            self._json(200, {"ok": True}); return

        # /update/<IMEI> -> lit update/IMEI.json
        m = re.match(r"^/update/([0-9A-Za-z_-]+)$", parsed.path)
        if m:
            imei = m.group(1)
            manifest_path = os.path.join(UPDATE_DIR, imei + ".json")
            # fallback insensible à la casse si le fichier exact n'existe pas
            if not os.path.exists(manifest_path):
                target = (imei + ".json").lower()
                if os.path.isdir(UPDATE_DIR):
                    for fn in os.listdir(UPDATE_DIR):
                        if fn.lower() == target:
                            manifest_path = os.path.join(UPDATE_DIR, fn)
                            break
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._json(200, data)
                except Exception as e:
                    self._json(500, {"error": "manifest_read_error", "detail": str(e), "path": manifest_path})
            else:
                self._json(404, {"error": "manifest_not_found", "imei": imei, "looked_in": UPDATE_DIR})
            return

        # /files/... -> sert depuis ota_local/files de manière sûre
        if parsed.path.startswith("/files/"):
            if not os.path.isdir(FILES_DIR):
                self._json(404, {"error": "files_dir_not_found", "dir": FILES_DIR}); return
            rel = parsed.path[len("/files/"):]
            # normalisation et protection contre traversal
            rel_norm = os.path.normpath(rel).replace("\\", "/")
            if rel_norm.startswith("../") or rel_norm == "..":
                self._json(403, {"error": "forbidden"}); return
            filepath = os.path.join(FILES_DIR, rel_norm)
            if not os.path.isfile(filepath):
                self._json(404, {"error": "file_not_found", "path": filepath}); return
            try:
                ctype = mimetypes.guess_type(filepath)[0] or "application/octet-stream"
                fs = os.stat(filepath)
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(fs.st_size))
                self.end_headers()
                with open(filepath, "rb") as f:
                    self.wfile.write(f.read())
                return
            except Exception as e:
                self._json(500, {"error": "file_serve_error", "detail": str(e), "path": filepath}); return

        # page racine d'aide
        if parsed.path == "/":
            self._json(200, {
                "message": "OTA local server up",
                "update_example": "/update/867123456789012",
                "report_endpoint": "/report",
                "file_example": "/files/app.bin"
            }); return

        # fallback (404)
        self._json(404, {"error": "not_found", "path": parsed.path})

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/report":
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length > 0 else b"{}"
            try:
                data = json.loads(body.decode("utf-8"))
            except Exception:
                data = {"raw": body.decode("utf-8", "ignore")}
            print("REPORT:", data)  # visible dans le terminal -> débogage
            self._json(200, {"ok": True})
            return
        self._json(404, {"error": "not_found"})

    def _json(self, code, obj):
        payload = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

if __name__ == "__main__":
    port = 8000
    print(f"Serving OTA locally on http://0.0.0.0:{port}")
    print(f"Using update dir: {UPDATE_DIR}")
    print(f"Using files dir : {FILES_DIR}")
    print("• GET  /update/IMEI  (serve update/IMEI.json)")
    print("• POST /report         (prints JSON)")
    print("• GET  /files/app.bin  (serves files/*)")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
