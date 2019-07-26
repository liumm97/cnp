class Service:
    max_threads = 5
    tunnel_time_out = 60 * 1
    users = {}
    __clients = {}
    __ports = {}

    def __init__(self, port):
        self.listen_port = port  # 监听端口

    def set_max_threads(self, max_threads):
        self.max_threads = max_threads

    def set_tunnel_time_out(self, time_out):
        self.tunnel_time_out = time_out

    def add_user(self, name, password):
        self.users[name] = password

    def user_exist(self, name):
        return self.users.get(name) is not None

    def test_password(self, name, password):
        return self.users.get(name) == password
