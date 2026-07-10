import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

FIXTURES = Path(__file__).resolve().parents[2] / ".specs" / "features" / "cli-v1" / "fixtures"
REDACTED_SESSION = "<redacted-session-token>"


class ContractHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def _fixture(self, name):
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    def _send(self, status, name):
        body = json.dumps(self._fixture(name)).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _record(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(content_length) or b"{}")
        self.server.requests.append((self.command, self.path, dict(self.headers), body))
        return body

    def _is_authenticated(self):
        return self.headers.get("X-Session-Token") == REDACTED_SESSION

    def do_GET(self):
        self.server.requests.append((self.command, self.path, dict(self.headers), None))
        if not self._is_authenticated():
            self._send(401, "errors.401.json")
        elif self.path == "/auth/me":
            self._send(200, "identity.success.json")
        elif self.path == "/projects":
            self._send(200, "projects.list.success.json")
        elif self.path == "/projects/project-1":
            self._send(200, "projects.show.success.json")
        else:
            self._send(403, "errors.403.json")

    def do_POST(self):
        body = self._record()
        if self.path == "/auth/login":
            self._send(200, "login.success.json")
        elif not self._is_authenticated():
            self._send(401, "errors.401.json")
        elif self.path == "/tasks/query" and body.get("project_id") == "project-foreign":
            self._send(403, "errors.403.json")
        elif self.path == "/tasks/query":
            self._send(200, "tasks.query.success.json")
        else:
            self._send(403, "errors.403.json")


class ApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), ContractHandler)
        cls.server.requests = []
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()
        cls.server.server_close()

    def request(self, method, path, body=None, authenticated=True):
        headers = {"Content-Type": "application/json"}
        if authenticated:
            headers["X-Session-Token"] = REDACTED_SESSION
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(f"{self.base_url}{path}", data=data, headers=headers, method=method)
        try:
            with urlopen(request) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)

    def test_fixtures_are_sanitized_and_have_required_contract_fields(self):
        fixtures = {
            path.name: json.loads(path.read_text(encoding="utf-8"))
            for path in FIXTURES.glob("*.json")
        }

        self.assertEqual(fixtures["login.success.json"]["session_token"], REDACTED_SESSION)
        self.assertTrue(
            {"id", "name", "email", "permissions"} <= fixtures["identity.success.json"].keys()
        )
        self.assertTrue(
            {"id", "key", "current_sprint"} <= fixtures["projects.list.success.json"][0].keys()
        )
        self.assertTrue(
            {"id", "key", "project_id", "is_archived"}
            <= fixtures["tasks.query.success.json"]["items"][0].keys()
        )
        self.assertTrue(
            {"items", "total", "page", "page_size"} <= fixtures["tasks.query.success.json"].keys()
        )
        self.assertTrue(
            all("password" not in json.dumps(value).lower() for value in fixtures.values())
        )

    def test_success_contracts_for_login_identity_projects_and_paginated_tasks(self):
        status, login = self.request(
            "POST", "/auth/login", {"email": "member@example.test", "password": "<redacted>"}, False
        )
        self.assertEqual(status, 200)
        self.assertEqual(login["session_token"], REDACTED_SESSION)
        self.assertEqual(login["user"]["id"], "user-member")
        method, path, _, body = self.server.requests[-1]
        self.assertEqual((method, path), ("POST", "/auth/login"))
        self.assertEqual(body, {"email": "member@example.test", "password": "<redacted>"})

        status, identity = self.request("GET", "/auth/me")
        self.assertEqual(status, 200)
        self.assertEqual(identity["email"], "member@example.test")

        status, projects = self.request("GET", "/projects")
        self.assertEqual(status, 200)
        self.assertEqual(projects[0]["id"], "project-1")

        status, project = self.request("GET", "/projects/project-1")
        self.assertEqual(status, 200)
        self.assertEqual(project["key"], "EX")

        status, page = self.request(
            "POST", "/tasks/query", {"project_id": "project-1", "page": 1, "page_size": 25}
        )
        self.assertEqual(status, 200)
        self.assertEqual(page["total"], 1)
        self.assertEqual(page["page"], 1)
        self.assertEqual(page["page_size"], 25)
        self.assertEqual(page["items"][0]["project_id"], "project-1")
        method, path, headers, body = self.server.requests[-1]
        self.assertEqual((method, path), ("POST", "/tasks/query"))
        self.assertEqual(headers["X-Session-Token"], REDACTED_SESSION)
        self.assertEqual(body, {"project_id": "project-1", "page": 1, "page_size": 25})

    def test_unauthenticated_and_forbidden_contracts_are_distinct(self):
        status, unauthenticated = self.request("GET", "/auth/me", authenticated=False)
        self.assertEqual(status, 401)
        self.assertEqual(unauthenticated["detail"], "Não autenticado. Faça login.")

        status, forbidden = self.request("POST", "/tasks/query", {"project_id": "project-foreign"})
        self.assertEqual(status, 403)
        self.assertEqual(forbidden["detail"], "Sem acesso a este projeto.")


if __name__ == "__main__":
    unittest.main()
