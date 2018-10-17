#!/usr/bin/env python3
# -*- coding: utf8 -*-
# bluphy@163.com
# 2018-08-23 11:38 by xw: copy from xTSPGBSimulator.
# 2018-05-24 16:52 by xw: new created.

#### BEGIN Calibration
DBHOST = '10.40.162.31'
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
sys.path.append(sys.path[0].rsplit('\\',1)[0])

import asyncio
import functools
import time
# from xDBService import writedb,connectdb
from async_timeout import timeout
import xOTABW.xOTABW as ota
import threading



gInterrupt_flagstr = ''
gDBhdl = None


#### BEGIN Advisor Service
async def receiveMsgFromAdvisor(client,reader)->bytes:
    result = {'msg':None, 'responsecode':0}
    msg = await reader.readline()
    if len(msg) > 5:
        result['msg'] = msg
    return result

async def sendMsg2Advisor(writer,msg:bytes):
    try:
        writer.write(msg)
        systime = time.time()
    except:
        print('Send Msg fail. Msg:',msg.hex())
    else:
        # writedb(msg,systime,1,gDBhdl)
        print('Send Msg:',msg.hex())

#### END## Advisor Service

#### BEGIN Vehicle Service

#### END Vehicle Service

async def handle_advisor_connection(reader:asyncio.StreamReader, writer:asyncio.StreamWriter):
    advisorclient = writer.get_extra_info('peername')
    advisorcinterface = writer.get_extra_info('sockname')
    print('Client {} connected.'.format(advisorclient))
    advisor = ota.AdvisorAgent(advisorcinterface)
    advisor.initAdvisorInterface(reader,writer)

    print('Waiting msg from {0}...'.format(advisorclient))
    # await asyncio.gather(vhl.processVhlMsg(),vhl.txMsg2Vhl(),vhl.processAdvisorMsg(),vhl.txMsg2Advisor())
    await asyncio.gather(advisor.processAdvisorMsg(),advisor.txMsg2Advisor())

    print('Client destroied') 

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

      
    print('Waiting msg from {0}...'.format(vhlclient))
    # await asyncio.gather(vhl.processVhlMsg(),vhl.txMsg2Vhl(),vhl.processAdvisorMsg(),vhl.txMsg2Advisor())
    await asyncio.gather(vhl.processVhlMsg(),vhl.txMsg2Vhl())

    print('Client destroied')  # <17>
    # writer.close()  # <18>
# END xTSPSimulator_TOP


#### BEGIN xTSPSimulator_MAIN
def main(address2vhl='127.0.0.1', port2vhl=ota.LISTENING_VHL_PORT, address2advisor='127.0.0.1', port2advisor=ota.LISTENING_CC_PORT):  # <1>
    # global gDBhdl
    # gDBhdl = connectdb(DBNAME,DBUSERNAME,DBPASSWORD,DBHOST,DBPORT)

    loop = asyncio.get_event_loop()

    server2vhl_coro = asyncio.start_server(handle_vehicle_connection, address2vhl, port2vhl, loop=loop) # <2>
    server2cc_coro = asyncio.start_server(handle_advisor_connection, address2advisor, port2advisor, loop=loop)
    print('Vehicle interface serving on {0} : {1}'.format(address2vhl,port2vhl))
    print('Call Center interface serving on {0} : {1}'.format(address2advisor,port2advisor))
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
