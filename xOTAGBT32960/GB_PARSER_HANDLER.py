#!/usr/bin/python
# -*- coding: utf8 -*-
#made by Xue Wei 20170731
from enum import Enum

xDEBUG = False

#### legacy global variable, latest version can handle the dynamic count of motors, battery cells and temperature probes
gMotorCnt = 1
gCellCnt = 96
gTempProbe = 24

#GBLogIn数据结构初始化[DID 3E01]

#GBLogOut数据结构初始化[DID 3E02]

#GBData数据结构初始化[DID 3E00]
GBData=[]
GBDataNames = ['整车数据','电机数据','燃料电池','发动机','定位数据','极值数据','报警数据','电压数据','温度数据']
GBDataLengths = [42,0,0,0,20,30,84,504,70]
for i in range(len(GBDataNames)):
    GBData.append({})
    GBData[i]['name'] = GBDataNames[i]
    GBData[i]['length'] = GBDataLengths[i]
    GBData[i]['raw'] = ''
#   GBData[i]['sub'] = []


    

dctGBData_01_VehicleStatus = {
    '01':'启动',
    '02':'熄火',
    '03':'其他',
    'FE':'异常',
    'FF':'无效'
}

dctGBData_01_ChargingStatus = {
    '01':'停车充电',
    '02':'行驶充电',
    '03':'未充电',
    '04':'充电完成',
    'FE':'异常',
    'FF':'无效'
}

dctGBData_01_OperatingStatus = {
    '01':'纯电',
    '02':'混动',
    '03':'燃油',
    'FE':'异常',
    'FF':'无效'
}

dctGBData_01_DCDCStatus = {
    '01':'工作',
    '02':'断开',
    'FE':'异常',
    'FF':'无效'
}

dctGBData_02_MotorStatus = {
    '01':'耗电',
    '02':'发电',
    '03':'关闭',
    '04':'准备',
    'FE':'异常',
    'FF':'无效'
}

dctGBData_05_LocatingStatus_Validation = {
    0 : '有效',
    1 : '无效'
}

dctGBData_05_LocatingStatus_Latitude = {
    0 : '北纬',
    1 : '南纬'
}

dctGBData_05_LocatingStatus_Longitude = {
    0 : '东经',
    1 : '西经'
}




def parseAnalog(raw,ratio=1,offset=0,unit=''):
    value = int(raw,16)*ratio + offset
    return str(value)+unit

def parseByDct(raw,dct):
    try:
        data = [raw+':'+dct[raw]]
    except KeyError:
        data = ['error: no mapping -> '+raw]
    return data
    

def parseASCIIStr(raw:str):
    try:
        value = '\''+bytearray.fromhex(raw).decode('ascii')
    except ValueError:
        value = 'ERROR:ASCII'
    return [value]  

def parseGBTime (raw:str):
    if xDEBUG:
        print(raw)
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
        return ['采集:'+year+'-'+month+'-'+date+' '+(len(hour)%2)*'0'+hour+':'+(len(minute)%2)*'0'+minute+':'+(len(sec)%2)*'0'+sec]

#0x01 整车数据
def parseVehicleStatus(raw):
    return parseByDct(raw,dctGBData_01_VehicleStatus)

def parseChargingStatus(raw):
    return parseByDct(raw,dctGBData_01_ChargingStatus)
    
def parseOperatingStatus(raw):
    return parseByDct(raw,dctGBData_01_OperatingStatus)
    
def parseVehicleSpeed(raw):
    value = int(raw,16)*0.1
    unit = 'km/h'
    data = [raw+':车速 '+str(value) +unit]
    return data
    
def parseOdometer(raw):
    value = int(raw,16)*0.1
    unit = 'km'
    data = [raw+':总里程 '+str(value) +unit]
    return data
    
def parseTotalVoltage(raw):
    value = int(raw,16)*0.1
    unit = 'V'
    data = [raw+':总电压 '+str(value) +unit]
    return data
    
def parseTotalCurrent(raw):
    value = int(raw,16)*0.1-1000
    unit = 'A'
    data = [raw+':总电流 '+str(value) +unit]
    return data
    
