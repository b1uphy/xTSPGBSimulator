#!/usr/bin/env python3
# -*- coding: utf8 -*-
# bluphy@163.com
# 2018-08-27 10:01:30 by xw: copy from xOTAGB.py
# 2018-5-29 17:06:51 by xw: new created.

#### BEGIN Calibration

#B-LINK default tukey
TUKEY = bytes.fromhex('5A3756216A2649754E512576572B4733')
#### ##END Calibration

#### BEGIN Constants
LISTENING_VHL_PORT = 9201
LISTENING_CC_PORT = 31029
OTABW_PREFIX = b'\x5f\x8a\xbb\xcd'
OTABW_SUFFIX = b'\xb2\x5e\x38\xa2'
# OTABW_PREFIX = '5F8ABBCD'.encode('ascii')
# OTABW_SUFFIX = 'B25E38A2'.encode('ascii')
MSG_CONFIG = 'OTAMSG_config.json'
TIMER_OTA_MSG_TIMEOUT_RX = 5
TIMER_OTA_MSG_TIMEOUT_TX = 2
TIMER_OTA_MSG_TIMEOUT_HEARTBEAT = 60
COUNTER_OTA_MSG_MAXRETRY = 3

#### ##END Constants

import time,asyncio
import hashlib
from Crypto.Cipher import AES
from bidict import bidict
import json
from async_timeout import timeout
from queue import Queue

# from xDUTDBSevice import getDUTInfo,getDUTInfoByVIN,generateTUKEY,setDUTInfo
from xDBSErvice.xDUTDBSeviceFake import getDUTInfo,getDUTInfoByVIN,generateTUKEY,setDUTInfo

# 全局字典，保存登入车辆的实例句柄
#gIMEIDict用于保存连接到服务器的车辆和advisor的对象句柄，结构{imei_0:{'vhl':vhl_instance_0,'advisor':advisor_instance_0},...}
gIMEIDict = {}


def decryptBWOTA(tukey:bytes,dsptchr_sg1_bdy_sg2:bytes) -> bytes:
    '''
    以16进制字节流形式，给定tukey和加密后的OTA消息的dispatcher+sig1+body+sig2，返回消息明文,需要注意的是当加密前的明文的长度不是16整数倍时，算法会自动补足，所以解密后的原文需要手动去除补足的字节，由于函数本身无法分辨哪些字节是补足的部分，需要调用者根据数据长度来判断
    '''
    if type(tukey)==str: tukey=bytes.fromhex(tukey)
    obj = AES.new(tukey,AES.MODE_ECB)
    
    unpad = lambda s : s[0:-s[-1]]
    msg = unpad(obj.decrypt(dsptchr_sg1_bdy_sg2))
    # length = int.from_bytes(msg[32:35],'big')
    #print('cipher text=',dsptchr_sg1_bdy_sg2,'length=',len(dsptchr_sg1_bdy_sg2))
    #print('decrypt msg=',msg,'length=',len(msg))
    
    return msg

