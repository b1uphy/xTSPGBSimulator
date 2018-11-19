#!/usr/bin/env python3
# -*- coding: utf8 -*-
# bluphy@163.com
# 2018-11-19 18:26:35 by xw: fixed a bug when analyzing GB Data 02
# 2018-5-29 17:06:51 by xw: new created.
import time
from bidict import bidict
# import xTSPGBSimulator.xOTAGBT32960.GB_PARSER_HANDLER as gbp

xDEBUG = False

CMD = {
    b'\x01' : '车辆登入',    
    b'\x02' : '实时数据',    
    b'\x03' : '补发数据',    
    b'\x04' : '车辆登出',    
    b'\x07' : '心跳',    
    b'\x80' : '查询命令',    
    b'\x81' : '设置命令',   
    b'\x82' : '控制命令'
    }

GBDataLengths = [21,-1,-1,6,10,15,-1,-1,-1]

def calBCCChk(buf:bytes):
    chk = buf[0]
    for byte in buf[1:]:
        chk = byte^chk
    return chk.to_bytes(1,byteorder='big')

def genGBTime()->bytes:
    '''
    生成国标格式的时间字节流
    '''
    lct = time.localtime()
    year = (lct.tm_year-2000).to_bytes(1,byteorder='big')
    month = lct.tm_mon.to_bytes(1,byteorder='big')
    date = lct.tm_mday.to_bytes(1,byteorder='big')
    hour = lct.tm_hour.to_bytes(1,byteorder='big')
    minute = lct.tm_min.to_bytes(1,byteorder='big')
    sec = lct.tm_sec.to_bytes(1,byteorder='big')
    gbtime = year+month+date+hour+minute+sec

    return gbtime

def splitData(raw:bytes):
    '''
    input raw packets and return a cat and its data
    '''
    cat = raw[0]
    if xDEBUG:    print('raw=',raw.hex())
    if xDEBUG:    print('cat=',cat)
    length = GBDataLengths[cat-1]

    if 0>length:
        if 2==cat: #驱动电机数据是变长的
            length = raw[1]*12+2
        elif 3==cat:
            length = int.from_bytes(raw[7:8],'big')+18
        elif 7==cat:
            n1=raw[6]
            n2=raw[7+4*n1]
            n3=raw[8+4*(n1+n2)]
            n4=raw[9+4*(n1+n2+n3)]
            length = 4*(n1+n2+n3+n4)+10
        elif 8==cat:
            length = 204
        elif 9==cat:
            length = 30
        else:
            print('ERROR: length mot correct')
            length = 0
    catdata = raw[1:length]
    raw = raw[length:]
    if xDEBUG:
        print('catdata=',catdata.hex()) 
        print('rawleft=',raw.hex())
    return (cat,catdata,raw)

def parseGBTime (raw:bytes):
    if xDEBUG:
        print(raw)
    if not len(raw)==6: 
        return ['error:GBTime length']
    else:
        x=int.from_bytes(raw,'big')   
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
        return year+'-'+month+'-'+date+' '+(len(hour)%2)*'0'+hour+':'+(len(minute)%2)*'0'+minute+':'+(len(sec)%2)*'0'+sec

def parseAnalog(raw:bytes,ratio=1,offset=0,unit='',endian='big'):
    value = int.from_bytes(raw,endian)*ratio + offset
    return str(value)+'  '+unit

def parseByDct(raw,dct):
    try:
        data = dct[raw]
    except KeyError:
        data = 'error: no mapping -> '+raw.hex()
    return data

def parseASCIIStr(raw:bytes):
    try:
        value = raw.decode('ascii')
    except ValueError:
        value = 'ERROR:ASCII'
    return value

def createOTAGBMsg(cmd:bytes, resp:bytes, VIN:str, secrettype:int, length:int, data:bytes):
    '''
    '''
    start = b'##'
    payload = cmd+resp+VIN.encode('ascii')+secrettype.to_bytes(1,byteorder='big')+length.to_bytes(2,byteorder='big')+data
    chk = calBCCChk(payload)
    msg = start + payload + chk
    return msg

