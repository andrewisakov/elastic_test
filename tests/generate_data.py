import asyncio
from aiohttp import ClientSession
from contextlib import closing
import datetime
import random
import time
import json
import psycopg2


PG_DBNAME = 'BYM'
PG_USER = 'postgres'
PG_PASS = 'postgres'
PG_HOST = '127.0.0.1'
PG_PORT = '5432'
PG_DSN = f'dbname={PG_DBNAME} user={PG_USER} password={PG_PASS} host={PG_HOST} port={PG_PORT}'


RESTAPI = 'http://192.168.0.154:8800'


async def create_order(loop, date_time) -> dict:
    start_time = time.perf_counter()
    # date_time = datetime.datetime.now() - datetime.timedelta(days=random.randrange(30))
    async with ClientSession(loop=loop) as session:
        async with session.post(f'{RESTAPI}/orders/create',
                            json={'date_time': str(date_time)}) as resp:
            resp_json = await resp.json()
            # print(f'create_order {resp.status}: {resp_text}')
            return resp.status, resp_json, time.perf_counter()-start_time


async def add_item(loop, item_data: dict) -> dict:
    start_time = time.perf_counter()
    order_id = item_data['order_id']
    product_id = item_data['product_id']
    async with ClientSession(loop=loop) as session:
        async with session.post(f'{RESTAPI}/orders/{order_id}/add_item',
                                json={'product_id': product_id, 'quantity': random.randrange(2)+1}) as resp:
            resp_json = await resp.json()
            return resp.status, resp_json, time.perf_counter()-start_time


async def orders_list(loop) -> list:
    start_time = time.perf_counter()
    async with ClientSession(loop=loop) as session:
        async with session.get(f'{RESTAPI}/orders/list') as resp:
            resp_json = await resp.json()
            return resp.status, resp_json, time.perf_counter()-start_time


async def order_items(order_data: dict) -> dict:
    start_time = time.perf_counter()
    order_id = order_data['id']
    async with ClientSession(loop=loop) as session:
        async with session.get(f'{RESTAPI}/orders/{order_id}') as resp:
            resp_json = await resp.json()
            return resp.status, resp_json, time.perf_counter()-start_time

pg = psycopg2.connect(dsn=PG_DSN)
products = []
with pg.cursor() as c:
    c.execute('select id from products')
    products = c.fetchall()

loop = asyncio.get_event_loop()

for d in range(30):
    requests = []
    for o in range(5):
        date_time = datetime.datetime(year=2018, month=7, day=18, hour=random.randrange(
            24), minute=random.randrange(60)) - datetime.timedelta(days=d)
        requests.append(loop.create_task(create_order(loop, date_time)))
    orders = loop.run_until_complete(asyncio.gather(*requests))
    requests = []
    for status, order, _ in orders:
        if status != 200:
            continue
        for i in range(random.randrange(5)+3):
            # product_id = random.choice(products)[0]
            # order_id = order['id']
            requests.append(loop.create_task(add_item(loop, {'order_id': order['id'], 'product_id': random.choice(products)[0]})))
        # asyncio.sleep(0.1)
    items = loop.run_until_complete(asyncio.gather(*requests))
    # print(len(items))
"""
orders = loop.run_until_complete(asyncio.gather(loop.create_task(orders_list(loop))))
# print(orders)
orders = loop.run_until_complete(asyncio.gather(loop.create_task(order_items({'id': 493}))))
print(orders)
for _, order, _ in orders:
    print(order)
    print(order[0]['id'], order[0]['items_cost'])
    for item in order[0]['items']:
        print(item)
"""
loop.stop()
loop.close()
pg.close()
