#Echo client program
#made by bluphy
#contact @163.com
# 2018-11-14 16:38:25 by xw: v0.5.1 fix a bug when change the network, the login username is not changed to the new socket
# 2018-11-12 14:35:43 by xw: v0.5 Support config file and vehicle history record
# 2018-10-31 18:24:07 by xw: v0.4 Fix bug txloop does not stopped when model destroied
# 2018-10-31 15:07:15 by xw: v0.3 supply to get reply msg from server
# 2018-09-25 16:34:13 by xw: 

str_version = 'v0.5.1'
import logging
import socket,time,sys,json
from threading import Thread
from queue import Queue

import base64

# SERVER_IP = '127.0.0.1'

SERVER_IP = '10.40.166.7'
SERVER_PORT = 31029             # The same port as used by the server
CFGFILE = 'xmonitor.cfg'
# SERVER_IP = '10.40.166.8'
# SERVER_PORT = 9201

# SERVER_IP = '218.1.38.234'
# SERVER_PORT = 1002

TIMER_CLOSESOCKET_DELAY = 0.1
#### BEGIN message template
msg_login = "{'name': 'login', 'data': {'username': ''} }"
msg_select_vehicle = "{'name': 'select_vehicle', 'data': {'VIN': ''} }"
msg_logout = "{'name': 'logout', 'data': '' }"
msg_disconnect_vehicle = "{'name': 'disconnect_vehicle', 'data': '' }"
msg_echo  = "{'name': 'echo', 'data': '' }"
msg_ack = "{'name':'ack','data':{'name':'','reply':{'result':'','data':''}}}"
#### END## message template



xDEBUG = False

def help(cmd=None):
    print('Hello!!')

class xGBT32960MonitorModel:
    def __init__(self):
        self.txq = Queue()
        self.rxq = Queue()
        self.configs = {'username':None,'VIN':None,'host':None}
        self.binded = False
        self.connected = False
        self.configsHistory = {'userHistory':[],'vhlHistory':[],'hostHistory':[]}
        # self.createSocket()
        self.loadCfg()

    def loadCfg(self,path=None):
        if not path: path = ''
        try:
            with open(path+CFGFILE,'r') as f:
                context = None
                for line in f:
                    if '[' in line:
                        context = line.split('[')[1].split(']')[0]
                        if xDEBUG: print('set config:',context)
                        continue
                    else:
                        pass # context not change
                    if 'History' in context:
                        self.configsHistory[context].append(line.strip())
                    elif 'Last' in context:
                        name,value = line.strip().split('=')
                        if name in {'username','VIN','host'}:                        
                            self.configs[name]=value                        
                            if xDEBUG: print('configs:',name,value)
                        else:
                            print('配置文件信息无效，将使用默认配置')
                            print('无效配置行:',line)
            
        except IOError:
            print('读取配置文件失败,使用默认值')
            self.configs['username'] = 'bwtester'
            self.configs['VIN'] = ''
            self.configs['host'] = '10.40.166.7:31029'
        
        #用户登录机制尚未实现，使用client IP代替username
        # self.configs['username'] = self.configs['username'] = xGBT32960MonitorModel.getClientSocketAsStr()

    def addToHistory(self,name,value):
        if not value in self.configsHistory[name]:
            self.configsHistory[name].append(value)
    def rmFromHistory(self,name,value):
        try:
            self.configsHistory[name].remove(value)
        except KeyError:
            print('WARNING class',type(self))
            print('function rmFromHistory:','Not found the specified history item')

    def clearHistory(self,name):
        try:
            self.configsHistory[name].clear()
        except KeyError:
            print('WARNING class',type(self))
            print('function clearHistory:','Not found the specified history list')

    def saveCfg(self,path=None):
        if not path: path = ''
        try:
            with open(path+CFGFILE,'w') as f:
                f.write('[configLast]\n')
                for name,value in self.configs.items():
                    f.write('{0}={1}\n'.format(name,value))
                for name,values in self.configsHistory.items():
                    f.write('[{}]\n'.format(name))
                    for e in values:
                        f.write('{}\n'.format(e))
        except IOError:
            print('Save configs fail')
        
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
        
        # if self.configs['host']: #如果模型的host值已经有了，覆盖掉默认值或传入值
        try:
            serverip,serverport = self.configs['host'].split(':')
            serverport = int(serverport,10)
        except ValueError:
            pass #use default
        finally:
            print('Connecting to {0}:{1}'.format(serverip,serverport))

        self.terminateFlag = False

        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.conn = self.s.connect((serverip, serverport))
        except OSError:
            print('ERROR: Create socket fails')
            result = -1
        else:
            self.connected = True
            self.clientinfo = self.s.getsockname()
            
            self.txthd = Thread(target=self.txMsg)
            self.txthd.start()
            # self.rxthd = Thread(target=self.rxMsg)
            # self.rxthd.start()
            result = 0
        finally:
            #用户登录机制尚未实现，使用client IP代替username
            self.configs['username'] = self.getClientSocketName()

        return result 
        
    def txMsg(self):
        while not self.terminateFlag:
            # txflag = True
            msg = self.txq.get()
            # while txflag:
            try:
                self.s.sendall(msg)
            except OSError:
                self.connected = False
                break
            # else:
                    # txflag = False
        print('tx stopped')    

    def getClientSocketName(self):
        return self.s.getsockname() 


    def rxMsg(self):
        # while True:
        try:
            header = self.s.recv(3)
        except OSError:
            self.connected = False
            # break
        else:
            length = int.from_bytes(header, byteorder='big')+1
            try:
                body_tail = self.s.recv(length)
            except OSError:
                self.connected = False
                print('connection error when rx')
                # break
            else:
                # self.rxq.put(body_tail[:-1])
                print('')
                msg = json.loads(body_tail[:-1].decode('utf8'))
                self.rxq.put(msg)
                name = msg['name']
                data = msg['data']
                if name != 'gbdata':
                    print(msg,'\n?>',end='')
                else:
                    print('Received a GB/T32960 msg','\n?>',end='')
                # print(gbdata_hndl(data),'\n?>',end='')
        
        # print('rx stopped','\n?>',end='')
        
    def closeSocket(self):
        try:
            self.s.close()
        except AttributeError:
            pass
        finally:
            self.connected = False
            return 0

    # def advisorLogout(self):
    #     self.sendMsg(eval(msg_disconnect_vehicle))
    #     self.sendMsg(eval(msg_logout))

    def destroy(self):
        
        self.sendMsg(eval(msg_disconnect_vehicle))
        self.sendMsg(eval(msg_logout))
        self.terminateFlag =True
        self.saveCfg()
        time.sleep(TIMER_CLOSESOCKET_DELAY)
        self.closeSocket()

    def create_msg_select_vehicle(self,VIN:str = None):
        msg = eval(msg_select_vehicle)
        if VIN:
            msg['data']['VIN']=VIN
        else:
            msg['data']['VIN']=self.configs['VIN']

        return msg
    
    def create_msg_login(self):
        msg = eval(msg_login)
        msg['data']['username']=self.configs['username']
        return msg


def main(serverip=SERVER_IP,serverport=SERVER_PORT):

    msg_select_vehicle1 = "{'name': 'select_vehicle', 'data': {'VIN': 'LMGFE1G0000000SY1'} }"
    msg_select_vehicle2 = "{'name': 'select_vehicle', 'data': {'VIN': 'LXVJ2GFC2GA030003'} }"
    msg_select_vehicle3 = "{'name': 'select_vehicle', 'data': {'VIN': 'LMGFE1G88D1022SY5'} }"

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
