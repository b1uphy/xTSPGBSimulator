#!/usr/bin/env python3
# -*- coding: utf8 -*-
# bluphy@163.com
# 2018-11-26 16:21:12 by xw: v0.5.5 fix bug for pyinstaller distributed exe file when loading icon 
# 2018-11-26 14:56:00 by xw: v0.5.4 change the default app icon to eks
# 2018-11-26 13:11:20 by xw: v0.5.3 support to show the rx time of heartbeat msg
# 2018-11-22 18:17:36 by xw: v0.5.2 support log view to show raw data
# 2018-11-12 16:30:00 by xw: v0.5.1 add selecting server ui
# 2018-11-12 14:36:41 by xw: v0.5 support config file and vehicle history record
# 2018-11-11 15:41:19 by xw: v0.4 support GB data 05,06,07,08,09;08,09 use predefined length
# 2018-11-10 00:55:17 by xw: v0.3 support GB data 02
# 2018-11-07 19:20:35 by xw: v0.2 support to monitor GB data 01
# 2018-09-07 19:42:24 by xw: fix bug when vin contains null character
# 2018-7-20 11:50:55 by xw: new created.
#### TODO:
# done 1.实时数据显示部分增加滚动条
# 2.数据校验助手，提示数据逻辑问题
# 3.优化初始窗口大小
# 4.增加服务器选择界面及服务器历史记录
# 5.增加用户登入界面
# 6.分割应用层与TCP层
# 7.增加支持 TLS1.2协议与服务器通讯
# 8.增加log记录功能
# 9.增加本地数据库，支持数据库检索功能
# 10.支持远程数据库检索功能

xDEBUG = False

str_Version = 'v0.5.5'
str_Title = 'GB大数据监视器'

import sys,os,ctypes,socket,time
sys.path.append(sys.path[0].rsplit('\\',1)[0])
print(sys.path)
# import xDBService.xDBService as xdbs
from tkinter import *
from tkinter.ttk import *
from threading import Thread

#import icon resource
import base64,eks
with open('tmpicon.ico','wb+') as tmp:
    tmp.write(base64.b64decode(eks.img))

user32 = ctypes.windll.user32
screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

