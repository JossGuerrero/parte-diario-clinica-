import os
import time
import logging
import pyodbc

logger = logging.getLogger(__name__)

DSN = os.environ.get('ACCESS_DSN', 'ClinicaAccess')


def get_connection(retries=5, delay=0.5, dsn=None, timeout=5):
    """Return a pyodbc connection to the Access DSN in read-only mode with retries.
    Raises the last exception on failure.
    """
    dsn = dsn or DSN
    last_err = None
    conn_str = f"DSN={dsn};Mode=Read;"
    for attempt in range(1, retries + 1):
        try:
            logger.debug('Attempt %s to connect to Access DSN=%s', attempt, dsn)
            return pyodbc.connect(conn_str, timeout=timeout, autocommit=True)
        except Exception as e:
            last_err = e
            logger.warning('Access connection attempt %s failed: %s', attempt, e)
            time.sleep(delay)
    logger.error('All attempts to connect to Access failed: %s', last_err)
    raise last_err
