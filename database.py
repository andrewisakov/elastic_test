from asyncio import Queue
import datetime
from decimal import Decimal
# import aiopg
# import psycopg2
from decorator import decorator
# import json
from settings import logger

pg_pool = None
es_pool = None
es_queue = Queue()


async def es_worker(operation, *args, **kwargs):
    logger.debug(f'es_worker {operation} ({args}, {kwargs})')
    if operation.upper() in ('ADD_ITEM', 'DEL_ITEM'):
        _order_id = args[0]['order_id']
        _product_id = args[0]['product_id']
        _order = await es_pool.get(index='orders', doc_type='orders', id=_order_id, ignore=404)
        # logger.debug(f'es_worker GET _order: {_order}')
        _items = set(_order['_source'].get('items') if _order['found'] else [])
        logger.debug(f'es_worker {operation}: {_order} {_items}')
        if operation.upper() == 'ADD_ITEM':
            _product = await es_pool.get(index='orders', doc_type='items', id=_product_id, ignore=404)
            if not _product['found']:
                _product = await db_query(f'select * from products where id={_product_id}')
                _product.pop()
                if _product:
                    await es_pool.index(index='orders', doc_type='items', id=_product_id,
                                        body=_product[0])
            _items.add(_product_id)
        elif operation.upper() == 'DEL_ITEM':
            _items.discard(_product_id)
        # logger.debug(f'es_worker {operation}: {_order_id} {_items}')
        _order = await es_pool.index(index='orders', doc_type='orders', id=_order_id,
                                        body={'id': _order_id, 'items': list(_items)})
    elif operation.upper() == 'UPDATE_PRODUCT':
        """ not implemented """
        pass


async def es_queue_work(queue):
    """ fighting with non-concurency/non-transactions of elasticsearch """
    while True:
        task, args, kwargs = await queue.get()
        await es_worker(task, *args, **kwargs)
        # logger.debug(f'es_queue_work: {task}({args}, {kwargs})')


@decorator
async def es_trace(f, operation='', *args, **kwargs):
    """ trace operations potentially influence on elasticsearch indexes """
    kwstr = ', '.join(f'k=v' for k, v in kwargs.items())
    logger.debug(f'calling {f.__name__}({args}, {kwstr})')
    result = await f(*args, **kwargs)
    logger.debug(f'es_trace {f.__name__}({operation})->{result}')
    if not(result['response'] < 0):
        await es_queue.put((operation, args, kwargs))
    return result


def json_pack(value):
    if isinstance(value, (datetime.datetime, Decimal, datetime.date, )):
        return str(value)
    return value

async def db_query(sql_query: str, values: tuple=None) -> list:
    logger.debug(f'db_query: {sql_query}')
    logger.debug(f'values: {values}')
    async with pg_pool.acquire() as db:
        async with db.cursor() as c:
            try:
                sql_result = []
                if values:
                    await c.execute(sql_query, values)
                else:
                    await c.execute(sql_query)
                try:
                    async for r in c:
                        sql_result.append(
                            {c.description[i].name: r[i] for i in range(len(c.description))})
                        # sql_result.append({c.description[i].name: json_pack(
                        #     r[i]) for i in range(len(c.description))})
                except:
                    pass
                sql_result.append({'response': len(sql_result)})
            except Exception as e:
                logger.error(f'{sql_query}: {e}')
                sql_result.append({'error': e.__str__().split('DETAIL:')[1].strip()})
                sql_result.append({'response':-1})
    return sql_result