xWIDTH = int(screensize[0]//10*6)
xHEIGHT = int(screensize[1]//10*8)
OFFSET_X = 300
OFFSET_Y = 100
from xOTAGBT32960 import OTAGBData,createOTAGBMsg,CMD,genGBTime,Field,timestamp
from xSigGenerator_GBM import *

COLUMNS = ['数据项名称','值','范围','有效性']
COLUMNS_WIDTH = [200,200,100,100]
COLUMNS_STRETCH = [False,True,False,False]

class xGBT32960MonitorView():
    def __init__(self):
        self.root=Tk()
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.title(str_Title +' '+ str_Version)
        self.root.iconbitmap(r'tmpicon.ico')
        os.remove('tmpicon.ico') 
        self.root.grid()
        self.root.minsize(xWIDTH, 600)
        goemtrystr = '{0}x{1}+{2}+{3}'.format(xWIDTH,xHEIGHT,OFFSET_X,OFFSET_Y)
        self.root.geometry(goemtrystr)

        self.frame = Frame(self.root)
        self.frame.grid(row=0,rowspan=1,column=0,columnspan=1,sticky='nesw')
        self.frame.rowconfigure(20,weight=1)
        self.frame.columnconfigure(10,weight=1)

        self.menubar = Frame(self.frame)
        self.menubar.grid(row=10,rowspan=1,column=10,columnspan=1,sticky=N+S+E+W)

        self.vhlViewFrame = Frame(self.frame)
        self.vhlViewFrame.grid(row=20,rowspan=1,column=10,columnspan=1,sticky=N+S+E+W)
        self.vhlViewFrame.rowconfigure(10,weight=1)
        self.vhlViewFrame.columnconfigure(20,weight=1)

        self.vhlInfoFrame = Frame(self.vhlViewFrame)
        self.vhlInfoFrame.grid(row=10,rowspan=1,column=10,columnspan=1,sticky=N+S+E+W)

        self.hostLbl = Label(self.vhlInfoFrame,text='Server')
        self.hostLbl.grid(row=5,rowspan=1,column=10,columnspan=1,sticky=N+S+E+W)
        self.host = StringVar()
        self.hostCombobox = Combobox(self.vhlInfoFrame,textvariable=self.host)
        self.hostCombobox.grid(row=5,rowspan=1,column=20,columnspan=1,sticky=N+S+E+W)

        self.connectingActionStrVar = StringVar()
        self.connectingActionStrVar.set('Connect')        
        self.toggleConnectingBtn = Button(self.vhlInfoFrame,textvariable=self.connectingActionStrVar)
        self.toggleConnectingBtn.grid(row=5,rowspan=1,column=30,columnspan=1,sticky=N+S+E+W)

        self.VINLbl = Label(self.vhlInfoFrame,text='Vehicle')
        self.VINLbl.grid(row=10,rowspan=1,column=10,columnspan=1,sticky=N+S+E+W)
        self.VIN = StringVar()
        self.VINCombobox = Combobox(self.vhlInfoFrame,textvariable=self.VIN)
        self.VINCombobox.grid(row=10,rowspan=1,column=20,columnspan=1,sticky=N+S+E+W)

        self.bindingActionStrVar = StringVar()
        self.bindingActionStrVar.set('Bind')        
        self.toggleBindingBtn = Button(self.vhlInfoFrame,textvariable=self.bindingActionStrVar)
        self.toggleBindingBtn.grid(row=10,rowspan=1,column=30,columnspan=1,sticky=N+S+E+W)
        self.toggleBindingBtn.state(["disabled"])

        self.echoBtn = Button(self.vhlInfoFrame,text='echo')
        self.echoBtn.grid(row=20,rowspan=1,column=30,columnspan=1,sticky=N+S+E+W)
        self.echoBtn.state(["disabled"])

        self.vhlLoggingInfoFrame = Frame(self.vhlInfoFrame)
        self.vhlLoggingInfoFrame.grid(row=30,rowspan=1,column=10,columnspan=21,sticky=N+S+E+W)
        self.vhlLoggingInfoFrame.rowconfigure(10,weight=1)
        self.vhlLoggingInfoFrame.rowconfigure(10,weight=1)
        self.vhlLoggingInfoFrame.columnconfigure(10,weight=1)
        self.vhlLoggingInfoFrame.columnconfigure(20,weight=1)
        self.vhlLoggingInfoFrame.columnconfigure(30,weight=1)
        self.vhlLoggingInfoFrame.columnconfigure(40,weight=1)

        self.loginLbl = Label(self.vhlLoggingInfoFrame,text='登入流水号:')
        self.loginLbl.grid(row=10,rowspan=1,column=10,columnspan=1,sticky=N+S+E+W)

        self.loginFlownum= StringVar()
        self.loginFlownumLbl = Label(self.vhlLoggingInfoFrame,textvariable=self.loginFlownum)
        self.loginFlownumLbl.grid(row=10,rowspan=1,column=20,columnspan=1,sticky=N+S+E+W)

        self.loginTimeLbl = Label(self.vhlLoggingInfoFrame,text='登入时间:')
        self.loginTimeLbl.grid(row=10,rowspan=1,column=30,columnspan=1,sticky=N+S+E+W)

        self.loginTime= StringVar()
        self.loginTimeValueLbl = Label(self.vhlLoggingInfoFrame,textvariable=self.loginTime)
        self.loginTimeValueLbl.grid(row=10,rowspan=1,column=40,columnspan=1,sticky=N+S+E+W)

        self.logoutLbl = Label(self.vhlLoggingInfoFrame,text='登出流水号:')
        self.logoutLbl.grid(row=20,rowspan=1,column=10,columnspan=1,sticky=N+S+E+W)

        self.logoutFlownum= StringVar()
        self.logoutFlownumLbl = Label(self.vhlLoggingInfoFrame,textvariable=self.logoutFlownum)
        self.logoutFlownumLbl.grid(row=20,rowspan=1,column=20,columnspan=1,sticky=N+S+E+W)

        self.logoutTimeLbl = Label(self.vhlLoggingInfoFrame,text='登出时间:')
        self.logoutTimeLbl.grid(row=20,rowspan=1,column=30,columnspan=1,sticky=N+S+E+W)

        self.logoutTime= StringVar()
        self.logoutTimeValueLbl = Label(self.vhlLoggingInfoFrame,textvariable=self.logoutTime)
        self.logoutTimeValueLbl.grid(row=20,rowspan=1,column=40,columnspan=1,sticky=N+S+E+W)

        self.collectTime = StringVar()
        self.collectTimeLbl = Label(self.vhlLoggingInfoFrame,text='采集时间:')
        self.collectTimeLbl.grid(row=30,rowspan=1,column=30,columnspan=1,sticky=N+S+E+W)
        self.collectTimeValueLbl = Label(self.vhlLoggingInfoFrame,textvariable=self.collectTime)
        self.collectTimeValueLbl.grid(row=30,rowspan=1,column=40,columnspan=1,sticky=N+S+E+W)

        self.heartbeatTime = StringVar()
        self.heartbeatLbl = Label(self.vhlLoggingInfoFrame,text='心跳报文:')
        self.heartbeatLbl.grid(row=40,rowspan=1,column=30,columnspan=1,sticky=N+S+E+W)
        self.heartbeatValueLbl = Label(self.vhlLoggingInfoFrame,textvariable=self.heartbeatTime)
        self.heartbeatValueLbl.grid(row=40,rowspan=1,column=40,columnspan=1,sticky=N+S+E+W)


        self.msgListFrame = Frame(self.vhlViewFrame)
        self.msgListFrame.grid(row=20,rowspan=1,column=10,columnspan=1,sticky=N+S+E+W)

        # self.msgListbox = Listbox(self.msgListFrame)
        # self.msgListbox.grid(row=10,rowspan=1,column=10,columnspan=1,sticky=N+S+E+W)

        self.vhlRTDataFrame = Frame(self.vhlViewFrame)
        self.vhlRTDataFrame.grid(row=10,rowspan=11,column=20,columnspan=1,sticky=N+S+E+W)
        self.vhlRTDataFrame.rowconfigure(10,weight=1)
        self.vhlRTDataFrame.columnconfigure(10,weight=1)

        self.vhlRTDataTree = Treeview(self.vhlRTDataFrame,columns=COLUMNS,show=['tree','headings'])
        self.vhlRTDataTree.grid(row=10,rowspan=1,column=10,columnspan=1,sticky=N+S+E+W)
        minwidth = self.vhlRTDataTree.column('#0', option='minwidth')
        self.vhlRTDataTree.column('#0', width=minwidth*2)
        self.vhlRTDataTree.column(COLUMNS[0], width=COLUMNS_WIDTH[0], anchor='w')
        self.vhlRTDataTree.column(COLUMNS[1], width=COLUMNS_WIDTH[1], anchor='e')
        self.vhlRTDataTree.column(COLUMNS[2], width=COLUMNS_WIDTH[2], anchor='e')
        self.vhlRTDataTree.column(COLUMNS[3], width=COLUMNS_WIDTH[3], anchor='e')
        # self.vhlRTDataTree.column(COLUMNS[4], width=COLUMNS_WIDTH[4], anchor='e')
        for i in range(len(COLUMNS)):
            self.vhlRTDataTree.heading(COLUMNS[i], text=COLUMNS[i])



        self.vhlRTDataTreeScrollY = Scrollbar(self.vhlRTDataFrame,orient=VERTICAL,command=self.vhlRTDataTree.yview)
        self.vhlRTDataTreeScrollY.grid(row=10,rowspan=1, column=20, sticky=N+S)

        self.vhlRTDataTree['yscrollcommand'] = self.vhlRTDataTreeScrollY.set
        # self.logWindow = Text(self.vhlRTDataFrame)
        # self.logWindow.grid(row=10,rowspan=11,column=10,columnspan=1,sticky=N+S+E+W)

        self.logText = Text(self.vhlRTDataFrame)
        self.logText.grid(row=20,rowspan=1,column=10,columnspan=1,sticky=N+S+E+W)

        self.logTextScrollY = Scrollbar(self.vhlRTDataFrame,orient=VERTICAL,command=self.logText.yview)
        self.logTextScrollY.grid(row=20,rowspan=1, column=20, sticky=N+S)
        self.logText['yscrollcommand'] = self.logTextScrollY.set

        self.status = StringVar()
        self.status.set('Hello')
        self.statusbar = Label(self.frame,textvariable=self.status)
        self.statusbar.grid(row=30,rowspan=1,column=10,columnspan=1,sticky=N+S+E+W)
        self.statusbar.bind('<Triple-Button-1>',self.clearStatusBar)
    
    def clearStatusBar(self,event):
        self.status.set('')
        
class xGBT32960MonitorController():
    def __init__(self):
        self.closeflag = False

        self.view = xGBT32960MonitorView()

        self.model = xGBT32960MonitorModel()

        self.view.toggleConnectingBtn.bind('<Button-1>',self.toggleConnecting)
        self.view.toggleBindingBtn.bind('<Button-1>',self.toggleBinding)
        self.view.echoBtn.bind('<Button-1>',self.echo)

        self.view.host.set(self.model.configs['host'])
        self.view.hostCombobox.configure(values=self.model.configsHistory['hostHistory'])
        self.view.hostCombobox.configure(postcommand=self.updateHostDropDown)
        
        self.rxthdExist = False #接收消息的线程是否启动的标记量

        self.rtViewInitFlag = False #实时信息显示窗数据项目初始化标记

        self.view.VIN.set(self.model.configs['VIN'])
        self.view.VINCombobox.configure(values=self.model.configsHistory['vhlHistory'])
        self.view.VINCombobox.configure(postcommand=self.updateVINDropDown)

        self.view.root.mainloop()
        
        self.closeflag = True
        self.model.rxq.put(None)
        time.sleep(0.1)
        self.model.destroy()
        time.sleep(0.1)
        self.model = None

    def updateHostDropDown(self):
        self.view.hostCombobox.configure(values=self.model.configsHistory['hostHistory'])

    def updateVINDropDown(self):
        self.view.VINCombobox.configure(values=self.model.configsHistory['vhlHistory'])

    def getVhlConnectingStatus(self):
        return 'To Be Implement'

    def toggleBinding(self,event):
        print('function toggle binding')
        if self.model.connected:
            if self.model.binded:
                self.unbindVhl()                
            else:
                self.bindVhl()
                
    def toggleConnecting(self,event):
        print('function toggle connecting')
        if self.model.connected: # 连接 -> 断开连接
            self.model.connected = False
            print('disconnect TSP1')
            self.toggleBtnState()           
            self.disconnectTSP()
            self.view.connectingActionStrVar.set('Connect')
            
        else: # 断开连接 -> 连接
            result = self.connectTSP()
            if 0==result: 
                self.view.connectingActionStrVar.set('Disconnect')
                self.toggleBtnState()
            else:
                self.view.status.set('ERROR: 无法连接到服务器')

    def toggleBtnState(self):
        print('disconnect TSP2')
        if self.model.connected:
            self.view.toggleBindingBtn.state(['!disabled'])
            self.view.echoBtn.state(['!disabled'])
        else:
            self.view.toggleBindingBtn.state(['disabled'])
            self.view.echoBtn.state(['disabled'])

    def disconnectTSP(self):
        self.logout()
        self.rxthdExist = False

    def connectTSP(self):
        self.view.status.set('INFO: 正在连接服务器')
        time.sleep(0.1)
        host = self.view.host.get().strip()
        self.model.configs['host'] = host      
        result = self.model.createSocket()
        if 0==result:
            self.model.addToHistory('hostHistory',host)

            self.rxthdExist =True
            self.rxthd = Thread(target=self.rxloop)
            self.rxthd.start()

            self.login()

        return result


    def login(self):
        self.model.sendMsg(self.model.create_msg_login())

    def echo(self,event):
        if self.model.connected:
            self.model.sendMsg(eval(msg_echo))
            self.view.status.set('echo')

    def bindVhl(self):
        VIN = self.view.VIN.get().strip().upper()
        self.model.configs['VIN'] = VIN
        self.model.sendMsg(self.model.create_msg_select_vehicle())
        self.model.binded = True
        self.model.addToHistory('vhlHistory',VIN)
        self.view.bindingActionStrVar.set('Unbind') 

    def unbindVhl(self):
        self.model.sendMsg(eval(msg_disconnect_vehicle))
        self.model.binded = False
        self.clearView()
        self.view.bindingActionStrVar.set('Bind')

    def logout(self):
        if self.model.binded:
            self.unbindVhl()
        self.model.destroy()
        # self.model=None

    def showMsg(self):
        msg = self.model.rxq.get()
        if not msg: return
        msgstr = '{0}\n'.format(msg)
        if msg['name']=='gbdata':
            gbRaw = base64.standard_b64decode(msg['data'].encode('ascii'))
            self.showGBT32960Msg(gbRaw)
        # self.view.logWindow.insert(END,msgstr)
        else:
            self.view.status.set(msg)

    def showLogin(self,gbobj):
        self.view.loginFlownum.set(gbobj.payload.flownum.phy)
        self.view.loginTime.set(gbobj.payload.gbtime.phy)

    def showLogout(self,gbobj):
        self.view.logoutFlownum.set(gbobj.payload.flownum.phy)
        self.view.logoutTime.set(gbobj.payload.gbtime.phy)

    def showHeartBeat(self,gbobj):
        self.view.heartbeatTime.set(timestamp())

    def showGBData(self,gbobj):
        if xDEBUG:
            print('Class',type(self),'func: showGBData -->')
            gbobj.printself()
            
        if not self.rtViewInitFlag:
            self.initRTDataView(gbobj)

        for f in gbobj.payload.phy:
            if f.name != '采集时间':

                for element in f.phy:
                    if isinstance(element.phy, list):
                        for sube in element.phy:
                            self.view.vhlRTDataTree.set(f.name+element.name+sube.name,column=COLUMNS[1],value=sube.phy)
                    else:
                        self.view.vhlRTDataTree.set(f.name+element.name,column=COLUMNS[1],value=element.phy)
            else:
                self.view.collectTime.set(f.phy)

    def showGBT32960Msg(self,gbRaw:bytes):
        if xDEBUG: print(gbRaw)
        gbobj = OTAGBData(gbRaw)
        msgname = gbobj.name
        self.view.logText.insert(END,gbobj.raw.hex()+'\n')
        self.view.logText.see(END)
        if msgname==CMD[b'\x01']:
            if xDEBUG:  print('登入：{}'.format(self.model.configs['VIN']))
            self.showLogin(gbobj)
        elif msgname==CMD[b'\x04']:
            if xDEBUG:  print('登出：{}'.format(self.model.configs['VIN']))
            self.showLogout(gbobj)
        elif msgname in {CMD[b'\x02']}:
            if xDEBUG:  print('数据：{}'.format(self.model.configs['VIN']))
            self.showGBData(gbobj)
        elif msgname in {CMD[b'\x03']}:
            if xDEBUG:  print('数据：{}'.format(self.model.configs['VIN']))
            # self.showGBData(gbobj)
        elif msgname in {CMD[b'\x07']}:
            if xDEBUG:  print('数据：{}'.format(self.model.configs['VIN']))
            self.showHeartBeat(gbobj)
        else:
            if xDEBUG:  print('其他：{}'.format(self.model.configs['VIN']))
            print('CMD {}'.format(msgname))

    def initRTDataView(self,gbobj):
        for f in gbobj.payload.phy:
            if f.name != '采集时间':
                self.view.vhlRTDataTree.insert('','end',iid=f.name,text='',values=(f.name,'','',''))
                self.view.vhlRTDataTree.item(f.name,open=True)
                for element in f.phy:
                    if isinstance(element.phy, list):
                        if xDEBUG: print('宏域')
                        self.view.vhlRTDataTree.insert(f.name,'end',iid=f.name+element.name,text='',values=(' '*5+element.name,'','',''),open=True)
                        for sube in element.phy:
                            self.view.vhlRTDataTree.insert(f.name+element.name,'end',iid=f.name+element.name+sube.name,text='',values=(' '*13+sube.name,sube.phy,'',''))
                    else:
                        self.view.vhlRTDataTree.insert(f.name,'end',iid=f.name+element.name,text='',values=(' '*5+element.name,element.phy,'',''))
            else:
                self.view.collectTime.set(f.phy)
        self.rtViewInitFlag = True

    def clearView(self):
        kids = self.view.vhlRTDataTree.get_children()
        [self.view.vhlRTDataTree.delete(kid) for kid in kids]
        self.rtViewInitFlag = False

        self.view.loginFlownum.set('')
        self.view.logoutFlownum.set('')
        self.view.loginTime.set('')
        self.view.logoutTime.set('')
        self.view.collectTime.set('')

    def rxloop(self):
        while (not self.closeflag) and self.rxthdExist:
            self.model.rxMsg()
            try:           
                self.showMsg() #this function will block until get a msg from server
            except Exception as e:
                print(e)
                print('WARNING:','Can not show msg to ui')
        print('exit Controller rxloop')


if __name__ == '__main__':

    app=xGBT32960MonitorController()
    print('Program Exit')
    
        