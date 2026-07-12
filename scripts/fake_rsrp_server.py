#!/usr/bin/env python3
"""Emit fake RSRP lines for non-simulate profiles."""

import argparse
import socket
import time


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=10000)
    p.add_argument("--interval", type=float, default=0.5)
    args = p.parse_args()

    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((args.host, args.port))
    srv.listen(1)
    print(f"listening on {args.host}:{args.port}")
    conn, addr = srv.accept()
    print("client", addr)
    try:
        t = 0.0
        while True:
            rsrp = -70.0 + (t % 10)
            conn.sendall(f"{rsrp:.1f}, 0.0, 0.0\n".encode())
            t += 1
            time.sleep(args.interval)
    finally:
        conn.close()
        srv.close()


if __name__ == "__main__":
    main()
