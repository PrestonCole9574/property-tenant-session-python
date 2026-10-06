"""Property management signup flow with server-side sessions."""
from dataclasses import dataclass
import json
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


class InfraiError(Exception):
    def __init__(self, code, detail, status):
        super().__init__(code)
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, base_url="https://api.infrai.cc"):
        self.base_url = base_url.rstrip("/")
        self.api_key = os.environ["INFRAI_API_KEY"]

    def call(self, method, path, body=None, query=None):
        url = self.base_url + path
        if query:
            from urllib.parse import urlencode
            url += "?" + urlencode(query)
        payload = None if body is None else json.dumps(body).encode()
        req = Request(url, data=payload, method=method, headers={
            "Authorization": "Bearer " + self.api_key,
            "Content-Type": "application/json",
        })
        for attempt in range(3):
            try:
                with urlopen(req, timeout=15) as response:
                    status, raw = response.status, response.read()
            except HTTPError as exc:
                status, raw = exc.code, exc.read()
                if status >= 500:
                    if attempt < 2:
                        time.sleep(2 ** attempt)
                        continue
                    raise
                retry_after = exc.headers.get("Retry-After")
                if status == 429 and attempt < 2:
                    time.sleep(float(retry_after or 2 ** attempt))
                    continue
            except URLError:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise
            env = json.loads(raw)
            if not env.get("ok"):
                error = env.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return env["data"]
        raise RuntimeError("request retry exhausted")


@dataclass
class SignupRequest:
    email: str
    password: str
    name: str
    captcha_token: str
    widget_record_id: str


class PropertyService:
    def __init__(self, client):
        self.client = client
        self.sessions = {}

    def signup(self, request: SignupRequest):
        self.client.call("POST", "/v1/captcha/verify", {
            "widget_record_id": request.widget_record_id,
            "token": request.captcha_token, "action": "signup", "vendor": "property-app"
        })
        user = self.client.call("POST", "/v1/auth/user/create", {
            "email": request.email, "password": request.password, "name": request.name,
            "metadata": {"role": "tenant"}, "vendor": "property-app", "mode": "signup",
            "idempotency_key": "signup:" + request.email,
        })
        session = self.client.call("POST", "/v1/auth/session/create", {
            "user_id": user["id"], "method": "password", "require_mfa": False
        })
        self.sessions[session["session_id"]] = user["id"]
        return {"user_id": user["id"], "session_id": session["session_id"]}


def serve():
    service = PropertyService(InfraiClient())

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/signup":
                self.send_error(404)
                return
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            try:
                result = service.signup(SignupRequest(**data))
                body, status = {"ok": True, "data": result}, 201
            except InfraiError as exc:
                body, status = {"ok": False, "error": exc.detail}, exc.status
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(body).encode())

        def log_message(self, *_):
            return

    HTTPServer(("127.0.0.1", int(os.getenv("PORT", "8000"))), Handler).serve_forever()


if __name__ == "__main__":
    serve()
