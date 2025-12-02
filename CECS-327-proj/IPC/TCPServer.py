import socket
from datetime import datetime
import json
import sys


def main(host="0.0.0.0", port=7896):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(3)
        print(f"Server listening on {host}:{port}...", flush=True)

        while True:
            try:
                conn, addr = server_socket.accept()
                print(f"[TCP] Connected by {addr}", flush=True)
                with conn:
                    while True:
                        data = conn.recv(1024)
                        if not data:
                            break
                        text = data.decode("utf-8").strip()
                        if text.startswith("{") or text.startswith("["):
                            pretty_print(text)
                        else:
                            print(f"TCP Direct Message: {text}\n", flush=True)
                        conn.sendall("Message Delivered.".encode("utf-8"))
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(
                            f"[{timestamp}] Message logged from {addr[0]}\n", flush=True
                        )
            except Exception as e:
                print(f"[ERROR] {e}", flush=True)


def pretty_print(data):
    try:
        parsed = json.loads(data)
        print(
            f"[MESSAGE SERVER] From {parsed.get('sender', 'Unknown')}: {parsed.get('content', data)}\n",
            flush=True,
        )
    except Exception:
        print(f"[RAW MESSAGE] {data}\n", flush=True)


if __name__ == "__main__":
    # Allow manual run like: python3 TCPServer.py 127.0.0.1 7897
    host = sys.argv[1] if len(sys.argv) > 1 else "0.0.0.0"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 7896
    main(host, port)
