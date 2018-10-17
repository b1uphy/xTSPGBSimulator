#!/usr/bin/env python3
# -*- coding: utf8 -*-
# bluphy@163.com
# 2018-09-21 17:44:42 by xw: new created

#### BEGIN CALIRATION
cal_str_server_IP = '10.40.166.8'
cal_int_server_port = 9201
#### END## CALIRATION

#### BEGIN TRANSLATION
str_vehiclepanel_title = '车辆信息'
str_vehiclepanel_VINlabel = 'VIN'
str_vehiclepanel_TUKEY = 'TUKEY'
str_browse = '浏览'
str_parse = '解析'
str_status_analyzing = '解析中'
str_status_completed = '解析完成'

str_menu_file = '文件'
str_menu_setting = '设置'
str_menu_help = '帮助'
str_menu_help_about = '关于'


#### END## TRANSLATION


from tkinter import *
from tkinter.ttk import *



class xTSPClientView(Frame):
    def __init__(self,master=None):
        super(xTSPClientView,self).__init__()
        self.columnconfigure(10, weight=1)
        self.rowconfigure(20, weight=1)
        self.grid(sticky=N+S+E+W)

        self.menuframe = Frame(self)
        # self.menuframe.rowconfigure(10)
        # self.menuframe.columnconfigure(10)
        self.menuframe.grid(row=10,column=10,sticky='nesw')
        self.mbs = {}
        menus = [str_menu_file,str_menu_setting,str_menu_help]
        i=0
        for m in menus:
            self.mbs[m]=Menubutton(self.menuframe, text=m)
            self.mbs[m].grid(row=10,column=i)
            self.mbs[m].menu = Menu(self.mbs[m], tearoff=0)
            self.mbs[m]['menu'] = self.mbs[m].menu
            i+=1
        self.mbs[str_menu_help].menu.add_command(label=str_menu_help_about)
        
        self.contentsFrame = Frame(self)
        self.contentsFrame.rowconfigure(10,weight=1)
        self.contentsFrame.columnconfigure(10,weight=1)
        self.contentsFrame.columnconfigure(20, weight=4)
        self.contentsFrame.grid(row=20,column=10,sticky='nesw')

        self.leftFrame = Frame(self.contentsFrame)
        self.leftFrame.rowconfigure(20,weight=1)
        self.leftFrame.columnconfigure(10,weight=1)
        self.leftFrame.grid(row=10,column=10,sticky='nesw')

        self.vhlInfoFrame = Frame(self.leftFrame)
        self.vhlInfoFrame.grid(row=10,column=10,sticky='nesw')

        lbls = ['VIN','IMEI','PhoneNo','Tukey','RSkey']
        self.vhlInfoLbls = []
        self.vhlInfoEntriesVar = []
        self.vhlInfoEntries = []
        i=0
        for lbl in lbls:
            self.vhlInfoLbls.append(Label(self.vhlInfoFrame,text=lbl,anchor=E))
            self.vhlInfoLbls[-1].grid(row=i,column=10,sticky='nesw')
            
                
            self.vhlInfoEntriesVar.append(StringVar())
            if i==0:
                self.vhlInfoEntries.append(Combobox(self.vhlInfoFrame,width=20))
            else:
                self.vhlInfoEntries.append(Label(self.vhlInfoFrame,textvariable=self.vhlInfoEntries))
            self.vhlInfoEntries[-1].grid(row=i,column=20,sticky='nesw')

            i+=1

        self.msgFrame = Frame(self.leftFrame)
        self.msgFrame.rowconfigure(10,weight=1)
        self.msgFrame.columnconfigure(10,weight=1)
        self.msgFrame.grid(row=20,column=10,sticky='nesw')

        self.msgtree = Treeview(self.msgFrame)
        self.msgtree.grid(row=10,column=10,sticky='nesw')

        self.rightFrame = Frame(self.contentsFrame)
        self.rightFrame.grid(row=10,column=20,sticky='nesw')
        self.rightFrame.rowconfigure(10,weight=1)
        self.rightFrame.columnconfigure(10,weight=1)
        self.logView = Text(self.rightFrame)
        self.logView.grid(row=10,column=10,sticky='nesw')

        self.statusFrame = Frame(self)
        self.statusFrame.grid(row=30,column=10,sticky='nesw')
        self.statusVar = StringVar()
        self.status = Label(self.statusFrame,textvariabl=self.statusVar)
        self.status.grid(row=10,column=10,sticky='nesw')
        self.statusVar.set('demo')

    def showAbout(self):
        pass

    def getMsglist(self):
        pass

    def initMsgTree(self):
        pass

    def showVhlInfo(self,VIN):
        pass


class xTSPClient:
    def __init__(self,server,port):
        pass

    def connectServer(self):
        pass

    def txMsg(self):
        pass
        
    def rxMsg(self):
        pass






if __name__=='__main__':
    root=Tk()
    root.rowconfigure(0,weight=1)
    root.columnconfigure(0,weight=1)
    # root.geometry('600x100'+'+'+str(screensize[0]//2-300)+'+'+str(screensize[1]//2-100))
    # root.geometry('400x600+700+400')
    app=xTSPClientView(master=root)
    app.master.title("xTSPClient_v0.1")
    app.mainloop()