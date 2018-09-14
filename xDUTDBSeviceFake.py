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

from jira import JIRA



# username = input('Please Input user name:')
# password = input('Please Input password:')

username = USERNAME
password = PASSWORD
auth = (username, password)
options = OPTIONS

# jira = JIRA(options,basic_auth=auth)

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
    for issue in jira.search_issues("project=TDM AND IMEI~{0}".format(imei), maxResults=1):
        field = CUSTOMFIELDMAP[info]
        try:
            issue.update(fields={field:value})
        except:
            print('ERROR: update DUT IMEI={0} {1} failed'.format(imei,info))
            return -1
    return 0

def getDUTInfo(imei:str)->dict:
    '''
    通过DUT的IMEI值获取DUT相关信息,相关字段参考 CUSTOMFIELDMAP 定义的键
    '''
    global gVhlinfo
    # print('getDUTInfo: imei=',imei)
    # result = {}
    # for issue in jira.search_issues("project=TDM AND IMEI~{0}".format(imei), maxResults=1):
    #     # print(dir(issue.fields))
    #     for field in CUSTOMFIELDMAP.keys():
    #         try:
    #             result[field] = getattr(issue.fields,CUSTOMFIELDMAP[field])
    #         except:
    #             result[field] = None
    return gVhlinfo

def getDUTInfoByVIN(vin:str)->dict:
    '''
    通过DUT的VIN值获取DUT相关信息的字典,相关字段参考 CUSTOMFIELDMAP 定义的键
    '''
    print('getDUTInfoByVIN: vin=',vin)
    result = {}
    for issue in jira.search_issues("project=TDM AND VIN~{0}".format(vin), maxResults=1):
        # print(dir(issue.fields))
        for field in CUSTOMFIELDMAP.keys():
            try:
                result[field] = getattr(issue.fields,CUSTOMFIELDMAP[field])
            except:
                result[field] = None
    return result

if __name__ == '__main__':
    '''
    module function test are following
    '''
    import time
    imeis = ['867808022358814',
    '353635080100908',
    '353635080101070',
    '353635080101138',
    '353635080127075',
    ]

    start = time.time()
    print(start)
    for imei in imeis:
        tmp = getDUTInfo(imei)
        print(tmp)
    end = time.time()
    print(end)
    duration = end - start
    print(duration)
    # print(getVehicleInfo(imei,'VIN'))

    # start = time.time()
    # print(start)
    # for i in imeis:
    #     setDUTInfo(i,'RSKEY','test')

    # end = time.time()
    # print(end)
    # duration = end - start
    # print(duration)