class Order:
    @staticmethod
    async def report(report_data: dict) -> list:
        report_data['response'] = -1
        select_report_orders = ('select ord.date_time::date as date, sum(oit.quantity*pro.price) '
                                'from order_items oit '
                                'join orders ord on(ord.id=oit.order_id) '
                                'join products pro on(pro.id=oit.product_id) '
                                'group by (ord.date_time::date) '
                                'having ord.date_time::date between %s and %s '
                                'order by ord.date_time::date')
        dates = (report_data['date_1'], report_data['date_2'])
        select_report = await db_query(select_report_orders, dates)
        report_data['response'] = select_report.pop()['response']
        report_data['report'] = {rep_row['date'].__str__(): rep_row['sum'].__str__() for rep_row in select_report}
        return report_data

    @staticmethod
    async def create(order_data: dict) -> dict:
        order_data['response'] = -1
        date_time = order_data.get('date_time', None)
        date_time = date_time if date_time else datetime.datetime.now()
        insert_order = f'insert into orders(date_time) values(\'{date_time}\') returning id'
        insert_order = await db_query(insert_order)
        response = insert_order.pop()['response']
        order_data['id'], order_data['response'] = insert_order[0]['id'], response
        order_data['date_time'] = date_time
        return order_data

    @staticmethod
    @es_trace('ORDER_DELETE')
    async def delete(order_data: dict) -> dict:
        order_data['response'] = -1
        order_id = order_data.get('id', 0)
        if order_id > 0:
            delete_order = f'delete from orders where id={order_id};'
            order_data['response'] = (await db_query(delete_order))[-1]['response']
        return order_data

    @staticmethod
    async def get(orders_data: dict) -> list:
        orders = []
        orders_data['response'] = 0
        order_id = orders_data.get('id', None)
        select_orders = 'select * from orders'
        if order_id:
            order_id = int(order_id)
            select_orders += (f' where id={order_id}' if order_id else '')
        select_orders = await db_query(select_orders)
        response = select_orders.pop()['response']
        if not (response < 0):
            for order in select_orders:
                items = await Order.get_items({'order_id': order['id']})
                orders.append({**order, **items, 'date_time': str(order['date_time'])})
                if orders_data['route'] == 'list':
                    del orders[-1]['items']
        orders_data['response'] = len(orders)
        orders_data['orders'] = orders
        return orders_data

    @staticmethod
    async def get_items(order_data: dict) -> dict:
        items = []
        order_data['response'] = -1
        items_cost = 0
        order_id = order_data.get('order_id', 0)
        if not (order_id > 0):
            return {'items': [], 'response': 0, 'items_cost': 0}
        select_items = ('select oits.product_id, p.sku, p.name, oits.quantity, p.price, '
                        'p.price*oits.quantity as item_cost '
                        'from order_items oits '
                        'join products p on (p.id=oits.product_id) '
                        f'where order_id={order_id} order by p.sku')
        order_items = await db_query(select_items)
        response = order_items.pop()['response']
        for item in order_items:
            items_cost += item['item_cost']
            items.append({k: json_pack(v) for k, v in item.items()})
        response = len(items)
        return {'items': items, 'response': response, 'items_cost': json_pack(items_cost)}

    # @staticmethod
    # async def update(order_data: dict) -> dict:
    #     order_data['response']= -1
    #     order_id = order_data.get('id', 0)
    #     if not (order_id > 0):
    #         return order_data
    #     items = order_data.get('items', {}).copy()
    #     order_data['items'] = []
    #     for item in items:
    #         item_data = (await Order.del_item(item)) if item['delete'] else (await Order.add_item(item))
    #         # item_data['response'] = response
    #         order_data['items'].append(item_data)
    #     response = 0
    #     order_data['response'] = response
    #     return order_data

    @staticmethod
    @es_trace('ADD_ITEM')
    async def add_item(item_data: dict) -> dict:
        item_data['response'] = -1
        product_id = item_data.get('product_id', None)
        order_id = item_data.get('order_id', None)
        quantity = item_data.get('quantity', None)
        if all((product_id, order_id, quantity)):
            quantity = Decimal(quantity)
            order_id = int(order_id)
            product_id = int(product_id)
            insert_item = ('insert into order_items(order_id, product_id, quantity) '
                        f'values({order_id}, {product_id}, {quantity}) '
                        'on conflict (order_id, product_id) do update '
                        f'set quantity={quantity}')
            item = await db_query(insert_item)
            item_data['response'] = item.pop()['response']
        return item_data

    @staticmethod
    @es_trace('DEL_ITEM')
    async def del_item(item_data: dict) -> dict:
        item_data['response'] = -1
        order_id = item_data.get('order_id', None)
        product_id = item_data.get('product_id', None)
        if all((order_id, product_id)):
            order_id = int(order_id)
            product_id = int(product_id)
            item_delete = (f'delete from order_items where (order_id={order_id} and product_id={product_id})')
            item_data['response'] = (await db_query(item_delete))[0]['response']
        else:
            item_data['error'] = 'not enougth product_id:int and(or) order_id:int'
        return item_data

    @staticmethod
    async def search_item(product_name: str):
        """elasticsearch integration and search method for orders: by fragment of product name."""
        pass


