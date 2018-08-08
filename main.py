import asyncio
import aiohttp_autoreload
import aiopg
from aiohttp import web
from elasticsearch_async import AsyncElasticsearch
import database
import settings
import routes


async def create_engines(app):
    database.pg_pool = await aiopg.create_pool(settings.PG_DSN)
    database.es_pool = AsyncElasticsearch(settings.ES_HOSTS, loop=app.loop)
    # database.es_pool.indices.delete(index='orders', ignore=400)
    database.es_pool.indices.create(index='orders')

    # fighting with non-concurency/non-transactions of elasticsearch
    asyncio.ensure_future(database.es_queue_work(database.es_queue), loop=app.loop)


async def dispose_engines(app):
    database.pg_pool.close()
    database.pg_pool.wait_closed()
    # database.es_pool.close()


if settings.DEBUG:
    aiohttp_autoreload.start()

# loop = asyncio.get_event_loop()
app = web.Application()
app.on_startup.append(create_engines)
app.on_cleanup.append(dispose_engines)
routes.setup(app)
web.run_app(app, port=8800, access_log=settings.logger)
