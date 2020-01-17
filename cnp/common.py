# 双向map
class DoubleMap():
    def __init__(self):
        self.kmap={} # k-v
        self.vmap={} # v-k
        return 

    def put(self,k,v) :
        self.kmap[k] =v 
        self.vmap[v] = k

    def get_k(self,k) :
        return self.kmap[k]

    def get_v(self,v):
        return self.vmap[v]

    def is_in_k(self,k):
        return k in self.kmap

    def is_in_v(self,v):
        return v in self.vmap

    def del_k(self,k):
        v = self.kmap[k]
        del self.vmap[v]
        del self.kmap[k]

    def del_v(self,v):
        k = self.vmap[v]
        del self.kmap[k]
        del self.vmap[v]

