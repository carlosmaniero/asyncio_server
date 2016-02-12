from server import App, BaseView
import utils
import asyncio
import os
import datetime
import serializers
from bson import ObjectId
from settings import db


app = App()


@app.route('/login/')
class LoginView(BaseView):
    @asyncio.coroutine
    def post(self):
        '''do the login :)'''
        email = self.request.data.get('email')
        password = self.request.data.get('password')

        user = yield from db.users.find_one({
            'email': email
        })

        if user:
            password_hash = yield from utils.get_password_hash(
                user['salt'],
                password.encode()
            )
            if user['password'] == password_hash:
                user['last_login'] = datetime.datetime.now()
                yield from db.users.save(user)

                user['token'] = yield from utils.generate_token(user)
                yield from serializers.user(user)
                self.response.set_content(user)
            else:
                self.invalid_response()
        else:
            self.invalid_response()
        yield from self.response.close()

    def invalid_response(self):
        self.response.status_code = 401
        self.response.set_content({'error': 'Login invalid'})


@app.route('/user/')
class UserView(BaseView):
    @asyncio.coroutine
    def get_user(self, email):
        ''' Get user by e-mail '''
        user = yield from db.users.find_one({'email': email})
        return user

    @asyncio.coroutine
    def validate_user(self, user):
        """ Validate user """
        email = user.get('email')
        password = user.get('password')
        has_error = False

        if email is None or len(email) < 1:
            self.response.set_content({'error': 'email is required'})
            has_error = True
        elif password is None or len(password) < 0:
            self.response.set_content({'error': 'password is required'})
            has_error = True

        if has_error:
            self.response.status_code = 400
            yield from self.response.close()
            return False

        _user = yield from self.get_user(email)

        if _user is not None:
            self.response.set_content({'error': 'User already exists'})
            yield from self.response.close()

        return True

    @asyncio.coroutine
    def post(self):
        ''' This method is called on HTTP POST'''
        user = self.request.data
        is_valid = yield from self.validate_user(user)

        if is_valid:
            user['salt'] = yield from utils.generate_salt()
            user['last_login'] = user['created'] = datetime.datetime.now()
            user['modified'] = None
            user['password'] = yield from utils.get_password_hash(
                user['salt'], user['password'].encode()
            )
            db.users.insert(user)
            yield from serializers.user(user)

            # Generate the token
            user['token'] = yield from utils.generate_token(user)

            self.response.status_code = 201
            self.response.set_content(user)
            yield from self.response.close()


@app.route('/user/{id}/')
class UserDetail(BaseView):
    @asyncio.coroutine
    def get_token(self):
        token = self.request.header.get('token')
        if token is None:
            self.response.status_code = 403
            self.response.set_content({
                'error': 'Token not found'
            })
            yield from self.response.close()
        else:
            token = yield from db.tokens.find_one({'token': token})
            if not token:
                self.response.status_code = 403
                self.response.set_content({
                    'error': 'Invalid Token'
                })
                yield from self.response.close()

        return token

    @asyncio.coroutine
    def get_user(self):
        token = yield from self.get_token()
        if token:
            _id = ObjectId(self.kwargs['id'])
            if ObjectId(token['user']) == _id:
                user = yield from db.users.find_one({
                    '_id': _id
                })
                if not user:
                    self.response.status_code = 404
                    self.response.set_content({
                        'error': 'User not found'
                    })
                    yield from self.response.close()
                return user
            else:
                self.response.status_code = 403
                self.response.set_content({
                    'error': 'Forbiden'
                })
                yield from self.response.close()

    @asyncio.coroutine
    def get(self):
        user = yield from self.get_user()

        if user:
            yield from serializers.user(user)
            self.response.set_content(user)
            yield from self.response.close()

    @asyncio.coroutine
    def put(self):
        user = yield from self.get_user()

        if user:
            data = self.request.data
            fields_to_remove = ['email', '_id', 'salt']

            for key in fields_to_remove:
                if key in data:
                    del data[key]

            user['modified'] = datetime.datetime.now()
            user.update(data)
            yield from db.users.save(user)
            yield from serializers.user(user)
            self.response.set_content(user)
            yield from self.response.close()

loop = asyncio.get_event_loop()

# start check_token
loop.call_soon(asyncio.async, utils.check_token())

# start the application
app.start(loop)
