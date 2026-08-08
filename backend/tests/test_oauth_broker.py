from __future__ import annotations

import concurrent.futures
import json
import tempfile
import threading
from pathlib import Path
from typing import ClassVar
from unittest import mock
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest

from app.oauth_broker import (
    ACCESS_CLIENT_ID_PATH,
    ACCESS_CLIENT_SECRET_PATH,
    HOSTED_ADMIN_CALLBACK,
    HOSTED_CALLBACK,
    LEASE_KEY_PATH,
    LOCAL_CALLBACK,
    SCOPES,
    BrokerLeaseSigner,
    BrokerResponse,
    FixedNeuronTransport,
    NeuronOAuthClient,
    OAuthBroker,
    OAuthBrokerError,
    OAuthOutOfBand,
    OAuthRedirect,
    OAuthTokens,
    _pkce_challenge,
)


def test_default_lease_key_uses_the_initialized_private_volume() -> None:
    assert Path("/run/shimpz-store-oauth/access-client-id") == ACCESS_CLIENT_ID_PATH
    assert Path("/run/shimpz-store-oauth/access-client-secret") == ACCESS_CLIENT_SECRET_PATH
    assert Path("/run/shimpz-store-oauth/lease-key") == LEASE_KEY_PATH


class _ProxySocket:
    def __init__(self, response: bytes) -> None:
        self.response = response
        self.sent = bytearray()
        self.closed = False

    def settimeout(self, _timeout: int) -> None:
        pass

    def sendall(self, payload: bytes) -> None:
        self.sent.extend(payload)

    def recv(self, _maximum: int) -> bytes:
        response, self.response = self.response, b""
        return response

    def close(self) -> None:
        self.closed = True


class _TlsContext:
    def __init__(self, secured: object) -> None:
        self.secured = secured
        self.calls: list[tuple[object, str]] = []

    def wrap_socket(self, stream: object, *, server_hostname: str) -> object:
        self.calls.append((stream, server_hostname))
        return self.secured


class _HttpResponse:
    status = 200

    @staticmethod
    def getheader(name: str, default: str = "") -> str:
        return "application/json" if name == "Content-Type" else default

    @staticmethod
    def read(_maximum: int) -> bytes:
        return b'{"authorization_url":"https://dash.cloudflare.com/oauth2/auth"}'


class _HttpConnection:
    instances: ClassVar[list[_HttpConnection]] = []

    def __init__(self, host: str, *, timeout: int) -> None:
        self.host = host
        self.timeout = timeout
        self.sock: object | None = None
        self.request_call: tuple[str, str, bytes, dict[str, str]] | None = None
        self.closed = False
        self.instances.append(self)

    def request(self, method: str, path: str, *, body: bytes, headers: dict[str, str]) -> None:
        self.request_call = (method, path, body, headers)

    @staticmethod
    def getresponse() -> _HttpResponse:
        return _HttpResponse()

    def close(self) -> None:
        self.closed = True


def test_fixed_transport_uses_exact_connect_proxy_and_end_to_end_neuron_tls() -> None:
    proxy = _ProxySocket(b"HTTP/1.1 200 Connection established\r\n\r\n")
    secured = object()
    context = _TlsContext(secured)
    _HttpConnection.instances.clear()
    with (
        mock.patch("app.oauth_broker.socket.create_connection", return_value=proxy) as connect,
        mock.patch("app.oauth_broker.ssl.create_default_context", return_value=context),
        mock.patch("app.oauth_broker.http.client.HTTPConnection", _HttpConnection),
    ):
        response = FixedNeuronTransport().request(
            url="https://neuron.shimpz.com/api/internal/oauth/cloudflare/authorization",
            headers={"Content-Type": "application/json"},
            body=b"{}",
        )

    assert response.status == 200
    connect.assert_called_once_with(("shimpz-store-egress", 8889), timeout=10)
    assert bytes(proxy.sent) == (b"CONNECT neuron.shimpz.com:443 HTTP/1.1\r\nHost: neuron.shimpz.com:443\r\n\r\n")
    assert context.calls == [(proxy, "neuron.shimpz.com")]
    connection = _HttpConnection.instances[0]
    assert connection.host == "neuron.shimpz.com"
    assert connection.sock is secured
    assert connection.request_call is not None
    assert connection.request_call[:2] == ("POST", "/api/internal/oauth/cloudflare/authorization")
    assert connection.closed


