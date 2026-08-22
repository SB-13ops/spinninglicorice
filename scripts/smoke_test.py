#!/usr/bin/env python3
"""Burnt Jacket post-deploy smoke test.

Walks the critical path against a *running* Burnt Jacket API and reports pass/fail
per check, with a non-zero exit code if anything critical fails. Use it right
after a deploy to confirm the API is healthy and the core flows work.

Only dependency is httpx:  pip install httpx

Usage:
    python smoke_test.py --base-url https://your-api.up.railway.app
    python smoke_test.py --base-url http://localhost:8000        # local

What it checks (in order):
    1.  GET  /api/v1/health                  -> API is up
    2.  POST /api/v1/auth/register           -> can create an account
    3.  POST /api/v1/auth/login (form)       -> can log in, get a JWT
    4.  GET  /api/v1/auth/me                  -> the JWT works
    5.  GET  /api/v1/collection               -> a protected route returns data
    6.  GET  /api/v1/home/feed                -> home feed (incl. hero) resolves
    7.  POST /api/v1/hunter/hunts             -> can create a hunt
    8.  POST /api/v1/hunter/parse             -> NL parse works (AI or regex)
    9.  POST /api/v1/groups                   -> social layer works
    10. GET  /api/v1/ai/status                -> reports AI enabled/disabled
    11. GET  /api/v1/collection (no auth)     -> correctly rejected (401)

Notes:
    * This creates a throwaway user each run (email uses a timestamp).
    * It does NOT test the Google/Facebook or Discogs OAuth round-trips — those
      need a real browser. It DOES tell you whether AI is configured.
"""
from __future__ import annotations

import argparse
import sys
import time
import uuid

try:
    import httpx
except ImportError:
    print("This script needs httpx:  pip install httpx")
    sys.exit(2)


