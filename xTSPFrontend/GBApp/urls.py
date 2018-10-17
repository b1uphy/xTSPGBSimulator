#!/usr/bin/env python3
# -*- coding: utf8 -*-
# bluphy@163.com
# 2018-7-16 15:15:22 by xw: new created.


from django.urls import path
from . import views
urlpatterns = [
    path('', views.index, name='index'),
]