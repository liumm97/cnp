import socket
HostPort = ('127.0.0.1',8080)
s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.bind(HostPort)
s.listen(1)
while True:
    conn,addr = s.accept()
    while True :
        data = conn.recv(1024).decode()
        if not data :
            print('client close ,wait new ...')
            break
        conn.send("I am received .. ".encode('utf-8'))
        print (data)