class Product:
    @staticmethod
    async def get(product_data: dict) -> dict:
        products = []
        product_id = product_data.get('id', 0)
        if not product_id:
            product_data['products'] = products
            product_data['response'] = -2
            return product_data
        select_product = f'select * from products where id={product_id}'
        select_product = await db_query(select_product)
        product_data['response'] = select_product.pop()['response']
        product_data['product'] = select_product[0]
        product_data['product']['price'] = json_pack(product_data['product']['price'])
        return product_data

    @staticmethod
    async def delete(product_data: dict) -> dict:
        product_data['response'] = -1
        product_id = int(product_data.get('id', 0))
        if not (product_id > 0):
            return product_data
        delete_product = f'delete from products where id={product_id}'
        product_data['response'] = (await db_query(delete_product))[0]['response']
        return product_data

    @staticmethod
    @es_trace('UPDATE_PRODUCT')
    async def update(product_data: dict) -> dict:
        product_data['response'] = -1
        update_product = []
        product_id = int(product_data.get('id', 0))
        if product_id > 0:
            if product_data['category_id']:
                update_product.append(('category_id', product_data['category_id'], ))
            if product_data['name']:
                update_product.append(('name', product_data['name'], ))
            if product_data['sku']:
                update_product.append(('sku', product_data['sku'], ))
            if product_data['price']:
                update_product.append(('price', Decimal(product_data['price']), ))
            if any(update_product):
                update_fields = ', '.join([pp[0] for pp in update_product])
                update_values = tuple([pp[1] for pp in update_product])
                update_product = (f'update products set ({update_fields}) = (' +
                                  ', '.join(('%s '*len(update_values)).split(' ')[:-1])+') '
                                  f'where id={product_id} returning id')
                update_product = await db_query(update_product, update_values)
                product_data['response'] = update_product.pop()['response']
                if not (product_data['response'] < 0):
                    product_data['id'] = update_product[0]['id']
                else:
                    product_data['error'] = update_product[0]['error']
        return product_data

    @staticmethod
    async def create(product_data: dict) -> dict:
        product_data['response'] = -1
        create_product = []
        create_product.append(
            None if 'category_id' not in product_data.keys() else ('category_id', int(product_data['category_id']), ))
        create_product.append(
            None if 'name' not in product_data.keys() else ('name', product_data['name']))
        create_product.append(
            None if 'sku' not in product_data.keys() else ('sku', product_data['sku']))
        create_product.append(
            None if 'price' not in product_data.keys() else ('price', Decimal(product_data['price']), ))
        if all(create_product):
            fields = []
            values = []
            for cp in create_product:
                fields.append(cp[0])
                values.append(cp[1])
            fields = ', '.join(fields)
            values = tuple(values)
            create_product = f'insert into products({fields}) values(' + ', '.join(
                ('%s '*len(values)).split(' ')[:-1]) + ') returning id'
            create_product = (await db_query(create_product, values))
            product_data['response'] = create_product.pop()['response']
            if not (product_data['response'] < 0):
                product_data['id'] = create_product[0]['id']
            else:
                product_data['error'] = create_product.pop()['error']
        else:
            product_data['response'] = -2
            product_data['need'] = list({'category_id', 'name', 'sku', 'price'} - {pp[0] for pp in create_product if pp})
        return product_data

    @staticmethod
    async def es_search(query: str) -> list:
        products = {}
        logger.debug(f'Product.es_search({query})')
        items = (await es_pool.search(index='orders', doc_type='items',
                                      body={'from': 0, 'size': 100,
                                            'query': {'match': {'name': query}}})
                 )['hits']['hits']
        # items = items['hits']['_source'] if items['total'] > 0 else []
        items = [{**item['_source'], '_score': item['_score']} for item in items]
        product_orders = {}
        for item in items:
            # logger.debug(f'Product.es_search: {item}')
            _product_id = item['id']
            _product_orders = (await es_pool.search(index='orders', doc_type='orders',
                                                    body={'from': 0, 'size': 100,
                                                          'query': {
                                                              'match': {'items': _product_id}}}
                                                    ))['hits']
            _product_orders = _product_orders['hits'] if _product_orders['total'] > 0 else None
            if _product_id not in product_orders.keys():
                product_orders[_product_id] = set()
            product_orders[_product_id] |= set([po['_source']['id'] for po in _product_orders])
            logger.debug(f'Product.es_search {_product_id}: {product_orders}')
        products['products'] = [{**item, 'orders': list(product_orders[item['id']])} for item in items]
        products['query'] = query
        return products


