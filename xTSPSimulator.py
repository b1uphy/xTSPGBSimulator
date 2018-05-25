#!/usr/bin/env python3
# bluphy@163.com
# 2018-05-24 16:52 by xw: new created.

# BEGIN xTSPSimulator_TOP
import sys
import asyncio

CRLF = b'\r\n'
PROMPT = b'?> '

async def handle_queries(reader, writer):  # <3>
    client = writer.get_extra_info('peername')
    print('Client {} connected.'.format(client))
    while True:  # <4>
        try:
            header = await reader.readexactly(24)  # <7>
        except :
            break

        if header:
            print('Received header {0}:\t{1}'.format(client,header))
            lengthraw = header[-2:]
            print('lengthraw:{}'.format(lengthraw))
            length = int.from_bytes(lengthraw, byteorder='big')+1
            print('length:{}'.format(length))
            data = await reader.readexactly(length)
            if data:
                print('Received from {0}:\t{1}'.format(client,data))  # <10>
        else:
            break
    print('Close the client socket')  # <17>
    writer.close()  # <18>
# END xTSPSimulator_TOP

# BEGIN xTSPSimulator_MAIN
def main(address='127.0.0.1', port=9201):  # <1>
    port = int(port)
    loop = asyncio.get_event_loop()
    server_coro = asyncio.start_server(handle_queries, address, port, loop=loop) # <2>
    server = loop.run_until_complete(server_coro) # <3>

    host = server.sockets[0].getsockname()  # <4>
    print('Serving on {}. Hit CTRL-C to stop.'.format(host))  # <5>
    try:
        loop.run_forever()  # <6>
        print('here')
    except KeyboardInterrupt:  # CTRL+C pressed
        pass

    print('Server shutting down.')
    server.close()  # <7>
    loop.run_until_complete(server.wait_closed())  # <8>
    loop.close()  # <9>


if __name__ == '__main__':
    main(*sys.argv[1:])  # <10>
# END xTSPSimulator_MAIN