def parseSOC(raw):
    value = int(raw,16)
    unit = '%'
    data = [raw+':SOC '+str(value) +unit]
    return data
    
def parseDCDCStatus(raw):
    return parseByDct(raw,dctGBData_01_DCDCStatus)

def parseShift(raw):
    
    value = int(raw,16)
    shiftMask = 0xF
    brakeMask = 0x10
    accMask = 0x20
    shiftRaw = shiftMask & value
    brakeRaw = brakeMask & value
    accRaw = accMask & value
    if shiftRaw == 0:
        shift = '空挡'
    elif shiftRaw == 0xD:
        shift = '倒挡'
    elif shiftRaw == 0xE:
        shift = 'D挡'
    elif shiftRaw == 0xF:
        shift = 'P挡'
    else:
        shift = str(shiftRaw)+'挡'
        
    if brakeRaw>0:
        brake = '制动力:有'
    else:
        brake = '制动力:无'
    
    if accRaw>0:
        acc = '驱动力:有'
    else:
        acc = '驱动力:无'
        
    return [raw+' 挡位信息->',shift,brake,acc]
    
def parseResistence(raw):
    value = int(raw,16)
    unit = 'kOu'
    data = [raw+':绝缘电阻 '+str(value) +unit]
    return data
    
def parseACCPosition(raw):
    value = int(raw,16)
    unit = '%'
    data = [raw+':加速踏板->'+str(value) +unit]
    return data
    
def parseBrakePosition(raw):
    value = int(raw,16)
    unit = '%'
    data = [raw+':制动踏板->'+str(value) +unit]
    return data

#GB02
def parseMotorStatus(raw):
    return parseByDct(raw,dctGBData_02_MotorStatus)
    
def parseMotorControllerTemp(raw):
    return ['控制器温度:'+raw+'->'+parseAnalog(raw,1,-40,'degC')]
    
def parseMotorSpeed(raw):
    return ['电机速度:'+raw+'->'+parseAnalog(raw,1,-20000,'r/min')]
    
def parseMotorTorque(raw):
    return ['转矩:'+raw+'->'+parseAnalog(raw,0.1,-2000,'N*m')]
    
def parseMotorTemp(raw):
    return ['电机温度:'+raw+'->'+parseAnalog(raw,1,-40,'degC')]
    
def parseMotorControllerInputVoltage(raw):
    return ['输入电压:'+raw+'->'+parseAnalog(raw,0.1,0,'V')]

def parseMotorCurrent(raw):
    return ['母线电流:'+raw+'->'+parseAnalog(raw,0.1,-1000,'A')]

def parseMotorInfo(raw):
    motorNum = raw[0:2]
    motorStatus = parseMotorStatus(raw[2:4])
    motorControllerTemp = parseMotorControllerTemp(raw[4:6])
    motorSpeed = parseMotorSpeed(raw[6:10])
    motorTorque = parseMotorTorque(raw[10:14])
    motorTemp = parseMotorTemp(raw[14:16])
    motorControllerInputVoltage = parseMotorControllerInputVoltage(raw[16:20])
    motorCurrent = parseMotorCurrent(raw[20:24])
    return [motorNum]+motorStatus+motorControllerTemp+motorSpeed+motorTorque+motorTemp+motorControllerInputVoltage+motorCurrent
    
#GB05
def parseLocatingStatus(raw):
    value = int(raw,16)
    validationMask = 0x1
    latitudeMask = 0x2
    longitudeMask = 0x4
    validation = dctGBData_05_LocatingStatus_Validation[value & validationMask]
    latitude = dctGBData_05_LocatingStatus_Latitude[value & latitudeMask]
    longitude = dctGBData_05_LocatingStatus_Longitude[value & longitudeMask]
    return [validation,latitude,longitude]

def parseLatitudeLongitude(raw):
    value = int(raw,16)/1000000
    return [str(value)]
    
    
#GB06
def parseSysNum(raw):
    return ['代号:'+str(int(raw,16))]
