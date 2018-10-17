#!/usr/bin/env python3
# -*- coding: utf8 -*-
# bluphy@163.com
# 2018-5-29 17:06:51 by xw: new created.
import time
from bidict import bidict

CMD = bidict({
    b'\x01' : '车辆登入',    
    b'\x02' : '实时数据',    
    b'\x03' : '补发数据',    
    b'\x04' : '车辆登出',    
    b'\x07' : '心跳',    
    b'\x80' : '查询命令',    
    b'\x81' : '设置命令',   
    b'\x82' : '控制命令'
    })
class Field:
    def __init__(self,name,raw,convertfunc=None,checkfunc=None):
        #print(raw)
        self.name = name

        if type(raw) is int:
            self.raw = raw.to_bytes(1,byteorder='big')
        else:
            self.raw = raw
        #print(type(self.raw))
        if convertfunc:          
            self.phy = convertfunc(self.raw)
        else:
            self.phy = self.raw.hex()

class Head:
    def __init__(self, header:bytes):
        #print(header[2])
        self.cmd = Field('命令标识', header[2], convertfunc=lambda x: CMD[x])
        self.resflg = Field('应答标志', header[3])
        self.VIN = Field('VIN', header[4:21],convertfunc=lambda x: x.decode('ascii'))
        self.secretflg = Field('加密方式', header[21])
        self.length = Field('数据长度', header[22:24], convertfunc=lambda x: int(x.hex(),16))

class OTAGBData:
    def __init__(self, msg:bytes):
        '''
        接收字节流数据作为初始化OTAGB消息的参数，对消息进行初始化
        '''
        if self.detectMsgFormat(msg):
            self.raw = msg
            self.head = Head(msg[:24])
            self.payload = msg[24:-1]
            self.chk = msg[-1]

    def detectMsgFormat(self, msg:bytes)->bool:
        '''
        检测数据是否符合规范，True符合规范，False不符合规范
        '''
        pass
        return True

def calBCCChk(buf:bytes):
    chk = buf[0]
    for byte in buf[1:]:
        chk = byte^chk
    return chk.to_bytes(1,byteorder='big')

def genGBTime()->bytes:
    '''
    生成国标格式的时间字节流
    '''
    lct = time.localtime()
    year = (lct.tm_year-2000).to_bytes(1,byteorder='big')
    month = lct.tm_mon.to_bytes(1,byteorder='big')
    date = lct.tm_mday.to_bytes(1,byteorder='big')
    hour = lct.tm_hour.to_bytes(1,byteorder='big')
    minute = lct.tm_min.to_bytes(1,byteorder='big')
    sec = lct.tm_sec.to_bytes(1,byteorder='big')
    gbtime = year+month+date+hour+minute+sec

    return gbtime

def createOTAGBMsg(cmd:bytes, resp:bytes, VIN:bytes, secrettype:int, length:int, data:bytes):
    '''
    '''
    start = b'##'
    payload = cmd+resp+VIN+secrettype.to_bytes(1,byteorder='big')+length.to_bytes(2,byteorder='big')+data
    chk = calBCCChk(payload)
    msg = start + payload + chk
    return msg


if __name__ == '__main__':
    msg = b'##\x04\xFELXVJ2GFC2GA030003\x01\x00\x08\x11\x11\x11\x11\x11\x11\x33\x33\x33'
    gbdata = OTAGBData(msg)
    print(gbdata.head.cmd.phy)
    msg2 = '232302FE4C4D47464531473030303030303053593101013512051005223101020301FFFF00000000000007D00002000000FF0002010103000FA043F800000013880501000000000000000006010100000101000001010001010007000000000000000000080101000007D0006000016000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000009010100180000000000000000000000000000000000000000000000008F'
    msg3 = '232301FE4C4D47464531473030303030303053593101001E1205100B0B30000138393836303631363031303035343538373630310100EC'
    tmp = bytes.fromhex(msg2)[2:-1]
    print(tmp)
    chk = calBCCChk(tmp)
  
    print('chk=',chk.hex())
    print('gbtime=',genGBTime().hex())
    print(createOTAGBMsg(b'\x01', b'\xFE', b'LXVJ2GFC2GA030003', 1, 7, genGBTime() ))
    print(createOTAGBMsg(CMD.inv['心跳'], b'\x01', b'LXVJ2GFC2GA030003', 1, 0, b''))