#!/usr/bin/env python3
# -*- coding: utf8 -*-
# bluphy@163.com
# 2018-11-11 15:41:19 by xw: v0.4 support GB data 05,06,07,08,09;08,09 use predefined length
# 2018-11-10 00:55:17 by xw: v0.3 support GB data 02
# 2018-11-07 19:20:35 by xw: v0.2 support to monitor GB data 01
# 2018-09-07 19:42:24 by xw: fix bug when vin contains null character
# 2018-7-20 11:50:55 by xw: new created.
#### TODO:
# done 1.实时数据显示部分增加滚动条
# 2.数据校验助手，提示数据逻辑问题
# 3.
# 4.

xDEBUG = False

str_Version = 'v0.4'
str_Title = 'GB大数据监视器'

import sys
sys.path.append(sys.path[0].rsplit('\\',1)[0])
print(sys.path)
# import xDBService.xDBService as xdbs
import time
from tkinter import *
from tkinter.ttk import *
import socket
from threading import Thread

from xOTAGBT32960.xOTAGBT32960 import OTAGBData,createOTAGBMsg,CMD,genGBTime,Field
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
        self.root.grid()

        self.frame = Frame(self.root)
        self.frame.grid(row=0,rowspan=1,column=0,columnspan=1,sticky='nesw')
        self.frame.rowconfigure(20,weight=1)
        self.frame.columnconfigure(10,weight=1)

        self.menubar = Frame(self.frame)
        self.menubar.grid(row=10,rowspan=1,column=10,columnspan=1,sticky=N+S+E+W)

        self.vhlViewFrame = Frame(self.frame)
        self.vhlViewFrame.grid(row=20,rowspan=1,column=10,columnspan=1,sticky=N+S+E+W)
        self.vhlViewFrame.rowconfigure(10,weight=1)
        # self.vhlViewFrame.columnconfigure(10,weight=1)
        self.vhlViewFrame.columnconfigure(20,weight=1)

        self.vhlInfoFrame = Frame(self.vhlViewFrame)
        self.vhlInfoFrame.grid(row=10,rowspan=1,column=10,columnspan=1,sticky=N+S+E+W)

        self.VINLbl = Label(self.vhlInfoFrame,text='Vehicle')
        self.VINLbl.grid(row=10,rowspan=1,column=10,columnspan=1,sticky=N+S+E+W)
        self.VIN = StringVar()
        self.VINCombobox = Combobox(self.vhlInfoFrame,textvariable=self.VIN)
        self.VINCombobox.grid(row=10,rowspan=1,column=20,columnspan=1,sticky=N+S+E+W)

        self.bindingActionStrVar = StringVar()
        self.bindingActionStrVar.set('Bind')
        
        self.toggleBindingBtn = Button(self.vhlInfoFrame,textvariable=self.bindingActionStrVar)
        self.toggleBindingBtn.grid(row=10,rowspan=1,column=30,columnspan=1,sticky=N+S+E+W)

        self.echoBtn = Button(self.vhlInfoFrame,text='echo')
        self.echoBtn.grid(row=20,rowspan=1,column=30,columnspan=1,sticky=N+S+E+W)

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


        self.msgListFrame = Frame(self.vhlViewFrame)
        self.msgListFrame.grid(row=20,rowspan=1,column=10,columnspan=1,sticky=N+S+E+W)

        # self.msgListbox = Listbox(self.msgListFrame)
        # self.msgListbox.grid(row=10,rowspan=1,column=10,columnspan=1,sticky=N+S+E+W)

        self.vhlRTDataFrame = Frame(self.vhlViewFrame)
        self.vhlRTDataFrame.grid(row=10,rowspan=11,column=20,columnspan=1,sticky=N+S+E+W)
        self.vhlRTDataFrame.rowconfigure(10,weight=1)
        self.vhlRTDataFrame.columnconfigure(10,weight=1)

        self.vhlRTDataTree = Treeview(self.vhlRTDataFrame,columns=COLUMNS,show=['tree','headings'])
        self.vhlRTDataTree.grid(row=10,rowspan=11,column=10,columnspan=1,sticky=N+S+E+W)
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
        self.vhlRTDataTreeScrollY.grid(row=10,rowspan=11, column=20, sticky=N+S)

        self.vhlRTDataTree['yscrollcommand'] = self.vhlRTDataTreeScrollY.set
        # self.logWindow = Text(self.vhlRTDataFrame)
        # self.logWindow.grid(row=10,rowspan=11,column=10,columnspan=1,sticky=N+S+E+W)

        self.status = StringVar()
        self.status.set('Hello')
        self.statusbar = Label(self.frame,textvariable=self.status)
        self.statusbar.grid(row=30,rowspan=1,column=10,columnspan=1,sticky=N+S+E+W)

