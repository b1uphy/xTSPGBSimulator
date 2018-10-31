#!/usr/bin/env python3
# -*- coding: utf8 -*-
# bluphy@163.com

# 2018-10-26 17:08:06 by xw: v0.3 更新Vehicle类，简化server架构，使vehicle interface和advisor interface结构统一
# 2018-10-17 11:32:06 by xw: v0.2 拆分应用层部分到单独文件，增加应用层日志功能
# 2018-05-24 16:52 by xw: new created.

# TODO: 
# 

str_version = 'v0.4'

# BEGIN Calibration
DBHOST = '127.0.0.1'
DBPORT = 5432
DBNAME = 'bw_GBDirect_db'
DBUSERNAME = 'bw_tester_admin'
DBPASSWORD = '123456'

TIMER_OTA_MSG_TIMEOUT = 30
LISTENING_VHL_PORT = 9201
LISTENING_ADVISOR_PORT = 31029
# END Calibration

# BEGIN debug
xDEBUG = True

# END debug 

# BEGIN xTSPSimulator_TOP
import sys
sys.path.append(sys.path[0].rsplit('\\',1)[0])

import asyncio
# import functools
import time
import json
from async_timeout import timeout

from xDBService.xDBService import connectdb
from xGBT32960ServerCore.xGBT32960ServerCore import Vehicle,Advisor

gDBhdl = None

async def handle_vehicle_connection(reader, writer):
    global gDBhdl
    vhl = Vehicle(reader,writer,gDBhdl)
    await vhl.startloop()
    print('Close the connection with vehicle VIN={0}'.format(vhl.VIN))
    vhl.destroy()
    vhl = None


async def handle_advisor_connection(reader:asyncio.StreamReader, writer:asyncio.StreamWriter):
    advisor = Advisor(reader,writer)
    await advisor.startloop()
    print('Close the connection with advisor:{0}'.format(advisor.username))
    advisor.destroy()
    advisor = None
    
# END xTSPSimulator_TOP

# BEGIN xTSPSimulator_MAIN
def main(address2vhl='127.0.0.1', port2vhl=LISTENING_VHL_PORT, address2advisor='127.0.0.1', port2advisor=LISTENING_ADVISOR_PORT):
    global gDBhdl
    gDBhdl = connectdb(DBNAME,DBUSERNAME,DBPASSWORD,DBHOST,DBPORT)

    loop = asyncio.get_event_loop()

    server2vhl_coro = asyncio.start_server(handle_vehicle_connection, address2vhl, port2vhl, loop=loop)
    server2advisor_coro = asyncio.start_server(handle_advisor_connection, address2advisor, port2advisor, loop=loop)

    task = asyncio.gather(server2vhl_coro,server2advisor_coro)
    servers = loop.run_until_complete(task)
    print('Vehicle interface serving on {0}'.format(servers[0].sockets[0].getsockname()))
    print('Advisor interface serving on {0}'.format(servers[1].sockets[0].getsockname()))
    try:
        print('run loop')
        loop.run_forever()
    finally:
        
        loop.close()
    for server in servers:
        server.close()
    gDBhdl['cursor'].close()
    gDBhdl['connection'].close()
    print('Server shut down.')

if __name__ == '__main__':
    main(*sys.argv[1:])  # <10>
    
# END xTSPSimulator_MAIN
