"""Offline compatibility checks for LeagueLedger's NetID PyJWT path."""

import io
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from unittest.mock import MagicMock, Mock, patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm
from jwt.exceptions import PyJWKClientConnectionError
from jwt.jwks_client import PyJWKClient


def _jwks_response(public_key):
    payload = {"keys": [json.loads(RSAAlgorithm.to_jwk(public_key)) | {"kid": "test"}]}
    return io.BytesIO(json.dumps(payload).encode())


def test_netid_rs256_token_validates_without_network():
    """A valid RS256 NetID-style token remains accepted by PyJWKClient."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    token = jwt.encode(
        {"sub": "offline-test", "aud": "leagueledger", "exp": 4102444800},
        private_key,
        algorithm="RS256",
        headers={"kid": "test"},
    )
    opener = MagicMock()
    opener.open.return_value.__enter__.return_value = _jwks_response(public_key)
    urlopen = Mock(return_value=_jwks_response(public_key))
    with (
        patch("jwt.jwks_client.urllib.request.build_opener", return_value=opener),
        patch(
            "jwt.jwks_client.urllib.request.urlopen",
            new=urlopen,
        ),
    ):
        signing_key = PyJWKClient("https://broker.netid.de/jwks").get_signing_key_from_jwt(token)
        claims = jwt.decode(token, signing_key.key, algorithms=["RS256"], audience="leagueledger")
    assert claims["sub"] == "offline-test"
    assert opener.open.call_count + urlopen.call_count == 1


def test_pyjwt_client_does_not_follow_jwks_redirect():
    """The patched client rejects a redirect without contacting its target."""
    reached = {"jwks": 0, "target": 0}

    class RedirectHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler API
            if self.path == "/jwks":
                reached["jwks"] += 1
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{self.server.server_port}/target")
                self.send_header("Content-Length", "0")
                self.end_headers()
            elif self.path == "/target":
                reached["target"] += 1
                body = b'{"keys": []}'
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        def log_message(self, _format, *_args):
            return

    server = HTTPServer(("127.0.0.1", 0), RedirectHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        error = None
        try:
            PyJWKClient(
                f"http://127.0.0.1:{server.server_port}/jwks", cache_jwk_set=False
            ).get_signing_key("unknown")
        except Exception as exc:  # the assertion below checks the exact API error
            error = exc
        assert reached["jwks"] >= 1
        assert reached["target"] == 0
        assert isinstance(error, PyJWKClientConnectionError)
    finally:
        server.shutdown()
        thread.join(timeout=2)

