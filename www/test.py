import orm,asyncio
from models import User, Blog, Comment

@asyncio.coroutine
def test():
    yield from orm.create_pool(user='root', password='root', database='my_blog')

    u = User(name='Test1', email='jack@163.com', passwd='1234567890', image='about:blank')

    yield from u.save()

# for x in test():
#     pass

loop = asyncio.get_event_loop()
loop.run_until_complete(test())
loop.close()