class Field:
    def __init__(self,name,raw,convertfunc=None,checkfunc=None):
        #print(raw)
        self.name = name

        if type(raw) is int:
            self.raw = raw.to_bytes(1,byteorder='big')
        else:
            self.raw = raw
        #print(type(self.raw))
        if convertfunc:          
            self.phy = convertfunc(self.raw)
        else:
            self.phy = self.raw.hex()
        pass
    def printself(self):
        if isinstance(self.phy, list):
            print(self.name,'raw:',self.raw.hex())
            for e in self.phy:
                e.printself()
        else:
            print(self.name,self.phy,'raw:',self.raw.hex())

class Head(Field):
    def __init__(self, header:bytes):
        #print(header[2])
        def convert(header:bytes):
            cmd = Field('命令标识', header[2], convertfunc=lambda x: CMD[x])
            resflg = Field('应答标志', header[3])
            VIN = Field('VIN', header[4:21],convertfunc=lambda x: x.decode('ascii'))
            secretflg = Field('加密方式', header[21])
            length = Field('数据长度', header[22:24], convertfunc=lambda x: int(x.hex(),16))
            return [cmd,resflg,VIN,secretflg,length]
        super(Head,self).__init__('header',header,convertfunc=convert)
        keys = 'cmd,resflg,VIN,secretflg,length'.split(',')
        for i in range(len(keys)):
            exec('self.{0}=self.phy[{1}]'.format(keys[i],i))
        pass
        # self.cmd = Field('命令标识', header[2], convertfunc=lambda x: CMD[x])
        # self.resflg = Field('应答标志', header[3])
        # self.VIN = Field('VIN', header[4:21],convertfunc=lambda x: x.decode('ascii'))
        # self.secretflg = Field('加密方式', header[21])
        # self.length = Field('数据长度', header[22:24], convertfunc=lambda x: int(x.hex(),16))

class PayloadLogin(Field):
    def __init__(self, payload:bytes):
        #print(header[2])
        def convert(payload:bytes):
            gbtime = Field('采集时间',payload[:6],parseGBTime)
            flownum = Field('登入流水号',payload[6:8],parseAnalog)
            ICCID = Field('ICCID',payload[8:28],parseASCIIStr)
            BatSysCnt = Field('可充电储能子系统数',payload[28],parseAnalog)
            BatSysCodeLen = Field('可充电储能子系统编码长度',payload[29],parseAnalog)
            BatSysCodeList = Field('可充电储能子系统编码列表',payload[29:])
            return [gbtime,flownum,ICCID,BatSysCnt,BatSysCodeLen,BatSysCodeList]
        super(PayloadLogin,self).__init__('Login',payload,convertfunc=convert)
        keys = 'gbtime,flownum,ICCID,BatSysCnt,BatSysCodeLen,BatSysCodeList'.split(',')
        for i in range(len(keys)):
            exec('self.{0}=self.phy[{1}]'.format(keys[i],i))

class PayloadLogout(Field):
    def __init__(self, payload:bytes):
        #print(header[2])
        def convert(payload:bytes):
            gbtime = Field('采集时间',payload[:6],parseGBTime)
            flownum = Field('登出流水号',payload[6:8],parseAnalog)
            return [gbtime,flownum]
        super(PayloadLogout,self).__init__('Logout',payload,convertfunc=convert)
        keys = 'gbtime,flownum'.split(',')
        for i in range(len(keys)):
            exec('self.{0}=self.phy[{1}]'.format(keys[i],i))


