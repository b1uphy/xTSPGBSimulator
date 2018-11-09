#Echo client program
#made by bluphy
#contact @163.com
# 2018-10-31 18:24:07 by xw: v0.4 Fix bug txloop does not stopped when model destroied
# 2018-10-31 15:07:15 by xw: v0.3 supply to get reply msg from server
# 2018-09-25 16:34:13 by xw: 

str_version = 'v0.4'
import logging
import socket,time,sys,json
from threading import Thread
from queue import Queue

import base64

# SERVER_IP = '127.0.0.1'
SERVER_IP = '218.1.38.234'
# SERVER_IP = '10.40.166.7'
SERVER_PORT = 1002             # The same port as used by the server

# SERVER_IP = '10.40.166.8'
# SERVER_PORT = 9201

# SERVER_IP = '218.1.38.234'
# SERVER_PORT = 1002


#### BEGIN message template
msg_login = "{'name': 'login', 'data': {'username': ''} }"
msg_select_vehicle = "{'name': 'select_vehicle', 'data': {'VIN': ''} }"
msg_logout = "{'name': 'logout', 'data': '' }"
msg_disconnect_vehicle = "{'name': 'disconnect_vehicle', 'data': '' }"
msg_echo  = "{'name': 'echo', 'data': '' }"
msg_ack = "{'name':'ack','data':{'name':'','reply':{'result':'','data':''}}}"
#### END## message template

msg_select_vehicle1 = "{'name': 'select_vehicle', 'data': {'VIN': 'LMGFE1G0000000SY1'} }"
msg_select_vehicle2 = "{'name': 'select_vehicle', 'data': {'VIN': 'LXVJ2GFC2GA030003'} }"
msg_select_vehicle3 = "{'name': 'select_vehicle', 'data': {'VIN': 'LMGFE1G88D1022SY5'} }"


def help(cmd=None):
    print('Hello!!')

class xGBT32960MonitorModel:
    def __init__(self):
        self.txq = Queue()
        self.rxq = Queue()
        self.configs = {}
        self.username = ''
        self.VIN = ''
        self.binded = False
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
        while not self.terminateFlag:
            # txflag = True
            msg = self.txq.get()
            # while txflag:
            try:
                self.s.sendall(msg)
            except OSError:
                break
            # else:
                    # txflag = False
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
                    # self.rxq.put(body_tail[:-1])
                    print('')
                    msg = json.loads(body_tail[:-1].decode('utf8'))
                    self.rxq.put(msg)
                    name = msg['name']
                    data = msg['data']
                    
                    print(msg,'\n?>',end='')
                    # print(gbdata_hndl(data),'\n?>',end='')
        
        print('rx stopped','\n?>',end='')
        
    def closeSocket(self):
        self.s.close()
        
    def destroy(self):
        self.sendMsg(eval(msg_disconnect_vehicle))
        self.sendMsg(eval(msg_logout))
        self.terminateFlag =True
        time.sleep(3)
        self.closeSocket()

    def create_msg_select_vehicle(self,VIN:str = None):
        msg = eval(msg_select_vehicle)
        if VIN:
            msg['data']['VIN']=VIN
        else:
            msg['data']['VIN']=self.VIN

        return msg
    
    def create_msg_login(self):
        msg = eval(msg_login)
        msg['data']['username']=self.username
        return msg


def main(serverip=SERVER_IP,serverport=SERVER_PORT):
    gbm =xGBT32960MonitorModel()

    while True:
        cmd = input('\n?>')
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
        elif cmd=='i':
            gbm.username = input('username:')
            gbm.sendMsg(gbm.create_msg_login())
        elif cmd=='i1':
            gbm.username = 'bwtester1'
            gbm.sendMsg(gbm.create_msg_login())            
        elif cmd=='v':
            gbm.sendMsg(gbm.create_msg_select_vehicle(input('VIN:').upper()))
        elif cmd=='v1':
            gbm.sendMsg(eval(msg_select_vehicle1))
        elif cmd=='v2':
            gbm.sendMsg(eval(msg_select_vehicle2))
        elif cmd=='v3':
            gbm.sendMsg(eval(msg_select_vehicle3))
        elif cmd=='u':
            gbm.sendMsg(eval(msg_disconnect_vehicle))
        elif cmd=='e':
            gbm.sendMsg(eval(msg_echo))
        elif cmd=='n':
            gbm =xGBT32960MonitorModel()            
        else:
            help()

if __name__ == '__main__':
    main(*sys.argv[1:])
