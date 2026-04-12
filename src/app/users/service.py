from typing import Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.user import User, UserType
from src.app.users.schemas import UserUpdate
from src.app.core.exceptions import (
    ForbiddenException, 
    NotFoundException, 
)

class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_email_or_raise(
        self, 
        email: str
    ) -> Optional[User]:
        """Retrieve a user by their email address or raise NotFoundException."""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)

        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundException("User not found")
        
        return user
    
    async def get_user_by_email_or_none(
        self,
        email: str
    ) -> Optional[User]:
        """Retrieve a user by their email address or return None."""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)

        return result.scalar_one_or_none()

    async def get_user_by_id_or_raise(
        self,
        user_id: uuid.UUID
    ) -> Optional[User]:
        """Retrieve a user by their ID or raise NotFoundException."""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)

        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundException("User not found")
        
        return user
    
    async def get_user_by_id_or_none(
        self, 
        user_id: uuid.UUID
    ) -> Optional[User]:
        """Retrieve a user by their ID or return None."""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)

        return result.scalar_one_or_none()

    async def create_user(
        self,
        name: str,
        email: str,
        password_hash: str,
        user_type: UserType,
        is_verified: bool = False
    ) -> User:
        """
        Create a new user with the provided data.
        
        This method does not check for existing users or hash the password - it assumes that has been done by the caller.
        """
        db_user = User(
            name=name,
            email=email,
            password_hash=password_hash,
            user_type=user_type,
            is_verified=is_verified
        )

        self.db.add(db_user)
        await self.db.flush() # get ID
        await self.db.refresh(db_user)

        return db_user
    
    async def update_user(
        self, 
        user_id: uuid.UUID, 
        current_user: User, 
        user_update: UserUpdate
    ) -> User:
        """Update a user's information."""
        user = await self.get_user_by_id_or_raise(user_id)
        
        # Only allow self-update unless admin
        if current_user.id != user_id and current_user.user_type != UserType.ADMIN:
            raise ForbiddenException("Not enough permissions")

        update_data = user_update.model_dump(exclude_unset=True)
        if not update_data:
            return user  # Nothing to update

        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)

        await self.db.flush()
        await self.db.refresh(user)
            
        return user
