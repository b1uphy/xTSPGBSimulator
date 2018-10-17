#!/usr/bin/env python3
# -*- coding: utf8 -*-
# bluphy@163.com
# 2018-09-07 19:42:24 by xw: fix bug when vin contains null character
# 2018-7-20 11:50:55 by xw: new created.

str_Version = 'v0.1'
str_Title = 'GB大数据监视器'

import xDBService.xDBService as xdbs
import time
from tkinter import *
from tkinter.ttk import *
import socket

def parseGBTime (raw:str):
    print('gbtime raw=',raw)
    if not len(raw)==12:         
        return ['error:GBTime length']
    else:
        x=int(raw,16)   
        maskYear = 0xFF0000000000
        maskMonth = 0x00FF00000000
        maskDate = 0x0000FF000000
        maskHour = 0x000000FF0000
        maskMin = 0x00000000FF00
        maskSec = 0x0000000000FF
        year = str(((x & maskYear) >>40 )+ 2000)
        month = str((x & maskMonth) >>32)
        date = str((x & maskDate) >>24)
        hour = str((x & maskHour) >>16)
        minute = str((x & maskMin) >>8)
        sec = str(x & maskSec)
        return [year+'-'+month+'-'+date+' '+(len(hour)%2)*'0'+hour+':'+(len(minute)%2)*'0'+minute+':'+(len(sec)%2)*'0'+sec]


class xGBT32960Monitor(Frame):
    def __init__(self,master=None):
        super(xGBT32960Monitor,self).__init__(master)
        self.grid(sticky='nesw')
        self.rowconfigure(10,weight=1)
        self.columnconfigure(10,weight=1)

        self.vhlLbl = Label(self,text='Vehicle')
        self.vhlLbl.grid(row=10,rowspan=1,column=10,columnspan=1,sticky=N+S+E+W)
        self.vhl = StringVar()
        self.vhlEntry = Entry(self,textvariable=self.vhl)
        self.vhlEntry.grid(row=10,rowspan=1,column=20,columnspan=1,sticky=N+S+E+W)

        self.connectingStatus = StringVar()
        self.connectingStatus.set('Not Connect')
        
        self.connectBtn = Button(master,textvariable=self.connectingStatus,command=self.toggleConnection)
        self.connectBtn.grid(row=10,rowspan=1,column=10,columnspan=10,sticky=N+S+E+W)

    def toggleConnection(self,event):
        pass

    def connectTSP(self,host,port):       
        print('Creating socket...')
        result = -1
        try:
            self.skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            #gSocket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,)
            self.skt.connect((host,port))
            self.socketName = self.skt.getsockname()
            print('Client info: ',self.socketName)
            
        except:
            print('Connecting failed, retry after 10 seconds')
            time.sleep(10)
        else:
            result = 0
        return result

    def getVhlConnectingStatus(self):
        return 'Not Connect'


def testDB():
    loginmsg = bytes.fromhex('232301FE4C58564433473242364A4130303032303501001E12041B09281F000438393836303631373031303030313335313335370100E7')
    logoutmsg = b'##\x01\xFELXVJ2GFC2GA030003\x04\x00\x08\x11\x11\x11\x11\x11\x11\x33\x33\x33'

    dbhdl = xdbs.connectdb('borgward_db','borgward', '123456','10.40.166.7',5432)
    conn = dbhdl['connection']
    cur = dbhdl['cursor']
    # xdbs.writedb(logoutmsg,time.time(),0,dbhdl)

    cur.execute("SELECT * FROM gbt32960 WHERE vin='LMGFE1G0000000SY1' LIMIT 10;")
    count = 0
    for record in cur:
        vin = record[0]
        msgtime = '采集时间: '+parseGBTime(record[1].tobytes().hex())[0]
        systime = '\t系统时间：{0}\traw sec:{1}'.format(time.strftime('%Y-%m-%d %H:%M:%S',time.gmtime(record[2])) ,record[2])
        print(vin,msgtime,systime)
        count+=1
        
    cur.close()
    conn.close()
    if count>5:
        print('DBtest OK')
    return 0

if __name__ == '__main__':


    root=Tk()
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    root.grid()
    # root.resizable(False,False)
    # goemtrystr = '+{0}+{1}'.format((screensize[0]-xWIDTH)//2,(screensize[1]-xHEIGHT)//2)
    # root.geometry(goemtrystr)
    # root.minsize(xWIDTH, 240)
    app=xGBT32960Monitor(master=root)
    app.master.title(str_Title +' '+ str_Version)
    app.mainloop()
    
        