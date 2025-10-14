import socket
def main():
    host = '0.0.0.0' # listen on all interfaces
    port = 7896 # same port used by client
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((host, port))
        server_socket.listen(1)
        print(f"Server listening on port {port}...")
        while True:
            conn, addr = server_socket.accept()
            with conn:
                print(f"Connected by {addr}")
                data = conn.recv(1024).decode('utf-8')
                if not data:
                    break
                print("Received:", data)
                response = f"Echo: {data}"
                conn.sendall(response.encode('utf-8'))
if __name__ == "__main__":
    main()
