import socket
import sys

def main():
    try:
        if len(sys.argv) < 2:
            print("Usage: python3 IPC/TCPClient.py <message> <host>")
            return
        message = sys.argv[1] 
        host = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
        server_port = 7896

        # create a socket and connect to server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            print(f"Connecting to host {server_port}...")
            s.connect((host, server_port))

            # Send the message
            s.sendall(message.encode('utf-8'))

            # receive the response
            data = s.recv(1024).decode('utf-8')
            print(f"[SERVER RESPONSE] {data}")

    except IndexError:
        print("Usage: python3 IPC/TCPclient.py <message> <host>")
    except socket.gaierror as e:
        print("Socket error:", e)
    except ConnectionRefusedError as e:
        print("Connection error:", e)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()
    