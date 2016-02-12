import asyncio


@asyncio.coroutine
def user(data):
    ''' Serialize the data '''
    del data['password']
    del data['salt']
    data['_id'] = str(data['_id'])
    data['last_login'] = str(data['last_login'])
    data['created'] = str(data['created'])
    if data['modified']:
        data['modified'] = str(data['modified'])
    return data
