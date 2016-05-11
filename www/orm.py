import asyncio,logging
import aiomysql
__author__ = 'jacktrane'

def log(sql, args=()):
  logging.info('SQL: %s' % sql)

@asyncio.coroutine
def create_pool(loop=None, **kw):
  logging.info('creat database connection pool...')
  global __pool
  __pool = yield from aiomysql.create_pool(
    host = kw.get('host','127.0.0.1'),
    port = kw.get('port', 3306),
    user = kw['user'],
    password = kw['password'],
    db = kw['database'],
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

def create_args_string(num):
  L = []
  for n in range(num):
    L.append('?')
  return ', '.join(L)
#这是父属性获取
class Field(object):
 
  def __init__(self, name, column_type, primary_key, default):
    self.name = name
    self.column_type = column_type
    self.primary_key = primary_key
    self.default = default

  def __str__(self):
    return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)
#string的属性获取
class StringField(Field):
  def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
    super().__init__(name, ddl, primary_key, default)
#布尔的
class BooleanField(Field):
  def __init__(self, name=None, default=False):
    super().__init__(name, 'boolean', False, default)
#整型的
class IntegerField(Field):
  def __init__(self, name=None, primary_key=False, default=0):
    super().__init__(name, 'int', primary_key, default)
#浮点型
class FloatField(Field):
  def __init__(self, name=None, primary_key=False, default=0.0):
    super().__init__(name, 'float', primary_key, default)
#文本
class TextField(Field):
  def __init__(self, name=None, default=None):
    super().__init__(name, 'text', False, default)




#model的元类
class ModelMetaclass(type):
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
        if v.primary_key:
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
    attrs['__select__'] = 'SELECT `%s`, %s FROM `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
    attrs['__insert__'] = 'INSERT INTO `%s`(%s, `%s`) VALUES (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
    attrs['__update__'] = 'UPDATE `%s` SET %s WHERE `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
    attrs['__delete__'] = 'DELETE FROM `%s` WHERE `%s`=?' % (tableName, primaryKey)
    return type.__new__(cls, name, bases, attrs)

#Model的建立
class Model(dict, metaclass=ModelMetaclass):
  def __init__(self, **kw):
    super(Model, self).__init__(**kw)
  
  def __getattr__(self, key):
    try:
      return self[key]
    except KeyError:
      raise AttributeError('Model object has no attribute %s' % key)

  def __setattr__(self, key, value):
    self[key]  = value

  def getValue(self, key):
    return getattr(self, key, None)

  def getValueOrDefault(self, key):
    value = getattr(self, key, None)
    if value is None:
      field = self.__mappings__[key]
      if field.default is not None:
        value = field.default() if callable(field.default) else field.default
        logging.debug('using default value for %s: %s' % (key, str(value)))
        setattr(self, key, value)
    return value

  @classmethod
  @asyncio.coroutine
  def find(cls, pk):
    ' 通过主键进行查找 '
    rs = yield from select('%s WHERE `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
    if len(rs) == 0:
      return None
    return cls(**rs[0])
  
  @classmethod
  @asyncio.coroutine
  def findAll(cls, where=None, args=None, **kw):
    sql = [cls.__select__]
    if where:
      sql.append('WHERE')
      sql.append(where)
    if args is None:
      args = []
    orderBy = kw.get('orderBy', None)
    if orderBy:
      sql.append('ORDER BY')
      sql.append(orderBy)
    limit = kw.get('limit', None)
    if limit is not None:
      sql.append('LIMIT')
      if isinstance(limit, int):
        sql.append('?')
        args.append(limit)
      elif isinstance(limit, tuple) and len(limit) == 2:
        sql.append('?, ?')
        args.extend(limit)
      else:
        raise ValueError('Invalid limit value: %s' % str(limit))
    rs = yield from select(' '.join(sql), args)
    return [cls(**r) for r in rs]

  @classmethod
  @asyncio.coroutine
  def findNumber(cls, selectField, where=None, args=None):
    sql = ['SELECT %s _num_ FROM `%s`' % (selectField, cls.__table__)]
    if where:
      sql.append('WHERE')
      sql.append(where)
    rs = yield from select(' '.join(sql), args, 1)
    if len(rs) == 0:
      return None
    return rs[0]['_num_']
    
  
  @asyncio.coroutine
  def save(self):
    args = list(map(self.getValueOrDefault, self.__fields__))
    args.append(self.getValueOrDefault(self.__primary_key__))
    rows = yield from execute(self.__insert__, args)
    if rows != 1:
      logging.warn('failed ro insert record: affected rows: %s' % rows)
  
  @asyncio.coroutine
  def update(self):
    # 像time.time,next_id之类的函数在插入的时候已经调用过了,没有其他需要实时更新的值,因此调用getValue
    args = list(map(self.getValue, self.__fields__)) 
    args.append(self.getValue(self.__primary_key__))
    rows = yield from execute(self.__update__, args)
    if rows != 1:
        logging.warn("failed to update by primary key: affected rows %s" % rows)
      

  @asyncio.coroutine
  def remove(self):
    args = [self.getValue(self.__primary_key__)] # 取得主键作为参数
    rows = yield from execute(self.__delete__, args) # 调用默认的delete语句
    if rows != 1:
        logging.warn("failed to remove by primary key: affected rows %s" % rows)