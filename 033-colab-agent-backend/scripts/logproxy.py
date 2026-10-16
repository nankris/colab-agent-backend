"""Tiny logging reverse proxy (debug only): 127.0.0.1:18435 -> 127.0.0.1:18434. Saves each request body to results/probe/req_N.json."""
import http.server, urllib.request, sys, os, itertools
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True); N = itertools.count()
class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        open(f"{OUT}/req_{next(N)}.json", "wb").write(body)
        req = urllib.request.Request("http://127.0.0.1:18434" + self.path, data=body, headers={"Content-Type": "application/json"})
        r = urllib.request.urlopen(req, timeout=600)
        self.send_response(r.status)
        for k, v in r.getheaders():
            if k.lower() not in ("transfer-encoding", "connection", "content-length"): self.send_header(k, v)
        self.send_header("Connection", "close"); self.end_headers()
        while True:
            c = r.read(1024)
            if not c: break
            self.wfile.write(c); self.wfile.flush()
    do_GET = do_POST
http.server.ThreadingHTTPServer(("127.0.0.1", 18435), H).serve_forever()
