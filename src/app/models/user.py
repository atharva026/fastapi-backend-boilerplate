from sqlalchemy import Boolean, String, Enum as SQLAlchemyEnum, DateTime
from sqlalchemy.orm import Mapped, mapped_column 
from src.app.models.base import BaseModelWithMixins
from enum import Enum
from datetime import datetime

# from src.app.core.config import config

class UserType(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"

class User(BaseModelWithMixins):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True, comment= "Email address of the user, used for login and notifications")
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Hashed password of the user, used for authentication")  # Nullable for OAuth users
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, comment="Indicates whether the user's email has been verified")
    user_type: Mapped[UserType] = mapped_column(
        SQLAlchemyEnum(
            UserType, 
            name="enum_user_type",
            # schema=config.DB_CONFIG.db_schema,
        ),
        nullable=False,
        default=UserType.USER,                 # Python side
        server_default=UserType.USER.value,    # DB side
        comment= "Type of user, indicating their role in the system"
    )

    last_login: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=True,
        comment="User last logged in",
    )
