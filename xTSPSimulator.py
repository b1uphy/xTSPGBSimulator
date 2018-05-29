#!/usr/bin/env python3
# bluphy@163.com
# 2018-05-24 16:52 by xw: new created.

# BEGIN xTSPSimulator_TOP
import sys
import asyncio
import functools
from  async_timeout import timeout

TIMER_OTA_MSG_TIMEOUT = 30

# BEGIN APP Layer
def writedb(VIN:str,systime,msgtime,msg:bytes,db):
    pass

def 

# END APP layer

# BEGIN OTA Layer
def dispatch(msg:bytes)->int:
    return 0


# END OTA layer


async def handle_vehicle_connection(reader, writer):  # <3>
    client = writer.get_extra_info('peername')
    print('Client {} connected.'.format(client))
    counter = 0
    while True:  # <4>
        counter += 1
        print('counter=',counter)
        print(client,' Waiting msg...')
        try:
            async with timeout(TIMER_OTA_MSG_TIMEOUT):
                header = await reader.readexactly(24)  # <7>
        except asyncio.TimeoutError:
            print('Rx timeout')
            print('Close connection because of timeout')
            break
        except:
            print('Connection broken!')
            break

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
                break
            

            
            
            if data:
                msg = header+data
                print('Received from {0}:\t{1}'.format(client,msg.hex()))  # <10>
                
            
        else:
            print('Nothing received')
            break
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
