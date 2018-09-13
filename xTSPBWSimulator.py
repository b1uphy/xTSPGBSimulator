#!/usr/bin/env python3
# -*- coding: utf8 -*-
# bluphy@163.com
# 2018-08-23 11:38 by xw: copy from xTSPGBSimulator.
# 2018-05-24 16:52 by xw: new created.

#### BEGIN Calibration
DBHOST = '192.168.1.69'
DBPORT = 5432
DBNAME = 'bw_GBPrivate_db'
DBUSERNAME = 'bw_tester_admin'
DBPASSWORD = '123456'

#### END## Calibration

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
import threading



gInterrupt_flagstr = ''
gDBhdl = None
gVhlhdl = {}

#### BEGIN CallCenter Service
async def receiveMsgFromCC(client,reader)->bytes:
    result = {'msg':None, 'responsecode':0}
    msg = await reader.readline()
    if len(msg) > 5:
        result['msg'] = msg
    return result

async def sendMsg2CC(writer,msg:bytes):
    try:
        writer.write(msg)
        systime = time.time()
    except:
        print('Send Msg fail. Msg:',msg.hex())
    else:
        # writedb(msg,systime,1,gDBhdl)
        print('Send Msg:',msg.hex())

#### END## CallCenter Service

#### BEGIN Vehicle Service

#### END Vehicle Service

async def handle_cc_connection(reader:asyncio.StreamReader, writer:asyncio.StreamWriter):
    client = writer.get_extra_info('peername')
    print('Get connected from call center')
    print('Client {} connected.'.format(client))
    
    # vhl = ota.Vehicle(client)
    while True:  # <4>
        
        print(client,' Waiting msg...')

        #处理接收消息
        result = await receiveMsgFromCC(client,reader)
        if result['responsecode'] == 0:
            msg = result['msg']
        else:
            break
        if msg: print(msg)
        #处理响应消息
        # result = vhl.processMsg(msg)

        #发送响应消息        
        responseMsg = result['msg']
        if responseMsg:
            await sendMsg2CC(writer,responseMsg)
        if result['responsecode'] == 'Close':
            break

    print('Close the client socket')  # <17>
    writer.close()  # <18>

async def handle_vehicle_connection(reader:asyncio.StreamReader, writer:asyncio.StreamWriter):  # <3>
    '''
    This is the callback function for asyncio.start_server: client_connected_cb
    The client_connected_cb parameter is called with two parameters: 
    client_reader, client_writer. client_reader is a StreamReader object, 
    while client_writer is a StreamWriter object. 
    The client_connected_cb parameter can either be a plain callback function or a coroutine function; 
    if it is a coroutine function, it will be automatically converted into a Task.
    '''
    vhlclient = writer.get_extra_info('peername')
    vhlinterface = writer.get_extra_info('sockname')
    print('Client {} connected.'.format(vhlclient))
    vhl = ota.VehicleAgent(vhlinterface)
    vhl.initVhlInterface(reader,writer)

    while True:  # <4>        
        print('Waiting msg from {0}...'.format(vhlclient))
        await asyncio.gather(vhl.processVhlMsg(),vhl.txMsg2Vhl(),vhl.processAdvisorMsg(),vhl.txMsg2Advisor())


    print('Close the client socket')  # <17>
    writer.close()  # <18>
# END xTSPSimulator_TOP

# async def startTSP(loop,address2vhl='127.0.0.1', port2vhl=LISTENING_VHL_PORT, address2cc='127.0.0.1', port2cc=LISTENING_CC_PORT):
#     port2vhl = int(port2vhl)
#     port2cc = int(port2cc)  

#     #server_coro is a corotine object, asyncio.start_server is a corotine function
#     server2vhl_coro = await asyncio.start_server(handle_vehicle_connection, address2vhl, port2vhl, loop=loop) # <2>
#     server2cc_coro = await asyncio.start_server(handle_cc_connection, address2cc, port2cc, loop=loop)
#     return {'vhlServer':server2vhl_coro,'ccServer':server2cc_coro}


#### BEGIN xTSPSimulator_MAIN
def main(address2vhl='127.0.0.1', port2vhl=ota.LISTENING_VHL_PORT, address2cc='127.0.0.1', port2cc=ota.LISTENING_CC_PORT):  # <1>
    # global gDBhdl
    # gDBhdl = connectdb(DBNAME,DBUSERNAME,DBPASSWORD,DBHOST,DBPORT)

    loop = asyncio.get_event_loop()

    server2vhl_coro = asyncio.start_server(handle_vehicle_connection, address2vhl, port2vhl, loop=loop) # <2>
    server2cc_coro = asyncio.start_server(handle_cc_connection, address2cc, port2cc, loop=loop)
    print('Vehicle interface serving on {0} : {1}'.format(address2vhl,port2vhl))
    print('Call Center interface serving on {0} : {1}'.format(address2cc,port2cc))
    # tasks = [asyncio.ensure_future(server2vhl_coro),asyncio.ensure_future(server2cc_coro)]
    task = loop.create_task(asyncio.gather(server2cc_coro,server2vhl_coro))

    try:
        loop.run_forever()
    finally:
        loop.close()
 # <9>


if __name__ == '__main__':
    if xDEBUG:
        # logoutmsg = b'##\x01\xFELXVJ2GFC2GA030003\x04\x00\x08\x11\x11\x11\x11\x11\x11\x33\x33\x33'
        # dbhdl = connectdb(DBNAME,DBUSERNAME,DBPASSWORD,DBHOST,DBPORT)
        # conn = dbhdl['connection']
        # cur = dbhdl['cursor']
        # writedb(logoutmsg,time.time(),1,dbhdl)
        # cur.close()
        # conn.close()
        # print('db test ok')
        pass

    main(*sys.argv[1:])  # <10>
    
    # disconnect with database
    # gDBhdl['cursor'].close()
    # gDBhdl['connection'].close()
#### END xTSPSimulator_MAIN
