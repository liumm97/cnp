import queue
import logging
import protocol
class StreamManager:
    def __init__(self,server_socket):
        self.server_socket = server_socket
        self.inputs = []
        self.outputs = []
        self.stream_to_socket = {}
        self.message_queue = {}
        self.stream_base_id = 0
        self.message_queue[self.server_socket] = queue.Queue()
        return 

    def generate_stream_id(self):
        self.stream_base_id += 1
        return self.stream_base_id

    def is_active_socket(self,socket) :
        for _,v in self.stream_to_socket:
            if v  == socket : return True
        return False 

    def get_socket(self,stream_id) :
        return self.stream_to_socket[stream_id]

    def get_stream_id(self,socket):
        for k,v in self.stream_to_socket:
            if v  == socket : return k
        return  


    # 打开一个流
    def open_stream(self,ty,rport,socket):
        # send open_stream_frame
        stream_id = self.generate_stream_id()
        logging.debug(" open stream id:{} port_type:{} remote_port:{}".format(stream_id,ty,rport))
        body = protocol.open_stream_data(ty,rport,stream_id)
        open_message = protocol.add_frame_head(protocol.FRAME_OPEN_STREAM,body)
        self.message_queue[self.server_socket].put(open_message)
        if self.server_socket not in self.outputs :
            self.outputs.append(self.server_socket)
        self.stream_to_socket[stream_id] = socket
        self.inputs.append(socket)
        return stream_id

    # 关闭一个流
    def reset_stream(self,stream_id,code) :
        if stream_id not in self.stream_to_socket :
            logging.warn(" reset stream  stream_id error  ")
            return 
        logging.debug(" clost stream id:{} code:{}".format(stream_id,code))
        body = protocol.reset_stream_data(code)
        reset_msg = protocol.add_frame_head(protocol.FRAME_RST_STREAM,body,stream_id)
        self.message_queue[self.server_socket].put(reset_msg)
        if self.server_socket not in self.outputs :
            self.outputs.append(self.server_socket)
        socket = self.stream_to_socket[stream_id]
        self.inputs.remove(socket)
        if socket in self.outputs :
            self.outputs.remove(socket)
        del self.stream_to_socket[stream_id]
        del self.message_queue[socket]
        socket.close()
        return 

    # 处理关闭一个流
    def hand_reset_stream(self,stream_id,code) :
        if stream_id not in self.stream_to_socket :
            logging.debug(" {} don't exist  ".format(stream_id))
            return 
        logging.debug( " hand reset_stream  stream_id:{} code :{}  ".format(stream_id,code))
        socket = self.stream_to_socket[stream_id]
        if self.message_queue[socket].empty():
            self.inputs.remove(socket)
            if socket in self.outputs : self.outputs.remove(socket)
            socket.close()
            del self.message_queue[socket]
        del self.stream_to_socket[stream_id]
        return

    # 处理游离socket 释放资源
    def hand_unactive_socket(self,socket) :
        logging.debug(" remove unactive socker:{}".format(socket))
        self.inputs.remove(socket)
        if socket in self.outputs :
            self.outputs.remove(socket)
        del self.message_queue[socket]
        socket.close()
        return 

    # 判断流是否存在
    def is_in_stream(self,stream_id) :
        if stream_id in self.stream_to_socket :
            return True
        return False 

    # socket 绑定流
    def blind_stream(self,stream_id,socket) :
        logging.debug(" blind socket to stream stream_id : {} <---->socket:{} ".format(stream_id,socket))
        self.stream_to_socket[stream_id] = socket
        self.message_queue[socket] =queue.Queue()
        self.inputs.append(socket)
        self.outputs.append(socket)
        return 

    def hand_send_data(self,socket) :
        try:
            # 如果消息队列中有消息,从消息队列中获取要发送的消息
            message_queue = self.message_queue[socket]
            send_data = ''
            if message_queue is not None:
                send_data = message_queue.get_nowait()
        except queue.Empty:
            self.outputs.remove(socket)
            if socket != self.server_socket and  not self.is_active_socket(socket) :
                self.inputs.remove(socket)
                socket.close()
                del self.message_queue[socket]
        else:
             logging.debug('send data {}'.format(send_data))
             socket.send(send_data)

    # 获取监听socket
    def get_select_sockets(self):
        return self.inputs,self.outputs,self.inputs

    def put_socket_data(self,socket,data) :
        self.message_queue[socket].put(data)
        return 