class Category:
    @staticmethod
    async def create(category_data: dict) -> dict:
        category_data['response'] = -1
        name = category_data.get('name', None)
        if not name:
            return category_data
        insert_category = (f'insert into categories(name) values(\'{name}\') returning id ')
        insert_category = await db_query(insert_category)
        category_data['response'] = insert_category.pop()['response']
        if category_data['response'] == -1:
            select_category = f'select id from categories where name=\'{name}\''
            insert_category = await db_query(select_category)
            category_data['response'] = insert_category.pop()['response']

        category_data['id'] = insert_category[0]['id']
        return category_data

    @staticmethod
    async def delete(category_data: dict) -> dict:
        category_data['response'] = -1
        category_id = category_data.get('id', 0)
        if not (category_id > 0):
            return category_data
        delete_category = f'delete from categories where id={category_id}'
        delete_category = await db_query(delete_category)
        category_data['response'] = delete_category[0]['response']
        return category_data

    @staticmethod
    async def update(category_data: dict) -> dict:
        category_data['response'] = -1
        category_id = category_data.get('id', None)
        name = category_data.get('name', None)
        if all((category_id, name, )):
            update_category = f'update categories set name=\'{name}\' where id={category_id} returning id'
            update_category = await db_query(update_category)
            category_data['id'] = update_category[0]['id']
            category_data['response'] = update_category[1]['response']
            category_data['old_name'] = name
        return category_data

    @staticmethod
    async def products(category_data: dict) -> dict:
        category_data['response'] = -1
        category_id = category_data.get('id', None)
        if category_id:
            category_id = int(category_id)
            select_category_products = f'select * from products where category_id={category_id}'
            category_products = await db_query(select_category_products)
            category_data['response'] = category_products.pop()['response']
            if not (category_data['response'] < 0):
                category_data['products'] = [{**product, 'price': json_pack(product['price'])} for product in category_products]
                category_name = await db_query(f'select name from categories where id={category_id}')
                response = category_name.pop()['response']
                if not (response < 0):
                    category_data['name'] = category_name[0]['name']
        return category_data

    @staticmethod
    async def get(category_data: dict) -> dict:
        category_data['response'] = -1
        category_id = category_data.get('id', None)
        select_category = 'select * from categories ' + (f'where id={category_id}' if category_id else '')
        select_category = await db_query(select_category)
        category_data['response'] = select_category.pop()['response']
        category_data['categories'] = select_category
        return category_data
