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
NRC = {
    b'\x08':'headerVersionNotSupported',
    b'\x09':'IMEINotMatched',
    b'\x10':'protocolVersionNotSupported',
    b'\x11':'serviceNotSupported',
    b'\x12':'subFunctionNotSupported',
    b'\x13':'incorrectMessageLengthOrInvalidFormat',
    b'\x14':'responseTooLong',
    b'\x21':'busyRepeatRequest',
    b'\x24':'requestSequenceError',
    b'\x25':'noResponseFromCANbusComponent',
    b'\x31':'requestOutOfRange',
    b'\x32':'internalFault',
    b'\x7f':'serviceNotSupportedForThisCustomer',
    b'\x35':'invalidKey',
    b'\x54':'notReceiveKey',
    b'\x55':'invalidResponse',
    b'\x56':'invalidChallenge',
    b'\x57':'RSKeyHaveBeenTeached',
    b'\x58':'RSKeyBoundFault', 
}

#### BEGIN Module test
if __name__ == '__main__':
    pass

#### END Module test