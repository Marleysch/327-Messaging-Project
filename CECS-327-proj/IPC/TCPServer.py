import socket
from datetime import datetime
import json

def main():
    host = '0.0.0.0' # listen on all interfaces
    port = 7896 # same port used by client

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((host, port))
        server_socket.listen(3) # let multiple clients connect
        print(f"Server listening on port {port}...")
        while True:
            try:
                conn, addr = server_socket.accept()
                print(f"Connected by {addr}")
                with conn:
                    while True:
                        data = conn.recv(1024).decode('utf-8')
                        if not data:
                            break
                        if data.startswith("{") or data.startswith("["):
                            pretty_print(data)
                        else:
                            print(f"TCP Direct Message: {data}\n")
                        conn.sendall("Message Delivered.".encode('utf-8'))
                        print(f"[Message Log] | From {addr}")
            except Exception as e:
                print(f"[ERROR] {e}")


# helper funct to make output more readable
def pretty_print(data):
    parsed = json.loads(data)
    print(f"[MESSAGE SERVER] From {parsed['sender']}: {parsed['content']}\n")


if __name__ == "__main__":
    main()

