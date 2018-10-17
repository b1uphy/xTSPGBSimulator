#!/usr/bin/env python3
# -*- coding: utf8 -*-
# bluphy@163.com
# 2018-08-30 10:35:03 by xw: new created.


#### BEGIN Calibration
OPTIONS = {
	'server': 'http://192.168.1.19:8080',
	}
USERNAME = 'Test1'
PASSWORD = '123456'
CUSTOMFIELDMAP = {
    'IMEI':'customfield_10802',
    'IMSI':'customfield_10803',
    'ICCID':'customfield_10804',
    'PhoneNum':'customfield_10805',  
    'VIN':'customfield_10806',
    'S/N':'customfield_10807',
    'TUKEY':'customfield_10810',
    'RSKEY':'customfield_10811',
    }

#### ##END Calibration


gVhlinfo = {
    'imei':'867808022358814',
    'VIN': '12345678901234567',
    'TUKEY' : '5A3756216A2649754E512576572B4733'
}

def generateTUKEY(imei:str)->str:
    '''
    To Be Update
    '''
    pass
    tukey = '5A3756216A2649754E512576572B4733'
    return tukey
   
def setDUTInfo(imei:str,info:str,value:str):

    return 0

def getDUTInfo(imei:str)->dict:
    '''
    通过DUT的IMEI值获取DUT相关信息,相关字段参考 CUSTOMFIELDMAP 定义的键
    '''
    global gVhlinfo

    return gVhlinfo

def getDUTInfoByVIN(vin:str)->dict:
    '''
    通过DUT的VIN值获取DUT相关信息的字典,相关字段参考 CUSTOMFIELDMAP 定义的键
    '''
    global gVhlinfo

    return gVhlinfo