class Runner:
    def __init__(self, base_url: str, timeout: float):
        self.base = base_url.rstrip("/")
        self.api = f"{self.base}/api/v1"
        self.client = httpx.Client(timeout=timeout, follow_redirects=False)
        self.passed = 0
        self.failed = 0
        self.warned = 0
        self.token: str | None = None
        self.email = f"smoke-{int(time.time())}-{uuid.uuid4().hex[:6]}@example.com"
        self.password = "smoke-test-password-123"

    # -- reporting -----------------------------------------------------------
    def ok(self, label: str, detail: str = ""):
        self.passed += 1
        print(f"  \033[32mPASS\033[0m  {label}" + (f"  ({detail})" if detail else ""))

    def fail(self, label: str, detail: str = ""):
        self.failed += 1
        print(f"  \033[31mFAIL\033[0m  {label}" + (f"  ({detail})" if detail else ""))

    def warn(self, label: str, detail: str = ""):
        self.warned += 1
        print(f"  \033[33mWARN\033[0m  {label}" + (f"  ({detail})" if detail else ""))

    def auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    # -- checks --------------------------------------------------------------
    def check_health(self):
        try:
            r = self.client.get(f"{self.api}/health")
            if r.status_code == 200 and r.json().get("status") == "ok":
                self.ok("health", r.json().get("service", ""))
            else:
                self.fail("health", f"status {r.status_code}")
        except Exception as exc:
            self.fail("health", f"unreachable: {exc}")
            return False
        return True

    def check_register(self):
        try:
            r = self.client.post(
                f"{self.api}/auth/register",
                json={"email": self.email, "password": self.password, "display_name": "Smoke Test"},
            )
            if r.status_code in (200, 201) and r.json().get("access_token"):
                self.token = r.json()["access_token"]
                self.ok("register + token issued")
            else:
                self.fail("register", f"status {r.status_code}: {r.text[:120]}")
        except Exception as exc:
            self.fail("register", str(exc))

    def check_login(self):
        # login uses the OAuth2 password form: fields username + password.
        try:
            r = self.client.post(
                f"{self.api}/auth/login",
                data={"username": self.email, "password": self.password},
            )
            if r.status_code == 200 and r.json().get("access_token"):
                self.token = r.json()["access_token"]  # prefer the fresh token
                self.ok("login (form) + token")
            else:
                self.fail("login", f"status {r.status_code}: {r.text[:120]}")
        except Exception as exc:
            self.fail("login", str(exc))

    def check_me(self):
        try:
            r = self.client.get(f"{self.api}/auth/me", headers=self.auth_headers())
            if r.status_code == 200 and r.json().get("email") == self.email:
                self.ok("auth/me (token valid)")
            else:
                self.fail("auth/me", f"status {r.status_code}")
        except Exception as exc:
            self.fail("auth/me", str(exc))

    def check_get(self, path: str, label: str):
        try:
            r = self.client.get(f"{self.api}{path}", headers=self.auth_headers())
            if r.status_code == 200:
                self.ok(label)
            else:
                self.fail(label, f"status {r.status_code}: {r.text[:120]}")
        except Exception as exc:
            self.fail(label, str(exc))

    def check_create_hunt(self):
        try:
            r = self.client.post(
                f"{self.api}/hunter/hunts",
                headers=self.auth_headers(),
                json={"name": "Smoke hunt", "query": "Bowie under $40", "auto_hunt": False},
            )
            if r.status_code in (200, 201):
                self.ok("create hunt")
            else:
                self.fail("create hunt", f"status {r.status_code}: {r.text[:120]}")
        except Exception as exc:
            self.fail("create hunt", str(exc))

    def check_parse(self):
        try:
            r = self.client.post(
                f"{self.api}/hunter/parse",
                headers=self.auth_headers(),
                json={"query": "early Miles Davis I don't own, VG+ or better under $40"},
            )
            if r.status_code == 200 and "criteria" in r.json():
                crit = r.json()["criteria"]
                self.ok("hunt parse", f"artists={crit.get('artists')}, price={crit.get('max_price')}")
            else:
                self.fail("hunt parse", f"status {r.status_code}")
        except Exception as exc:
            self.fail("hunt parse", str(exc))

    def check_create_group(self):
        try:
            r = self.client.post(
                f"{self.api}/groups",
                headers=self.auth_headers(),
                json={"name": "Smoke group", "description": "smoke test"},
            )
            if r.status_code in (200, 201):
                self.ok("create group (social layer)")
            else:
                self.fail("create group", f"status {r.status_code}: {r.text[:120]}")
        except Exception as exc:
            self.fail("create group", str(exc))

    def check_ai_status(self):
        try:
            r = self.client.get(f"{self.api}/ai/status")
            if r.status_code == 200:
                enabled = r.json().get("enabled")
                if enabled:
                    self.ok("ai/status", "AI ENABLED")
                else:
                    # Not a failure — AI is optional — but worth flagging.
                    self.warn("ai/status", "AI disabled (no ANTHROPIC_API_KEY set)")
            else:
                self.fail("ai/status", f"status {r.status_code}")
        except Exception as exc:
            self.fail("ai/status", str(exc))

    def check_auth_required(self):
        try:
            r = self.client.get(f"{self.api}/collection")  # no auth header
            if r.status_code == 401:
                self.ok("unauthenticated request rejected (401)")
            else:
                self.fail("auth enforcement", f"expected 401, got {r.status_code}")
        except Exception as exc:
            self.fail("auth enforcement", str(exc))

    # -- run -----------------------------------------------------------------
    def run(self) -> int:
        print(f"\nBurnt Jacket smoke test → {self.base}\n")
        if not self.check_health():
            print("\nAPI is unreachable; stopping.\n")
            return 1
        self.check_register()
        if not self.token:
            print("\nCould not obtain a token; stopping auth-dependent checks.\n")
        else:
            self.check_login()
            self.check_me()
            self.check_get("/collection", "collection (protected)")
            self.check_get("/home/feed", "home feed (hero resolves)")
            self.check_create_hunt()
            self.check_parse()
            self.check_create_group()
            self.check_get("/insights/value", "insights: value summary")
            self.check_get("/insights/completion", "insights: completion")
        self.check_ai_status()
        self.check_auth_required()

        print(
            f"\n{self.passed} passed, {self.failed} failed"
            + (f", {self.warned} warning(s)" if self.warned else "")
            + "\n"
        )
        return 0 if self.failed == 0 else 1


def main():
    ap = argparse.ArgumentParser(description="Burnt Jacket post-deploy smoke test")
    ap.add_argument("--base-url", required=True, help="e.g. https://your-api.up.railway.app")
    ap.add_argument("--timeout", type=float, default=30.0)
    args = ap.parse_args()
    sys.exit(Runner(args.base_url, args.timeout).run())


if __name__ == "__main__":
    main()
