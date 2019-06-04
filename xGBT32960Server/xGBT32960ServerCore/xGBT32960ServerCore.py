#!/usr/bin/env python3
# -*- coding: utf8 -*-
# bluphy@163.com
# 2019-06-04 18:41:16 by xw: Fix bug for system blocked when can not write to log because of log file is opened by another application like excel
# 2019-04-16 13:58:00 by xw: Add breath time between coro loop, make advisor client response more quickly
# 2019-04-10 13:12:00 by xw: Optimize vehicle interface log, put logs in a same file for a same VIN
# 2019-04-03 16:37:00 by xw: Fix a bug when reply advisor client a reply msg has a timestamp prefix by mistake
# 2019-04-03 16:30:00 by xw: Add feature to support multi advisor cilent connect to a same vehicle.
# 2019-04-03 15:11:00 by xw: Fix bug when VIN is changed of the connected vehicle
# 2019-04-03 12:30:00 by xw: Add feature to reply connected vehicles to advisor client.
# 2018-12-06 15:47:43 by xw: delay some time after vehicle send logout msg
# 2018-12-06 15:26:25 by xw: handle an unicode error from advisor msg
# 2018-10-16 14:11:02 by xw: new created.

msg_ack = "{'name':'ack','data':{'name':'','reply':{'result':'','data':''}}}"

# BEGIN Calibration
TIMER_OTA_MSG_TIMEOUT = 30
TIMER_OTA_MSG_GOODBYE = 1

SIZE_VEHICLE_LOG_MAX = 10 # unit is megabytes
# END Calibration

gInterrupt_flagstr = ''
gVIN_Vhl_Advisor_Mapping = {}

xDEBUG = False

import sys,os
# sys.path.append('D:\\bluphy\\nutcloud\\xProject\\LogParser')

import time
import json
import asyncio
from asyncio import Queue,QueueEmpty,wait

from async_timeout import timeout

import base64

from .xDBService import writedb
from .xOTAGBT32960 import OTAGBData,createOTAGBMsg,CMD,genGBTime,timestamp

def getConnectedVehicles():
    global gVIN_Vhl_Advisor_Mapping
    VINs = []
    for VIN in gVIN_Vhl_Advisor_Mapping.keys():
        try:
            if gVIN_Vhl_Advisor_Mapping[VIN]['vhl'] != None:
                VINs.append(VIN)
        except KeyError:
            pass

    return VINs

