import socket
hostport = ('127.0.0.1',18080)
s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.connect(hostport)
 
while True:
    user_input = input('>>> ').strip()
    s.send(user_input.encode('utf-8'))
