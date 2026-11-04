"""ORCID sign-in (OAuth 2, the `/authenticate` scope of ORCID's free public API).

The portal learns only the signed-in person's ORCID iD and name; it asks for no other access to their record.
"""

import json
import urllib.error
import urllib.parse
import urllib.request


class OrcidError(Exception):
    pass


class OrcidClient:
    def __init__(self, base, client_id, client_secret, redirect_uri, timeout=15):
        self.base = base.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.timeout = timeout

    @property
    def configured(self):
        return bool(self.client_id and self.client_secret)

    def authorize_url(self, state):
        q = urllib.parse.urlencode({"client_id": self.client_id, "response_type": "code", "scope": "/authenticate",
                                    "redirect_uri": self.redirect_uri, "state": state})
        return f"{self.base}/oauth/authorize?{q}"

    def exchange(self, code):
        """(ORCID iD, name) of the person who signed in, from the authorization code ORCID returned."""
        data = urllib.parse.urlencode({"client_id": self.client_id, "client_secret": self.client_secret,
                                       "grant_type": "authorization_code", "code": code,
                                       "redirect_uri": self.redirect_uri}).encode()
        req = urllib.request.Request(f"{self.base}/oauth/token", data=data, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                out = json.loads(res.read())
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise OrcidError(f"ORCID sign-in could not be completed: {exc}") from exc
        if not out.get("orcid"):
            raise OrcidError("ORCID did not return an ORCID iD")
        return out["orcid"], out.get("name")