#GB07
def parseAlertFlag(raw):
    value = int(raw,16)
    data = ['AlertFlag:'+raw]
    flagNames = ['温度差异','电池高温','车载储能装置类型过压','车载储能装置类型欠压','SOC低',\
    '单体电池过压','单体电池欠压','SOC过高','SOC跳变','可充电储能系统不匹配','电池单体一致性差',\
    '绝缘报警','DCDC温度','制动系统','DCDC状态','驱动电机控制器温度','高压互锁状态','驱动电机温度',\
    '车载储能装置类型过充']
    mask = 0x1
    flagstr = ''
    for i in range(len(flagNames)):
        flag = ((mask<<i)&value)>>i
        if flag ==1: flagstr += ';'+flagNames[i]
    if value >= 0x80000: 
        reserved = 'reserve error'
    else:
        reserved = 'reserve good'
    data += [flagstr+';'+reserved]
    return data
#GB08   
def parseEnergyStorageVoltageInfo(raw):
    data = []
    sysNum = ['SysNum:'+raw[0:2]]
    sysVoltage = [parseAnalog(raw[2:6],0.1,0,'V')]
    sysCurrent = [parseAnalog(raw[6:10],0.1,-1000,'A')]
    cellTotalCnt = ['单体总数:'+parseAnalog(raw[10:14])]
    cellThisStartIndex = ['本帧启始号:'+parseAnalog(raw[14:18])]
    cellThisCnt = int(raw[18:20],16)
    cellThisCntText = ['本帧数量:'+str(cellThisCnt)]
    
    data += sysNum + sysVoltage + sysCurrent + cellTotalCnt + cellThisStartIndex + cellThisCntText
    
    raw = raw[20:]
    for i in range(cellThisCnt):
        data += ['No.'+str(i+1)+':'+parseAnalog(raw[0:4],1,0,'mV')]
        raw = raw[4:]
        
    rawLeft = raw
    
    return data,cellThisCnt,rawLeft
    
def parseEnergyStorageVoltageInfoList(raw,sysCnt):
    data = []
    
    for i in range(sysCnt):
        tmpdata,cellThisCnt,raw = parseEnergyStorageVoltageInfo(raw)
        data += tmpdata
        
    reserved = ['预留:'+raw]
    data += reserved
    
    return data
    
#GB09
def parseEnergyStorageTempInfo(raw):
    data = []
    sysNum = ['SysNum:'+raw[0:2]]
    
    probeCnt = int(raw[2:6],16)
    probeCntText = ['探针数量:'+str(probeCnt)]
    data += sysNum + probeCntText
    
    raw = raw[6:]
    for i in range(probeCnt):
        data += ['No.'+str(i+1)+':'+parseAnalog(raw[0:2],1,-40,'degC')]
        raw = raw[2:]
    rawLeft = raw
    return data,rawLeft

def parseEnergyStorageTempInfoList(raw,sysCnt):
    data = []
    for i in range(sysCnt):
        tmpdata,raw = parseEnergyStorageTempInfo(raw)
        data += tmpdata
        
    reserved = ['预留:'+raw]
    data += reserved
    return data
############    
GBData01 = []
GBData01Names = ['车辆状态','充电状态','运行模式','车速','累计里程','总电压','总电流','SOC','DCDC状态','挡位','绝缘电阻','加速踏板行程值','刹车状态']
GBData01Lengths = [2,2,2,4,8,4,4,2,2,2,4,2,2]
GBData01Handlers = [parseVehicleStatus,parseChargingStatus,parseOperatingStatus,parseVehicleSpeed,parseOdometer,parseTotalVoltage,parseTotalCurrent,parseSOC,parseDCDCStatus,parseShift,parseResistence,parseACCPosition,parseBrakePosition]
for i in range(len(GBData01Names)):
    GBData01.append({})
    GBData01[i]['name'] = GBData01Names[i]
    GBData01[i]['length'] = GBData01Lengths[i]
    GBData01[i]['raw'] = ''
    GBData01[i]['handler'] = GBData01Handlers[i]