def split_dispatcher_sig1_body_sig2(raw:bytes):
    result = {}
    result['dispatcher'] = raw[:35]
    length = int.from_bytes(result['dispatcher'][-3:],'big')
    
    result['sig1'] = raw[35:55]
    if len(raw)>55:
        result['body'] = raw[55:-20]
        result['sig2'] = raw[-20:]
    return result

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
    加密报文
    '''
    # pad = b'\x00'
    # tmp = raw+pad*(16-len(raw)%16)
    BS = 16
    pad = lambda s: s + (BS - len(s) % BS) * (BS - len(s) % BS).to_bytes(1,'big')
    obj = AES.new(tukey,AES.MODE_ECB)
    # return obj.encrypt(tmp)
    return obj.encrypt(pad(raw))

def createOTABWHeader(imei:str,*,Header_version:bytes=b'\x01',testflag:bytes=b'\x01', nondatalength:bytes=b'\x35')->bytes:
    '''
    '''
    return b''.join([Header_version,testflag,nondatalength,imei.encode('ascii')])

def createOTABWDispatcher(equipment_id:str,eventid:int,sid:bytes,subfunc:bytes,uplink_counter:int,down_link_counter:int,data_length:int,*,protocol_version=b'\x02',epuipment_idtype=b'\x01',hour_date=None):
    equipment_id = b'\x00'*(20-len(equipment_id))+equipment_id.encode('ascii')
    eventid = eventid.to_bytes(2,'big')
    hour_date = genDispatcherTime()
    uplink_counter = uplink_counter.to_bytes(1,'big')
    down_link_counter = down_link_counter.to_bytes(1,'big')
    data_length = data_length.to_bytes(3,'big')
    return b''.join([protocol_version,epuipment_idtype,equipment_id,eventid,sid,subfunc,hour_date,uplink_counter,down_link_counter,data_length])

def createOTABWBody_Response(sid:bytes=None,subfunc:bytes=None,NRC:bytes=b'\x00',**parameters):
    '''
    NRC : NEGATIVE RESPONSE CODE

    '''
    print('NRC=',NRC.hex())
    body = None
    if NRC == b'\x00':
        if sid == b'\x13' and subfunc == b'\x02':
            body = parameters['body']
        # elif sid == b'\x13' and subfunc == b'\x04':
        # elif sid == b'\x16' and subfunc == b'\x02':
        # elif sid == b'\x16' and subfunc == b'\x04':
        # elif sid == b'\x24' and subfunc == b'\x01':
        else:
            body = b''
    else:
        body = NRC

    
    return body


# def generateResponse(header:Header_OTABW,dispatcher:Dispatcher_OTABW,body:Body_OTABWMsg,tukey=None)->bytes:
#     sig1 = computeSha1( b''.join([header,dispatcher]))
#     if len(body)==0:
#         sig2 = b''
#     else:
#         sig2 = computeSha1(b''.join([header,dispatcher,sig1,body]))

#     original = b''.join([OTABW_PREFIX,header,dispatcher,sig1,body,sig2,OTABW_SUFFIX])

#     if not tukey:        
#         response = original
#     else:
#         response = b''.join([OTABW_PREFIX,header,encryptMsg(tukey,b''.join([dispatcher,sig1,body,sig2])),OTABW_SUFFIX])
#     return response


def createOTA(header:bytes,dispatcher:bytes,body:bytes,tukey=None)->bytes:
    sig1 = computeSha1( b''.join([header,dispatcher]))
    if len(body)==0:
        sig2 = b''
    else:
        sig2 = computeSha1(b''.join([header,dispatcher,sig1,body]))

    original = b''.join([OTABW_PREFIX,header,dispatcher,sig1,body,sig2,OTABW_SUFFIX])

    if not tukey:        
        otamsg = original
    else:
        otamsg = b''.join([OTABW_PREFIX,header,encryptMsg(tukey,b''.join([dispatcher,sig1,body,sig2])),OTABW_SUFFIX])
    return otamsg

class BWMsgCore:
    def __init__(self,sid:bytes,subfunc:bytes,body:bytes):
        
        self.sid = sid
        self.subfunc = subfunc
        self.body = body

    def __repr__(self):
        return '<sid={0},subfunc={1},body={2}>'.format(self.sid.hex(),self.subfunc.hex(),self.body.hex())


    def generateOTAMsg(self,vhl):
        result = {}
        equipment_id = vhl.info['VIN']
        event_id = vhl.eventID
        vhl.downlink += 1
        downlink = vhl.downlink
        uplink = 0
        datalen = calDataLength(len(self.body))    
        header = createOTABWHeader(vhl.imei)
        dispatcher = createOTABWDispatcher(equipment_id,event_id,self.sid,self.subfunc,uplink,downlink,datalen)
        result['value'] = createOTA(header,dispatcher,self.body)
        result['code'] = 0
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

class BWHeader:
    def __init__(self, header:bytes):
        #print(header)
        self.raw = header
        self.headerVersion = Field('Header_version', header[0])
        self.testFlag = Field('TestFlag', header[1])
        self.nondatalen = Field('Non-Data_Len', header[2])
        try:
            self.IMEI = Field('IMEI', header[3:],convertfunc=lambda x: x.decode('ascii'))
        except:
            print(header)
            self.phy = header[3:].hex()

class BWDispatcher:
    def __init__(self, dispatcher:bytes):
        #print(dispatcher)
        self.raw = dispatcher
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
        

class BWBody:
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


# BEGIN APP Layer/
class VehicleAgent:
    def __init__(self,interface,firstmsg:bytes=None,**config):
        global gIMEIDict
        self.register = gIMEIDict
        # self.registerFlag = False
        self.imei = None
        self.info = None
        print(interface)
        #应用层与传输层的接口对象
        self.readerVhl = None
        self.writerVhl = None
        self.readerAdvisor = None
        self.writerAdvisor = None
        
        #车辆连接状态
        self.state = 'connecting'

        # #
        # self.data = None
        # # self.msg = None
        
        #车辆接口的一些dispatcher要素，需要在车辆模型中进行统一管理
        self.eventID = 0
        self.uplink = 0
        self.downlink = 0
        self.config = config

        #消息队列
        # 接收的消息直接在TCP传输层进行缓存，这里只保存应用层要发出消息的缓存队列
        # self.inMsgsQueue=asyncio.Queue()
        self.outMsgs2VhlQueue=asyncio.Queue()
        self.outMsgs2AdvisorQueue=asyncio.Queue()

    def initVhlInterface(self,reader,writer):
        self.readerVhl = reader
        self.writerVhl = writer

    def initAdvisorInterface(self,reader,writer):
        self.readerAdvisor = reader
        self.writerAdvisor = writer

    def dissectMsg(self,msg:bytes):
        '''
        解析消息，对消息格式内容进行检查(待实现)，返回包含 BW OTA 消息核心内容的类实例 的结果字典
        return BWMsgCore
        '''
        result = {}
        # print('dissect msg:',msg.hex())
        #Step 1: Analysis msg.
        header = BWHeader(msg[:18])
        if not self.imei:
            #First msg, init connection in app level and get vehicle infomation from database
            self.imei = header.IMEI.phy
            print('imei=',self.imei)

            if not (self.imei in self.register.keys()):
                self.register[self.imei] = {}
            self.register[self.imei]['vhl'] = self

            self.info = getDUTInfo(self.imei)
        else:
            self.state = 'connected'

        decrypted = decryptBWOTA(self.info['TUKEY'],msg[18:])
        rxraw = header.raw+decrypted
        print('IMEI {0} :\n \tRx Uncrypted: {1}'.format(self.imei,rxraw.hex()))

        msgparts = split_dispatcher_sig1_body_sig2(decryptBWOTA(self.info['TUKEY'],msg[18:]))
        dispatcher = BWDispatcher(msgparts['dispatcher'])
        sig1 = msgparts['sig1']
        if len(msgparts.keys())>2:
            body = BWBody(msgparts['body'])
            sig2 = msgparts['sig2']
        else:
            body = b''
            sig2 = b''
        
        result['value'] = BWMsgCore(dispatcher.Service_ID.raw,dispatcher.SubFunction.raw,body)
        result['code'] = 0

        return result
    def parseMsgCore(self,msgcore:BWMsgCore):
        '''
        to be implement
        return the response dict, the structure as below:
        result = {
            'value': bytes, 
            'code': int/str
        }
        responsecode definition:
        0: positive response
        >0: same as the OTA NRC code definition
        '''
        print('parseMsgCore: enter')
        result = {}
        # sid = msgcore.sid
        sid = b'\x1d'
        # subfunc = msgcore.subfunc
        subfunc = b'\x00'
        body = b''
        result['value'] = BWMsgCore(sid,subfunc,body)
        result['code'] = 0
        print('rseponse msgcore:',result['value'])
        print('parseMsgCore: return')
        return result

    async def processVhlMsg(self):
        '''
        
        '''
        while True:
            print('processVhlMsg: enter')
            print('#Step 0: wait msg')
            result = await self.rxMsgFromVhl()
            if result['code']>=0:
                print('#Step 1: dissect msg')
                msgcore = self.dissectMsg(result['value'])
                
                print('#Step 2: generate the tx msgcore')
                response = self.parseMsgCore(msgcore)

                print('#Step 3: put the msg {0} into tx queue'.format(response['value']))
                await self.outMsgs2VhlQueue.put(response['value'])
            else:
                self.writerVhl.close()
                self.state = 'disconnected'
                print('socket disconnected')
                break
        print('processVhlMsg: return')
        return result['code']

    async def rxMsgFromVhl(self):
        '''
        put the raw msg bytes without the OTABW_PREFIX and OTABW_SUFFIX
        '''
        result = {'value':None, 'code':-1}
        OTAprefix = None
        try:
            rxtime = time.strftime('%Y%m%d %H:%M:%S')
            async with timeout(TIMER_OTA_MSG_TIMEOUT_RX):
                OTAprefix = await self.readerVhl.readexactly(len(OTABW_PREFIX.hex()))
                
        except asyncio.TimeoutError:
            print('Rx timeout')
            print('Close connection with {0} because of timeout1'.format(self.imei))
            result['code'] = -1    
        except ConnectionError:
            print('Connection broken with {0} !'.format(self.imei))
            result['code'] = -2

        if OTAprefix:
            print('OTAprefix:',OTAprefix)
            if OTAprefix.decode('ascii') == OTABW_PREFIX.hex():
                raw = None
                try:
                    async with timeout(TIMER_OTA_MSG_TIMEOUT_RX):
                        raw = await self.readerVhl.readuntil(OTABW_SUFFIX.hex().encode('ascii'))
                    systime = time.time()
                    
                except asyncio.TimeoutError:
                    print('Rx timeout')
                    print('Close connection with {0} because of timeout2'.format(self.imei))
                    result['code'] = -1           
                
                if raw:
                    result['value'] = bytes.fromhex(raw.decode('ascii'))[:-len(OTABW_SUFFIX)]
                    result['code'] = 0
                    # if not self.imei:
                    #     self.imei =  result['value'][3:18].decode('ascii')
                # writedb(result['msg'],systime,0,gDBhdl)
                    # print('{0} Received from {1}:\t{2}'.format(rxtime,self.imei,result['value'].hex()))

        return result

    async def txMsg2Vhl(self):
        while True:
            print('txMsg2Vhl: enter')

            if self.state == 'disconnected': break

            try:
                async with timeout(15):
                    msgcore = await self.outMsgs2VhlQueue.get()
            except asyncio.TimeoutError:
                print('txMsg2Vhl: nothing to send...')
            else:
                msg = msgcore.generateOTAMsg(self)['value'].hex().encode('ascii')
                print('Sending msg to {0}:\n\t{1}'.format(self.imei,msg))
                try:
                    self.writerVhl.write(msg)
                    systime = time.time()
                except ConnectionError:
                    print('Send Msg fail. Msg:',msg.hex())
                    break
                else:
                    # writedb(msg,systime,1,gDBhdl)
                    print('Send Msg:',msg.hex())

        print('txMsg2Vhl: return')

    async def processAdvisorMsg(self):
        pass

    async def rxMsgFromAdvisor(self):
        pass

    async def txMsg2Advisor(self):
        while True:
            print('txMsg2Advisor: enter')
            if self.state == 'disconnected': break
            
            try:
                async with timeout(TIMER_OTA_MSG_TIMEOUT_TX):
                    msg = await self.outMsgs2AdvisorQueue.get()
            except asyncio.TimeoutError:
                pass
            else:
                try:
                    self.writerAdvisor.write(msg)
                    systime = time.time()
                except ConnectionError:
                    print('Send Msg fail. Msg:',msg.hex())
                    break
                else:
                    # writedb(msg,systime,1,gDBhdl)
                    print('Send Msg:',msg.hex())
        print('txMsg2Advisor: return')

class AdvisorAgent:
    def __init__(self,client,firstmsg:bytes=None,**config):
        global gIMEIDict
        self.register = gIMEIDict
        self.client = client
        self.info = None
        self.vhl = None
        self.imei = None
        self.msglist = self.initMsgList()

    def processMsg(self,msg:bytes):
        json.loads(msg.decode('utf8'))

        if not self.imei:
            #First msg, init connection in app level and get vehicle infomation from database
            self.imei = header.IMEI.phy
            print('imei=',self.imei)

            if not (self.imei in gIMEIDict.keys()):
                gIMEIDict[self.imei] = {}
            gIMEIDict[self.imei]['vhl'] = self


    def bindVehicle(self):
        self.vhl = None

    def initMsgList(self,msgconfig=MSG_CONFIG):
        pass

# END APP layer

if __name__ == '__main__':
    # following are test
    # import xDUTDBSevice as xddbs
    imei = '353635080101088'
    # vhlinfo = xddbs.getDUTInfo(imei)
    equipment_id = 'LMGFE1G88D1022SY3'
    eventid = 0
    sid = b'\x60'
    subfunc = b'\x81'
    uplink_counter = 175
    downlink_counter = 0
    # body = createOTABWBody_Response(NRC=b'\x13')
    body=b'\xc0\x17\x00\x10'
    datalen = calDataLength(len(body))
    header = createOTABWHeader(imei)
    dispatcher = createOTABWDispatcher(equipment_id,eventid,sid,subfunc,uplink_counter,downlink_counter,datalen,protocol_version=b'\x01',hour_date=b'\x28\x46\x40\xe3') 

    tukey = TUKEY
    print('generateResponse')
    print('dispatcher=',dispatcher.hex())
    print('body=',body.hex())
    print('debug: length of dispatcher and body',len(dispatcher+body))
    msg = createOTA(header,dispatcher,body,tukey=tukey)
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

    msg = bytes.fromhex('0100353836373830383032373236343136350443AFC6454CCF3C7B87F53076CAA3BEB92F0354217C070448523FD9E668F3041AAAF20082989D5E630B3C4B3B3A6740692C6359906447857E2F920D48ADF89C11AE013B08DF1A0599E08211B0A961C4EE1143E6D8021CF64A5A5A95ABD5D4186531CF22A22BA85FD810936FDA48D8AA')    
    ori = decryptBWOTA(tukey,msg[18:])
    print('ori=',ori.hex())
    result = split_dispatcher_sig1_body_sig2(ori)
    print(result)
    for i in result.keys():
        print(result[i].hex())


    print('20180903')
    msg= bytes.fromhex('5F8ABBCD010035333533363335303830313031303838842984F15CEDED2D3855394B6DA99ECF0850661DC1594DD8C28004A401ED0A8A7F25F9E49C33780515524AD818EBD299715250863E71D779D281A3FC29FE844A5A13E78BC9E5B7BC6A005B231ED8F2D2B25E38A2')
    mw = msg[22:-4]
    print('mw=',mw)
    ori = decryptBWOTA(tukey,mw)
    print('ori=',ori.hex())
    result = split_dispatcher_sig1_body_sig2(ori)
    print(result)
    for i in result.keys():
        print(result[i].hex())