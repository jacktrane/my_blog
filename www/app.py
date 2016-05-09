#!/usr/bin/python3
#coding:utf-8
__author__ = 'jacktrane wu'

import logging; logging.basicConfig(level=logging.INFO)

import asyncio, os, json, time
from aiohttp import web
from datetime import datetime

def index(request):
  return web.Response(body=b'<h1>web app</h1>')
#初始化
@asyncio.coroutine
def init(loop):
  app = web.Application(loop=loop)
  app.router.add_route('GET', '/', index)
  srv = yield from loop.create_server(app.make_handler(), '127.0.0.1', 8000)
  logging.info('server started at http://127.0.0.1:8000...')
  return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()