
#!/usr/bin/python3
#coding: utf-8

__author__ = 'jacktrane'

' url handlers '

import re, time, json, logging, hashlib, base64, asyncio

from coromethod import get, post

from models import User, Comment, Blog, next_id

import hashlib
from config.config import configs
COOKIE_NAME = 'jacsession'
_COOKIE_KEY = configs.session.secret

# 计算加密cookie:
def user2cookie(user, max_age):
    # build cookie string by: id-expires-sha1
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)

# 解密cookie:
@asyncio.coroutine
def cookie2user(cookie_str):
    '''
    Parse cookie and load user if cookie is valid.
    '''
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            return None
        user = yield from User.find(uid)
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd = '******'
        return user
    except Exception as e:
        logging.exception(e)
        return None

        
# @get('/')
# @asyncio.coroutine
# def index(request):
#   users = yield from User.findAll()
#   return {
#     '__template__': '__base__.html',
#     'users': users
#   }

@get('/')
@asyncio.coroutine
def index(request):
  summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
  blogs = [
    Blog(id='1', name='Test Blog', summary=summary, created_at=time.time()-120),
    Blog(id='2', name='Something New', summary=summary, created_at=time.time()-3600),
    Blog(id='3', name='Learn Swift', summary=summary, created_at=time.time()-7200),
    Blog(id='4', name='Learn Swift', summary=summary, created_at=time.time()-10800),
    Blog(id='5', name='Learn Swift', summary=summary, created_at=time.time()-11100),
    Blog(id='6', name='Learn Swift', summary=summary, created_at=time.time()-20000),
    Blog(id='7', name='Learn Swift', summary=summary, created_at=time.time()-30000),
    Blog(id='8', name='Learn Swift', summary=summary, created_at=time.time()-40000),
    Blog(id='9', name='Learn Swift', summary=summary, created_at=time.time()-50000),
    Blog(id='10', name='Learn Swift', summary=summary, created_at=time.time()-60000),
    Blog(id='11', name='Learn Swift', summary=summary, created_at=time.time()-70000)
  ]
  # page = Page(num,page_index=page_index)
  return {
    '__template__': 'blogs.html',
    'blogs': blogs
  }

@get('/register')
def register():
  return {
    '__template__': 'register.html'
  }

_RE_EMAIL = re.compile(r'^[a-zA-Z0-9\.\-\_]+\@[a-zA-Z0-9\-\_]+(\.[a-zA-Z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[a-f0-9]{40}$')

# @get('/api/users')
# def api_get_users():
#   users = yield from User.findAll(orderBy='created_at desc')
#   for u in users:
#     u.passwd = '******'
#   return dict(users=users)

#注册用户
@post('/api/users')
def api_register_user(*, email, name, passwd):
  if not name or not name.strip():
    raise APIValueError('name')
  if not email or not _RE_EMAIL(email):
    raise APIValueError('email')
  if not passwd or not _RE_SHA1(passwd):
    raise APIValueError('passwd')
  users = yield from User.findAll('email=?', [email])
  if len(users) > 0:
    raise APIError('register: failed', 'email', 'email is already in use')
  uid = next_id()
  sha1_passwd = '%s:%s' % (uid,passwd)
  user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
  yield from user.save()
  #通过session访问
  r = web.Response()
  r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
  user.passwd = '*******'
  r.content_type = 'application/json'
  r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
  return r

#用户登录验证
@post('/api/authenticate')
def authenticate(*, email, passwd):
    if not email:
        raise APIValueError('email', 'Invalid email.')
    if not passwd:
        raise APIValueError('passwd', 'Invalid password.')
    users = yield from User.findAll('email=?', [email])
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist.')
    user = users[0]
    # check passwd:
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd', 'Invalid password.')
    # authenticate ok, set cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