@pytest.mark.parametrize(
    "proxy_response",
    [
        b"HTTP/1.1 403 Forbidden\r\n\r\n",
        b"HTTP/1.1 200 Connection established\r\nUnexpected: value\r\n\r\n",
        b"",
    ],
)
def test_fixed_transport_fails_closed_on_proxy_response(proxy_response: bytes) -> None:
    proxy = _ProxySocket(proxy_response)
    with (
        mock.patch("app.oauth_broker.socket.create_connection", return_value=proxy),
        pytest.raises(OAuthBrokerError),
    ):
        FixedNeuronTransport().request(
            url="https://neuron.shimpz.com/api/internal/oauth/cloudflare/authorization",
            headers={"Content-Type": "application/json"},
            body=b"{}",
        )
    assert proxy.closed


class _Transport:
    def __init__(self, responses: list[BrokerResponse]) -> None:
        self.responses = responses
        self.requests: list[dict[str, object]] = []

    def request(self, **request) -> BrokerResponse:
        self.requests.append(request)
        return self.responses.pop(0)


class _Neuron:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def authorization(self, *, state: str, code_challenge: str, scopes: tuple[str, ...]) -> str:
        self.calls.append(("authorization", (state, code_challenge, scopes)))
        return "https://dash.cloudflare.com/oauth2/auth"

    def exchange(self, *, code: str, verifier: str, scopes: tuple[str, ...]) -> OAuthTokens:
        self.calls.append(("exchange", (code, verifier, scopes)))
        return OAuthTokens("access-token-private-123456", "refresh-token-private-123456", 3600)

    def refresh(self, *, refresh_token: str, scopes: tuple[str, ...]) -> OAuthTokens:
        self.calls.append(("refresh", (refresh_token, scopes)))
        return OAuthTokens("rotated-access-private-123456", "rotated-refresh-private-123456", 3600)

    def revoke(self, *, token: str) -> None:
        self.calls.append(("revoke", token))


def _secret(path: Path, value: bytes) -> Path:
    path.write_bytes(value)
    path.chmod(0o400)
    return path


