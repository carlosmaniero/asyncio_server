import os
import motor.motor_asyncio

url = os.environ.get('OPENSHIFT_MONGODB_DB_URL')
host = os.environ.get('OPENSHIFT_PYTHON_IP', 'localhost')
port = os.environ.get('OPENSHIFT_PYTHON_PORT', 8000)

print(url)
client = motor.motor_asyncio.AsyncIOMotorClient(url)
db = client.register_test
