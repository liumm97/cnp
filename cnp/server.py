import sys 
import traceback
import socket
import stream
import select 
import logging
import protocol


class Server :
    maver = 0
    miver = 1
    def __init__(self,config):
        self.config = config
        self.uname = self.config["uname"]
        self.passwd = self.config["passwd"]
        self.listen_port = config['listen_port']
        self.listen_socket = None
        self.server_socket = None 
        self.server_buf = b''
        self.stream_manager = None
        self.status = 0
        self.proxy_sockets= []
        self.proxy_socket_map = {}

    def init(self,socket):
        # 认证 
        data = socket.recv(1024)
        self.handle_auth(data)
        data = socket.recv(1024)
        self.hand_register(data)
        self.stream_manager = stream.StreamManager(socket)
        return 

    def destroy(self) :
        self.server_socket.close()
        self.server_buf = []
        self.stream_manager.destroy()
        self.stream_manager = None 
        for psocket in self.proxy_sockets :
            psocket.close()
        return 

    def handle_auth(self,data):
        logging.debug("auth receive data :{}".format(data))
        if not protocol.can_parse(data):
            logging.info("Receive  Invalid  Frame ")
            raise Exception("Receive Invalid Frame  ")
        ty = protocol.view_frame_type(data)
        body = protocol.get_frame_data(data)
        if ty != protocol.FRAME_AUTH :
            logging.info("Receive  Invalid  Frame ")
            raise Exception("Receive Invalid Frame  ")
        maver ,miver ,uname,passwd = protocol.parse_auth_data(body)
        logging.info('{}.{} {} {}'.format(maver,miver,uname,passwd))
        if (maver,miver) != (Server.maver,self.miver) :
            body = protocol.terminate_data(Server.maver,Server.miver,0x2)
            data = protocol.add_frame_head(protocol.FRAME_TERMINATE,body)
            self.server_socket.send(data)
            raise Exception(" Version Error  ")
        if (uname,passwd) != (self.uname,self.passwd) :
            body = protocol.terminate_data(Server.maver,Server.miver,0x12)
            data = protocol.add_frame_head(protocol.FRAME_TERMINATE,body)
            self.server_socket.send(data)
            raise Exception(" uname or passwd error   ")
        logging.info("client auth success")
        return 

    def hand_register(self,data) :
        logging.debug("register receive data :{}".format(data))
        if not protocol.can_parse(data) :
            logging.info("Receive  Invalid  Frame ")
            raise Exception("Receive Invalid Frame  ")
        ty = protocol.view_frame_type(data)
        body = protocol.get_frame_data(data)
        if ty != protocol.FRAME_REGISTER :
            logging.info("Receive  Invalid  Frame ")
            raise Exception("Receive Invalid Frame ")
        tports ,_ = protocol.parse_register_data(body)
        try :
            for tport in tports :
                listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                listen_socket.bind(('127.0.0.1', tport[1]))
                listen_socket.listen(5)
                self.proxy_sockets.append(listen_socket)
                self.proxy_socket_map[listen_socket] = tport[0]
        except :
            body = protocol.terminate_data(Server.maver,Server.miver,0x21)
            data = protocol.add_frame_head(protocol.FRAME_TERMINATE,body)
            self.server_socket.send(data)
            raise
        logging.info("port register success ")
        return 

    def handle_server_receive(self,data):
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
            logging.debug("stream_id = {}".format(stream_id))
            body = protocol.get_frame_data(pkg)
            if ty == protocol.FRAME_TERMINATE : # 终止帧 
                logging.info(" Client Connection Failed,{}")
                raise Exception("Client TERMINATE ")
            elif ty == protocol.FRAME_RST_STREAM : # 关闭流
                code = protocol.parse_reset_data(body)
                self.stream_manager.hand_reset_stream(stream_id,code)
            elif ty == protocol.FRAME_DATA : # 转发数据
                rsocket = self.stream_manager.get_socket(stream_id)
                if rsocket :
                    self.stream_manager.put_socket_data(rsocket,body)
            data = data[len_pkg:]
        return 


    def handle_receive(self,readable) :
        for s in readable :
            if s == self.server_socket :
                data = s.recv(1024)
                logging.debug(" receive data {}".format(data))
                if data ==b'':
                    logging.info(" Client  Close")
                    raise Exception("Client Close ")
                self.handle_server_receive(data)
                continue
            if s in self.proxy_sockets :
                logging.debug(" proxy port new connect ")
                conn,_= s.accept()
                self.stream_manager.open_stream(0x1,self.proxy_socket_map[s],conn)
                continue
            data = s.recv(1024)
            logging.debug(" receive data {}".format(data))
            stream_id = self.stream_manager.get_stream_id(s)
            logging.debug(" stream_id = {}".format(stream_id))
            if  not stream_id : continue
            if data == b'' :
                self.stream_manager.reset_stream(stream_id,0x0)
                continue
            pkg = protocol.add_frame_head(protocol.FRAME_DATA,data,stream_id)
            self.stream_manager.put_socket_data(self.server_socket,pkg)
        return

    def handle_send(self ,writable) :
        for s in writable:
            self.stream_manager.hand_send_data(s)
        return

    def handle_exception(self,exceptional):
        for s in exceptional :
            if s  ==  self.server_socket :
                logging.error(' Server Listen Port Exception ')
                sys.exit(0)
                return
            if s in self.proxy_sockets :
                logging.error(' Server Proxy Port Exception ')
                raise Exception("Server Proxy Port Exception ")

            logging.debug('exception condition on' +  s.getpeername())
            if not self.stream_manager.is_active_socket(s) :
                self.stream_manager.hand_unactive_socket(socket)
                continue
            stream_id = self.stream_manager.get_stream_id(s)
            self.stream_manager.reset_stream(stream_id,0x3)
            return

    def run(self) :
        while True  :
            inputs , outputs , _  = self.stream_manager.get_select_sockets()
            logging.debug("input socket {}".format(inputs))
            logging.debug("out socket {}".format(outputs))
            readable, writable, exceptional = select.select(inputs + self.proxy_sockets,outputs,inputs + self.proxy_sockets)
            if readable :
                self.handle_receive(readable)
            if writable  :
                self.handle_send(writable)
            if exceptional  :
                print(exceptional)
                self.handle_exception(exceptional)


    def start(self):
        s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s.bind(('127.0.0.1',self.listen_port))
        self.listen_socket =s 
        s.listen(1)
        while True :
            try :
                logging.info(" New Client ...")
                conn,_ = s.accept()
                self.server_socket = conn
                self.init(conn)
                self.run()
            except Exception as e :
                traceback.print_exc()
                self.destroy()
                logging.info(" Client Close")



if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    config = {
            "uname":"root",
            "passwd":"123456",
            "listen_port":8080,
            "tcp_ports" :[(22,1022),(33,1033)],
            }
    server = Server(config)
    server.start()




