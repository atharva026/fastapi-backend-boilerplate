import asyncio
import getpass
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.security import get_password_hash
from src.app.models.user import User, UserType
from src.app.core.database import on_startup, on_shutdown, get_db

# Pydantic Schemas
class AdminBase(BaseModel):
    name: str
    email: EmailStr


class AdminCreate(AdminBase):
    password: str


class Admin(AdminBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# Database Functions
async def get_user_by_email(
    db: AsyncSession,
    email: EmailStr,
) -> Optional[User]:
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_admin(
    db: AsyncSession,
    admin: AdminCreate,
) -> User:
    db_admin = User(
        name=admin.name,
        email=admin.email,
        password_hash=get_password_hash(admin.password),
        user_type=UserType.ADMIN,
        is_verified=True,
    )

    db.add(db_admin)

    try:
        await db.commit()
        await db.refresh(db_admin)
        return db_admin
    except Exception:
        await db.rollback()
        raise


# CLI Entry Point
async def main() -> None:
    print("\n--- Create First Admin User ---\n")
    await on_startup()

    try:
        username = input("Enter name: ").strip()
        email = input("Enter email: ").strip().lower()

        password = getpass.getpass("Enter password: ")
        password_confirm = getpass.getpass("Confirm password: ")

        if password != password_confirm:
            print("Passwords do not match.")
            return

        admin_in = AdminCreate(
            name=username,
            email=email,
            password=password,
        )

        async for db in get_db():
            existing_user = await get_user_by_email(db, email)

            if existing_user:
                print(f"User '{email}' already exists.")
                return

            admin = await create_admin(db, admin_in)

        print(f"Successfully created admin user: {admin.email}")
    finally:
        await on_shutdown()

if __name__ == "__main__":
    asyncio.run(main())