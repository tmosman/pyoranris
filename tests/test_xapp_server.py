"""Tests for legacy binary xApp TCP server reconnect behavior."""

from __future__ import annotations

import socket
import struct
import threading
import time

from pyoranris.net.xapp_server import XAppServer


def test_handle_client_exits_when_peer_closes():
    srv = XAppServer("127.0.0.1", 8081)
    srv.running = True
    server_sock, client_sock = socket.socketpair()
    try:
        t = threading.Thread(target=srv.handle_client, args=(server_sock,), daemon=True)
        t.start()
        client_sock.send(struct.pack("iiii", 0, -60, 0, 1000))
        time.sleep(0.05)
        item = srv.data_queue.get_nowait()
        assert item[0] == -60
        client_sock.close()
        t.join(timeout=1.0)
        assert not t.is_alive()
        # Handler must not spin on zeros after disconnect.
        time.sleep(0.05)
        assert srv.data_queue.qsize() <= 1
    finally:
        server_sock.close()


def test_drain_queue_clears_stale_samples():
    srv = XAppServer("127.0.0.1", 8081)
    srv._enqueue_kpi([0, 0, 0])
    srv._enqueue_kpi([-55, 1.0, 2.0])
    srv.drain_queue()
    assert srv.data_queue.empty()