#   GBData01[i]['sub'] = {}

GBData05 = []
GBData05Names = ['定位状态','经度','纬度']
GBData05Lengths = [2,8,8]
GBData05Handlers = [parseLocatingStatus,parseLatitudeLongitude,parseLatitudeLongitude]
for i in range(len(GBData05Names)):
    GBData05.append({})
    GBData05[i]['name'] = GBData05Names[i]
    GBData05[i]['length'] = GBData05Lengths[i]
    GBData05[i]['raw'] = ''
    GBData05[i]['handler'] = GBData05Handlers[i]
    
    
''' 
GBData01Names = ['车辆状态','充电状态','运行模式','车速','累计里程','总电压','总电流','SOC','DCDC状态','挡位','绝缘电阻','加速踏板行程值','刹车状态']
GBData01Lengths = [2,2,2,4,8,4,4,2,2,2,4,2,2]
GBData01Handlers = [None,None,None,None,None,None,None,None,None,None,None,None,None]
for i in range(len(GBData01Names)):
    GBData[0]['sub'].append({})
    GBData[0]['sub'][i]['name'] = GBData01Names[i]
    GBData[0]['sub'][i]['length'] = GBData01Lengths[i]
    GBData[0]['sub'][i]['raw'] = ''
    GBData[0]['sub'][i]['handler'] = GBData01Handlers[i]

GBData02Names = ['车辆状态','充电状态','运行模式','车速','累计里程','总电压','总电流','SOC','DCDC状态','挡位','绝缘电阻','加速踏板行程值','刹车状态']
GBData02Lengths = [2,2,2,4,8,4,4,2,2,2,4,2,2]
GBData02Handlers = [None,None,None,None,None,None,None,None,None,None,None,None,None]
for i in range(len(GBData01Names)):
    GBData[1]['sub'].append({})
    GBData[1]['sub'][i]['name'] = GBData02Names[i]
    GBData[1]['sub'][i]['length'] = GBData02Lengths[i]
    GBData[1]['sub'][i]['raw'] = ''
    GBData[1]['sub'][i]['handler'] = GBData02Handlers[i]
'''

def parseGBLogin(raw):
    print('login')
    try:
        gbTime = parseGBTime(raw[0:12])
        flowNumIn = [raw[12:16]]
        ICCID = parseASCIIStr(raw[16:56])
        sysCnt_ChargeableEnergyStorage = [raw[56:58]]
        sysNum_ChargeableEnergyStorage = [raw[58:60]]
    except IndexError:
        return ['error:Login data ->'+raw] 
    return gbTime+flowNumIn+ICCID+sysCnt_ChargeableEnergyStorage+sysNum_ChargeableEnergyStorage

def parseGBLogout(raw):
    print('logout')
    gbTime = parseGBTime(raw[0:12])
    flowNumOut = [raw[12:16]]
    return gbTime+flowNumOut

def parseGBHeartbeat(raw:str):
    pass
    return ['parseGBHeartbeat Not implemented']

def parseGBDataTemplate(GBDataID,raw):

    cmdID = raw[0:2]
    data = ['GB'+cmdID+':'+raw]
    raw = raw[2:]
    data += [cmdID]
    for i in range(len(GBDataID)):
        GBDataID[i]['raw'] = raw[0:GBDataID[i]['length']]
        raw = raw[GBDataID[i]['length']:]
        hdl = GBDataID[i]['handler']
        if hdl == None:
            data += [GBDataID[i]['raw']]
        else:
            data += hdl(GBDataID[i]['raw'])
    return data
    
    
def parseGBData_01(raw):
    if not len(raw) == 42: return ['error:GB02 length -> '+raw]
    data = ['GB01:'+raw]
    cmdID = [raw[0:2]]
    raw = raw[2:]
    data += cmdID
    for i in range(len(GBData01Names)):
        GBData01[i]['raw'] = raw[0:GBData01[i]['length']]
        raw = raw[GBData01[i]['length']:]
        hdl = GBData01[i]['handler']
        if hdl == None:
            data += [GBData01[i]['raw']]
        else:
