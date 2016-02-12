import requests
import random
import pytest
import json
import time


@pytest.fixture
def user():
    return {
        "name": "João da Silva",
        "email": "joao{}@silva{}.org".format(
            random.randint(0, 9999),
            random.randint(0, 9999),
        ),
        "password": "hunter2",
        "phones": [
            {
                "number": "987654321",
                "ddd": "21"
            }
        ]
    }


def test_user_creation(user):
    req = requests.post(
        'http://localhost:8888/user/',
        json.dumps(user),
        headers={'Content-Type': 'application/json'}
    )
    # Validate the status_code
    assert req.status_code == 201

    # assert if the output is equal the input
    user_created = json.loads(req.content.decode())
    for key, value in user.items():
        if key not in ('password', 'salt'):
            assert user_created[key] == value

    # assert if token is created
    assert 'token' in user_created


def test_user_validate_email(user):
    del user['email']

    req = requests.post(
        'http://localhost:8888/user/',
        json.dumps(user),
        headers={'Content-Type': 'application/json'}
    )

    assert req.status_code == 400


def test_user_validate_password(user):
    del user['password']

    req = requests.post(
        'http://localhost:8888/user/',
        json.dumps(user),
        headers={'Content-Type': 'application/json'}
    )

    assert req.status_code == 400


def test_login(user):
    # Create an user
    req_create = requests.post(
        'http://localhost:8888/user/',
        json.dumps(user),
        headers={'Content-Type': 'application/json'}
    )
    created = json.loads(req_create.content.decode())

    login = {
        'email': user['email'],
        'password': user['password']
    }

    req_login = requests.post(
        'http://localhost:8888/login/',
        json.dumps(login),
        headers={'Content-Type': 'application/json'}
    )
    logged = json.loads(req_login.content.decode())

    assert req_login.status_code == 200

    # Check if last_login and token are updated
    assert created['token'] != logged['token']
    assert created['last_login'] != logged['last_login']


def test_profile(user):
    # Create an user
    req_create = requests.post(
        'http://localhost:8888/user/',
        json.dumps(user),
        headers={'Content-Type': 'application/json'}
    )
    created = json.loads(req_create.content.decode())

    # Get Profile
    req_profile = requests.get(
        'http://localhost:8888/user/{}/'.format(created['_id']),
        headers={
            'Content-Type': 'application/json',
            'token': created['token']
        }
    )

    assert req_profile.status_code == 200


def test_profile_blank_token(user):
    # Create an user
    req_create = requests.post(
        'http://localhost:8888/user/',
        json.dumps(user),
        headers={'Content-Type': 'application/json'}
    )
    created = json.loads(req_create.content.decode())

    # Get Profile
    req_profile = requests.get(
        'http://localhost:8888/user/{}/'.format(created['_id']),
        headers={
            'Content-Type': 'application/json',
        }
    )

    assert req_profile.status_code == 403


def test_profile_expired_token(user):
    # Create an user
    req_create = requests.post(
        'http://localhost:8888/user/',
        json.dumps(user),
        headers={'Content-Type': 'application/json'}
    )
    created = json.loads(req_create.content.decode())

    # Wait from token expires
    time.sleep(11)

    # Get Profile
    req_profile = requests.get(
        'http://localhost:8888/user/{}/'.format(created['_id']),
        headers={
            'Content-Type': 'application/json',
            'token': created['token']
        }
    )

    assert req_profile.status_code == 403


def test_update_profile(user):
    # Create an user
    req_create = requests.post(
        'http://localhost:8888/user/',
        json.dumps(user),
        headers={'Content-Type': 'application/json'}
    )
    created = json.loads(req_create.content.decode())

    # Get Profile
    req_update_profile = requests.put(
        'http://localhost:8888/user/{}/'.format(created['_id']),
        json.dumps({'name': 'José da Silva'}),
        headers={
            'Content-Type': 'application/json',
            'token': created['token']
        }
    )

    assert req_update_profile.status_code == 200
