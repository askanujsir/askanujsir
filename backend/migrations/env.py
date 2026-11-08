from alembic import context
from sqlalchemy import engine_from_config, pool
from app.config import settings
from app.db import Base
import app.models  # noqa: register tables
config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))
target_metadata = Base.metadata
def run():
    engine = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata)
        with context.begin_transaction(): context.run_migrations()
run()
