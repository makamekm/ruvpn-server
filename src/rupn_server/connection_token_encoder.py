from __future__ import annotations

import base64
import hashlib
import hmac
import json


class ConnectionTokenEncoder:
    def __init__(self, secret: str) -> None:
        self.secret = secret

    def encode(self, connection_uri: str) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {"uri": connection_uri}
        signing_input = ".".join([_base64url_json(header), _base64url_json(payload)])
        signature = hmac.new(self.secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
        return f"{signing_input}.{_base64url(signature)}"


def _base64url_json(value: dict[str, str]) -> str:
    encoded = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _base64url(encoded)


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
