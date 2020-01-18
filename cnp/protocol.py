import struct


FRAME_AUTH = 0x1
FRAME_REGISTER = 0x2
FRAME_TERMINATE = 0x3 
FRAME_OPEN_STREAM = 0x4 
FRAME_RST_STREAM = 0x5 
FRAME_DATA = 0x6

TERMINATE_ERR = {
        0x10 : "版本号不兼容",
        0x11 : "用户不存在",
        0x12 : "密码错误",
        0x20 : "端口不被允许",
        0x21 : "端口已占用"
        }

def can_parse(data) :
    if len(data) < 2 : return False 
    lp = len_pkg(data)
    if len(data) < lp : return False
    return True


# 获取帧总长度
def len_pkg(data) :
    (ln,) = struct.unpack('>H',data[:2])
    return ln + 8


# 添加帧首部
def add_frame_head(ty,data,stream_id = 0,flag = 0):
    hdata = struct.pack('>H2BL',len(data),ty,flag,stream_id)
    return hdata + data

def view_frame_type(data) :
    (ty,) = struct.unpack('>B',data[2:3])
    return ty

def view_frame_flag(data):
    (flag,) = struct.unpack('>B',data[3:4])
    return flag

def view_stream_id(data) :
    (stream_id,) = struct.unpack('>L',data[4:8])
    return stream_id

def get_frame_data(data) :
    return data[8:]

def auth_data(maver,miver,uname,passwd) :
       udata , pdata = uname.encode('utf8'),passwd.encode('utf8')
       cdata = struct.pack('>2B',maver,miver) 
       pdata =  struct.pack('>BB{}s{}s'.format(len(udata),len(pdata)),len(udata),len(pdata),udata,pdata )
       return cdata + pdata

def parse_auth_data(data):
    maver,miver,ul,pl = struct.unpack('>4B',data[:4])
    udata,pdata = struct.unpack('>{}s{}s'.format(ul,pl),data[4:4+ul+pl])
    return maver,miver,udata.decode(),pdata.decode()

def register_data(tports,uports):
    cdata = struct.pack('>2B',len(tports),len(uports))
    pdata = b''
    for  port in tports + uports:
        pdata += struct.pack('>2H',port[0],port[1])
    return cdata + pdata

def parse_register_data(data):
    tl,ul = struct.unpack('>2B',data[:2])
    ports = struct.unpack('>{}H'.format((tl+ul) *2 ),data[2:])
    tports =  [(ports[i*2],ports[i*2+1]) for i in range(tl)]
    uports = [(ports[i*2],ports[i*2+1]) for i in range(tl,tl+ul)]
    return tports,uports

def terminate_data(maver,miver,err_code) :
    return struct.pack('>2BH',maver,miver,err_code)


def open_stream_data(ptype,rport,stream_id) :
    return struct.pack('>BHL',ptype,rport,stream_id)

def parse_open_stream_data(data):
    return struct.unpack('>BHL',data)

def reset_stream_data(code) :
    return struct.pack('>B',code)

def parse_reset_data(data) :
    code , = struct.unpack('>B',data)
    return code 

def parse_terminate_data(data):
    maver,minver ,err_code = struct.unpack('2BH',data)
    err_msg =  TERMINATE_ERR.get(err_code,"未知错误")
    return maver,minver,err_code,err_msg



# 验证帧有效
def valid_frame(data) :
    ty = view_frame_type(data) 
    stream_id = view_stream_id(data)
    if ty ==FRAME_AUTH  and stream_id == 0:
        return True
    if ty == FRAME_REGISTER and stream_id == 0 :
        return True
    if ty == FRAME_TERMINATE and stream_id == 0 :
        return True
    if ty == FRAME_OPEN_STREAM and stream_id == 0 :
        return True
    if ty == FRAME_RST_STREAM:
        return True
    if ty == FRAME_DATA and stream_id > 0 :
        return True
    return False 



if __name__ == "__main__" :
    maver,miver = 1,2
    uname,passwd= 'root','123456'
    err_code = 0x1
    if parse_auth_data(auth_data(maver,miver,uname,passwd)) != (maver,miver,uname,passwd) :
        raise Exception(' opt auth_data err')
    tports= [(10022,11122)]
    uports = []
    if parse_register_data(register_data(tports,uports)) != (tports,uports) :
        raise Exception(' opt register_data err ')
    if parse_terminate_data(terminate_data(maver,miver,err_code)) != (maver,miver,err_code) :
        raise Exception(" opt terminate_data err ")
    if parse_open_stream_data(open_stream_data(1,2,3)) != (1,2,3):
        raise Exception(" opt open stream  err ")
    if parse_reset_data(reset_stream_data(1)) != 1 :
        raise Exception(" opt reset  stream  err ")


