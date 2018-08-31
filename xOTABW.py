#!/usr/bin/env python3
# -*- coding: utf8 -*-
# bluphy@163.com
# 2018-08-27 10:01:30 by xw: copy from xOTAGB.py
# 2018-5-29 17:06:51 by xw: new created.

#### BEGIN Calibration
#B-LINK default tukey
TUKEY = '5A3756216A2649754E512576572B4733'
#### ##END Calibration

#### BEGIN Constants
OTABW_PREFIX = b'\x5f\x8a\xbb\xcd'
OTABW_SUFFIX = b'\xb2\x5e\x38\xa2'

#### ##END Constants

import time
import hashlib
from Crypto.Cipher import AES
from bidict import bidict

def decryptBWOTA(tukey:bytes,dsptchr_sg1_bdy_sg2:bytes) -> bytes:
    '''
    以16进制字节流形式，给定tukey和加密后的OTA消息的dispatcher+sig1+body+sig2，返回消息明文,需要注意的是当加密前的明文的长度不是16整数倍时，算法会自动补足，所以解密后的原文需要手动去除补足的字节，由于函数本身无法分辨哪些字节是补足的部分，需要调用者根据数据长度来判断
    '''

    obj = AES.new(tukey,AES.MODE_ECB)
    msg = obj.decrypt(dsptchr_sg1_bdy_sg2)
    length = int.from_bytes(msg[32:35],'big')
    #print('cipher text=',dsptchr_sg1_bdy_sg2,'length=',len(dsptchr_sg1_bdy_sg2))
    #print('decrypt msg=',msg,'length=',len(msg))
    return msg[:35+length]

def split_dispatcher_sig1_body_sig2(raw:bytes):
    result = {}
    result['dispatcher'] = raw[:35]
    length = int.from_bytes(result['dispatcher'][-3:],'big')
    
    result['sig1'] = raw[35:55]
    if len(raw)>55:
        result['body'] = raw[55:-20]
        result['sig2'] = raw[-20:]
    return result

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

class Header_OTABW:
    def __init__(self, header:bytes):
        #print(header)
        self.headerVersion = Field('Header_version', header[0])
        self.testFlag = Field('TestFlag', header[1])
        self.nondatalen = Field('Non-Data_Len', header[2])
        try:
            self.IMEI = Field('IMEI', header[3:],convertfunc=lambda x: x.decode('ascii'))
        except:
            print(header)
            self.phy = header[3:].hex()

class Dispatcher_OTABW:
    def __init__(self, dispatcher:bytes):
        #print(dispatcher)
        self.Protocol_version = Field('Protocol_version', dispatcher[0])
        self.Equipment_ID_Type = Field('Equipment_ID_Type', dispatcher[1])
        self.Equipment_ID = Field('Equipment_ID', dispatcher[2:22])
        self.Event_id = Field('Event_id', dispatcher[22:24])
        self.Service_ID = Field('Service_ID', dispatcher[24])
        self.SubFunction = Field('SubFunction', dispatcher[25])
        self.hour_date = Field('hour_date', dispatcher[26:30])
        self.Uplink_Counter = Field('Uplink_Counter', dispatcher[30])
        self.Downlink_Counter = Field('Downlink_Counter', dispatcher[31])
        self.Data_Length = Field('Data_Length', dispatcher[32:35],lambda x:int.from_bytes(x,'big'))
        

class Body_OTABWMsg:
    def __init__(self, msg:bytes):
        '''
        接收未加密的字节流数据(包括body)作为初始化OTAGB消息的参数，对消息进行初始化        
        '''
        self.raw = msg
        if self.detectFormat(msg):
            pass

    def detectFormat(self, msg:bytes)->bool:
        '''
        检测数据是否符合规范，True符合规范，False不符合规范
        '''
        pass
        return True

def computeSha1(x:bytearray):
    '''
    给定16进制字节流，计算出相应的sha1值，输入输出都以16进制字符串表示
    TU key 使用此算法
    '''
    obj = hashlib.sha1()
    obj.update(x)
    y=obj.digest()
    return y

def genDispatcherTime(utc=None)->bytes:
    '''
    生成Dispatcher格式的时间字节流
    '''
    if not utc: utc = time.gmtime()
    year = (utc.tm_year-2014)<<26
    month = utc.tm_mon<<22
    date = utc.tm_mday<<17
    hour = utc.tm_hour<<12
    minute = utc.tm_min<<6
    sec = utc.tm_sec
    dispatchertime = (year+month+date+hour+minute+sec).to_bytes(4,byteorder='big')

    return dispatchertime

