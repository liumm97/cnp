import struct 

def add_head(ty,data,stream_id = 0,flag = 0):
    hdata = struct.pack('>H2BL',len(data),ty,flag,stream_id)
    return hdata + data

def rm_head(data) :
    ln , ty , flag ,stream_id = struct.unpack('>H2BL', data[:8])
    data = data[8:8+ln]
    return ln , ty , flag ,stream_id ,data

def len_pack(data) :
    (ln,) = struct.unpack('>H',data[:2])
    return ln + 8 


if __name__== '__main__' :
    data = 'hello world'.encode('utf8')
    ty,stream_id ,data,flag = len(data),1024,data,8
    hdata = add_head(ty,data,stream_id ,flag)
    if (len(data) ,ty ,flag,stream_id,data) != rm_head(hdata) :
        raise Exception(" head detail error  ")
    if len_pack (hdata) != len(hdata) :
        raise Exception(' len_pack  error ')
    