class GBData_01(Field):
    VehicleStatusDct = {
        b'\x01':'启动',
        b'\x02':'熄火',
        b'\x03':'其他',
        b'\xFE':'异常',
        b'\xFF':'无效'
    }

    ChargingStatusDct = {
        b'\x01':'停车充电',
        b'\x02':'行驶充电',
        b'\x03':'未充电',
        b'\x04':'充电完成',
        b'\xFE':'异常',
        b'\xFF':'无效'
        }

    OperatingStatusDct = {
        b'\x01':'纯电',
        b'\x02':'混动',
        b'\x03':'燃油',
        b'\xFE':'异常',
        b'\xFF':'无效'
    }

    DCDCStatusDct = {
        b'\x01':'工作',
        b'\x02':'断开',
        b'\xFE':'异常',
        b'\xFF':'无效'
    }

    Names = ['车辆状态','充电状态','运行模式','车速','累计里程','总电压','总电流','SOC','DCDC状态','挡位','绝缘电阻','加速踏板行程值','刹车状态']
    Lengths = [1,1,1,2,4,2,2,1,1,1,2,1,1]
    Handlers = 'parseVehicleStatus,parseChargingStatus,parseOperatingStatus,parseVehicleSpeed,parseOdometer,parseTotalVoltage,parseTotalCurrent,parseSOC,parseDCDCStatus,parseShift,parseResistence,parseACCPosition,parseBrakePosition'.split(',')
    # Popertys = 
    def __init__(self, raw:bytes):
        if xDEBUG:
            print('GBData_01 raw=',raw.hex())

        def convert(raw:bytes):
            fields = []
            sum = 0
            for i in range(len(GBData_01.Names)):
                name = GBData_01.Names[i]
                cfunc = eval('GBData_01.'+GBData_01.Handlers[i])
                fields.append(Field(name,raw[sum:sum+GBData_01.Lengths[i]],convertfunc=cfunc))
                if xDEBUG:
                    print('convert',name,'\t',raw[sum:sum+GBData_01.Lengths[i]].hex())
                sum +=GBData_01.Lengths[i]

            return fields
        super(GBData_01,self).__init__('01 整车数据',raw,convertfunc=convert)

        # keys = 'gbtime,flownum'.split(',')
        # for i in range(len(keys)):
        #     exec('self.{0}=self.phy[{1}]'.format(keys[i],i))
        #  
    @staticmethod      
    def parseVehicleStatus(raw:bytes):
        return parseByDct(raw,GBData_01.VehicleStatusDct)
    @staticmethod
    def parseChargingStatus(raw):
        return parseByDct(raw,GBData_01.ChargingStatusDct)
    @staticmethod
    def parseOperatingStatus(raw):
        return parseByDct(raw,GBData_01.OperatingStatusDct)
    @staticmethod    
    def parseVehicleSpeed(raw):
        value = int.from_bytes(raw,'big')*0.1
        unit = 'km/h'
        data = str(value) +'  '+unit
        return data
    @staticmethod    
    def parseOdometer(raw):
        value = int.from_bytes(raw,'big')*0.1
        unit = 'km'
        data = str(value) +'  '+unit
        return data
    @staticmethod    
    def parseTotalVoltage(raw):
        value = int.from_bytes(raw,'big')*0.1
        unit = 'V'
        data = str(value) +'  '+unit
        return data
    @staticmethod    
    def parseTotalCurrent(raw):
        value = int.from_bytes(raw,'big')*0.1-1000
        unit = 'A'
        data = str(value) +'  '+unit
        return data
    @staticmethod    
    def parseSOC(raw):
        value = int.from_bytes(raw,'big')
        unit = '%'
        data = str(value) +'  '+unit
        return data

    @staticmethod    
    def parseDCDCStatus(raw):
        return parseByDct(raw,GBData_01.DCDCStatusDct)

    @staticmethod
    def parseShift(raw):
        
        value = int.from_bytes(raw,'big')
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
            
        return ','.join([shift,brake,acc])

    @staticmethod    
    def parseResistence(raw):
        value = int.from_bytes(raw,'big')
        unit = 'kOu'
        data = str(value) +'  '+unit
        return data

    @staticmethod    
    def parseACCPosition(raw):
        value = int.from_bytes(raw,'big')
        unit = '%'
        data = str(value) +'  '+unit
        return data

    @staticmethod
    def parseBrakePosition(raw):
        value = int.from_bytes(raw,'big')
        unit = '%'
        data = str(value) +'  '+unit
        return data
