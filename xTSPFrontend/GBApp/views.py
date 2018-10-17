#!/usr/bin/env python3
# -*- coding: utf8 -*-
# bluphy@163.com
# 2018-7-16 15:15:22 by xw: new created.
from django.shortcuts import render

from django.http import HttpResponse


def index(request):
    return HttpResponse("Hello, world. You're at the polls index.")