#           tmp = GBData01[i]['raw']
#           print('GB01' +str(i)+'->'+ tmp)
#           data += hdl(tmp)
            data += hdl(GBData01[i]['raw'])
    return data
    
def parseGBData_02(raw):
    if xDEBUG:
        print('cmd02='+raw)
    if len(raw)==0: return ['']*(gMotorCnt*8+3)
    #if not len(raw) == 52: return ['error:GB02 length -> '+raw]
    data = ['GB02:'+raw]
    cmdID = [raw[0:2]]
    motorCnt = int(raw[2:4],16)
    data += cmdID + ['电机数量:'+str(motorCnt)]
    raw = raw[4:]
    for i in range(motorCnt):       
        data += parseMotorInfo(raw[0:24])
        raw = raw[24:]
        
    return data

def parseGBData_03(raw):
#   return parseGBDataTemplate(GBData02,raw)
    return ['GB03:->'+raw]
def parseGBData_04(raw):
#   return parseGBDataTemplate(GBData02,raw)
    return ['GB04:->'+raw]
def parseGBData_05(raw):
    
    if not len(raw) == 20: return ['error:GB05 length -> '+raw]
    return parseGBDataTemplate(GBData05,raw)
#   return ['GB05:->'+raw]

def parseGBData_06(raw):
    data = ['GB06:'+raw]
    cmdID = [raw[0:2]]
    
    raw = raw[2:]
    
    sysMaxVolNum = parseSysNum(raw[0:2])
    cellMaxVolNum = parseSysNum(raw[2:4])
    cellMaxVol = ['最高电压:'+parseAnalog(raw[4:8],0.001,0,'V')]
    
    sysMinVolNum = parseSysNum(raw[8:10])
    cellMinVolNum = parseSysNum(raw[10:12])
    cellMinVol = ['最低电压:'+parseAnalog(raw[12:16],0.001,0,'V')]
    
    raw = raw[16:]
    sysMaxTempNum = parseSysNum(raw[0:2])
    cellMaxTempNum = parseSysNum(raw[2:4])
    cellMaxTemp = ['最高温度:'+parseAnalog(raw[4:6],1,-40,'degC')]
    
    sysMinTempNum = parseSysNum(raw[6:8])
    cellMinTempNum = parseSysNum(raw[8:10])
    cellMinTemp = ['最低温度:'+parseAnalog(raw[10:12],1,-40,'degC')]
    
    data += cmdID+sysMaxVolNum+cellMaxVolNum+cellMaxVol+sysMinVolNum+cellMinVolNum+cellMinVol+sysMaxTempNum+cellMaxTempNum+cellMaxTemp+sysMinTempNum+cellMinTempNum+cellMinTemp
#   return parseGBDataTemplate(GBData02,raw)
    return data
    
def parseGBData_07(raw):
    data = ['GB07:'+raw[0:12]]
    cmdID = [raw[0:2]]
    maxAlerLvl = ['最高报警等级:'+raw[2:4]]
    alertFlag = parseAlertFlag(raw[4:12])
    alertCode = ['故障代码表:'+raw[12:]]
    data += cmdID + maxAlerLvl + alertFlag + alertCode
    return data
    
def parseGBData_08(raw):
    data = ['GB08:'+raw[0:12]]

    cmdID = [raw[0:2]]
    sysCnt = int(raw[2:4],16)
    sysCntText = ['SysCnt:'+raw[2:4]]
    raw = raw[4:]
    data += cmdID + sysCntText + parseEnergyStorageVoltageInfoList(raw,sysCnt)  
    return data
    
def parseGBData_09(raw):
    data = ['GB09:'+raw[0:]]
    cmdID = [raw[0:2]]
    sysCnt = int(raw[2:4],16)
    sysCntText = ['SysCnt:'+raw[2:4]]
    raw = raw[4:]
    data += cmdID + sysCntText + parseEnergyStorageTempInfoList(raw,sysCnt) 
    return data
    