class GBData_02(Field):
    Names = ['驱动电机数量','驱动电机总成信息列表']
    Lengths = [1,-1]
    MotorInfoNames = '序号,状态,控制器温度,转速,转矩,温度,控制器输入电压,控制器直流母线电流'.split(',')
    MotorInfoLengths = [1,1,1,2,2,1,2,2]
    MotorInfoHandlers = 'MotorNum,MotorStatus,ControllerTemp,MotorSpeed,MotorTorque,MotorTemp,ControllerInputVoltage,ControllerCurrent'.split(',')
    MotorStatus = {
    b'\x01':'耗电',
    b'\x02':'发电',
    b'\x03':'关闭',
    b'\x04':'准备',
    b'\xFE':'异常',
    b'\xFF':'无效'
    }

    def __init__(self, raw:bytes):
        if xDEBUG:
            print('GBData_02 raw=',raw.hex())

        super(GBData_02,self).__init__('02 驱动电机数据',raw,convertfunc=GBData_02.parse)


    @staticmethod
    def parseMotorNum(raw:bytes):
        return '%02d'%int.from_bytes(raw,'big')

    @staticmethod
    def parseMotorStatus(raw:bytes):
        return parseByDct(raw,GBData_02.MotorStatus)

    @staticmethod    
    def parseControllerTemp(raw:bytes):
        return parseAnalog(raw,1,-40,'degC')

    @staticmethod   
    def parseMotorSpeed(raw:bytes):
        return parseAnalog(raw,1,-20000,'r/min')

    @staticmethod    
    def parseMotorTorque(raw:bytes):
        return parseAnalog(raw,0.1,-2000,'N*m')

    @staticmethod    
    def parseMotorTemp(raw:bytes):
        return parseAnalog(raw,1,-40,'degC')

    @staticmethod    
    def parseControllerInputVoltage(raw:bytes):
        return parseAnalog(raw,0.1,0,'V')

    @staticmethod
    def parseControllerCurrent(raw:bytes):
        return parseAnalog(raw,0.1,-1000,'A')

    @staticmethod
    def parseMotorInfo(raw:bytes):
        fields = []
        for name,length,handler in zip(GBData_02.MotorInfoNames,GBData_02.MotorInfoLengths,GBData_02.MotorInfoHandlers):
            cfunc = eval('GBData_02.parse'+handler)
            fields.append(Field(name,raw[:length],convertfunc=cfunc))
            raw = raw[length:]
        if xDEBUG:
            print('Parse Motor info...')
            for f in fields:
                print(f.name,'\t',f.phy)

        return fields

    @staticmethod
    def parse(raw:bytes):
        fields = []
        if xDEBUG:
            print('cmd02='+raw.hex())

        motorinfolength = sum(GBData_02.MotorInfoLengths)
        motorCnt = Field('电机数量',raw[0])
        cnt = int.from_bytes(motorCnt.raw,'big')      
        fields.append(motorCnt)
        raw = raw[1:]
        cnt = int.from_bytes(motorCnt.raw,'big')
        for i in range(cnt):
            motorInfos = Field('驱动电机 %02d'%(i+1),raw[:motorinfolength],convertfunc=GBData_02.parseMotorInfo)       
            fields.append(motorInfos)
            raw = raw[motorinfolength:]
      
        return fields

