#!/usr/bin/env python3
# -*- coding: utf8 -*-
# bluphy@163.com
# 2018-12-06 15:47:43 by xw: delay some time after vehicle send logout msg
# 2018-12-06 15:26:25 by xw: handle an unicode error from advisor msg
# 2018-10-16 14:11:02 by xw: new created.

msg_ack = "{'name':'ack','data':{'name':'','reply':{'result':'','data':''}}}"

# BEGIN Calibration
TIMER_OTA_MSG_TIMEOUT = 30
TIMER_OTA_MSG_GOODBYE = 1
LISTEMING_PORT = 9201
# END Calibration

gInterrupt_flagstr = ''
gVIN_Vhl_Advisor_Mapping = {}

xDEBUG = False

import sys
# sys.path.append('D:\\bluphy\\nutcloud\\xProject\\LogParser')

import time
import json
import asyncio
from asyncio import Queue,QueueEmpty,wait

from async_timeout import timeout

import base64

from .xDBService import writedb
from .xOTAGBT32960 import OTAGBData,createOTAGBMsg,CMD,genGBTime

# BEGIN APP Layer/
class Vehicle:
    def __init__(self,reader,writer,dbhdl):
        self.client = writer.get_extra_info('peername')
        print('Vehicle {} connected.'.format(self.client))
        self.reader = reader
        self.writer = writer
        self.db = dbhdl
        self.VIN = None # str
        self.state = 'connected'
        self.data = None # OTAGBData obj
        self.msg = None # bytes
        self.advisor = None
    
    async def startloop(self):
        counter = 0
        while True:  # <4>
            counter += 1
            print('counter=',counter)
            print(self.client,' Waiting msg...')

            #处理接收消息
            result = await self.receiveMsg()
            if result['code'] == 0:
                msg = result['msg']
            else:
                print('rx error msg in vehicle interface, code=',result['code'])
                break        
            #处理响应消息
            result = self.processMsg(msg)        
            responseMsg = result['msg']
            if responseMsg:
                await self.sendMsg(responseMsg)
            if result['code'] == 'Close':
                await asyncio.sleep(TIMER_OTA_MSG_GOODBYE)    
                break        


    def processMsg(self,msg)->bytes:
        result = {'msg':None, 'code':0}
        self.msg = msg
        self.data = OTAGBData(msg)

        if xDEBUG:
            print('rx vehicle msg:')
            self.data.printself()

        if self.VIN:
            #当不是连接后的第一条消息时
            if self.VIN != self.data.head.VIN.phy:
                self.VIN = self.data.head.VIN.phy
                print('VIN is not match')
        else:
            #TCP连接后的第一条消息
            self.VIN = self.data.head.VIN.phy
            self.logname = '{0}_{1}.csv'.format(self.VIN,time.strftime('%Y%m%d%H%M%S'))
            self.register()
        
        if self.data.head.cmd.phy == '车辆登入':
            self.state = 'Login'
            print('Vehicle login: VIN = ',self.VIN)
            result = self.responseLogin()

        elif self.data.head.cmd.phy == '实时数据' or self.data.head.cmd.phy == '补发数据':

            #BDDemo
            '''
            chargingState_raw = self.data.payload[8]
            if chargingState_raw==1:
                chargingState = 1
            else:
                chargingState = 0
            SOC =self.data.payload[5]
            print('SOC=',SOC)
            print('Vehicle {0} chargingState={1}'.format(self.VIN,chargingState))
            with open('C:\\BDdemo\\demo.json','w') as fout:
                fout.write(json.dumps({'chargingState':chargingState,'SOC':SOC}))
            '''
            pass

        elif self.data.head.cmd.phy == '车辆登出':
            print('Vehicle logout: VIN = ',self.VIN)
            result = self.responseLogout()

        elif self.data.head.cmd.phy == '心跳':
            result = self.responseHeartbeat()
        else:
            print('Error CMD')
            result['code'] = 'Error CMD'

        self.forward2Advisor(self.msg)
        self.writeLog()

        return result

    def responseLogin(self):
        result = {'msg':None, 'code':0}
        if xDEBUG:
            print('data payload')
            print(self.data.payload.phy)
        result['msg'] = createOTAGBMsg(b'\x01', b'\x01', self.VIN, 1, genGBTime()+self.data.payload.raw[6:])
        print("response result['msg']",result['msg'])
        return result

    def responseLogout(self):
        result = {'msg':None, 'code':'Close'}
        result['msg'] = createOTAGBMsg(b'\x04', b'\x01', self.VIN, 1, genGBTime()+self.data.payload.raw[6:])        
        return result

    def responseHeartbeat(self):
        result = {'msg':None, 'code':0}
        result['msg'] = createOTAGBMsg(b'\x07', b'\x01', self.VIN, 1, b'')
        return result

    def destroy(self):
        self.VIN = None
        self.writer.close()
        # self.log.close()

    def writeLog(self):
        ##采集数据写入日志
        rxtime = time.strftime('%Y%m%d %H:%M:%S,')
        gbdatas = self.msg.hex()

        try:
            with open('log\\'+self.logname,'a') as log:
                log.write(rxtime+gbdatas+'\n')
        except IOError:
            print('[Warning] : write log fail {0} -> {1}'.format(rxtime,gbdatas))

    def register(self):
        try:
            gVIN_Vhl_Advisor_Mapping[self.VIN]
        except KeyError:
            gVIN_Vhl_Advisor_Mapping[self.VIN] = {}
        finally:
            print('register vehicle {0}'.format(self.VIN))
            gVIN_Vhl_Advisor_Mapping[self.VIN]['vhl'] = self

    def createGBT32960Msg(self,msg):
        return json.dumps({'name':'gbdata','data':base64.standard_b64encode(msg).decode('ascii')}).encode('utf8')

    def forward2Advisor(self,msg):
       
        try:
            self.advisor = gVIN_Vhl_Advisor_Mapping[self.VIN]['advisor']            
        except KeyError:
            pass            
        else:
            if self.advisor:
                self.advisor.putVhlMsg(self.createGBT32960Msg(msg))
                if xDEBUG:
                    print('forward2Advisor') 

    async def receiveMsg(self)->bytes:
        result = {'msg':None, 'code':-1}
        header = None
        try:
            # rxtime = time.strftime('%Y%m%d %H:%M:%S')
            async with timeout(TIMER_OTA_MSG_TIMEOUT):
                header = await self.reader.readexactly(24)
                
        except asyncio.TimeoutError:
            print('Rx timeout')
            print('Close connection with vehicle because of timeout')
            result['code'] = 'Timeout!'    
        except OSError:
            print('Connection with vehicle broken!')
            result['code'] = 'Connection broken'
        except Exception as e:
            print('ERROR: unhandled error in receive vehicle msg header,', e)
        else:
            if header:
                #print('Received header {0}:\t{1}'.format(client,header.hex()))
                lengthraw = header[-2:]
                #print('lengthraw:{}'.format(lengthraw))
                length = int.from_bytes(lengthraw, byteorder='big')+1 # the length including the sum byte
                #print('length:{}'.format(length))

                data = None
                try:
                    async with timeout(TIMER_OTA_MSG_TIMEOUT):
                        data = await self.reader.readexactly(length)
                    systime = time.time()
                except asyncio.TimeoutError:
                    
                    print('Rx timeout')
                    print('Close connection because of timeout')
                    result['code'] = 'Timeout!'
                except asyncio.IncompleteReadError as err:
                    print('WARNING: wrong msg format ',err)

                except OSError:
                    print('WARNING: got connection error')
                    result['code'] = 'Connection broken'
                except Exception as e:
                    print('ERROR: unhandled error in receive vehicle msg body,', e)
                else:
                    if data:
                        result['msg'] = header+data            
                        writedb(result['msg'],systime,0,self.db)
                        timestamp = time.strftime('%Y%m%d %H:%M:%S',time.localtime(systime))
                        print('{0} Received from vehicle {1}:\t{2}'.format(timestamp,self.client,result['msg'].hex().upper()))  # <10>
                        result['code'] = 0

        return result

    async def sendMsg(self,msg:bytes):
        try:
            self.writer.write(msg)        
        except OSError:
            print('Send Msg to vehicle fail -> Msg:',msg.hex())
        else:
            systime = time.time()
            writedb(msg,systime,1,self.db)
            print('Send Msg to vehicle:',msg.hex())

