import os
import logger as _logger


DEBUG=True

APP_DIR = os.path.dirname(__file__)
logger = _logger.rotating_log(os.path.join(APP_DIR, 'bym_log.log'), 'bym_log')

ES_HOSTS = ['127.0.0.1:9200', ]
PG_DBNAME = 'BYM'
PG_USER = 'postgres'
PG_PASS = 'postgres'
PG_HOST = '127.0.0.1'
PG_PORT = '5432'
PG_DSN = f'dbname={PG_DBNAME} user={PG_USER} password={PG_PASS} host={PG_HOST} port={PG_PORT}'
