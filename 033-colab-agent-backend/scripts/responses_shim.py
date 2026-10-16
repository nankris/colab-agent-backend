"""Responses-API stream shim between Codex CLI and Ollama (runs in the sandbox, next to Codex).

Why: Ollama 0.40.4's streamed /v1/responses gives a text message and a following function_call the SAME
output_index and never sends output_item.done for the message. Codex then keeps the text and drops the tool
call, so the agent "announces" a step and ends the turn. Non-streamed responses are correct.

What it does: forwards each POST /v1/responses to Ollama with stream=false, then replays the finished response
to Codex as a well-formed SSE stream (one output_index per item, messages before tool calls, *.done events,
response.completed with usage). Everything else (GET /v1/models etc.) is passed through.
Usage: python3 responses_shim.py LISTEN_PORT UPSTREAM_BASE   e.g. 18436 http://127.0.0.1:18434
Logs one line per request to stdout: epoch, wall seconds, input/output tokens, item types.
"""
import http.server, json, sys, time, urllib.request

PORT, UP = int(sys.argv[1]), sys.argv[2].rstrip("/")


class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _pass(self, body=None):
        req = urllib.request.Request(UP + self.path, data=body, method=self.command,
                                     headers={"Content-Type": "application/json"})
        try:
            r = urllib.request.urlopen(req, timeout=900); data, st = r.read(), r.status
        except urllib.error.HTTPError as e:
            data, st = e.read(), e.code
        self.send_response(st); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

    def do_GET(self):
        self._pass()

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if not self.path.rstrip("/").endswith("/responses"):
            return self._pass(body)
        d = json.loads(body); want_stream = d.get("stream", False); d["stream"] = False
        t0 = time.time()
        req = urllib.request.Request(UP + self.path, data=json.dumps(d).encode(), headers={"Content-Type": "application/json"})
        try:
            resp = json.loads(urllib.request.urlopen(req, timeout=900).read())
        except urllib.error.HTTPError as e:
            data = e.read(); self.send_response(e.code); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data); return
        out = resp.get("output") or []
        out = [o for o in out if o.get("type") == "message"] + [o for o in out if o.get("type") != "message"]
        out = [o for o in out if not (o.get("type") == "message" and not "".join(
            c.get("text", "") for c in (o.get("content") or [])).strip())]
        resp["output"] = out
        u = resp.get("usage") or {}
        print(int(t0), round(time.time() - t0, 2), u.get("input_tokens"), u.get("output_tokens"),
              ",".join(o.get("type", "?") + (":" + o["name"] if o.get("name") else "") for o in out), flush=True)
        if not want_stream:
            data = json.dumps(resp).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data); return
        self.send_response(200); self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache"); self.send_header("Connection", "close"); self.end_headers()
        seq = [0]

        def ev(t, **kw):
            kw["type"] = t; kw["sequence_number"] = seq[0]; seq[0] += 1
            self.wfile.write(f"event: {t}\ndata: {json.dumps(kw)}\n\n".encode())

        base = dict(resp); base["status"] = "in_progress"; base["output"] = []
        ev("response.created", response=base); ev("response.in_progress", response=base)
        for i, o in enumerate(out):
            if o.get("type") == "message":
                o.setdefault("status", "completed")
                ev("response.output_item.added", output_index=i, item=dict(o, content=[], status="in_progress"))
                for j, c in enumerate(o.get("content") or []):
                    txt = c.get("text", "")
                    ev("response.content_part.added", item_id=o.get("id"), output_index=i, content_index=j,
                       part=dict(c, text=""))
                    ev("response.output_text.delta", item_id=o.get("id"), output_index=i, content_index=j, delta=txt)
                    ev("response.output_text.done", item_id=o.get("id"), output_index=i, content_index=j, text=txt)
                    ev("response.content_part.done", item_id=o.get("id"), output_index=i, content_index=j, part=c)
                ev("response.output_item.done", output_index=i, item=o)
            elif o.get("type") == "function_call":
                ev("response.output_item.added", output_index=i, item=dict(o, arguments="", status="in_progress"))
                ev("response.function_call_arguments.delta", item_id=o.get("id"), output_index=i, delta=o.get("arguments", ""))
                ev("response.function_call_arguments.done", item_id=o.get("id"), output_index=i, arguments=o.get("arguments", ""))
                ev("response.output_item.done", output_index=i, item=o)
            else:
                ev("response.output_item.added", output_index=i, item=o)
                ev("response.output_item.done", output_index=i, item=o)
        resp["status"] = "completed"
        ev("response.completed", response=resp)
        self.wfile.flush(); self.close_connection = True


http.server.ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
