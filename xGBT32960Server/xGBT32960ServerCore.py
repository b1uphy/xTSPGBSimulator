#!/usr/bin/env python3
# -*- coding: utf8 -*-
# bluphy@163.com
# 2018-10-16 14:11:02 by xw: new created.

# BEGIN Calibration
TIMER_OTA_MSG_TIMEOUT = 30
LISTEMING_PORT = 9201
# END Calibration

gInterrupt_flagstr = ''
gDBhdl = None
import time
from xOTAGBT32960.xOTAGB import OTAGBData,createOTAGBMsg,CMD,genGBTime
from GB_PARSER_HANDLER import parseGBPkgs
# BEGIN APP Layer/
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
            self.logname = '{0}_{1}.csv'.format(self.data.head.VIN.phy,time.strftime('%Y%m%d%H%M%S'))
        if self.data.head.cmd.phy == '车辆登入':
            self.state = 'Login'
            print('Vehicle login: VIN = ',self.VIN.decode('ascii'))
            result = self.responseLogin()

        elif self.data.head.cmd.phy == '实时数据' or self.data.head.cmd.phy == '补发数据':

            #BDDemo
            '''
            chargingState_raw = self.data.payload[8]
            if chargingState_raw==1:
                chargingState = 1
            else:
                chargingState = 0
            SOC =self.data.payload[5]
            print('SOC=',SOC)
            print('Vehicle {0} chargingState={1}'.format(self.VIN,chargingState))
            with open('C:\\BDdemo\\demo.json','w') as fout:
                fout.write(json.dumps({'chargingState':chargingState,'SOC':SOC}))
            '''
            pass

        elif self.data.head.cmd.phy == '车辆登出':
            print('Vehicle logout: VIN = ',self.VIN.decode('ascii'))
            result = self.responseLogout()

        elif self.data.head.cmd.phy == '心跳':
            result = self.responseHeartbeat()
        else:
            print('Error CMD')
            result['responsecode'] = 'Error CMD'
        self.writeLog()

        return result

    def responseLogin(self):
        result = {'msg':None, 'responsecode':0}
        result['msg'] = createOTAGBMsg(CMD.inv['车辆登入'], b'\x01', self.VIN, 1, 30, genGBTime()+self.data.payload[6:])
        print("response result['msg']",result['msg'])
        return result

    def responseLogout(self):
        result = {'msg':None, 'responsecode':'Close'}
        result['msg'] = createOTAGBMsg(CMD.inv['车辆登出'], b'\x01', self.VIN, 1, 8, genGBTime()+self.data.payload[6:])        
        return result

    def responseHeartbeat(self):
        result = {'msg':None, 'responsecode':0}
        result['msg'] = createOTAGBMsg(CMD.inv['心跳'], b'\x01', self.VIN, 1, 0, b'')
        return result

    def destroy(self):
        self.VIN = None
        # self.log.close()

    def writeLog(self):
        ##采集数据写入日志
        rxtime = time.strftime('%Y%m%d %H:%M:%S,')
        gbdatas = ','.join(parseGBPkgs(self.data.raw.hex()))

        try:
            with open(self.logname,'a') as log:
                log.write(rxtime+gbdatas+'\n')
        except IOError:
            print('[Warning] : write log fail {0} -> {1}'.format(rxtime,gbdatas))
# END APP layer