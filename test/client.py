import socket
import sys

HOST, PORT = "localhost", 11122
data = 'hello world' 
if __name__=='__main__':
    i = 0
    while True :
        i += 1
        # Create a socket (SOCK_STREAM means a TCP socket)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Connect to server and send data
            sock.connect((HOST, PORT))
            sock.sendall(bytes(data + str(i) + "\n", "utf-8"))
            # Receive data from the server and shut down
            received = str(sock.recv(1024), "utf-8")
            sock.close()

            print("Sent:     {}{}".format(data,i))
            print("Receive    {}".format(received))

