import asyncio,logging
import aiomysql
__author__ = 'jacktrane'
@asyncio.coroutine
def creat_pool(loop, **kw):
  logging.info('creat database connection pool...')
  global __pool
  __pool = yield from aiomysql.create_pool(
    host = kw.get('host','127.0.0.1'),
    port = kw.get('port', 3306),
    user = kw['user'],
    password = kw['password'],
    db = kw['db'],
    charset = kw.get('charset', 'utf8'),
    autocommit = kw.get('autocommit', True),
    maxsize = kw.get('maxsize', 10),
    minsize = kw.get('minsize', 1),
    loop = loop
  )
#select 所用的
@asyncio.coroutine
def select(sql, args, size=None):
  log(sql, args)
  global __pool
  with (yield from __pool) as conn:
    cur = yield from conn.cursor(aiomysql.DictCursor)
    yield from cur.execute(sql.replace('?', '%s'), args or ())
    if size:
      rs = yield from cur.fetchmany(size)
    else:
      rs = yield from cur.fetchall()
    yield from cur.close()
    logging.info('rows returned: %s' % len(rs))
    return rs

#这是各种insert、update、delete
@asyncio.coroutine
def execute(sql, args):
  log(sql)
  with (yield from __pool) as conn:
    try:
      cur = yield from conn.cursor()
      yield from cur.execute(sql.replace('?', '%s'), args)
      affected = cur.rowcount
      yield from cur.close()
    except BaseException as e:
      raise
    return affected
#model的元类
class ModelMetalclass(type):
  def __new__(cls, name, bases, attrs):
    #排除Model类本身
    if name == 'Model':
      return type.__new__(cls, name, bases, attrs)
    #获取table名字
    tableName = attrs.get('__table__', None) or name
    logging.info('found model: %s (table: %s)' % (name, tableName))
    
    #获取所有的field和主键名
    mappings = dict()
    fields = []
    primaryKey = None
    for k,v in attrs.items():
      if isinstance(v, Field):
        logging.info('  found mapping:%s ==> %s' % (k, v))
        mappings[k] = v
        if v.primaryKey:
          #主键
          if primaryKey:
            raise RuntimeError('Duplicate primary key for field: %s' % k)
          primaryKey = k
        else:
          fields.append(k)
    if not primaryKey:
      raise RuntimeError('Primary key not found.')
    for k in mappings.keys():
      attrs.pop(k)
    escaped_fields = list(map(lambda f: '`%s`' % f, fields))
    attrs['__mappings__'] = mappings # 保持属性和列的映射关系
    attrs['__table__'] = tableName
    attrs['__primary_key__'] = primaryKey
    attrs['__fields__'] = fields #除了主键外的属性
    attrs['__select__'] = 'SELECT `%s`, %s FROM `%s`' % (primaryKey, ','.join)
