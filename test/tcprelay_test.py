import socket
import sys
import logging
sys.path.append('..')
from cnp import tcprelay ,eventloop
logging.basicConfig(level=logging.DEBUG)

relay_addr = ('127.0.0.1',18080)
relay = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
relay.bind(relay_addr)
relay.listen(1)
local,addr = relay.accept()


remote_server = ('127.0.0.1',8080)
remote = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
remote.connect(remote_server)

loop =  eventloop.EventLoop()
tcprelay = tcprelay.TCPRelay(local,remote,loop)
loop.run()


    

