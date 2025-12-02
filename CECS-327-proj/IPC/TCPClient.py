import socket
import sys


def main():
    try:
        if len(sys.argv) < 4:
            print("Usage: python3 TCPClient.py <message> <host> <port>")
            return

        message = sys.argv[1]
        host = sys.argv[2]
        server_port = int(sys.argv[3])

        # create a socket and connect to server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            print(f"[CLIENT] Connecting to {host}:{server_port}...")
            s.connect((host, server_port))

            # Send the message
            s.sendall(message.encode("utf-8"))

            # receive the response
            data = s.recv(1024).decode("utf-8")
            print(f"[SERVER RESPONSE] {data}")

    except IndexError:
        print("Usage: python3 TCPClient.py <message> <host> <port>")
    except socket.gaierror as e:
        print("Socket error:", e)
    except ConnectionRefusedError as e:
        print("Connection error:", e)
    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    main()
