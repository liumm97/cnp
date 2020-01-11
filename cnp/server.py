import socket

class Server :
    def __init__(self,config):
        self._config = config
        s = socket.socket()
        host = socket.gethostname()
        s.bind((host,config["server_port"]))
        s.listen(5)
        self.ptmap={}


