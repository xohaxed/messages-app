"""Database connection pool and health probe."""

from psycopg_pool import ConnectionPool

from .config import settings

CONNINFO = (
    f"host={settings.db_host} port={settings.db_port} "
    f"dbname={settings.db_name} user={settings.db_user} "
    f"password={settings.db_password}"
)

# open=False        -> do not connect at import time. The app must boot even
#                      when the database is down, otherwise /health could
#                      never report the problem: the process would just die.
# check=...         -> validate a connection BEFORE handing it to a request.
#                      Without this, connections to a database container that
#                      was destroyed and recreated stay in the pool and every
#                      request fails until a restart.
# max_lifetime      -> recycle connections periodically.
# reconnect_timeout -> keep retrying rather than giving up instantly.
pool = ConnectionPool(
    CONNINFO,
    min_size=1,
    max_size=5,
    open=False,
    max_lifetime=300,
    reconnect_timeout=10,
    check=ConnectionPool.check_connection,
)


def check_db() -> bool:
    """Return True if a trivial query succeeds within 2 seconds.

    The short timeout matters: a health check that hangs for 30s makes a load
    balancer conclude the whole host is dead, turning a database blip into a
    full outage.
    """
    try:
        with pool.connection(timeout=2) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False