class GBData_05(Field):

    Names = ['定位状态','经度','纬度']
    Lengths = [1,4,4]
    Handlers = 'parseLocatingStatus,parseLatitudeLongitude,parseLatitudeLongitude'.split(',')

    LocatingStatus_Validation = {
        0 : '有效',
        1 : '无效'
    }

    LocatingStatus_Latitude = {
        0 : '北纬',
        1 : '南纬'
    }

    LocatingStatus_Longitude = {
        0 : '东经',
        1 : '西经'
    }

    def __init__(self, raw:bytes):
        if xDEBUG:
            print('GBData_05 raw=',raw.hex())

        def convert(raw:bytes):
            fields = []
            for name,length,handler in zip(GBData_05.Names,GBData_05.Lengths,GBData_05.Handlers):
                data = raw[:length]
                raw = raw[length:]
                cfunc = eval('GBData_05.'+handler)
                fields.append(Field(name,data,cfunc))

            if xDEBUG:
                for f in fields:
                    print(f.name,f.phy)
            return fields
        super(GBData_05,self).__init__('05 定位数据',raw,convertfunc=convert)

    
    @staticmethod
    def parseLocatingStatus(raw:bytes):
        if type(raw)==int:
            value = raw
        else:
            value = int.from_bytes(raw,'big')
        validationMask = 0x1
        latitudeMask = 0x2
        longitudeMask = 0x4
        validation = GBData_05.LocatingStatus_Validation[value & validationMask]
        latitude = GBData_05.LocatingStatus_Latitude[value & latitudeMask]
        longitude = GBData_05.LocatingStatus_Longitude[value & longitudeMask]
        result = ','.join([validation,latitude,longitude])
       
        return result
    
    @staticmethod
    def parseLatitudeLongitude(raw:bytes):
        value = int.from_bytes(raw,'big')/1000000
        return str(value)+' degC'

class GBData_06(Field):
    Names = ['最高电压单体:系统号','最高电压单体:序号','最高电压单体:电压值','最低电压单体:系统号','最低电压单体:序号','最低电压单体:电压值',\
    '最高温度探针:系统号','最高温度探针:序号','最高温度探针:温度值','最低温度探针:系统号','最低温度探针:序号','最低温度探针:温度值']
    
    Lengths = [1,1,2,1,1,2,1,1,1,1,1,1]
    Handlers = 'parseNum,parseNum,parseCellVoltage'.split(',')*2 + 'parseNum,parseNum,parseProbeTemp'.split(',')*2
    def __init__(self, raw:bytes):
        if xDEBUG:
            print('GBData_06 raw=',raw.hex())

        def convert(raw:bytes):
            fields = []
            for name,length,handler in zip(GBData_06.Names,GBData_06.Lengths,GBData_06.Handlers):
                data = raw[:length]
                raw = raw[length:]
                cfunc = eval('GBData_06.'+handler)
                fields.append(Field(name,data,cfunc))

            if xDEBUG:
                for f in fields:
                    print(f.name,f.phy)
            return fields
        super(GBData_06,self).__init__('06 极值数据',raw,convertfunc=convert)

    @staticmethod
    def parseNum(raw:bytes):
        return parseAnalog(raw)

    @staticmethod
    def parseCellVoltage(raw:bytes):
        return parseAnalog(raw,0.001,0,'V')

    @staticmethod
    def parseProbeTemp(raw:bytes):
        return parseAnalog(raw,1,-40,'degC')

class GBData_07(Field):
    Names= ['最高报警等级','报警标志位','可充电储能装置故障总数','可充电储能装置故障代码表','驱动电机故障总数','驱动电机故障代码表','发动机故障总数','发送机故障列表','其他故障总数','其他故障代码列表']
    Lengths=[1,4,1,-1,1,-1,1,-1,1,-1]
    Handlers='parseMaxAlertLevel,parseAlertFlag'.split(',')+'parseCounts,parseCodeList'.split(',')*4
    def __init__(self, raw:bytes):
        if xDEBUG:
            print('GBData_07 raw=',raw.hex())

        def convert(raw:bytes):
            fields = []
            position = 0
            for name,length,handler in zip(GBData_07.Names,GBData_07.Lengths,GBData_07.Handlers):
                if length == -1: #-1表示长度可变
                    length = int.from_bytes(fields[-1].raw,'big')  #长度由上一个字段表示          
                data = raw[position:position+length]
                position = position + length
                cfunc = eval('GBData_07.'+handler)
                fields.append(Field(name,data,cfunc))

            if xDEBUG:
                for f in fields:
                    print(f.name,f.phy)
            return fields
        super(GBData_07,self).__init__('07 报警数据',raw,convertfunc=convert)

    @staticmethod
    def parseMaxAlertLevel(raw:bytes):
        return parseAnalog(raw)

    @staticmethod
    def parseAlertFlag(raw:bytes):

        value = int.from_bytes(raw,'big')
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

        if len(flagstr)==0:
            flagstr = '无故障'

        return flagstr+';'+reserved     

    @staticmethod
    def parseCounts(raw:bytes):
        return parseAnalog(raw)

    @staticmethod
    def parseCodeList(raw:bytes):
        return 'raw:'+raw.hex()

