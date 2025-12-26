import time
from app.security import sign_payload
from app.api import _enforce_node_ip_allowlist
from types import SimpleNamespace
import ipaddress
import pytest


def test_sign_payload_changes_with_nonce():
    body = b'{"config":{}}'
    sig1 = sign_payload("secret", body, "1", "nonce1")
    sig2 = sign_payload("secret", body, "1", "nonce2")
    assert sig1 != sig2


def test_enforce_node_ip_allowlist():
    settings = SimpleNamespace(node_agent_allowed_ips=["10.0.0.0/24", "192.168.1.10"])
    _enforce_node_ip_allowlist("10.0.0.5", settings)
    _enforce_node_ip_allowlist("192.168.1.10", settings)
    with pytest.raises(Exception):
        _enforce_node_ip_allowlist("8.8.8.8", settings)
