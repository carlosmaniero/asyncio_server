from settings import db
import hashlib
import binascii
import asyncio
import os
import uuid
import datetime


@asyncio.coroutine
def get_password_hash(salt, password):
    dk = hashlib.pbkdf2_hmac('sha256', password, salt, 100000)
    return binascii.hexlify(dk)


@asyncio.coroutine
def generate_salt():
    return binascii.hexlify(os.urandom(16))


@asyncio.coroutine
def generate_token(user):
    token = str(uuid.uuid1())
    # If exists, remove the token from the same user
    yield from db.tokens.remove({'user': user['_id']})

    # Create a token
    yield from db.tokens.insert({
        'user': user['_id'],
        'token': token,
        'created_at': datetime.datetime.now()
    })

    return token


@asyncio.coroutine
def check_token():
    while True:
        # Remove invalid expired tokens
        lt = datetime.datetime.now() - datetime.timedelta(seconds=10)
        total = yield from db.tokens.find({'created_at': {'$lt': lt}}).count()
        if total:
            print('Removing {} tokens'.format(total))
        yield from db.tokens.remove({'created_at': {'$lt': lt}})
        yield from asyncio.sleep(1)
