import asyncio
import os
from sqlalchemy import select
from app.core.database import async_session
from app.models.user import User
from app.core.security import create_access_token, hash_password

async def get_desktop_token():
    async with async_session() as db:
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if not user:
            user = User(username="desktop_user", email="desktop@omnia.local", hashed_password=hash_password("pwd"))
            db.add(user)
            await db.commit()
            await db.refresh(user)
        
        token = create_access_token({"sub": str(user.id)})
        print(f"DESKTOP_TOKEN={token}")

if __name__ == "__main__":
    asyncio.run(get_desktop_token())
