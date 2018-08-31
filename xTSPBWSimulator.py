#!/usr/bin/env python3
# -*- coding: utf8 -*-
# bluphy@163.com
# 2018-08-23 11:38 by xw: copy from xTSPGBSimulator.
# 2018-05-24 16:52 by xw: new created.

# BEGIN Calibration
DBHOST = '192.168.1.69'
DBPORT = 5432
DBNAME = 'bw_GBPrivate_db'
DBUSERNAME = 'bw_tester_admin'
DBPASSWORD = '123456'

TIMER_OTA_MSG_TIMEOUT = 30
LISTEMING_PORT = 9201
# END Calibration

# BEGIN debug
xDEBUG = True

# END debug 

# BEGIN xTSPSimulator_TOP
import sys
import asyncio
import functools
import time
# from xDBService import writedb,connectdb
from async_timeout import timeout
import xOTABW as ota 
from xDUTDBSevice import getDUTInfo,generateTUKEY,setDUTInfo


gInterrupt_flagstr = ''
gDBhdl = None
# BEGIN APP Layer/
class Vehicle:
    def __init__(self,client):
        self.client = client
        self.imei = None
        self.state = 'connected'
        self.data = None
        # self.msg = None
        self.info = None
        self.eventID = None
        self.uplink = None
        self.downlink = None

    def processMsg(self,msg)->bytes:
        if not self.imei:
            self.imei = ota.Header_OTABW(msg[:18]).IMEI.phy
            print('imei=',self.imei)
            self.info = getDUTInfo(self.imei)

        decrypted = ota.split_dispatcher_sig1_body_sig2(ota.decryptBWOTA(self.info['TUKEY'],msg[18:]))
        dispatcher = ota.Dispatcher_OTABW(decrypted['dispatcher'])
        sig1 = ota.Dispatcher_OTABW(decrypted['dispatcher'])
        if len(decrypted.keys())>2:
            body = ota.Body_OTABWMsg(decrypted['body'])
            sig2 = ota.Body_OTABWMsg(decrypted['sig2'])

        result = {'msg':None, 'responsecode':0}
        
        # if self.VIN:
        #     if self.VIN != self.data.head.VIN.raw:
        #         self.VIN = self.data.head.VIN.raw
        #         print('VIN is not match')
        # else:
        #     self.VIN = self.data.head.VIN.raw

        # if self.data.head.cmd.phy == '车辆登入':
        #     self.state = 'Login'
        #     print('Vehicle login: VIN = ',self.VIN.decode('ascii'))
        #     result = self.responseLogin()

        # elif self.data.head.cmd.phy == '实时数据' or self.data.head.cmd.phy == '补发数据':
        #     pass

        # elif self.data.head.cmd.phy == '车辆登出':
        #     print('Vehicle logout: VIN = ',self.VIN.decode('ascii'))
        #     result = self.responseLogout()

        # elif self.data.head.cmd.phy == '心跳':
        #     result = self.responseHeartbeat()
        # else:
        #     print('Error CMD')
        #     result['responsecode'] = 'Error CMD'
        
        return result

    def responseLogin(self):
        result = {'msg':None, 'responsecode':0}
        result['msg'] = createOTAGBMsg(CMD.inv['车辆登入'], b'\x01', self.VIN, 1, 30, genGBTime()+self.data.payload[6:])
        print("response result['msg']",result['msg'])
        return result

    def responseLogout(self):
        result = {'msg':None, 'responsecode':'Close'}
        result['msg'] = createOTAGBMsg(CMD.inv['车辆登出'], b'\x01', self.VIN, 1, 8, genGBTime()+self.data.payload[6:])
        return result

    def responseHeartbeat(self):
        result = {'msg':None, 'responsecode':0}
        result['msg'] = createOTAGBMsg(CMD.inv['心跳'], b'\x01', self.VIN, 1, 0, b'')
        return result

# END APP layer