# BEGIN APP Layer/
class Vehicle:
    def __init__(self,reader,writer,dbhdl):
        self.client = writer.get_extra_info('peername')
        print(f'{timestamp()}\tVehicle {self.client} connected.')
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
            await asyncio.sleep(0.1) #加入短暂延时以便其他携程有机会获取CPU时间
            counter += 1
            print('counter=',counter)
            print(self.client,f'{timestamp()}\tWaiting msg...')

            #处理接收消息
            result = await self.receiveMsg()
            if result['code'] == 0:
                msg = result['msg']
            else:
                print(f'{timestamp()}\tRx error msg in vehicle interface, code=',result['code'])
                break        
            #处理响应消息
            result = self.processMsg(msg)        
            responseMsg = result['msg']
            responseCode = result['code']
            if responseMsg:
                await self.sendMsg(responseMsg)
            if responseCode == 'Close':
                await asyncio.sleep(TIMER_OTA_MSG_GOODBYE)    
                break
            elif responseCode == 'ErrorCMD':
                pass
            elif responseCode == 'InvalidMsgFormat':
                pass

    def processMsg(self,msg)->bytes:
        result = {'msg':None, 'code':0}
        self.msg = msg
        try:
            self.data = OTAGBData(msg)
        except IndexError as e:
            result['code'] = 'InvalidMsgFormat'
            try:
                print(f"{timestamp()}\tWARNING: Invalid msg format ->{self.VIN}: {e} ")
            except:
                print(f"{timestamp()}\tWARNING: Invalid msg format ->VIN Unknown: {e} ")
            self.writeLog(f"Invalid msg format {e}")
        else:
            if xDEBUG:
                print(f'{timestamp()}\tRx vehicle msg:')
                self.data.printself()

            if self.VIN:
                #当不是连接后的第一条消息时
                if self.VIN != self.data.head.VIN.phy:
                    print(f'{timestamp()}\tWARNING: VIN is not match')
                    self.unregister() #老VIN取消注册
                    self.initVhl()
            else:
                #TCP连接后的第一条消息
                self.initVhl()
            
            if self.data.head.cmd.phy == '车辆登入':
                self.state = 'Login'
                print(f'{timestamp()}\tVehicle login: VIN = {self.VIN}')
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
                print(f'{timestamp()}\tVehicle logout: VIN = {self.VIN}',)
                result = self.responseLogout()

            elif self.data.head.cmd.phy == '心跳':
                result = self.responseHeartbeat()
            else:
                print(f'{timestamp()}\tError CMD')
                result['code'] = 'ErrorCMD'

            self.forward2Advisors(self.msg)

            self.writeLog()

        return result

    def responseLogin(self):
        result = {'msg':None, 'code':0}
        if xDEBUG:
            print(f'{timestamp()}\tData payload')
            print(self.data.payload.phy)
        result['msg'] = createOTAGBMsg(b'\x01', b'\x01', self.VIN, 1, genGBTime()+self.data.payload.raw[6:])
        print(f"{timestamp()}\tResponse {result['msg']}")
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

    def writeLog(self, extracontents=None):
        ##采集数据写入日志
        rxtime = time.strftime('%Y%m%d %H:%M:%S,')
        gbdatas = self.msg.hex()

        try:
            with open(self.logpath,'a') as log:
                log.write(rxtime+gbdatas+'\n')
                if extracontents:
                    log.write(rxtime+extracontents+'\n')
        except IOError or PermissionError:
            print(f'{timestamp()}\tWARNING: write log fail {rxtime} -> {gbdatas}')

    def initVhl(self):
        self.VIN = self.data.head.VIN.phy
        self.logpath = f"log\\{self.VIN}.csv"
        if os.path.exists(self.logpath):
            if os.path.getsize(self.logpath)/(1024*1024)>SIZE_VEHICLE_LOG_MAX:
                os.rename(self.logpath, f"{self.logpath.rsplit('.',1)[0]}_{time.strftime('%Y%m%d%H%M%S')}.csv")
        self.register() #注册新的VIN

    def register(self):
        try:
            gVIN_Vhl_Advisor_Mapping[self.VIN]
        except KeyError:
            gVIN_Vhl_Advisor_Mapping[self.VIN] = {}
        finally:
            print(f'{timestamp()}\tRegister vehicle {self.VIN}')
            gVIN_Vhl_Advisor_Mapping[self.VIN]['vhl'] = self

    def unregister(self):
        try:
            gVIN_Vhl_Advisor_Mapping[self.VIN]['vhl'] = None
            
        except KeyError:
            print(f"{timestamp()}\tVIN: {self.VIN} is not registered")
        else:
            print(f"{timestamp()}\tVIN: {self.VIN} is unregistered")

    def createGBT32960Msg(self,msg):
        return json.dumps({'name':'gbdata','data':base64.standard_b64encode(msg).decode('ascii')}).encode('utf8')

    def forward2Advisors(self,msg):
       
        try:
            self.advisors = gVIN_Vhl_Advisor_Mapping[self.VIN]['advisors']            
        except KeyError:
            pass            
        else:
            for advisor in self.advisors:
                if advisor:
                    advisor.putVhlMsg(self.createGBT32960Msg(msg))
                    if xDEBUG:
                        print(f'{timestamp()}\tForward2Advisor {advisor.username}') 

    async def receiveMsg(self)->bytes:
        result = {'msg':None, 'code':-1}
        header = None
        try:
            # rxtime = time.strftime('%Y%m%d %H:%M:%S')
            async with timeout(TIMER_OTA_MSG_TIMEOUT):
                header = await self.reader.readexactly(24)
        except asyncio.TimeoutError:
            print(f'{timestamp()}\tRx timeout')
            print(f'{timestamp()}\tClose connection with vehicle because of header timeout')
            result['code'] = 'TimeoutHeader'
            self.unregister()    
        except OSError:
            print(f'{timestamp()}\tConnection with vehicle VIN: {self.VIN} broken!')
            result['code'] = 'Connection broken'
            self.unregister()
        except Exception as e:
            print(f'{timestamp()}\tERROR: unhandled error in receive vehicle msg header,', e)
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
                except asyncio.TimeoutError:                   
                    print(f'{timestamp()}\tRx timeout')
                    print(f'{timestamp()}\tClose connection because of body timeout')
                    result['code'] = 'TimeoutBody'
                    self.unregister()
                except asyncio.IncompleteReadError as err:
                    print(f'{timestamp()}\tWARNING: wrong msg format {err}')
                except OSError:
                    print(f'{timestamp()}\tWARNING: got connection error')
                    result['code'] = 'Connection broken'
                    self.unregister()
                except Exception as e:
                    print(f'{timestamp()}\tERROR: unhandled error in receive vehicle msg body,{e}')
                else:
                    if data:
                        result['msg'] = header+data            
                        writedb(result['msg'],time.time(),0,self.db)
                        
                        print(f"{timestamp()}\tReceived from vehicle {self.client}:\t{result['msg'].hex().upper()}")  
                        result['code'] = 0

        return result

    async def sendMsg(self,msg:bytes):
        try:
            self.writer.write(msg)        
        except OSError:
            print(f'{timestamp()}\tSend Msg to vehicle fail -> Msg:{msg.hex()}')
        else:
            systime = time.time()
            writedb(msg,systime,1,self.db)
            print(f'{timestamp()}\tSend Msg to vehicle: {msg.hex()}')

