from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings


client = AsyncIOMotorClient(settings.mongo_uri)
db = client[settings.mongo_db]


async def get_database():
    return db
