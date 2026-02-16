#!/usr/bin/env python3
"""
Find the first open port in a range. Used by run_dashboard.sh to avoid port conflicts.
Usage: python scripts/find_port.py <start> <end>
Prints the port number to stdout and exits 0, or exits 1 if none free.
"""
import socket
import sys


def is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(('', port))
            return True
        except OSError:
            return False


def find_port(start: int, end: int):
    for port in range(start, end + 1):
        if is_port_free(port):
            return port
    return None


def main():
    if len(sys.argv) != 3:
        print("Usage: find_port.py <start> <end>", file=sys.stderr)
        sys.exit(2)
    start = int(sys.argv[1])
    end = int(sys.argv[2])
    port = find_port(start, end)
    if port is not None:
        print(port)
        sys.exit(0)
    sys.exit(1)


if __name__ == '__main__':
    main()