GBDataHandlers = [parseGBData_01,parseGBData_02,parseGBData_03,parseGBData_04,parseGBData_05,parseGBData_06,parseGBData_07,parseGBData_08,parseGBData_09]

'''
def parseGBDatas(raw):
    data = []
    for i in range(len(GBData)):
        GBData[i]['raw'] = raw[0:GBData[i]['length']]
        raw = raw[GBData[i]['length']:]
        if xDEBUG:
            print('GBData '+str(i+1)+' raw='+GBData[i]['raw'])
        hdl = GBDataHandlers[i]
#       hdl = parseGBDataTemplate(GBData[i])

        data += hdl(GBData[i]['raw'])

    return data
'''

def parseGBDatasBW(raw):
    data = []
    for i in range(len(GBData)):        
        GBData[i]['raw'] = ''
    
    while (len(raw)>0):
        cmd = int(raw[:2],16)-1
        
        if cmd ==1: 
            if xDEBUG:
                print('here')
                print('raw=',raw[:52])
            GBData[cmd]['length'] = (int(raw[2:4],16)*12+2)*2
            if xDEBUG:
                print(GBData[cmd]['length'])
        elif cmd==3:
            print('error:',raw)
            return 'error'
        else:
            pass
            
        GBData[cmd]['raw'] = raw[0:GBData[cmd]['length']] 
        raw =  raw[GBData[cmd]['length']:]
            
        if xDEBUG:
            print('GBData '+str(cmd+1) + ' raw=' + GBData[cmd]['raw'])
    
    for i in range(len(GBData)):
        hdl = GBDataHandlers[i]
#       hdl = parseGBDataTemplate(GBData[i])

        data += hdl(GBData[i]['raw'])

    return data


def parseGBDatasDirect(raw):
    #由于BWOTA增加了预留位，和国标的长度不一致
    #id 07 报警数据长度
    GBData[6]['length'] =  20
    #id 08 单体电压数据
    GBData[7]['length'] =  408
    #id 09 探针温度数据
    GBData[8]['length'] =  60
    data = []
    
    for i in range(len(GBData)):        
        GBData[i]['raw'] = ''
    
    while (len(raw)>0):
        cmd = int(raw[:2],16)-1
        
        #02驱动电机数据是变长的
        if cmd ==1: 
            if xDEBUG:
                print('here')
                print('raw=',raw[:52])
            GBData[cmd]['length'] = (int(raw[2:4],16)*12+2)*2
            if xDEBUG:
                print(GBData[cmd]['length'])
        elif cmd==3:
            print('error:',raw)
            return 'error'
        else:
            pass
        
        if GBData[cmd]['length']==0:
            return 'error' 
        GBData[cmd]['raw'] = raw[0:GBData[cmd]['length']] 
        
        raw =  raw[GBData[cmd]['length']:]
            
        if xDEBUG:
            print('GBData '+str(cmd+1) + ' raw=' + GBData[cmd]['raw'])
    
    for i in range(len(GBData)):
        hdl = GBDataHandlers[i]
#       hdl = parseGBDataTemplate(GBData[i])

        data += hdl(GBData[i]['raw'])

    return data
    
#GBT32960.3 Table 2
def parseGBPkgs(raw:str):
    raw = raw.strip()
    data = []
    head = parseASCIIStr(raw[:4])
    cmd = [raw[4:6]]
    ack = [raw[6:8]]
    VIN = parseASCIIStr(raw[8:42])
    encrypt = [raw[42:44]]
    length = [raw[44:48]]
    check = ['校验码: '+raw[-2:]]
    raw = raw[48:-2]

    data = data + head + cmd + ack + VIN + encrypt + length
    
    if xDEBUG:
        print('parseGBPkgs raw='+raw)
        print('head='+str(data))
    
    if cmd[0] == '02' or cmd[0] == '03':
        gbtime = parseGBTime(raw[:12])
        data += gbtime + parseGBDatasDirect(raw[12:])
    elif cmd[0] == '01':
        data += parseGBLogin(raw)
    elif cmd[0] == '04':
        data += parseGBLogout(raw)
    return data+check

