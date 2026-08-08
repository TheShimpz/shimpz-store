"""Failure and capacity coverage for the hosted OAuth broker core."""

from __future__ import annotations

import json
from urllib.parse import urlencode

import pytest

from app import oauth_broker as broker


class _Unencodable(str):
    def encode(self, *_args, **_kwargs):
        raise UnicodeError


class _Undecodable(bytes):
    def decode(self, *_args, **_kwargs):
        raise UnicodeError


class _Transport:
    def __init__(self, response):
        self.response = response

    def request(self, **_request):
        if isinstance(self.response, BaseException):
            raise self.response
        return self.response


class _Client(broker.NeuronOAuthClient):
    def _access_headers(self):
        return {"CF-Access-Client-Id": "id", "CF-Access-Client-Secret": "secret"}


def _response(value, *, status=200, content_type="application/json"):
    body = value if isinstance(value, bytes) else json.dumps(value).encode()
    return broker.BrokerResponse(status, content_type, body)


def _authorization_url(state="a" * 43, challenge="b" * 43, **changes):
    fields = {
        "response_type": "code",
        "client_id": "cloudflare-client-id",
        "redirect_uri": broker.HOSTED_CALLBACK,
        "scope": " ".join(broker.SCOPES),
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    fields.update(changes)
    return "https://dash.cloudflare.com/oauth2/auth?" + urlencode(fields)


@pytest.mark.parametrize(
    ("operation", "value"),
    [
        (lambda value: broker._binding(value), None),
        (lambda value: broker._code(value, label="code"), None),
        (lambda value: broker._code(value, label="code"), "short"),
        (lambda value: broker._scopes(value), []),
    ],
)
def test_scalar_contracts_reject_invalid_values(operation, value):
    with pytest.raises(broker.OAuthBrokerError):
        operation(value)


@pytest.mark.parametrize(
    "value",
    [
        ["zone.read", "dns.read"],
        ["dns.read", "dns.read"],
        ["dns.read", "unknown"],
        ["dns.read", 1],
    ],
)
def test_caller_scopes_are_canonical_and_provider_scopes_stay_closed(value):
    with pytest.raises(broker.OAuthBrokerError):
        broker._scopes(value)
    if value != ["zone.read", "dns.read"]:
        with pytest.raises(broker.OAuthBrokerError):
            broker._returned_scopes(value)

    assert broker._returned_scopes(["zone.read", "dns.read"]) == ("dns.read", "zone.read")


def test_code_rejects_unencodable_text():
    with pytest.raises(broker.OAuthBrokerError):
        broker._code(_Unencodable("value"), label="code")


def test_secret_reader_translates_open_and_short_read_failures(tmp_path, monkeypatch):
    missing = tmp_path / "missing"
    with pytest.raises(broker.OAuthBrokerError, match="unavailable"):
        broker._read_secret(missing, maximum=32, modes=frozenset({0o400}))

    path = tmp_path / "secret"
    path.write_bytes(b"secret")
    path.chmod(0o400)
    monkeypatch.setattr(broker.os, "read", lambda *_args: b"")
    with pytest.raises(broker.OAuthBrokerError, match="file contract"):
        broker._read_secret(path, maximum=32, modes=frozenset({0o400}))

    chunks = iter((b"x" * 33,))
    monkeypatch.setattr(broker.os, "read", lambda *_args: next(chunks))
    with pytest.raises(broker.OAuthBrokerError, match="file contract"):
        broker._read_secret(path, maximum=32, modes=frozenset({0o400}))


def test_proxy_reader_translates_socket_and_size_failures(monkeypatch):
    class Failed:
        def recv(self, _maximum):
            raise OSError("failed")

    with pytest.raises(broker.OAuthBrokerError, match="unavailable"):
        broker._read_proxy_response(Failed())

    class Oversized:
        def recv(self, _maximum):
            return b"x" * (broker.MAX_PROXY_RESPONSE_BYTES + 1)

    with pytest.raises(broker.OAuthBrokerError, match="invalid"):
        broker._read_proxy_response(Oversized())


def test_neuron_tunnel_translates_connection_failure(monkeypatch):
    def fail(*_args, **_kwargs):
        raise OSError("failed")

    monkeypatch.setattr(broker.socket, "create_connection", fail)
    with pytest.raises(broker.OAuthBrokerError, match="unavailable"):
        broker._open_neuron_tunnel()


def test_fixed_transport_rejects_endpoint_oversize_and_http_failure(monkeypatch):
    transport = broker.FixedNeuronTransport()
    with pytest.raises(broker.OAuthBrokerError, match="endpoint"):
        transport.request(url="https://evil.example/path", headers={}, body=b"{}")

    class Response:
        status = 200

        @staticmethod
        def read(_maximum):
            return b"x" * (broker.MAX_RESPONSE_BYTES + 1)

        @staticmethod
        def getheader(_name, default=""):
            return default

    class Connection:
        def __init__(self, *_args, **_kwargs):
            self.sock = None

        def request(self, *_args, **_kwargs):
            pass

        def getresponse(self):
            return Response()

        def close(self):
            pass

    monkeypatch.setattr(broker, "_open_neuron_tunnel", lambda: object())
    monkeypatch.setattr(broker.http.client, "HTTPConnection", Connection)
    with pytest.raises(broker.OAuthBrokerError, match="response"):
        transport.request(
            url=f"{broker.NEURON_ORIGIN}/api/internal/oauth/cloudflare/authorization",
            headers={},
            body=b"{}",
        )

    def failed_request(self, *_args, **_kwargs):
        raise OSError("failed")

    monkeypatch.setattr(Connection, "request", failed_request)
    with pytest.raises(broker.OAuthBrokerError, match="unavailable"):
        transport.request(
            url=f"{broker.NEURON_ORIGIN}/api/internal/oauth/cloudflare/authorization",
            headers={},
            body=b"{}",
        )


def test_neuron_access_headers_reject_encoding_and_identity(tmp_path, monkeypatch):
    client = broker.NeuronOAuthClient(client_id_path=tmp_path / "id", client_secret_path=tmp_path / "secret")
    values = iter((_Undecodable(b"id"), b"secret-material-that-is-long-enough"))
    monkeypatch.setattr(broker, "_read_secret", lambda *_args, **_kwargs: next(values))
    with pytest.raises(broker.OAuthBrokerError, match="credential"):
        client._access_headers()

    values = iter((b"invalid", b"secret-material-that-is-long-enough"))
    monkeypatch.setattr(broker, "_read_secret", lambda *_args, **_kwargs: next(values))
    with pytest.raises(broker.OAuthBrokerError, match="credential"):
        client._access_headers()


@pytest.mark.parametrize(
    "response",
    [
        _response({}, status=500),
        _response(b"not-json"),
        _response([]),
    ],
)
def test_neuron_object_rejects_status_json_and_shape(response):
    with pytest.raises(broker.OAuthBrokerError):
        broker.NeuronOAuthClient._object(response)


def test_neuron_call_rejects_unknown_operation():
    with pytest.raises(broker.OAuthBrokerError, match="operation"):
        _Client(_Transport(_response({})))._call("unknown", {})


@pytest.mark.parametrize(
    "value",
    [
        {},
        {"authorization_url": 1},
        {"authorization_url": "https://dash.cloudflare.com/oauth2/auth?broken"},
        {"authorization_url": _authorization_url(response_type="token")},
    ],
)
def test_neuron_authorization_rejects_invalid_response(value):
    client = _Client(_Transport(_response(value)))
    with pytest.raises(broker.OAuthBrokerError, match="response"):
        client.authorization(state="a" * 43, code_challenge="b" * 43, scopes=broker.SCOPES)


@pytest.mark.parametrize(
    "value",
    [
        {},
        {"access_token": "a" * 16, "refresh_token": "b" * 16, "scopes": [], "expires_in": 3600},
        {
            "access_token": "a" * 16,
            "refresh_token": "b" * 16,
            "scopes": list(broker.SCOPES),
            "expires_in": True,
        },
    ],
)
def test_neuron_tokens_reject_invalid_shape_scopes_and_expiry(value):
    with pytest.raises(broker.OAuthBrokerError):
        broker.NeuronOAuthClient._tokens(value, broker.SCOPES)


def test_neuron_exchange_refresh_and_revoke_validate_results():
    tokens = {
        "access_token": "a" * 16,
        "refresh_token": "b" * 16,
        "scopes": list(broker.SCOPES),
        "expires_in": 3600,
    }
    client = _Client(_Transport(_response(tokens)))
    assert client.exchange(code="code", verifier="verifier", scopes=broker.SCOPES).expires_in == 3600
    client = _Client(_Transport(_response(tokens)))
    assert client.refresh(refresh_token="b" * 16, scopes=broker.SCOPES).expires_in == 3600
    client = _Client(_Transport(_response({"revoked": False})))
    with pytest.raises(broker.OAuthBrokerError):
        client.revoke(token="a" * 16)
    client = _Client(_Transport(_response({"revoked": True})))
    client.revoke(token="a" * 16)


def test_lease_signer_rejects_short_key_non_string_and_expired_lease():
    tokens = broker.OAuthTokens("a" * 16, "b" * 16, 3600)
    with pytest.raises(broker.OAuthBrokerError, match="key"):
        broker.BrokerLeaseSigner(b"short").issue(tokens, broker.SCOPES)
    now = 1_800_000_000
    signer = broker.BrokerLeaseSigner(b"k" * 32, clock=lambda: now)
    with pytest.raises(broker.OAuthBrokerError, match="lease"):
        signer.verify(None, tokens.access_token)
    lease = signer.issue(tokens, broker.SCOPES)
    with pytest.raises(broker.OAuthBrokerError, match="lease"):
        signer.verify(lease, "c" * 16)
    expired = broker.BrokerLeaseSigner(b"k" * 32, clock=lambda: now + broker.LEASE_TTL_SECONDS + 1)
    with pytest.raises(broker.OAuthBrokerError, match="lease"):
        expired.verify(lease, tokens.access_token)


class _Neuron:
    def __init__(self, *, fail_authorization=False, fail_exchange=False):
        self.fail_authorization = fail_authorization
        self.fail_exchange = fail_exchange

    def authorization(self, **_kwargs):
        if self.fail_authorization:
            raise broker.OAuthBrokerError("failed")
        return "https://dash.cloudflare.com/oauth2/auth"

    def exchange(self, **_kwargs):
        if self.fail_exchange:
            raise RuntimeError("failed")
        return broker.OAuthTokens("a" * 16, "b" * 16, 3600)


def _start(instance, state="s" * 43):
    return instance.start(
        local_state=state,
        local_code_challenge="c" * 43,
        callback_mode="out-of-band",
        scopes=list(broker.SCOPES),
    )


def test_broker_expires_grants_and_enforces_start_capacity(monkeypatch):
    instance = broker.OAuthBroker(_Neuron(), broker.BrokerLeaseSigner(b"k" * 32), clock=lambda: 100)
    tokens = broker.OAuthTokens("a" * 16, "b" * 16, 3600)
    for index, state in enumerate(("s" * 43, "t" * 43)):
        instance._authorizations[str(index) * 43] = broker._PendingAuthorization(
            state, "c" * 43, "hosted", "v" * 43, broker.SCOPES, 99
        )
        instance._grants[str(index) * 64] = broker._PendingGrant(state, "c" * 43, tokens, broker.SCOPES, 99)
        instance._active_local_states.add(state)
    instance._expire(100)
    assert not instance._authorizations and not instance._grants and not instance._active_local_states

    monkeypatch.setattr(broker, "CAPACITY", 0)
    with pytest.raises(broker.OAuthBrokerError, match="capacity"):
        _start(instance)


def test_broker_retries_binding_and_cleans_failed_authorization(monkeypatch):
    instance = broker.OAuthBroker(
        _Neuron(fail_authorization=True),
        broker.BrokerLeaseSigner(b"k" * 32),
        clock=lambda: 100,
    )
    instance._authorizations["a" * 43] = broker._PendingAuthorization(
        "x" * 43,
        "c" * 43,
        "hosted",
        "v" * 43,
        broker.SCOPES,
        200,
    )
    values = iter(("a" * 43, "b" * 43, "v" * 43))
    monkeypatch.setattr(instance, "_random_binding", lambda: next(values))
    with pytest.raises(broker.OAuthBrokerError):
        _start(instance)
    assert "b" * 43 not in instance._authorizations
    assert "s" * 43 not in instance._active_local_states


def test_broker_failed_authorization_tolerates_concurrent_removal():
    class RemovingNeuron:
        instance = None

        def authorization(self, **_kwargs):
            self.instance._authorizations.clear()
            raise broker.OAuthBrokerError("failed")

    neuron = RemovingNeuron()
    instance = broker.OAuthBroker(neuron, broker.BrokerLeaseSigner(b"k" * 32), clock=lambda: 100)
    neuron.instance = instance
    with pytest.raises(broker.OAuthBrokerError):
        _start(instance)


def test_broker_callback_enforces_capacity_and_cleans_failed_exchange(monkeypatch):
    instance = broker.OAuthBroker(_Neuron(), broker.BrokerLeaseSigner(b"k" * 32), clock=lambda: 100)
    _start(instance)
    state = next(iter(instance._authorizations))
    monkeypatch.setattr(broker, "CAPACITY", 0)
    with pytest.raises(broker.OAuthBrokerError, match="capacity"):
        instance.callback(state=state, code="authorization-code", scopes=list(broker.SCOPES))

    monkeypatch.setattr(broker, "CAPACITY", 4096)
    failed = broker.OAuthBroker(
        _Neuron(fail_exchange=True),
        broker.BrokerLeaseSigner(b"k" * 32),
        clock=lambda: 100,
    )
    _start(failed)
    failed_state = next(iter(failed._authorizations))
    with pytest.raises(RuntimeError, match="failed"):
        failed.callback(state=failed_state, code="authorization-code", scopes=list(broker.SCOPES))
    assert failed._grant_reservations == 0
    assert not failed._active_local_states


def test_broker_callback_retries_claim_collision_and_claim_rejects_shape(monkeypatch):
    instance = broker.OAuthBroker(_Neuron(), broker.BrokerLeaseSigner(b"k" * 32), clock=lambda: 100)
    _start(instance)
    state = next(iter(instance._authorizations))
    instance._grants["a" * 64] = broker._PendingGrant(
        "x" * 43,
        "c" * 43,
        broker.OAuthTokens("a" * 16, "b" * 16, 3600),
        broker.SCOPES,
        200,
    )
    values = iter(("a" * 64, "b" * 64))
    monkeypatch.setattr(broker.secrets, "token_hex", lambda _size: next(values))
    completion = instance.callback(state=state, code="authorization-code", scopes=list(broker.SCOPES))
    assert completion.completion_code.endswith("b" * 64)
    with pytest.raises(broker.OAuthBrokerError, match="grant"):
        instance.claim(claim="bad", state="s" * 43, code_verifier="v" * 43)