def calDataLength(bodylen:int):
    if bodylen==0:
        return 20
    else:
        return 40+bodylen

def encryptMsg(tukey:bytes,raw:bytes)->bytes:
    '''
    need to padding the raw
    '''
    pad = b'\x00'
    tmp = raw+pad*(16-len(raw)%16)
    obj = AES.new(tukey,AES.MODE_ECB)
    return obj.encrypt(tmp)

def createOTABWHeader(imei:str,*,Header_version:bytes=b'\x01',testflag:bytes=b'\x01', nondatalength:bytes=b'\x35')->bytes:
    '''
    '''
    return b''.join([Header_version,testflag,nondatalength,imei.encode('ascii')])

def createOTABWDispatcher(equipment_id:str,eventid:int,sid:bytes,subfunc:bytes,uplink_counter:int,down_link_counter:int,data_length:int,*,protocol_version=b'\x02',epuipment_idtype=b'\x01'):
    equipment_id = b'\x00'*(20-len(equipment_id))+equipment_id.encode('ascii')
    eventid = eventid.to_bytes(2,'big')
    hour_date = genDispatcherTime()
    uplink_counter = uplink_counter.to_bytes(1,'big')
    down_link_counter = down_link_counter.to_bytes(1,'big')
    data_length = data_length.to_bytes(3,'big')
    return b''.join([protocol_version,epuipment_idtype,equipment_id,eventid,sid,subfunc,hour_date,uplink_counter,down_link_counter,data_length])

def createOTABWBody_Response(sid:bytes=None,subfunc:bytes=None,NRC:bytes=b'\x00',*parameters):
    '''
    NRC : NEGATIVE RESPONSE CODE

    '''
    print('NRC=',NRC.hex())
    body = None
    if NRC == b'\x00':
        if sid == b'\x13' and subfunc == b'\x02':
            body = RS_response
        # elif sid == b'\x13' and subfunc == b'\x04':
        # elif sid == b'\x16' and subfunc == b'\x02':
        # elif sid == b'\x16' and subfunc == b'\x04':
        # elif sid == b'\x24' and subfunc == b'\x01':
        else:
            body = b''
    else:
        body = NRC
        print('goes else')
    
    return body


def generateResponse(header:Header_OTABW,dispatcher:Dispatcher_OTABW,body:Body_OTABWMsg,tukey=None)->bytes:
    sig1 = computeSha1( b''.join([header,dispatcher]))
    if len(body)==0:
        sig2 = b''
    else:
        sig2 = computeSha1(b''.join([header,dispatcher,sig1,body]))

    original = b''.join([OTABW_PREFIX,header,dispatcher,sig1,body,sig2,OTABW_SUFFIX])

    if not tukey:        
        response = original
    else:
        response = b''.join([OTABW_PREFIX,header,encryptMsg(tukey,b''.join([dispatcher,sig1,body,sig2])),OTABW_SUFFIX])
    return response


if __name__ == '__main__':
    # following are test
    # import xDUTDBSevice as xddbs
    imei = '353635080101104'
    # vhlinfo = xddbs.getDUTInfo(imei)
    equipment_id = '3'*17
    eventid = 3333
    sid = b'\xff'
    subfunc = b'\x91'
    uplink_counter = 0
    downlink_counter = 33
    body = createOTABWBody_Response(NRC=b'\x13')
    datalen = calDataLength(len(body))
    header = createOTABWHeader(imei)
    dispatcher = createOTABWDispatcher(equipment_id,eventid,sid,subfunc,uplink_counter,downlink_counter,datalen) 

    tukey = TUKEY
    print('generateResponse')
    print('dispatcher=',dispatcher.hex())
    print('body=',body.hex())
    msg = generateResponse(header,dispatcher,body,tukey=tukey)
    print('密文:',msg.hex())
    print('decryptBWOTA')
    ori = decryptBWOTA(tukey,msg[22:-4])
    print('split_dispatcher_sig1_body_sig2')
    result = split_dispatcher_sig1_body_sig2(ori)
    print('解密拆分后:',result)
    for i in result.keys():
        print(result[i].hex())

    print('real example')
    msg = bytes.fromhex('010035383637383038303237323634313635010130303000000000000000000000000000000000000000ff9112025b6a0401000029dda80bb5e7dfca46c7c3afbd0b4d29a58ce5bece13ed5d90332c3157031ae63c0a79d8800e03a72d61')
    result = split_dispatcher_sig1_body_sig2(msg[18:])
    print(result)
    for i in result.keys():
        print(result[i].hex())

        
