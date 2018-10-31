#Echo client program
#made by bluphy
#contact @163.com
# 2018-10-31 15:07:15 by xw: v0.3 supply to get reply msg from server
# 2018-09-25 16:34:13 by xw: 

str_version = 'v0.3'

import socket,time,sys,json
from threading import Thread
from queue import Queue

import base64

SERVER_IP = '127.0.0.1'
# SERVER_IP = '10.40.166.7'
SERVER_PORT = 31029             # The same port as used by the server

#### BEGIN message template
msg_login = "{'name': 'login', 'data': {'username': ''} }"
msg_select_vehicle = "{'name': 'select_vehicle', 'data': {'VIN': ''} }"
msg_logout = "{'name': 'logout', 'data': '' }"
msg_disconnect_vehicle = "{'name': 'disconnect_vehicle', 'data': '' }"
msg_echo  = "{'name': 'echo', 'data': '' }"
msg_ack = "{'name':'ack','data':{'name':'','reply':{'result':'','data':''}}"
#### END## message template

msg_select_vehicle1 = "{'name': 'select_vehicle', 'data': {'VIN': 'LMGFE1G0000000SY1'} }"
msg_select_vehicle2 = "{'name': 'select_vehicle', 'data': {'VIN': 'LXVJ2GFC2GA030003'} }"
msg_select_vehicle3 = "{'name': 'select_vehicle', 'data': {'VIN': 'LMGFE1G88D1022SY5'} }"

def gbdata_hndl(data):
    gbmsg = base64.standard_b64decode(data.encode('utf8'))
    return gbmsg
    
def create_msg_select_vehicle(VIN:str):
    msg = eval(msg_select_vehicle)
    msg['data']['VIN']=VIN
    return msg
    
def create_msg_login(username:str):
    msg = eval(msg_login)
    msg['data']['username']=username
    return msg

def help(cmd=None):
    print('Hello!!')

class xGBMonitor:
    def __init__(self):
        self.txq = Queue()
        self.rxq = Queue()
        # self.createSocket()
        
    def sendMsg(self,msg:dict):
        '''
        发送消息为自定义格式 header[3 bytes] + body[]
        '''
        jsonstr = json.dumps(msg)
        tail = b'\n'
        body = jsonstr.encode('utf8')
        length = len(body)
        header = length.to_bytes(3,'big')
        self.txq.put(header+body+tail)
        self.socketStatus = None

    def createSocket(self,serverip=SERVER_IP,serverport=SERVER_PORT):
        print('Connecting to {0}:{1}'.format(serverip,serverport))
        self.terminateFlag = False
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn = self.s.connect((serverip, serverport))
        self.clientinfo = self.s.getsockname()
        
        self.txthd = Thread(target=self.txMsg)
        self.txthd.start()
        self.rxthd = Thread(target=self.rxMsg)
        self.rxthd.start()
        
    def txMsg(self):
        while True:
            txflag = True
            msg = self.txq.get()
            while txflag:
                try:
                    self.s.sendall(msg)
                except OSError:
                    break
                else:
                    txflag = False
        print('tx stopped')    

        
    def rxMsg(self):
        while True:
            try:
                header = self.s.recv(3)
            except OSError:
                break
            else:
                length = int.from_bytes(header, byteorder='big')+1
                try:
                    body_tail = self.s.recv(length)
                except OSError:
                    print('connection error when rx')
                    break
                else:
                    self.rxq.put(body_tail[:-1])
                    print('')
                    msg = json.loads(body_tail[:-1].decode('utf8'))
                    name = msg['name']
                    data = msg['data']
                    
                    print(msg,'\n?>',end='')
                    # print(gbdata_hndl(data),'\n?>',end='')
        print('rx stopped','\n',end='')
        
    def closeSocket(self):
        self.s.close()
        
    def destroy(self):
        self.sendMsg(eval(msg_disconnect_vehicle))
        self.sendMsg(eval(msg_logout))
        self.terminateFlag =True
        time.sleep(3)
        self.closeSocket()

        
def main(serverip=SERVER_IP,serverport=SERVER_PORT):
    gbm =xGBMonitor()

    while True:
        cmd = input('?>')
        if   cmd == 'q':
            gbm.destroy()
            gbm=None
        elif cmd=='exit':
            if gbm:
                gbm.destroy()
                gbm=None
            break
        elif cmd=='s':
            gbm.createSocket(serverip,serverport)
        elif cmd=='v':
            gbm.sendMsg(create_msg_select_vehicle(input('VIN:').upper()))
        elif cmd=='v1':
            gbm.sendMsg(eval(msg_select_vehicle1))
        elif cmd=='v2':
            gbm.sendMsg(eval(msg_select_vehicle2))
        elif cmd=='v3':
            gbm.sendMsg(eval(msg_select_vehicle3))
        elif cmd=='n':
            gbm =xGBMonitor()
        elif cmd=='u':
            gbm.sendMsg(eval(msg_disconnect_vehicle))
        elif cmd=='i':
            gbm.sendMsg(create_msg_login(input('username:')))
        elif cmd=='i1':
            gbm.sendMsg(create_msg_login('bwtester1'))
        elif cmd=='e':
            gbm.sendMsg(eval(msg_echo))
        else:
            help()

if __name__ == '__main__':
    main(*sys.argv[1:])
