import os
import motor.motor_asyncio

url = os.environ.get('OPENSHIFT_MONGODB_DB_URL')
client = motor.motor_asyncio.AsyncIOMotorClient(url)
db = client.register_test
