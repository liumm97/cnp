import queue
import logging
import protocol
from common import  DoubleMap

class Stream():
    def __init__(self,stream_id,sock):
        logging.debug(" create stream stream_id={} socket={}".format(stream_id,sock.fileno()))
        self.stream_id = stream_id
        self.sock=sock
        self.msg_queue = queue.Queue()
        self.is_open = True


    def recv_msg(self):
        data = self.sock.recv(1024)
        logging.debug(" recv data {}".format(data))
        return 

    def put_msg(self,msg) :
        self.msg_queue.put(msg)
        return 

    def send_msg(self):
        logging.debug(" stream send msg stream_id={} socket={}".format(self.stream_id,self.sock.fileno()))
        try:
            send_data = self.msg_queue.get_nowait()
        except queue.Empty:
            logging.debug("send queue empty")
        else:
             logging.debug('send data {}'.format(send_data))
             self.sock.send(send_data)
        return 

    def is_empty(self) :
        return self.msg_queue.empty()

    def destroy(self) :
        logging.debug(" destroy stream stream_id={} socket={}".format(self.stream_id,self.sock.fileno()))
        self.sock.close()
        self.sock = None
        self.msg_queue = None 
        return 

    def __hash__(self) :
        return self.stream_id

    def __eq__(self,other):
        if self.stream_id == other.stream_id :
            return True
        return False 

# 流管理器
class StreamManager:
    def __init__(self,ssock,ssock_queue):
        self.inputs=[]
        self.outputs=[]
        self.base_stream_id = 0
        self.ssock = ssock
        self.ssock_queue = ssock_queue
        self.stream_map = {}
        self.stream_sock_map=DoubleMap()
        self.to_destories = []
        return 

    def generate_stream_id(self):
        self.base_stream_id += 1
        return self.base_stream_id

    def stream_to_sock(self,stream) :
        return self.stream_sock_map.get_k(stream)

    def sock_to_stream(self,sock):
        return self.stream_sock_map.get_v(sock)
    


    # 打开一个流
    def open_stream(self,ty,rport,sock):
        # 发送对应帧
        stream_id = self.generate_stream_id()
        logging.debug("open stream  id={} ty={} rport={}".format(stream_id,ty,rport))
        body = protocol.open_stream_data(ty,rport,stream_id)
        msg = protocol.add_frame_head(protocol.FRAME_OPEN_STREAM,body)
        self.ssock_queue.put(msg)

        # 建立对应流
        stream = Stream(stream_id,sock)
        self.stream_map[stream_id] =stream
        self.stream_sock_map.put(stream,sock)
        return 

    # 关闭一个流
    def reset_stream(self,stream_id,code) :
        # 发送关闭流帧
        logging.debug(" clost stream id={} code={}".format(stream_id,code))
        body = protocol.reset_stream_data(code)
        msg = protocol.add_frame_head(protocol.FRAME_RST_STREAM,body,stream_id)
        self.ssock_queue.put(msg)

        # 将流更改为close ,并加入到待销毁
        stream = self.stream_map[stream_id]
        stream.is_open = False
        self.to_destories.append(stream)
        return 
        
    # 处理关闭一个流
    def hand_reset_stream(self,stream_id,code) :
        if stream_id not in self.stream_map:
            logging.debug("to reset stream not exist stream_id={}".format(stream_id))
            return 
        logging.debug( "hand reset_stream stream_id={} code={}  ".format(stream_id,code))
        stream = self.stream_map[stream_id]
        if  not stream.is_open:
            logging.debug(" stream had close stream_id={}".format(stream_id))
            return 

        # 将流更改为close ,并加入到待销毁
        stream = self.stream_map[stream_id]
        stream.is_open = False
        self.to_destories.append(stream)
        return 

    # socket 绑定流
    def blind_stream(self,stream_id,sock) :
        logging.debug("blind socket to stream stream_id={} socket={}".format(stream_id,sock.fileno()))
        stream= Stream(stream_id,sock)
        self.stream_map[stream_id] =stream
        self.stream_sock_map.put(stream,sock)
        return

    def put_sock_msg(self,sock,msg):
        stream = self.stream_sock_map.get_v[sock]
        if  not stream.is_open :
            logging.debug("to  put msg stream close ")
            return 
        stream.put_msg(msg)
        if sock not in self.outputs:
            self.outputs.append(sock)
        return 

    def hand_send(self,sock) :
        stream = self.stream_sock_map.get_v[sock]
        stream.send_msg()
        if stream.is_empty():
            if sock in self.outputs :
                self.outputs.remove(sock)
            if not stream.is_open () :
                self.to_destories.append(stream)
        return 


    def hand_recv(self,sock):
        stream = self.stream_sock_map.get_v[sock]
        data = stream.recv_msg()
        if data == b'': # 目标socket close
            self.reset_stream(stream.stream_id,0x0)
            return 
        if not stream.is_open :
            return 
        msg = protocol.add_frame_head(protocol.FRAME_DATA,data,stream.stream_id)
        self.ssock_queue.put(msg)
        return 


    #  获取需要监听的端口
    def select_socks(self):
        return self.inputs,self.outputs

    def destroy_streams(self):
        for stream in self.to_destories:
            stream.destroy()
            del self.stream_map[stream.stream_id]
            del self.stream_sock_map.del_k[stream]
        return 

    def destroy(self):
        for stream in self.stream_map.values():
            stream.destroy()
        self.stream_map = None
        self.stream_sock_map=None
        return 


        
