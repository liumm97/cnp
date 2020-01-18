import socket
import logging
import sys
import select
import time
import protocol
import stream
import queue

class  Client():
    mar_version = 0
    min_version = 1
    def __init__(self,config) :
        self.config = config
        self.uname = self.config["uname"]
        self.passwd = self.config["passwd"]
        self.server_ip  = config['server_ip']
        self.server_port = config['server_port']
        self.tcp_ports = self.config["tcp_ports"]
        self.udp_ports=[]
        self.ssock = None 
        self.ssock_queue = queue.Queue()
        self.sbuff = b''
        self.stream_manager = None
    
    def init(self) :
        logging.info(" connect server ...  ")
        # 与服务端建立连接 ，并且发送认认证和端口注册信息
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.server_ip,self.server_port))
        self.ssock = sock
        self.stream_manager = stream.StreamManager(self.ssock,self.ssock_queue)

        # 认证信息
        auth_body = protocol.auth_data(Client.mar_version,Client.min_version,self.uname,self.passwd)
        auth_msg = protocol.add_frame_head(protocol.FRAME_AUTH,auth_body)
        self.ssock_queue.put(auth_msg)

        # 端口信息
        register_body  = protocol.register_data(self.tcp_ports,self.udp_ports)
        print(register_body)
        register_msg = protocol.add_frame_head(protocol.FRAME_REGISTER,register_body)
        self.ssock_queue.put(register_msg)
        return 

    # 新建一个流
    def open_stream(self,ty,port,stream_id):
        # 判断流是否存在
        stream_manager = self.stream_manager
        if stream_manager.stream_is_exist(stream_id) :
            stream_manager.reset_stream(stream_id,0x2)
            return 

        # 建立流
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        stream_manager.blind_stream(stream_id,sock)
        try :
            sock.connect(('127.0.0.1', port))
        except :
            logging.error(" connect  port error  port={}".format(port))
            stream_manager.reset_stream(stream_id,0x1)
        return 



    def handle_server_receive(self) :
        data = self.ssock.recv(1024)
        logging.debug(" receive data {}".format(data))
        if data ==b'':
            logging.info("server connect close")
            sys.exit(0)
            return
        data = self.sbuff + data
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
                logging.info(" server version  {}.{} ".format(maver,miver))
                logging.info(" connect failed,{}".format(errmsg))
                sys.exit(0)
                return 
            elif ty == protocol.FRAME_OPEN_STREAM: # 新建流
                ty,port ,stream_id  =  protocol.parse_open_stream_data(body)
                self.open_stream(ty,port,stream_id)
            elif ty == protocol.FRAME_RST_STREAM : # 关闭流
                code = protocol.parse_reset_data(body)
                self.stream_manager.handle_reset_stream(stream_id,code)
            elif ty == protocol.FRAME_DATA : # 转发数据
                if self.stream_manager.stream_is_exist(stream_id) : 
                    stream = self.stream_manager.stream_map[stream_id]
                    self.stream_manager.put_sock_msg(stream.sock,body)
            data = data[len_pkg:]

    def handle_server_send(self) :
        try:
            send_data = self.ssock_queue.get_nowait()
        except queue.Empty:
            logging.debug("send queue empty")
        else:
             logging.debug('send data {}'.format(send_data))
             self.ssock.send(send_data)
        return

    def handle_receive(self,readable) :
        for s in readable :
            if s == self.ssock :
                self.handle_server_receive()
                continue
            self.stream_manager.handle_recv(s)
        return 

    def handle_send(self ,writable) :
        for s in writable:
            if s == self.ssock :
                self.handle_server_send()
                continue
            self.stream_manager.handle_send(s)
        return 


    def handle_exception(self,exceptional):
        for s in exceptional :
            if s  ==  self.ssock :
                logging.error(' server connection exception ')
                sys.exit(0)
                return 
            logging.debug('exception condition on' +  s.getpeername())
            self.stream_manager.handle_exception(s)
        return 

    def run(self) :
        self.init()
        while True  :
            inputs , outputs  = self.stream_manager.select_socks()
            inputs.append(self.ssock)
            if  not self.ssock_queue.empty():
                outputs.append(self.ssock)
            print(inputs)
            readable, writable, exceptional = select.select(inputs,outputs,inputs)
            if readable :
                self.handle_receive(readable)
            if writable  :
                self.handle_send(writable)
            if exceptional  :
                print(exceptional)
                self.handle_exception(exceptional)
            self.stream_manager.destroy_streams()

if __name__== '__main__' :
    logging.basicConfig(level=logging.DEBUG)
    config = {
            "uname":"root",
            "passwd":"123456",
            "server_ip":"127.0.0.1",
            "server_port":8080,
            "tcp_ports" :[(10022,11122)],
            "udp_ports" :[],
            }
    cli = Client(config)
    cli.run()

