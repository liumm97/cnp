import socket

s = socket.socket()

host = '127.0.0.1'
port = 10022
s.bind((host, port))

s.listen(5)
while True:
    print("wait new client ... ")
    c, _ = s.accept()
    while True:
        data = c.recv(1024).strip()
        if data ==b'':
            c.close()
            break
        if data == b'quit':
            c.close()
            break
        print('Received message == {}'.format(data))
        c.send(data + b' reply \n')

