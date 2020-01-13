import socket
import logging
import struct
import sys
import select
import  common

def Client():
    mar_version = 0
    min_version = 1
    def __init__(self,config) :
        self.config = config
        self.uname = self.config["uname"]
        self.passwd = self.config["passwd"]
        self.server_ip  = config['server_ip']
        self.server_port = config['server_port']
        self.tcp_ports = self.config["tcp_ports"]
        self.udp_ports = self.config["udp_ports"]
        self.socket = None
        self.socket_buf = b''
        self.stream = {}   # stream_id -> socket
        self.inputs = []
        self.outputs = []
        self.message_queues = {}

    # 与服务端建立连接
    def __connect(self) :
        # 建立连接
        s = socket.socket()
        s.connect((self.server_ip, self.server_port))
        self.socket = s
        return 

    # auth_frame
    def __auth_pkg(self):
       # 构造auth pkg
       udata , pdata = self.uname.encode('utf8'),self.passwd.encode('utf8')
       cdata = struct.pack('2B',mar_version,min_version) 
       auth_data = struct.pack('B' + len(udata) + 'sB' + len(pdata) +'s',len(udata),udata,len(pdata),pdata )
       data =  common.add_head(0x1,cdata+auth_data)
       return data

       # register_frame
    def __register_pkg(self):
        cdata = struct.pack('2B',len(self.tcp_ports),len(self.udp_ports))
        pdata = bytes()
        for  port in self.tcp_ports +self.udp_ports:
           pdata += struct.pack('2H',port[0],port[1])
        data = common.add_head(0x2,cdata + pdata)
        return data

    def __parse_terminate(self,data):
        err_map = {
                0x10 : "版本号不兼容",
                0x11 : "用户不存在",
                0x12 : "密码错误",
                0x20 : "端口不被允许",
                0x21 : "端口已占用"
                }
        maver,minver ,err_code = struct.pack('2BH',data)
        logging.error(" 客户端被终止")
        logging.error("服务器版本:{}.{} 终止原因:{}".format(maver,minver,err_map.get(err_code,"未知错误")))
        sys.exit(0)
        return 

    # OPEN_STREAM 帧 (0x3)
    def open_stream(self,data) :
        ty,port,stream_id = struct.unpack("BHL",data)
        # 流是否存在
        if stream_id in self.stream :
            # rest stream 
            body = struct.pack('B',0x2)
            hdata = common.add_head(0x4,body,stream_id)
            self.message_queues[self.socket].put(hdata)
            return 
        # 创建流
        rsocket = None 
        try :
            if ty == 0x1 :
                rsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if ty == 0x2 :
                rsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            rsocket.connect(('127.0.0.1', port))
            self.stream[stream_id] = rsocket
        except :
              body = struct.pack('B',0x1)
              hdata = common.add_head(0x4,body,stream_id)
        return 

    def __handle_socker_receive(self,data) :
        data = self.socket_buf + data
        while True :
            if len(data) < 2 : break
            len_pkg = common.len_pack(data)
            if len(data) < len_pkg : continue
            _,ty,_,stream_id,body = common.rm_head(data[:len_pkg])
            if ty == 0x2 : # 终止帧 
                self.__parse_terminate(body)
            elif ty == 0x3 : # 新建流
                self.open_stream(body)
            elif ty == 0x4 : # 关闭流
                del self.stream[stream_id]
            elif ty == 0x5 : # 转发数据
                rsocket = self.stream[stream_id]
                if not rsocket : pass
                self.message_queues[rsocket].put(body)
            else : pass
            data = data[:len_pkg]
    def __handler_receive(self,readable) :
        for s in readable :
            if s == self.socket :
                data = self.socket_buf + s.recv(1024)
                self.__handle_socker_receive(data)
            else :
                 data = s.recv(1024)
                 if data != b'' :
                     for s

                     pass
                 



        return 


    def start(self) :
        # 构造初始化帧
        self.__control_queue.append(self.__auth_pkg(),self.__register_pkg())
        self.__connect()
        while True  :
            readable, writable, exceptional = select.select(self.inputs,self.outputs,self.inputs)

        


        



        









       





       
