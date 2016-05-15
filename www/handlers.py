#!/usr/bin/python3
#coding: utf-8

__author__ = 'jacktrane'

' url handlers '

import re, time, json, logging, hashlib, base64, asyncio

from coromethod import get, post

from models import User, Comment, Blog, next_id

@get('/')
@asyncio.coroutine
def index(request):
  users = yield from User.findAll()
  return {
    '__template__': 'test.html',
    'users': users
  }