def test_neuron_client_sends_access_service_identity_and_validates_fixed_authorization() -> None:
    state = "a" * 43
    challenge = "b" * 43
    authorization_url = "https://dash.cloudflare.com/oauth2/auth?" + urlencode(
        {
            "response_type": "code",
            "client_id": "cloudflare-client-id-123456",
            "redirect_uri": HOSTED_CALLBACK,
            "scope": " ".join(SCOPES),
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    transport = _Transport(
        [
            BrokerResponse(
                200,
                "application/json",
                json.dumps({"authorization_url": authorization_url}).encode(),
            )
        ]
    )
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        client = NeuronOAuthClient(
            transport,
            client_id_path=_secret(root / "id", ("c" * 32 + ".access").encode()),
            client_secret_path=_secret(root / "secret", b"service-token-private-material-123456"),
        )
        assert client.authorization(state=state, code_challenge=challenge, scopes=SCOPES) == authorization_url

    request = transport.requests[0]
    assert request["url"] == "https://neuron.shimpz.com/api/internal/oauth/cloudflare/authorization"
    assert request["headers"]["CF-Access-Client-Id"] == "c" * 32 + ".access"
    assert "CF-Access-Client-Secret" in request["headers"]
    assert "client_secret" not in request["body"].decode()


def test_neuron_client_rejects_world_readable_access_files() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        client_id = _secret(root / "id", ("c" * 32 + ".access").encode())
        client_id.chmod(0o444)
        client = NeuronOAuthClient(
            _Transport([]),
            client_id_path=client_id,
            client_secret_path=_secret(root / "secret", b"service-token-private-material-123456"),
        )

        with pytest.raises(OAuthBrokerError, match="file contract"):
            client.authorization(state="a" * 43, code_challenge="b" * 43, scopes=SCOPES)


def test_broker_lease_signer_rejects_a_world_readable_key() -> None:
    with tempfile.TemporaryDirectory() as directory:
        key = _secret(Path(directory) / "lease-key", b"k" * 32)
        key.chmod(0o444)

        with pytest.raises(OAuthBrokerError, match="file contract"):
            BrokerLeaseSigner(key_path=key).issue(OAuthTokens("access-token", "refresh-token", 3600), SCOPES)


def test_broker_keeps_tokens_out_of_browser_and_claims_once_with_local_pkce() -> None:
    neuron = _Neuron()
    signer = BrokerLeaseSigner(b"k" * 32, clock=lambda: 1_800_000_000)
    broker = OAuthBroker(neuron, signer, clock=lambda: 100.0)
    local_verifier = "v" * 43
    local_state = "s" * 43

    authorization_url = broker.start(
        local_state=local_state,
        local_code_challenge=_pkce_challenge(local_verifier),
        callback_mode="loopback",
        scopes=list(SCOPES),
    )
    assert authorization_url == "https://dash.cloudflare.com/oauth2/auth"
    broker_state = neuron.calls[0][1][0]
    completion = broker.callback(
        state=broker_state,
        code="authorization-code-private-123456",
        scopes=list(SCOPES),
    )
    assert isinstance(completion, OAuthRedirect)
    callback = completion.location
    parsed = urlsplit(callback)
    query = parse_qs(parsed.query, strict_parsing=True)
    assert callback.startswith(LOCAL_CALLBACK + "?")
    assert set(query) == {"state", "claim"}
    assert "access-token" not in callback
    assert "refresh-token" not in callback

    payload = broker.claim(claim=query["claim"][0], state=local_state, code_verifier=local_verifier)
    assert set(payload) == {
        "access_token",
        "refresh_token",
        "expires_in",
        "scopes",
        "broker_lease",
    }
    with pytest.raises(OAuthBrokerError):
        broker.claim(claim=query["claim"][0], state=local_state, code_verifier=local_verifier)

    refreshed = broker.refresh(
        refresh_token=payload["refresh_token"],
        lease=payload["broker_lease"],
        scopes=list(SCOPES),
    )
    broker.revoke(token=refreshed["access_token"], lease=refreshed["broker_lease"])
    assert [call[0] for call in neuron.calls] == [
        "authorization",
        "exchange",
        "refresh",
        "revoke",
    ]


def test_broker_preserves_a_read_only_scope_subset_without_refresh_widening() -> None:
    read_scopes = ("dns.read", "offline_access", "zone.read")
    neuron = _Neuron()
    broker = OAuthBroker(neuron, BrokerLeaseSigner(b"k" * 32), clock=lambda: 100.0)
    verifier = "v" * 43
    state = "s" * 43

    broker.start(
        local_state=state,
        local_code_challenge=_pkce_challenge(verifier),
        callback_mode="out-of-band",
        scopes=list(read_scopes),
    )
    completion = broker.callback(
        state=neuron.calls[0][1][0],
        code="authorization-code-private-123456",
        scopes=list(read_scopes),
    )
    assert isinstance(completion, OAuthOutOfBand)
    claim = completion.completion_code.rsplit(".", 1)[1]
    payload = broker.claim(claim=claim, state=state, code_verifier=verifier)

    assert payload["scopes"] == list(read_scopes)
    assert neuron.calls[0][1][2] == read_scopes
    assert neuron.calls[1][1][2] == read_scopes
    with pytest.raises(OAuthBrokerError, match="lease"):
        broker.refresh(
            refresh_token=payload["refresh_token"],
            lease=payload["broker_lease"],
            scopes=list(SCOPES),
        )
    assert [call[0] for call in neuron.calls] == ["authorization", "exchange"]


def test_broker_refuses_callback_scope_drift_before_token_exchange() -> None:
    read_scopes = ("dns.read", "offline_access", "zone.read")
    neuron = _Neuron()
    broker = OAuthBroker(neuron, BrokerLeaseSigner(b"k" * 32), clock=lambda: 100.0)
    state = "s" * 43
    broker.start(
        local_state=state,
        local_code_challenge="c" * 43,
        callback_mode="out-of-band",
        scopes=list(read_scopes),
    )

    with pytest.raises(OAuthBrokerError, match="unavailable"):
        broker.callback(
            state=neuron.calls[0][1][0],
            code="authorization-code-private-123456",
            scopes=list(SCOPES),
        )

    assert [call[0] for call in neuron.calls] == ["authorization"]
    assert not broker._authorizations
    assert not broker._active_local_states


def test_broker_returns_only_the_named_hosted_admin_callback() -> None:
    neuron = _Neuron()
    broker = OAuthBroker(neuron, BrokerLeaseSigner(b"k" * 32), clock=lambda: 100.0)
    broker.start(
        local_state="s" * 43,
        local_code_challenge="c" * 43,
        callback_mode="hosted",
        scopes=list(SCOPES),
    )
    state = neuron.calls[0][1][0]

    completion = broker.callback(state=state, code="authorization-code-private-123456", scopes=list(SCOPES))

    assert isinstance(completion, OAuthRedirect)
    assert completion.location.startswith(HOSTED_ADMIN_CALLBACK + "?")
    with pytest.raises(OAuthBrokerError):
        broker.start(
            local_state="s" * 43,
            local_code_challenge="c" * 43,
            callback_mode="https://evil.example",
            scopes=list(SCOPES),
        )


def test_broker_rejects_wrong_pkce_tampered_lease_and_expired_state() -> None:
    neuron = _Neuron()
    now = [100.0]
    broker = OAuthBroker(
        neuron,
        BrokerLeaseSigner(b"k" * 32, clock=lambda: now[0]),
        clock=lambda: now[0],
    )
    verifier = "v" * 43
    broker.start(
        local_state="s" * 43,
        local_code_challenge=_pkce_challenge(verifier),
        callback_mode="loopback",
        scopes=list(SCOPES),
    )
    state = neuron.calls[0][1][0]
    completion = broker.callback(state=state, code="authorization-code-private-123456", scopes=list(SCOPES))
    assert isinstance(completion, OAuthRedirect)
    claim = parse_qs(urlsplit(completion.location).query)["claim"][0]
    with pytest.raises(OAuthBrokerError):
        broker.claim(claim=claim, state="s" * 43, code_verifier="x" * 43)
    payload = broker.claim(claim=claim, state="s" * 43, code_verifier=verifier)
    with pytest.raises(OAuthBrokerError):
        broker.refresh(
            refresh_token=payload["refresh_token"],
            lease=str(payload["broker_lease"])[:-1] + "x",
            scopes=list(SCOPES),
        )

    broker.start(
        local_state="t" * 43,
        local_code_challenge=_pkce_challenge(verifier),
        callback_mode="loopback",
        scopes=list(SCOPES),
    )
    expired_state = neuron.calls[-1][1][0]
    now[0] += 301
    with pytest.raises(OAuthBrokerError):
        broker.callback(state=expired_state, code="authorization-code-private-123456", scopes=list(SCOPES))


def test_broker_out_of_band_completion_keeps_the_fixed_claim_and_pkce_contract() -> None:
    neuron = _Neuron()
    now = [100.0]
    broker = OAuthBroker(neuron, BrokerLeaseSigner(b"k" * 32), clock=lambda: now[0])
    verifier = "v" * 43
    state = "s" * 43
    broker.start(
        local_state=state,
        local_code_challenge=_pkce_challenge(verifier),
        callback_mode="out-of-band",
        scopes=list(SCOPES),
    )

    completion = broker.callback(
        state=neuron.calls[0][1][0],
        code="authorization-code-private-123456",
        scopes=list(SCOPES),
    )

    assert isinstance(completion, OAuthOutOfBand)
    version, returned_state, claim = completion.completion_code.split(".")
    assert version == "c1"
    assert returned_state == state
    assert len(claim) == 64
    assert "access-token" not in completion.completion_code
    now[0] += 299
    assert broker.claim(claim=claim, state=state, code_verifier=verifier)["access_token"].startswith("access-token")


def test_broker_reserves_one_local_state_until_its_grant_is_claimed() -> None:
    neuron = _Neuron()
    broker = OAuthBroker(neuron, BrokerLeaseSigner(b"k" * 32), clock=lambda: 100.0)
    verifier = "v" * 43
    state = "s" * 43

    def start() -> str:
        return broker.start(
            local_state=state,
            local_code_challenge=_pkce_challenge(verifier),
            callback_mode="out-of-band",
            scopes=list(SCOPES),
        )

    start()
    with pytest.raises(OAuthBrokerError, match="unavailable"):
        start()
    completion = broker.callback(
        state=neuron.calls[0][1][0],
        code="authorization-code-private-123456",
        scopes=list(SCOPES),
    )
    assert isinstance(completion, OAuthOutOfBand)
    with pytest.raises(OAuthBrokerError, match="unavailable"):
        start()

    _, _, claim = completion.completion_code.split(".")
    broker.claim(claim=claim, state=state, code_verifier=verifier)
    assert start() == "https://dash.cloudflare.com/oauth2/auth"


def test_broker_reserves_local_state_while_neuron_exchanges_the_code() -> None:
    entered = threading.Event()
    release = threading.Event()

    class BlockingNeuron(_Neuron):
        def exchange(self, *, code: str, verifier: str, scopes: tuple[str, ...]) -> OAuthTokens:
            entered.set()
            if not release.wait(1):
                raise RuntimeError("test exchange timed out")
            return super().exchange(code=code, verifier=verifier, scopes=scopes)

    neuron = BlockingNeuron()
    broker = OAuthBroker(neuron, BrokerLeaseSigner(b"k" * 32), clock=lambda: 100.0)
    state = "s" * 43
    broker.start(
        local_state=state,
        local_code_challenge="c" * 43,
        callback_mode="out-of-band",
        scopes=list(SCOPES),
    )
    broker_state = neuron.calls[0][1][0]
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        exchange = executor.submit(
            broker.callback,
            state=broker_state,
            code="authorization-code-private-123456",
            scopes=list(SCOPES),
        )
        assert entered.wait(1)
        try:
            with pytest.raises(OAuthBrokerError, match="unavailable"):
                broker.start(
                    local_state=state,
                    local_code_challenge="c" * 43,
                    callback_mode="out-of-band",
                    scopes=list(SCOPES),
                )
        finally:
            release.set()
        assert isinstance(exchange.result(timeout=1), OAuthOutOfBand)
