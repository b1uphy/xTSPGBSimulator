#!/usr/bin/env python3
# bluphy@163.com
# 2018-05-24 16:52 by xw: new created.

# BEGIN xTSPSimulator_TOP
import sys
import asyncio
import functools
from  async_timeout import timeout
from xOTAGB import OTAGBData,createOTAGBMsg,CMD,genGBTime
TIMER_OTA_MSG_TIMEOUT = 30

gInterrupt_flagstr = ''
# BEGIN APP Layer
class Vehicle:
    def __init__(self,client):
        self.client = client
        self.VIN = None
        self.state = 'connected'
        self.data = None
        self.msg = None

    def processMsg(self,msg)->bytes:
        result = {'msg':None, 'responsecode':0}
        self.data = OTAGBData(msg)
        if self.VIN:
            if self.VIN != self.data.head.VIN.raw:
                self.VIN = self.data.head.VIN.raw
                print('VIN is not match')
        else:
            self.VIN = self.data.head.VIN.raw

        if self.data.head.cmd.phy == '车辆登入':
            self.state = 'Login'
            print('Vehicle login: VIN = ',self.VIN.decode('ascii'))
            result = self.responseLogin()

        elif self.data.head.cmd.phy == '实时数据' or self.data.head.cmd.phy == '补发数据':
            pass

        elif self.data.head.cmd.phy == '车辆登出':
            print('Vehicle logout: VIN = ',self.VIN.decode('ascii'))
            result = self.responseLogout()

        elif self.data.head.cmd.phy == '心跳':
            result = self.responseHeartbeat()
        else:
            print('Error CMD')
            result['responsecode'] = 'Error CMD'
        
        return result

    def responseLogin(self):
        result = {'msg':None, 'responsecode':0}
        result['msg'] = createOTAGBMsg(CMD.inv['车辆登入'], b'\xFE', self.VIN, 1, 7, genGBTime())
        print("response result['msg']",result['msg'])
        return result

    def responseLogout(self):
        result = {'msg':None, 'responsecode':'Close Connection'}
        return result

    def writedb(self, VIN:str, systime, msgtime, direction,msg:bytes, db):
        pass


# END APP layer

# BEGIN OTA Layer
async def receiveMsg(client,reader)->bytes:
    result = {'msg':None, 'responsecode':0}
    header = None
    try:
        async with timeout(TIMER_OTA_MSG_TIMEOUT):
            header = await reader.readexactly(24) 
    except asyncio.TimeoutError:
        print('Rx timeout')
        print('Close connection because of timeout')
        result['responsecode'] = 'Timeout!'
    except:
        print('Connection broken!')
        result['responsecode'] = 'Connection broken'

    if header:
        print('Received header {0}:\t{1}'.format(client,header.hex()))
        lengthraw = header[-2:]
        print('lengthraw:{}'.format(lengthraw))
        length = int.from_bytes(lengthraw, byteorder='big')+1 # the length including the sum byte
        print('length:{}'.format(length))

        data = None
        try:
            async with timeout(TIMER_OTA_MSG_TIMEOUT):
                data = await reader.readexactly(length)
        except asyncio.TimeoutError:
            print('Rx timeout')
            print('Close connection because of timeout')
            result['responsecode'] = 'Timeout!'
        
        if data:
            result['msg'] = header+data
            print('Received from {0}:\t{1}'.format(client,result['msg'].hex()))  # <10>

    return result

async def sendMsg(writer,msg:bytes):
    try:
        writer.write(msg)
    except:
        print('Send Msg fail. Msg:',msg.hex())
    else:
        print('Send Msg:',msg.hex())
# END OTA layer


async def handle_vehicle_connection(reader, writer):  # <3>
    client = writer.get_extra_info('peername')
    print('Client {} connected.'.format(client))
    counter = 0
    vhl = Vehicle(client)
    while True:  # <4>
        counter += 1
        print('counter=',counter)
        print(client,' Waiting msg...')
        result = await receiveMsg(client,reader)
        if result['responsecode'] == 0:
            msg = result['msg']
        else:
            break
        
        result = vhl.processMsg(msg)
        if result['responsecode'] == 'Close Connection':
            break
        responseMsg =result['msg']
        if responseMsg:
            await sendMsg(writer,responseMsg)

    print('Close the client socket')  # <17>
    writer.close()  # <18>
# END xTSPSimulator_TOP

# BEGIN xTSPSimulator_MAIN
def main(address='127.0.0.1', port=9201):  # <1>
    port = int(port)
    loop = asyncio.get_event_loop()
    server_coro = asyncio.start_server(handle_vehicle_connection, address, port, loop=loop) # <2>
    server = loop.run_until_complete(server_coro) # <3>

    host = server.sockets[0].getsockname()  # <4>
    print('Serving on {}. Hit CTRL-C to stop.'.format(host))  # <5>

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
    main(*sys.argv[1:])  # <10>
# END xTSPSimulator_MAIN
