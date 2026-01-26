from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase
from src.app.mixins import TimestampMixin, UUIDPrimaryKeyMixin

NAMING_CONVENTION = {
    "all_column_names": lambda constraint, table: "_".join(
        sorted(column.name for column in constraint.columns)
    ),
    "ix": "ix__%(table_name)s__%(all_column_names)s",
    "uq": "uq__%(table_name)s__%(all_column_names)s",
    "ck": "ck__%(table_name)s__%(constraint_name)s",
    "fk": "fk__%(table_name)s__%(all_column_names)s__%(referred_table_name)s",
    "pk": "pk__%(table_name)s",
}

class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention=NAMING_CONVENTION,
    )

class BaseModel(Base):
    __abstract__ = True


class BaseModelWithMixins(
    UUIDPrimaryKeyMixin, # primary key first
    Base, 
    TimestampMixin       # timestamps last
):
    __abstract__ = True
