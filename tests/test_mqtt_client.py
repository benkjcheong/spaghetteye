from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from spaghettimonster import mqtt_client  # noqa: E402


class _DummyClient:
    def __init__(self, bind_address: str = "", bind_port: int = 0):
        self._host = "192.168.1.33"
        self._port = 8883
        self._connect_timeout = 5
        self._bind_address = bind_address
        self._bind_port = bind_port

    def _get_proxy(self):
        return None


def test_create_socket_connection_skips_default_source_bind(monkeypatch):
    create_connection = Mock(return_value=object())
    monkeypatch.setattr(mqtt_client.socket, "create_connection", create_connection)

    out = mqtt_client._create_socket_connection(_DummyClient())

    assert out is create_connection.return_value
    create_connection.assert_called_once_with(("192.168.1.33", 8883), timeout=5)


def test_create_socket_connection_preserves_explicit_source_bind(monkeypatch):
    create_connection = Mock(return_value=object())
    monkeypatch.setattr(mqtt_client.socket, "create_connection", create_connection)

    out = mqtt_client._create_socket_connection(_DummyClient(bind_address="0.0.0.0", bind_port=40000))

    assert out is create_connection.return_value
    create_connection.assert_called_once_with(
        ("192.168.1.33", 8883),
        timeout=5,
        source_address=("0.0.0.0", 40000),
    )


def test_build_client_uses_async_connect(monkeypatch):
    connect_async_calls = []

    class DummyClient:
        def __init__(self, *args, **kwargs):
            self.on_connect = None
            self.on_disconnect = None
            self.on_message = None

        def username_pw_set(self, *args, **kwargs):
            pass

        def tls_set(self, *args, **kwargs):
            pass

        def tls_insecure_set(self, *args, **kwargs):
            pass

        def reconnect_delay_set(self, *args, **kwargs):
            pass

        def connect_async(self, *args, **kwargs):
            connect_async_calls.append((args, kwargs))

    monkeypatch.setattr(mqtt_client, "_PatchedClient", DummyClient)

    client = mqtt_client.build_client(
        printer_ip="192.168.1.33",
        printer_serial="0309BA531601162",
        access_code="12345678",
        on_payload=lambda payload: None,
    )

    assert isinstance(client, DummyClient)
    assert connect_async_calls == [(("192.168.1.33", 8883), {"keepalive": 60})]
