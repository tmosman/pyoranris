import socket, threading, time
from pyoranris.net.tcp_interface import TCPInterface

def _start_echo_server(port, stop_event):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('127.0.0.1', port))
    s.listen(1)
    s.settimeout(0.5)
    try:
        conn, addr = s.accept()
        with conn:
            while not stop_event.is_set():
                try:
                    data = conn.recv(4096)
                    if not data:
                        break
                    conn.sendall(data)
                except Exception:
                    pass
    finally:
        s.close()

def test_tcp_roundtrip(tmp_path):
    port = 12000
    stop_event = threading.Event()
    t = threading.Thread(target=_start_echo_server, args=(port, stop_event), daemon=True)
    t.start()
    time.sleep(0.1)
    cli = TCPInterface('127.0.0.1', port)
    cli.connect()
    msg = b'hello'
    cli.send(msg)
    r = cli.recv(1024)
    assert r == msg
    stop_event.set()
    t.join(timeout=1)
