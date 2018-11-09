#!/usr/bin/env python3
# -*- coding: utf8 -*-
# bluphy@163.com
# 2018-5-29 17:06:51 by xw: new created.
import time
from bidict import bidict
# import xTSPGBSimulator.xOTAGBT32960.GB_PARSER_HANDLER as gbp

xDEBUG = False

CMD = bidict({
    b'\x01' : '车辆登入',    
    b'\x02' : '实时数据',    
    b'\x03' : '补发数据',    
    b'\x04' : '车辆登出',    
    b'\x07' : '心跳',    
    b'\x80' : '查询命令',    
    b'\x81' : '设置命令',   
    b'\x82' : '控制命令'
    })

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

# dctGBData_02_MotorStatus = {
#     '01':'耗电',
#     '02':'发电',
#     '03':'关闭',
#     '04':'准备',
#     'FE':'异常',
#     'FF':'无效'
# }

# dctGBData_05_LocatingStatus_Validation = {
#     0 : '有效',
#     1 : '无效'
# }

# dctGBData_05_LocatingStatus_Latitude = {
#     0 : '北纬',
#     1 : '南纬'
# }

# dctGBData_05_LocatingStatus_Longitude = {
#     0 : '东经',
#     1 : '西经'
# }


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
        #print(header[2])
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
        if xDEBUG:
            print('GBData_01 raw=',raw.hex())
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
        super(GBData_02,self).__init__('02 驱动电机数据',raw,convertfunc=GBData_02.parse)
        if xDEBUG:
            print('GBData_02 raw=',raw.hex())

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
        # print('Parse Motor info...')
        fields = []
        for name,length,handler in zip(GBData_02.MotorInfoNames,GBData_02.MotorInfoLengths,GBData_02.MotorInfoHandlers):
            cfunc = eval('GBData_02.parse'+handler)
            fields.append(Field(name,raw[:length],convertfunc=cfunc))

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
        # print(motorCnt.name,'\t',cnt)        
        fields.append(motorCnt)
        raw = raw[1:]
        cnt = int.from_bytes(motorCnt.raw,'big')
        for i in range(cnt):
            # print('init parse motor info')
            motorInfos = Field('驱动电机 %02d'%(i+1),raw[:motorinfolength],convertfunc=GBData_02.parseMotorInfo)       
            fields.append(motorInfos)
            raw = raw[motorinfolength:]

            
        return fields

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
                print(e)
                print('This msg should be heartbeat')
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

if __name__ == '__main__':

    msg1 = '232301FE4C4D47464531473030303030303053593101001E1205100B0B30000138393836303631363031303035343538373630310100EC'
    gblogin = OTAGBData(bytes.fromhex(msg1))

    # msg2 = b'##\x04\xFELXVJ2GFC2GA030003\x01\x00\x08\x11\x11\x11\x11\x11\x11\x33\x33\x33'
    # gblogout = OTAGBData(msg2)

    # msg3 = '232302FE4C4D47464531473030303030303053593101013512051005223101020301FFFF00000000000007D00002000000FF0002010103000FA043F800000013880501000000000000000006010100000101000001010001010007000000000000000000080101000007D0006000016000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000009010100180000000000000000000000000000000000000000000000008F'
    # gbdata = OTAGBData(bytes.fromhex(msg3))
    
    msg4 ='232302FE4C58564A3247464332474130323939383401014111091A0F1516010103010000000001220FA0272463010F0870000002020104494E204E20450FAA27060204494E204E16450FB427100501000000000000000006010810540101104001023F01013E070000000000000000000801010FA02724006000016010401040104010401040104010401054104010401040104010401040104010401040104010401040104010401040104010401040104010401040104010401040104010401040104010401040104010401040104010401054104010401040104010401040104010401040104010401040104010401040104010401040104010401040104010401040104010401040104010401040104010541040104010401040104010401040104010541040104010401040104010541040104010401040105409010100183E3F3E3E3E3E3E3F3F3F3F3E3E3F3F3F3F3F3F3E3E3E3E3FFA'
    gbdata = OTAGBData(bytes.fromhex(msg4))
    print('gbdata payload:=',gbdata.payload.raw.hex())
    pass

   
    tmp = bytes.fromhex(msg1)[2:-1]
    print(tmp)
    
    chk = calBCCChk(tmp)
    print('chk=',chk.hex())

    print('gbtime=',parseGBTime((genGBTime())))

    print(createOTAGBMsg(b'\x01', b'\xFE', 'LXVJ2GFC2GA030003', 1, 7, genGBTime() ))

    print(createOTAGBMsg(CMD.inv['心跳'], b'\x01', 'LXVJ2GFC2GA030003', 1, 0, b''))