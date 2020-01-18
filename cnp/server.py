import sys 
import traceback
import queue
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
        self.lport = config['listen_port']
        self.lsock = None
        self.ssock = None 
        self.ssock_queue = None
        self.sbuf = b''
        self.proxy_sockets= []
        self.proxy_socket_map = {}
        self.stream_manager = None

    def init(self,sock):
        # init 
        self.ssock=sock
        self.ssock_queue=queue.Queue()
        self.sbuf = b''
        self.proxy_sockets= []
        self.proxy_socket_map = {}
        # 认证 
        data = sock.recv(1024)
        self.handle_auth(data)
        data = sock.recv(1024)
        self.handle_register(data)
        self.stream_manager = stream.StreamManager(self.ssock,self.ssock_queue)
        return 

    def destroy(self) :
        if self.ssock:
            self.ssock.close()
        self.ssock_queue =None
        self.sbuf = b''
        if self.stream_manager :
            self.stream_manager.destroy()
            self.stream_manager = None 
        for psocket in self.proxy_sockets :
            psocket.close()
        self.proxy_sockets = []
        self.proxy_socket_map = {}
        return 

    def handle_auth(self,data):
        logging.info("handle auth receive {}".format(data))
        if not protocol.can_parse(data):
            logging.info("receive  invalid  data ")
            raise Exception("receive invalid data  ")
        ty = protocol.view_frame_type(data)
        body = protocol.get_frame_data(data)
        if ty != protocol.FRAME_AUTH :
            logging.info("receive invalid data ")
            raise Exception("receive invalid data ")
        maver ,miver ,uname,passwd = protocol.parse_auth_data(body)
        logging.info('version={}.{} uname={} passwd={}'.format(maver,miver,uname,passwd))
        if (maver,miver) != (Server.maver,self.miver) :
            body = protocol.terminate_data(Server.maver,Server.miver,0x2)
            data = protocol.add_frame_head(protocol.FRAME_TERMINATE,body)
            self.ssock.send(data)
            raise Exception(" version error ")
        if (uname,passwd) != (self.uname,self.passwd) :
            body = protocol.terminate_data(Server.maver,Server.miver,0x12)
            data = protocol.add_frame_head(protocol.FRAME_TERMINATE,body)
            self.ssock.send(data)
            raise Exception(" uname or passwd error   ")
        logging.info("client auth success")
        return 

    def handle_register(self,data) :
        logging.debug("register receive {}".format(data))
        if not protocol.can_parse(data) :
            logging.info("receive invalid  data")
            raise Exception("receive invalid  data ")
        ty = protocol.view_frame_type(data)
        body = protocol.get_frame_data(data)
        if ty != protocol.FRAME_REGISTER :
            logging.info("receive invalid  data")
            raise Exception("receive invalid  data")
        tports ,_ = protocol.parse_register_data(body)
        print(tports)
        try :
            for tport in tports :
                listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                listen_socket.bind(('127.0.0.1', tport[1]))
                listen_socket.listen(5)
                logging.debug("register port ... ")
                logging.debug(listen_socket)
                self.proxy_sockets.append(listen_socket)
                self.proxy_socket_map[listen_socket] = tport[0]
        except :
            body = protocol.terminate_data(Server.maver,Server.miver,0x21)
            data = protocol.add_frame_head(protocol.FRAME_TERMINATE,body)
            self.ssock.send(data)
            raise
        logging.info("port register success ")
        return 

    def handle_server_receive(self):
        data = self.ssock.recv(1024)
        logging.debug(" receive data {}".format(data))
        if data ==b'':
            logging.info("client connect close")
            raise Exception("client connect close")
            return
        data = self.sbuf + data
        while True :
            if  not protocol.can_parse(data) :
                self.sbuf = data
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
                logging.info(" client close")
                raise Exception("client close")
            elif ty == protocol.FRAME_RST_STREAM : # 关闭流
                code = protocol.parse_reset_data(body)
                self.stream_manager.handle_reset_stream(stream_id,code)
            elif ty == protocol.FRAME_DATA : # 转发数据
                if self.stream_manager.stream_is_exist(stream_id) :
                    stream = self.stream_manager.stream_map[stream_id]
                    self.stream_manager.put_sock_msg(stream.sock,body)
            data = data[len_pkg:]
        return 


    def handle_receive(self,readable) :
        for s in readable :
            if s == self.server_socket :
                self.handle_server_receive()
                continue
            if s in self.proxy_sockets:
                logging.debug(" proxy port new connect ")
                conn,_= s.accept()
                self.stream_manager.open_stream(0x1,self.proxy_socket_map[s],conn)
                continue
            self.stream_manager.handle_recv(s)
        return

    def handle_server_send(self) :
        try:
            send_data = self.ssock_queue.get_nowait()
        except queue.Empty:
            logging.debug("send queue empty")
        else:
             logging.debug('send data {}'.format(send_data))
             self.ssock.send(send_data)
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
                logging.error('server listen port exception ')
                raise Exception("server listen port exception")
                return
            if s in self.proxy_sockets :
                logging.error('server proxy port exception ')
                raise Exception("server proxy port exception")
            self.stream_manager.handle_exception(s)
        return

    def run(self) :
        while True  :
            inputs , outputs = self.stream_manager.select_socks()
            inputs = inputs +  self.proxy_sockets
            inputs.append(self.ssock)
            if not self.ssock_queue.empty() :
                outputs.append(self.ssock)
            readable, writable, exceptional = select.select(inputs,outputs,inputs)
            if readable :
                self.handle_receive(readable)
            if writable  :
                self.handle_send(writable)
            if exceptional  :
                self.handle_exception(exceptional)
            self.stream_manager.destroy_streams()

    def start(self):
        s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s.bind(('0.0.0.0',self.lport))
        self.lsock =s 
        s.listen(1)
        while True :
            try :
                logging.info(" wait new  client ...")
                conn,_ = s.accept()
                self.server_socket = conn
                self.init(conn)
                self.run()
            except Exception as e :
                traceback.print_exc()
                self.destroy()
                logging.info(" client close ")


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    config = {
            "uname":"root",
            "passwd":"123456",
            "listen_port":8080,
            }
    server = Server(config)
    server.start()
