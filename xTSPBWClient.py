#Echo client program
import socket,time,sys

SERVER = '127.0.0.1'
# SERVER = '192.168.1.3'
SERVER_PORT = 31029             # The same port as used by the server

def main(cmd):
    print(cmd)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        conn = s.connect((SERVER, SERVER_PORT))
        clientinfo = s.getsockname()
        
        s.sendall(cmd.encode('ascii'))
        result = s.recv(1024)
        print(result.decode('ascii'))



if __name__ == '__main__':
    try:
        cmds = sys.argv[1:]
    except IndexError:
        cmdline = b'help'
        print('Index Error')
    else:
        if len(cmds)==0:
            while True:
                cmdline = input('COMMAND:\n>')
                main(cmdline)
        else:
            cmdline = ''
            for i in cmds:
                cmdline = cmdline + i +' '
            cmdline = cmdline.strip()
            main(cmdline)
