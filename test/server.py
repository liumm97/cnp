import socket
import struct
HostPort = ('127.0.0.1',10022)
s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.bind(HostPort)
s.listen(1)
while True:
    conn,addr = s.accept()
    while True :
        print("receive data ... ")
        data = conn.recv(1024)
        if not data :
            print('client close ,wait new ...')
            break
        print (data)
        if data == b'quit\r\n' :
            conn.close()
            break
        conn.send(data[:-2] + b' reply\n')