# BEGIN OTA Layer
async def receiveMsg(client,reader)->bytes:
    '''
    return the raw msg bytes without the OTABW_PREFIX and OTABW_SUFFIX
    '''
    result = {'msg':None, 'responsecode':0}
    OTAprefix = None
    try:
        rxtime = time.strftime('%Y%m%d %H:%M:%S')
        async with timeout(TIMER_OTA_MSG_TIMEOUT):
            OTAprefix = await reader.readexactly(4)
            
    except asyncio.TimeoutError:
        print('Rx timeout')
        print('Close connection because of timeout')
        result['responsecode'] = 'Timeout!'    
    except:
        print('Connection broken!')
        result['responsecode'] = 'Connection broken'

    if OTAprefix and OTAprefix == ota.OTABW_PREFIX:
        #print('Received header {0}:\t{1}'.format(client,header.hex()))
        # lengthraw = header[-2:]
        #print('lengthraw:{}'.format(lengthraw))
        # length = int.from_bytes(lengthraw, byteorder='big')+1 # the length including the sum byte
        #print('length:{}'.format(length))

        raw = None
        try:
            async with timeout(TIMER_OTA_MSG_TIMEOUT):
                raw = await reader.readuntil(b'\xb2\x5e\x38\xa2')
            systime = time.time()
            
        except asyncio.TimeoutError:
            print('Rx timeout')
            print('Close connection because of timeout')
            result['responsecode'] = 'Timeout!'           
        
        if raw:
            
            result['msg'] = raw[:-4]
            # writedb(result['msg'],systime,0,gDBhdl)
            print('{0} Received from {1}:\t{2}'.format(rxtime,client,raw.hex()))  # <10>

    return result

async def sendMsg(writer,msg:bytes):
    try:
        writer.write(msg)
        systime = time.time()
    except:
        print('Send Msg fail. Msg:',msg.hex())
    else:
        # writedb(msg,systime,1,gDBhdl)
        print('Send Msg:',msg.hex())
# END OTA layer


async def handle_vehicle_connection(reader:asyncio.StreamReader, writer:asyncio.StreamWriter):  # <3>
    '''
    This is the callback function for asyncio.start_server: client_connected_cb
    The client_connected_cb parameter is called with two parameters: 
    client_reader, client_writer. client_reader is a StreamReader object, 
    while client_writer is a StreamWriter object. 
    The client_connected_cb parameter can either be a plain callback function or a coroutine function; 
    if it is a coroutine function, it will be automatically converted into a Task.
    '''
    client = writer.get_extra_info('peername')
    print('Client {} connected.'.format(client))
    counter = 0
    vhl = Vehicle(client)
    while True:  # <4>
        counter += 1
        print('counter=',counter)
        print(client,' Waiting msg...')

        #处理接收消息
        result = await receiveMsg(client,reader)
        if result['responsecode'] == 0:
            msg = result['msg']
        else:
            break
        
        #处理响应消息
        result = vhl.processMsg(msg)

        #发送响应消息        
        responseMsg = result['msg']
        if responseMsg:
            await sendMsg(writer,responseMsg)
        if result['responsecode'] == 'Close':
            break

    print('Close the client socket')  # <17>
    writer.close()  # <18>
# END xTSPSimulator_TOP

#### BEGIN xTSPSimulator_MAIN
def main(address='127.0.0.1', port=LISTEMING_PORT):  # <1>
    # global gDBhdl
    # gDBhdl = connectdb(DBNAME,DBUSERNAME,DBPASSWORD,DBHOST,DBPORT)

    port = int(port)
    loop = asyncio.get_event_loop()
    server_coro = asyncio.start_server(handle_vehicle_connection, address, port, loop=loop) # <2>
    server = loop.run_until_complete(server_coro) # <3>

    host = server.sockets[0].getsockname()  # <4>
    print('xTSPBWSimulator serving on {}. Hit CTRL-C to stop.'.format(host))  # <5>

    try:
        loop.run_forever()  # <6>
        print('Can not be here')
    except KeyboardInterrupt:  # CTRL+C pressed
        pass

    print('Server shutting down.')
    server.close()  # <7>
    loop.run_until_complete(server.wait_closed())  # <8>
    loop.close()  # <9>


if __name__ == '__main__':
    if xDEBUG:
        # logoutmsg = b'##\x01\xFELXVJ2GFC2GA030003\x04\x00\x08\x11\x11\x11\x11\x11\x11\x33\x33\x33'
        # dbhdl = connectdb(DBNAME,DBUSERNAME,DBPASSWORD,DBHOST,DBPORT)
        # conn = dbhdl['connection']
        # cur = dbhdl['cursor']
        # writedb(logoutmsg,time.time(),1,dbhdl)
        # cur.close()
        # conn.close()
        print('db test ok')

    main(*sys.argv[1:])  # <10>
    
    # disconnect with database
    # gDBhdl['cursor'].close()
    # gDBhdl['connection'].close()
#### END xTSPSimulator_MAIN