class GBData_08(Field):
    Names= ['可充电储能子系统个数','电压信息列表']
    Lengths=[1,-1]
    Handlers='parseEnergyStorageSysCnt,parseEnergyStorageVoltageInfoList'.split(',')
    def __init__(self, raw:bytes):
        if xDEBUG:
            print('GBData_08 raw=',raw.hex())

        def convert(raw:bytes):
            fields = []
            for name,length,handler in zip(GBData_08.Names,GBData_08.Lengths,GBData_08.Handlers):
                cfunc = eval('GBData_08.'+handler)
                if length==-1:
                    data = raw
                    fields = fields+cfunc(int.from_bytes(fields[-1].raw,'big'),data)
                else:
                    data = raw[:length]
                    raw = raw[length:]                    
                    fields.append(Field(name,data,cfunc))
            return fields

        super(GBData_08,self).__init__('08 电压数据',raw,convertfunc=convert)

    @staticmethod
    def parseEnergyStorageSysCnt(raw:bytes):
        return parseAnalog(raw)

    @staticmethod
    def parseSysVoltage(raw:bytes):
        return parseAnalog(raw,0.1,0,'V')

    @staticmethod
    def parseSysCurrent(raw:bytes):
        return parseAnalog(raw,0.1,-1000,'A') 

    @staticmethod
    def parseCellVoltage(raw:bytes):
        return parseAnalog(raw,1,0,'mV')

    @staticmethod        
    def parseEnergyStorageVoltageInfo(raw):
        
        sysNum = Field('系统编号',raw[0:1],convertfunc=parseAnalog)
        sysVoltage = Field('系统电压',raw[1:3],convertfunc=GBData_08.parseSysVoltage)
        sysCurrent = Field('系统电流',raw[3:5],convertfunc=GBData_08.parseSysCurrent)
        cellTotalCnt = Field('单体总数',raw[5:7],convertfunc=parseAnalog)
        cellThisStartIndex = Field('本帧启始号:',raw[7:9],convertfunc=parseAnalog)
        
        cellThisCntText = Field('本帧数量',raw[9:10],convertfunc=parseAnalog)
        cellVoltageList = GBData_08.parseCellVoltageList(raw[10:])
        fields =[sysNum, sysVoltage, sysCurrent, cellTotalCnt, cellThisStartIndex, cellThisCntText]+cellVoltageList
        
        if xDEBUG:
            print('Parse Cell Voltage info...')
            for f in fields:
                print(f.name,'\t',f.phy)

        return fields

    @staticmethod  
    def parseCellVoltageList(raw:bytes):
        fields = []  
        for i in range(len(raw)//2):
            fields.append(Field('No.'+str(i+1),raw[0:2],GBData_08.parseCellVoltage))
            raw = raw[2:]        
        return fields

    @staticmethod        
    def parseEnergyStorageVoltageInfoList(sysCnt,raw):
        fields =[]        
        for i in range(sysCnt):
            cellThisCnt = int.from_bytes(raw[9:10],'big')
            length = 10+2*cellThisCnt
            data = raw[:length]
            raw = raw[length:]
            fields.append(Field('可充电储能子系统序号 %02d'%(i+1),data,GBData_08.parseEnergyStorageVoltageInfo))
        return fields

class GBData_09(Field):
    Names= ['可充电储能子系统个数','温度信息列表']
    Lengths=[1,-1]
    Handlers='parseEnergyStorageSysCnt,parseEnergyStorageTempInfoList'.split(',')
    def __init__(self, raw:bytes):
        if xDEBUG:
            print('GBData_09 raw=',raw.hex())

        def convert(raw:bytes):
            fields = []
            for name,length,handler in zip(GBData_09.Names,GBData_09.Lengths,GBData_09.Handlers):
                cfunc = eval('GBData_09.'+handler)
                if length==-1:
                    data = raw
                    fields = fields+cfunc(int.from_bytes(fields[-1].raw,'big'),data)
                else:
                    data = raw[:length]
                    raw = raw[length:]                    
                    fields.append(Field(name,data,cfunc))
            return fields
        super(GBData_09,self).__init__('09 温度数据',raw,convertfunc=convert)

    @staticmethod
    def parseEnergyStorageSysCnt(raw:bytes):
        return parseAnalog(raw)

    @staticmethod
    def parseEnergyStorageTempInfoList(sysCnt:int,raw:bytes):
        fields =[]        
        for i in range(sysCnt):
            probeThisCnt = int.from_bytes(raw[1:3],'big')
            length = 3+probeThisCnt
            data = raw[:length]
            raw = raw[length:]
            fields.append(Field('子系统序号 %02d'%(i+1),data,GBData_09.parseEnergyStorageTempInfo))        
        return fields    

    @staticmethod
    def parseEnergyStorageTempInfo(raw:bytes):
        sysNum = Field('系统编号',raw[0:1],convertfunc=parseAnalog)
        probeCnt = Field('探针个数',raw[1:3],convertfunc=parseAnalog)
        probeTempList = GBData_09.parseProbeTempList(raw[3:])
        fields = [sysNum,probeCnt]+probeTempList

        if xDEBUG:
            print('Parse Probe Temp info...')
            for f in fields:
                print(f.name,'\t',f.phy)

        return fields



    @staticmethod
    def parseProbeTempList(raw:bytes):
        fields = []  
        for i in range(len(raw)):
            fields.append(Field('No.'+str(i+1),raw[0:1],GBData_09.parseProbeTemp))
            raw = raw[1:]        
        return fields 

    @staticmethod
    def parseProbeTemp(raw:bytes):
        return parseAnalog(raw,1,-40,'degC')

class PayloadData(Field):
    def __init__(self, raw:bytes):
        def convert(raw:bytes):
            fields = []
            gbtime = Field('采集时间',raw[:6],convertfunc=parseGBTime)
            raw = raw[6:]
            fields.append(gbtime)
            while len(raw)>0:
                cat,catdata,raw = splitData(raw)
                try:
                    fields.append(eval('GBData_%(cat)02d(catdata)'%{'cat':cat}))
                except NameError:
                    if xDEBUG:
                        print('Need to implenment parseHandler for ','GBData_%(cat)02d(catdata)'%{'cat':cat})
            return fields
        super(PayloadData,self).__init__('采集数据',raw,convertfunc=convert)
        # keys = 'cmd,resflg,VIN,secretflg,length'.split(',')
        # for i in range(len(keys)):
        #     exec('self.{0}=self.phy[{1}]'.format(keys[i],i))
    def split(self):
        pass

class OTAGBData(Field):
    def __init__(self, msg:bytes):
        '''
        接收字节流数据作为初始化OTAGB消息的参数，对消息进行初始化
        生成消息的树形结构{'name00':[{'name10':value01},{'name11':value11},...]}
        '''
        def convert(msg:bytes):
            head = Head(msg[:24])
            chk = Field('校验字节',msg[-1])
            try:
                cls = eval('Payload'+OTAGBData.parsePayloadType(head.cmd.raw))
                payload = cls(msg[24:-1])
                pass
            except NameError as e:
                # print(e)
                # print('This msg should be heartbeat')
                payload = None         
            return [head,payload,chk]

        super(OTAGBData,self).__init__('GBT32960',msg,convertfunc=convert)
        
        self.head = self.phy[0]
        self.payload = self.phy[1]
        self.CRC = self.phy[2]
        self.name = CMD[self.head.cmd.raw]

        # if self.detectMsgFormat(msg):
    @staticmethod
    def parsePayloadType(cmd:bytes):
        if cmd in {b'\x02',b'\x03'}:
            result = 'Data'
        elif b'\x01'==cmd:
            result = 'Login'
        elif b'\x04'==cmd:
            result = 'Logout'
        elif b'\x07'==cmd:
            result = 'Heartbeat'
        return result

    def detectMsgFormat(self, msg:bytes)->bool:
        '''
        检测数据是否符合规范，True符合规范，False不符合规范
        '''
        pass
        return True

def traverseFieldTree(ftree:Field,dojob:'function'=print):
        if isinstance(ftree.phy,list):
            for subftree in ftree.phy:
                traverseFieldTree(subftree,dojob)
        else:
            dojob(ftree.phy)


if __name__ == '__main__':

    msg1 = '232301FE4C4D47464531473030303030303053593101001E1205100B0B30000138393836303631363031303035343538373630310100EC'
    gblogin = OTAGBData(bytes.fromhex(msg1))

    # msg2 = b'##\x04\xFELXVJ2GFC2GA030003\x01\x00\x08\x11\x11\x11\x11\x11\x11\x33\x33\x33'
    # gblogout = OTAGBData(msg2)

    # msg3 = '232302FE4C4D47464531473030303030303053593101013512051005223101020301FFFF00000000000007D00002000000FF0002010103000FA043F800000013880501000000000000000006010100000101000001010001010007000000000000000000080101000007D0006000016000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000009010100180000000000000000000000000000000000000000000000008F'
    # gbdata = OTAGBData(bytes.fromhex(msg3))
    
    # msg4 ='232302FE4C58564A3247464332474130323939383401014111091A0F1516010103010000000001220FA0272463010F0870000002020104494E204E20450FAA27060204494E204E16450FB427100501000000000000000006010810540101104001023F01013E070000000000000000000801010FA02724006000016010401040104010401040104010401054104010401040104010401040104010401040104010401040104010401040104010401040104010401040104010401040104010401040104010401040104010401040104010401054104010401040104010401040104010401040104010401040104010401040104010401040104010401040104010401040104010401040104010401040104010541040104010401040104010401040104010541040104010401040104010541040104010401040105409010100183E3F3E3E3E3E3E3F3F3F3F3E3E3F3F3F3F3F3F3E3E3E3E3FFA'
    msg4 =''.join('23 23 02 FE 4C 4D 47 46 45 31 47 30 30 30 30 30 30 30 53 59 31 01 01 41 12 0B 13 11 1A 23 01 02 03 01 FF FF 00 00 00 00 00 00 07 D0 00 02 00 00 00 FF 00 02 02 01 03 00 0F A0 43 F8 00 00 00 13 88 02 03 00 0F A0 43 F8 00 00 00 13 88 05 01 00 00 00 00 00 00 00 00 06 01 01 00 00 01 01 00 00 01 01 00 01 01 00 07 00 00 00 00 00 00 00 00 00 08 01 01 00 00 07 D0 00 60 00 01 60 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 09 01 01 00 18 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 45'.split())
    gbdata = OTAGBData(bytes.fromhex(msg4))
    gbdata.printself()
    pass

   
    tmp = bytes.fromhex(msg1)[2:-1]
    print(tmp)
    
    chk = calBCCChk(tmp)
    print('chk=',chk.hex())

    print('gbtime=',parseGBTime((genGBTime())))

    print(createOTAGBMsg(b'\x01', b'\xFE', 'LXVJ2GFC2GA030003', 1, 7, genGBTime() ))

    print(createOTAGBMsg(b'\x07', b'\x01', 'LXVJ2GFC2GA030003', 1, 0, b''))