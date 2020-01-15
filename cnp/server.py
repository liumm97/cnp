import socket
import common
import struct

class Server :
    maver = 0
    miver = 1
    def __init__(self,config):
        self.config = config
        self.uname = "root"
        self.passwd = "123456"
        self.server_ip  = "127.0.0.1"
        self.server_port = 8080
        self.socket = None
        self.socket_buf = b''
        self.stream_to_socket = {}   # stream_id -> socket
        self.inputs = []
        self.outputs = []
        self.message_queues = {}

    def parse_auth_pkg(self,data): 
        maver ,miver,ul,pl = struct.unpack('4B',data[:4])
        data = data[4:]
        print(maver,miver,ul)
        if (maver,miver) != (Server.maver,Server.miver) :
             data = struct.pack('2BH',Server.maver,Server.miver,0x10)
             hdata = common.add_head(0x2,data)
             #self.message_queues[self.socket].put(hdata)
             self.socket.send(hdata)
             return 
        uname ,passwd = struct.unpack('{}s{}s'.format(ul,pl),data[:ul+pl])
        if uname.decode() != self.uname :
             data = struct.pack('2BH',0,2,0x11)
             hdata = common.add_head(0x2,data)
             self.socket.send(hdata)
             #self.message_queues[self.socket].put(hdata)
             return 
        if passwd.decode() != self.passwd:
             data = struct.pack('2BH',0,2,0x12)
             hdata = common.add_head(0x2,data)
             self.socket.send(hdata)
             #self.message_queues[self.socket].put(hdata)
             return 
        return 




    def start(self):
        s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s.bind((self.server_ip,self.server_port))
        s.listen(1)
        while True :
            conn,addr = s.accept()
            self.socket = conn
            while True :
                print("receive data ... ")
                data = conn.recv(1024)
                if not data :
                    print('client close ,wait new ...')
                    break
                len_pkg = len(data)
                self.parse_auth_pkg(data[8:len_pkg])
config = {}
ser = Server(config)
ser.start()






