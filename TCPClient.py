import socket
import sys

def main():
    try:
        message = sys.argv[1]
        host = sys.argv[2]
        server_port = 7896

        # create a socket and connect to the server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, server_port))
            # Send the message
            s.sendall(message.encode('utf-8'))
            # receive the response
            data = s.recv(1024).decode('utf-8')
            print("Received:", data)
    except IndexError:
        print("Usage: python3 TCPclient.py <message> <hostname>")
    except socket.gaierror as e:
        print("Socket error:", e)
    except ConnectionRefusedError as e:
        print("Connection error:", e)
    except Exception as e:
        print("Error:", e)
if __name__ == "__main__":
    main()
