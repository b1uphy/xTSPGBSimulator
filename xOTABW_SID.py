#!/usr/bin/env python3
# -*- coding: utf8 -*-
# bluphy@163.com
# 2018-08-27 15:25:51 by xw: new created

#### BEGIN Description

#### ##END Description

#### BEGIN Calibration

#### ##END Calibration

#### BEGIN Constants

#### ##END Constants

from bidict import bidict
ServiceFunction={
    'Establish Connection':{
        'service type':'Establish Connection',
        'sidtsp':'1d',
        'sidtbx':'6d',
        'subfunction':'00',
        'initiator':'tbx',
        'responder':'tsp',
        'channel':'private',
        'body': {
            'request': None,
            'presponse': None,
            'nresponse': 'NRC',
        },
    },

    'DataMining Upload, non response':{
        'service type':'DATAMining',
        'sidtsp': None,
        'sidtbx':'60',
        'subfunction':'81',
        'initiator':'tbx',
        'responder':None,
        'channel':'private',
        'body': {
            'request': None,
            'presponse': None,
            'nresponse': 'NRC',
        },
    },

}
#### BEGIN Module test
if __name__ == '__main__':
    pass

#### END Module test