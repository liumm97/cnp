import socket
import logging
import sys
import select
import time
import protocol
import stream

class  Client():
    mar_version = 0
    min_version = 1
    def __init__(self,config) :
        self.config = config
        self.uname = self.config["uname"]
        self.passwd = self.config["passwd"]
        self.server_ip  = config['server_ip']
        self.server_port = config['server_port']
        self.server_buf = []
        self.tcp_ports = self.config["tcp_ports"]
        self.udp_ports = self.config["udp_ports"]
        self.stream_manager = None
    
    def init(self) :
        logging.info(" Connect Server ... ")
        # 与服务端建立连接 ，并且发送认认证和端口注册信息
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((self.server_ip,self.server_port))
        self.server_socket = server_socket
        self.stream_manager = stream.StreamManager(server_socket)

        # 认证信息
        auth_body = protocol.auth_data(Client.mar_version,Client.min_version,self.uname,self.passwd)
        auth_data = protocol.add_frame_head(protocol.FRAME_AUTH,auth_body)
        self.stream_manager.put_socket_data(self,auth_data)

        # 端口信息
        register_body  = protocol.register_data(self.tcp_ports,self.udp_ports)
        register_data = protocol.add_frame_head(protocol.FRAME_REGISTER,register_body)
        server_socket.send(auth_data + register_data)
        self.stream_manager.put_socket_data(self,register_data)
        return 

    # 新建一个流
    def open_stream(self,ty,port,stream_id):
        # 判断流是否存在
        stream_manager = self.stream_manager
        if self.stream_manager.is_in_stream(stream_id) :
            stream_manager.reset_stream(stream_id,0x2)
            return 
        # 打开socket  
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        try :
            host = socket.gethostname()
            s.connect((host, port))
        except :
            logging.error(" connect tcp port({}) error ".format(port))
            stream_manager.reset_stream(stream_id,0x1)
            return 
        stream_manager.blind_stream(stream_id,s)
        return 




    def handle_server_receive(self,data) :
        data = self.server_buf + data
        while True :
            if  not protocol.can_parse(data) :
                self.server_buf = data
                break
            len_pkg = protocol.len_pkg(data)
            pkg = data[:len_pkg] 
            if  not protocol.valid_frame(pkg) :
                logging.warn(" receive invalid pkg ")
                data = data[len_pkg:]
                continue
            ty = protocol.view_frame_type(pkg)
            stream_id = protocol.view_stream_id(pkg)
            body = protocol.get_frame_data(pkg)
            if ty == protocol.FRAME_TERMINATE : # 终止帧 
                maver,miver,_,errmsg = protocol.parse_terminate_data(body)
                logging.info(" Server Version  {}.{} ".format(maver,miver))
                logging.info(" Connection Failed,{}".format(errmsg))
                sys.exit(0)
                return 
            elif ty == protocol.FRAME_OPEN_STREAM: # 新建流
                ty,port ,stream_id  =  protocol.parse_open_stream_data(body)
                self.open_stream(ty,port,stream_id)
            elif ty == protocol.FRAME_RST_STREAM : # 关闭流
                code = protocol.parse_reset_data(body)
                self.stream_manager.hand_reset_stream(stream_id,code)
            elif ty == protocol.FRAME_DATA : # 转发数据
                rsocket = self.stream_manager.get_socket(stream_id)
                if rsocket :
                    self.stream_manager.put_socket_data(rsocket,body)
            data = data[len_pkg:]

    def handler_receive(self,readable) :
        for s in readable :
            data = s.recv(1024)
            logging.debug(" receive data {}".format(data))
            if s == self.server_socket :
                if data ==b'':
                    logging.info("Server Connectin Close")
                    sys.exit(0)
                    return 
                self.handle_server_receive(data)
                continue
            stream_id = self.stream_manager.get_stream_id(socket)
            if  not stream_id : continue
            if data == b'' :
                self.stream_manager.reset_stream(stream_id,0x0)
        return 

    def handler_send(self ,writable) :
        for s in writable:
            self.stream_manager.hand_send_data(s)
        return 


    def handler_exception(self,exceptional):
        for s in exceptional :
            if s  ==  self.server_socket :
                logging.error(' Server Connection Exception ')
                sys.exit(0)
                return 
            logging.debug('exception condition on' +  s.getpeername())
            if not self.stream_manager.is_active_socket(s) :
                self.stream_manager.hand_unactive_socket(socket)
                continue
            stream_id = self.stream_manager.get_stream_id(s)
            self.stream_manager.reset_stream(stream_id,0x3)
            return 

    def run(self) :
        self.init()
        while True  :
            readable, writable, exceptional = select.select(self.stream_manager.get_select_sockets())
            if readable :
                self.handler_receive(readable)
            if writable  :
                self.handler_send(writable)
            if exceptional  :
                print(exceptional)
                self.handler_exception(exceptional)

if __name__== '__main__' :
    logging.basicConfig(level=logging.DEBUG)
    config = {
            "uname":"root",
            "passwd":"123456",
            "server_ip":"127.0.0.1",
            "server_port":8080,
            "tcp_ports" :[(22,1022),(33,1033)],
            "udp_ports" : [(22,1022),(33,1033)]
            }
    cli = Client(config)
    cli.run()