class xGBT32960MonitorController():
    def __init__(self):
        self.closeflag = False

        self.view = xGBT32960MonitorView()        
        self.view.toggleBindingBtn.bind('<Button-1>',self.toggleBinding)
        self.view.echoBtn.bind('<Button-1>',self.echo)

        self.model = xGBT32960MonitorModel()

        self.connectTSP()
        self.rxthd = Thread(target=self.rxloop)
        self.rxthd.start()
        self.login(None)
        self.rtViewInitFlag = False
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

    def updateVINDropDown(self):
        self.view.VINCombobox.configure(values=self.model.configsHistory['vhlHistory'])
    # def setConfigToModel(self,*args,**keywors):
    #     with open('xmonitor.cfg') as f:
    #         context = None
    #         for line in f:
    #             if '[' in line:
    #                 context = line.split('[')[1].split(']')[0]
    #                 if xDEBUG: print('set config:',context)
    #                 continue
    #             else:
    #                 pass # context not change
    #             if 'History' in context:
    #                 eval('self.model.{}.append(line.strip())'.format(context))
    #             elif 'Last' in context:
    #                 name,value = line.strip().split('=')
    #                 if name in {'username','VIN','host'}:                        
    #                     self.model.configs[name]=value                        
    #                     if xDEBUG: print('configs:',name,value)
    #                 else:
    #                     print('配置文件信息无效，将使用默认配置')
    #                     print('无效配置行:',line)

    #     # self.username = 'default'
    #     # self.model.VIN = ''
    #     # self.host =

    def getVhlConnectingStatus(self):
        return 'To Be Implement'

    def toggleBinding(self,event):
        print('toggle function')
        if self.model.binded:
            self.unbindVhl(event)
            self.view.bindingActionStrVar.set('bind')
        else:
            self.bindVhl(event)
            self.view.bindingActionStrVar.set('unbind')       

    def connectTSP(self):      
        self.model.createSocket()
    
    def login(self,event):
        self.model.sendMsg(self.model.create_msg_login())

    def echo(self,event):
        self.model.sendMsg(eval(msg_echo))
        self.view.status.set('echo')

    def bindVhl(self,event):
        VIN = self.view.VIN.get().strip().upper()
        self.model.configs['VIN'] = VIN
        self.model.sendMsg(self.model.create_msg_select_vehicle())
        self.model.binded = True
        self.model.addToHistory('vhlHistory',VIN)

    def unbindVhl(self,event):
        self.model.sendMsg(eval(msg_disconnect_vehicle))
        self.model.binded = False
        self.clearView()

    def logout(self,event):
        self.model.destroy()
        self.model=None

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

    def showGBData(self,gbobj):
        if xDEBUG:
            print('Class',type(self),'func: showGBData -->')
            gbobj.printself()
            
        if not self.rtViewInitFlag:
            self.initRTDataView(gbobj)

        for f in gbobj.payload.phy:
            if f.name != '采集时间':
                # self.view.vhlRTDataTree.insert('','end',iid=f.name,values=(f.name,'','','',''))
                for element in f.phy:
                    if isinstance(element.phy, list):
                        for sube in element.phy:
                            self.view.vhlRTDataTree.set(f.name+element.name+sube.name,column=COLUMNS[1],value=sube.phy)
                    else:
                        self.view.vhlRTDataTree.set(f.name+element.name,column=COLUMNS[1],value=element.phy)
                    # if xDEBUG: print(element.name,'\t',element.phy)
                #     self.view.vhlRTDataTree.insert(f.name,'end',iid=element.name,values=(element.name,element.phy,'','',''))
            else:
                self.view.collectTime.set(f.phy)

    def showGBT32960Msg(self,gbRaw:bytes):
        if xDEBUG: print(gbRaw)
        gbobj = OTAGBData(gbRaw)
        msgname = gbobj.name
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
        while not self.closeflag:            
            self.showMsg() #this function will block until get a msg from server
        print('exit Controller rxloop')


if __name__ == '__main__':

    app=xGBT32960MonitorController()
    print('Program Exit')
    
        