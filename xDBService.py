#!/usr/bin/env python3
# -*- coding: utf8 -*-
# bluphy@163.com
# 2018-7-20 11:50:55 by xw: new created.


import psycopg2,time

def connectdb(dbname,dbusername,dbpassword,dbhost='127.0.0.1',dbport=5432):
    conn = psycopg2.connect('dbname={dbname} user={dbusername} password={dbpassword} host={dbhost} port={dbport}'.format_map(vars()))
    cur = conn.cursor()
    return {'connection':conn,'cursor':cur}
def parseGBPkgs_bytes(raw:bytes):
    # raw = raw.strip()
    dct = {}
    dct['head'] = raw[:2]
    dct['cmd'] = raw[2:3]
    dct['ack'] = raw[3:4]
    dct['VIN'] = raw[4:21].decode('ascii')
    dct['encrypt'] = raw[21:22]
    dct['length'] = int.from_bytes(raw[22:24], byteorder='big')
    dct['msgtime'] = raw[24:30]
    dct['data'] = raw[30:-1]
    dct['check'] = raw[-1:]
    return dct

def checkmsg(raw:bytes):
    return 0

def writedb(raw:bytes, systime, direction, dbhdl):
    '''
    systime use ms
    direction definition:
    0:tbox to tsp gb public
    1:tsp gb public to tbox
    2:tsp private to tsp gb public
    3:tsp gb public to tsp private
    '''
    conn = dbhdl['connection']
    cur = dbhdl['cursor']
    dct = parseGBPkgs_bytes(raw)
    #print(dct)
    vin = dct['VIN']
    msgtime = dct['msgtime']
    systime = systime
    cmd = dct['cmd']
    # direction = direction
    encryption = dct['encrypt']
    check = dct['check']
    msglen = dct['length'] 
    errorcode = checkmsg(raw) 
    # raw = raw
    cur.execute("INSERT INTO gbt32960 (vin, msgtime, systime, cmd, \
    direction, encryption, errorcode, msglen, rawmsg, checkbyte) \
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);",\
    (vin, msgtime, systime, cmd, direction, encryption, errorcode, msglen, raw, check))
    conn.commit()

if __name__ == '__main__':
    loginmsg = bytes.fromhex('232301FE4C58564433473242364A4130303032303501001E12041B09281F000438393836303631373031303030313335313335370100E7')
    logoutmsg = b'##\x01\xFELXVJ2GFC2GA030003\x04\x00\x08\x11\x11\x11\x11\x11\x11\x33\x33\x33'

    dbhdl = connectdb('bw_GBDirect_db','bw_tester_admin', '123456','192.168.1.69',5432)
    conn = dbhdl['connection']
    cur = dbhdl['cursor']
    writedb(logoutmsg,time.time(),0,dbhdl)

    cur.execute("SELECT * FROM gbt32960;")
    for record in cur:
        print(record)
    cur.close()
    conn.close()
    