class Advisor:
    def __init__(self,reader,writer):
        self.client = writer.get_extra_info('peername')
        print('Client {} connected as advisor.'.format(self.client))
        self.VIN = '' # str
        self.username = None #str
        self.msg = None # bytes

        #msg queue between vehicle interface
        self.vhlMsgInQueue = Queue()
        self.vhlMsgOutQueue = Queue()

        #msg queue between advisor client interface
        self.inputQueue = Queue()
        self.outputQueue = Queue()

        #socket interface with advisor client 
        self.reader = reader
        self.writer = writer
   
    def putVhlMsg(self,msg:bytes):
        self.outputQueue.put_nowait(msg)

    async def startloop(self):
        if xDEBUG:
            print('Start advisor subloop')
            print('Advisor {0} counter=xxx'.format(self.username))

        done,pending = await wait([self.rxloop(),self.txloop()])
        for f in pending:
            f.cancel()
        if xDEBUG:
            print('End advisor subloop')
       

    async def rxloop(self):
        if xDEBUG:
            print('run rxloop')
        rxcounter = 0
        while True:
            try:
                result = await self.receiveMsg()
            except OSError:   
                break
            else:
                print('Processing msg...')
                if result['code'] == 0:
                    self.processMsg(result['msg'])
                else:
                    print('rx error msg in vehicle interface, code=',result['code'])
            rxcounter +=1

            if xDEBUG:
                print('Advisor {0} rx counter {1}'.format(self.username,rxcounter))
            # if self.terminateFlag: break

    async def txloop(self):
        if xDEBUG:
            print('run txloop')
        txcounter = 0
        while True:
            msg = await self.outputQueue.get()
            timestamp = time.strftime('%Y%m%d %H:%M:%S')

            try:
                result = await self.sendMsg(msg)
            except OSError:
                print('{0} Send Msg to advisor {1} fail: {2}'.format(timestamp,self.username,msg.hex()))
                break
            else:
                print('{0} Send Msg to advisor {1}: {2}'.format(timestamp,self.username,msg.hex()))
            finally:
                txcounter += 1

                if xDEBUG:
                    print(result['code'])
                    print('Advisor {0} tx counter {1}'.format(self.username,txcounter))            
            
    async def receiveMsg(self,timeout=-1):
        result = {'msg':None, 'code':0}
        raw = None
        header = None
        body = None

        raw = await self.reader.readline()
        header =  raw[:3]          
        length = int.from_bytes(header, byteorder='big')
        body = raw[3:-1]

        systime = time.time()
        if body:
            result['msg'] = body            
            timestamp = time.strftime('%Y%m%d %H:%M:%S',time.localtime(systime))
            print('{0} Received from advisor {1}:\t{2}'.format(timestamp,self.client,result['msg'].decode('utf8'))) 

        return result

    def reply(self,ack):
        self.outputQueue.put_nowait(json.dumps(ack).encode('utf8'))

    def replyOK(self,msgobj):
        if xDEBUG:
            print('reply')
        ack = eval(msg_ack)
        ack['data']['name'] = msgobj['name']
        ack['data']['reply']['result'] = 'OK'
        # ack['data']['reply']['data'] = ''
        self.reply(ack)

    def replyOKWithData(self,msgobj,data:str):
        if xDEBUG:
            print('reply')
        ack = eval(msg_ack)
        ack['data']['name'] = msgobj['name']
        ack['data']['reply']['result'] = 'OK'
        ack['data']['reply']['data'] = data
        self.reply(ack)

    async def sendMsg(self,body:bytes):
        result = {'msg':None, 'code':0}
        tail = b'\n'
        header = len(body).to_bytes(3,'big')
        self.writer.write(header+body+tail)
        await self.writer.drain()
        return result

    def destroy(self):
        self.unbindVhl()
        self.writer.close()
        print('Advisor {0} disconnected'.format(self.username))

    def bindVhl(self):       
        try:
            gVIN_Vhl_Advisor_Mapping[self.VIN]
        except KeyError:
            gVIN_Vhl_Advisor_Mapping[self.VIN] = {}
        finally:
            print('bind advisor {0} to vehicle {1}'.format(self.username,self.VIN))
            gVIN_Vhl_Advisor_Mapping[self.VIN]['advisor'] = self

    def unbindVhl(self):
        try:
            gVIN_Vhl_Advisor_Mapping[self.VIN]['advisor']
        except KeyError:
            print("advisor {0} NOT bind with vehicle yet")
        else:
            print('unbind advisor {0} to vehicle {1}'.format(self.username,self.VIN))  
            gVIN_Vhl_Advisor_Mapping[self.VIN]['advisor'] = None 
            self.VIN = ''

    def login(self,msgobj):        
        self.username = msgobj['data']['username']
        self.replyOK(msgobj)

        print('advisor {0} login'.format(self.username))

    def selectVhl(self,msgobj):
        self.unbindVhl()
        self.VIN = msgobj['data']['VIN']
        print('advisor {0} select vehicle {1}'.format(self.username,self.VIN))
        self.bindVhl()
        self.replyOK(msgobj)

    def disconnect_vehicle(self,msgobj):
        self.unbindVhl()
        self.replyOK(msgobj)

    def echo(self,msgobj):
        replydata = 'Advisor is {0}, selected vehicle {1}'.format(self.username,self.VIN)
        self.replyOKWithData(msgobj,replydata)
        print(replydata)

    def logout(self,msgobj):
        self.replyOK(msgobj)
        self.destroy()
        
    def processMsg(self,msg:bytes):
        result = {'msg':None, 'code':0}
        try:
            msgobj = json.loads(msg.decode('utf8'))
        except UnicodeError as e:
            print('WARNING: advisor msg format is not good,',e)
        else:
            if type(msgobj) == dict:
                if msgobj['name'] == 'login':
                    self.login(msgobj)
                elif msgobj['name'] == 'select_vehicle':
                    self.selectVhl(msgobj)
                elif msgobj['name'] == 'disconnect_vehicle':
                    self.disconnect_vehicle(msgobj)
                elif msgobj['name'] == 'echo':
                    self.echo(msgobj)
            else:
                print('WARNING: msg format error : {0}'.format(msg.hex()))

        return result

# END APP layer