"""initial schema (snapshot of current models; later changes: `alembic revision --autogenerate -m msg`)"""
from alembic import op
from app.db import Base
import app.models  # noqa
revision = "0001"; down_revision = None
def upgrade(): Base.metadata.create_all(bind=op.get_bind())
def downgrade(): Base.metadata.drop_all(bind=op.get_bind())