class Advisor:
    def __init__(self,reader,writer):
        self.client = writer.get_extra_info('peername')
        print(f'{timestamp()}\tClient {self.client} connected as advisor')
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
            print(f'{timestamp()}\tStart advisor subloop')
            print(f'{timestamp()}\tAdvisor {self.username} counter=xxx')

        done, pending = await wait([self.rxloop(),self.txloop()])
        for f in pending:
            f.cancel()
        if xDEBUG:
            print(f'{timestamp()}\tEnd advisor subloop')
       

    async def rxloop(self):
        if xDEBUG:
            print(f'{timestamp()}\tRun advisor rxloop')
        rxcounter = 0
        while not self.reader.at_eof():
            try:
                result = await self.receiveMsg()
            except OSError as e:
                print(f'{timestamp()}\tERROR: {e}')
                break
            else:
                print(f'{timestamp()}\tProcessing msg...')
                if result['code'] == 0:
                    processresult = self.processMsg(result['msg'])
                    if processresult ['code'] == 0:
                        pass
                    elif processresult['code'] == 'UnicodeError':
                        pass
                    elif processresult['code'] == 'AttributeError':
                        pass
                    else:
                        pass
                else:
                    print(f"{timestamp()}\tRx error msg in vehicle interface, code = {result['code']}")
            rxcounter +=1

            if xDEBUG:
                print(f'{timestamp()}\tAdvisor {self.username} rx counter {rxcounter}')
            # if self.terminateFlag: break

    async def txloop(self):
        if xDEBUG:
            print(f'{timestamp()}\tRun advisor {self.username} txloop')
        txcounter = 0
        while True:
            await asyncio.sleep(0.1) #加入短暂延时以便其他携程有机会获取CPU时间
            msg = await self.outputQueue.get()
            
            try:
                result = await self.sendMsg(msg)
            except OSError:
                print(f'{timestamp()}\tFail to send Msg to advisor {self.username}: {msg.hex()}')
                self.destroy() #失败后回收资源
                break
            else:
                print(f'{timestamp()}\tSend Msg to advisor {self.username}: {msg.hex()}')
            finally:
                txcounter += 1

                if xDEBUG:
                    print(f"{timestamp()}\tSend result is Code {result['code']}")
                    print(f'{timestamp()}\tAdvisor {self.username} tx counter {txcounter}')            
            
    async def receiveMsg(self,timeout=-1):
        if xDEBUG:
            print(f'{timestamp()}\tReceiving msg from advisor {self.username}')

        result = {'msg':None, 'code':0}
        # raw = None
        # header = None
        # body = None

        raw = await self.reader.readline()
        # header =  raw[:3]         #Should used for check msg format 
        # length = int.from_bytes(header, byteorder='big')
        body = raw[3:-1]

        if body:
            result['msg'] = body            
            print(f"{timestamp()}\tReceived from advisor {self.client}:\t{result['msg'].decode('utf8')}") 
        else:
            result['code'] = 'BlankMsg'
            print(f"{timestamp()}\tReceived blank msg from advisor {self.client}") 
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
        print(f'{timestamp()}\tAdvisor {self.username} disconnected')

    def bindVhl(self):       
        try:
            gVIN_Vhl_Advisor_Mapping[self.VIN]
        except KeyError:
            gVIN_Vhl_Advisor_Mapping[self.VIN] = {}
        finally:
            print(f'{timestamp()}\tBind advisor {self.username} to vehicle {self.VIN}')
            try:
                gVIN_Vhl_Advisor_Mapping[self.VIN]['advisors']
            except KeyError:
                gVIN_Vhl_Advisor_Mapping[self.VIN]['advisors'] = []
            finally:
                gVIN_Vhl_Advisor_Mapping[self.VIN]['advisors'].append(self)

    def unbindVhl(self):
        try:
            gVIN_Vhl_Advisor_Mapping[self.VIN]['advisors'].remove(self)
        except (KeyError, ValueError):
            print(f'{timestamp()}\tAdvisor {self.username} NOT bind with vehicle yet')
        else:
            print(f'{timestamp()}\tUnbind advisor {self.username} to vehicle {self.VIN}')  
            # gVIN_Vhl_Advisor_Mapping[self.VIN]['advisor'] = None 
            self.VIN = ''

    def login(self,msgobj):        
        self.username = msgobj['data']['username']
        self.replyOK(msgobj)

        print(f'{timestamp()}\tAdvisor {self.username} login')

    def selectVhl(self,msgobj):
        self.unbindVhl()
        self.VIN = msgobj['data']['VIN']
        print(f'{timestamp()}\tAdvisor {self.username} select vehicle {self.VIN}')
        self.bindVhl()
        self.replyOK(msgobj)

    def disconnect_vehicle(self,msgobj):
        self.unbindVhl()
        self.replyOK(msgobj)

    def echo(self,msgobj):
        replydata = f'Advisor is {self.username}, selected vehicle {self.VIN}'
        self.replyOKWithData(msgobj,replydata)
        print(replydata)

    def logout(self,msgobj):
        self.replyOK(msgobj)
        self.destroy()

    def showConnectedVehicles(self, msgobj):
        print(f"{timestamp()}\tReceive command {msgobj['name']}")
        replydata = ','.join(getConnectedVehicles())
        print(f"{timestamp()}\tConnected vehicles:{replydata}")
        self.replyOKWithData(msgobj, replydata)

    def processMsg(self,msg:bytes):
        if xDEBUG:
            print(f"{timestamp()}\tProcessing msg to advisor {self.username}")

        result = {'msg':None, 'code':0}
        try:
            msgobj = json.loads(msg.decode('utf8'))
        except UnicodeError as e:
            print( f"{timestamp()}\tWARNING: advisor msg format is not good, {e}")
            result['code'] = 'UnicodeError'
        except AttributeError as e:
            print( f"{timestamp()}\tWARNING: advisor msg is None, {e}")
            result['code'] = 'AttributeError'
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
                elif msgobj['name'] == 'show_connected_vehicles':
                    self.showConnectedVehicles(msgobj)
            else:
                print( f'{timestamp()}\tWARNING: msg format error : {msg.hex()}')

        return result

# END APP layer