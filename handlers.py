#!/usr/bin/python3
import datetime
import time
import json
from aiohttp import web
from settings import logger
from decimal import Decimal
import database
from settings import logger


class Order(web.View):
    async def _get_parameters(self, request):
        order_id = request.match_info.get('order_id', None)
        order_id = int(order_id) if order_id else None
        return order_id, request.rel_url.parts[-1]

    async def post(self):  # Create
        order_id, route = await self._get_parameters(self.request)
        # data = {k: v for k, v in data.items()}
        try:
            data = await self.request.json()
        except:
            pass
            data = {}
        if route == 'create':
            order = await database.Order.create(data)
        elif route == 'add_item':
            order = await database.Order.add_item({'order_id': order_id, **data})
        order['route'] = route
        return web.json_response(order)

    async def get(self):  # Read
        order_id, route = await self._get_parameters(self.request)
        # orders['route'] = route
        orders = await database.Order.get({'id': order_id, 'route': route})
        if route != 'list':
            orders = orders['orders']
        return web.json_response(orders)

    async def put(self):  # Update
        data = (await self.request.json()).get('query', None)
        logger.debug(f'Order.put {data}')
        return web.json_response()

    async def delete(self):  # Delete
        order_id, route = await self._get_parameters(self.request)
        logger.debug(f'Order.delete {order_id}')
        if route == 'del_item':
            product_id = await self.request.json()
            product_id = product_id.get('product_id', None)
            order_data = await database.Order.del_item({'order_id': order_id, 'product_id': product_id})
        else:
            order_data = await database.Order.delete({'id': order_id})
        return web.json_response(order_data)


class Product(web.View):
    # async def _generate_sku(self, name, cat_id, prod_id):
    #     sku = 'sku'
    #     return sku

    async def _get_parameters(self, request):
        product_id = request.match_info.get('product_id', None)
        product_id = int(product_id) if product_id else None
        return product_id, request.rel_url.parts[-1]

    async def post(self):
        # product_id, _ = await self._get_parameters(self.request)
        product_json = await self.request.json()
        create_product = await database.Product.create(product_json)
        return web.json_response(create_product)

    async def get(self):
        product_id, route = await self._get_parameters(self.request)
        print (product_id, route)
        products = await database.Product.get({'id': product_id})
        products['route'] = route

        return web.json_response(products)

    async def put(self):
        product_id, _ = await self._get_parameters(self.request)
        product_json = await self.request.json()
        product = await database.Product.update(product_json)
        return web.json_response(product)

    async def delete(self):
        product_id, category_id, name, sku = await self._get_parameters(self.request)


class Category(web.View):
    async def _get_parameters(self, request):
        category_id = request.match_info.get('category_id', None)
        category_id = int(category_id) if category_id else None
        return category_id, request.rel_url.parts[-1]

    async def post(self):
        category_id, route = await self._get_parameters(self.request)
        categories = {}
        if route == 'create':
            request_json = await self.request.json()
            categories = await database.Category.create({'name': request_json['name']})
        # categories['request_json'] = request_json
        categories['route'] = route
        return web.json_response(categories)

    async def delete(self):
        # bad idea :)
        category_id, route = await self._get_parameters(self.request)
        categories = {}
        categories = await database.Category.delete({'id': category_id})
        categories['route'] = route
        return web.json_response(categories)

    async def get(self):
        category_id, route = await self._get_parameters(self.request)
        if route == 'products':
            categories = await database.Category.products({'id': category_id})
        else:
            categories = await database.Category.get({'id': category_id})
        categories['route'] = route
        return web.json_response(categories)

    async def put(self):
        # rename category
        category_id, _ = await self._get_parameters(self.request)
        request_json = await self.request.json()
        categories = {'id': category_id, 'response': -1}
        if 'name' in request_json.keys():
            categories = await database.Category.update({'id': category_id, 'name': request_json['name']})
        return web.json_response(categories)


class Report(web.View):
    async def get(self):
        date_1 = self.request.rel_url.query['date1']
        date_2 = self.request.rel_url.query['date2']
        date_1 = datetime.datetime.strptime(date_1, '%Y%m%d').date().__str__()
        date_2 = datetime.datetime.strptime(date_2, '%Y%m%d').date().__str__()
        response = await database.Order.report({'date_1': date_1, 'date_2': date_2})
        return web.json_response(response)


class ES(web.View):
    async def get(self):
        query = self.request.rel_url.query['query']
        response = await database.Product.es_search(query)
        return web.json_response(response)

    async def post(self):
        """ not implemented """
        request_json = await self.request.json()
        # await database.Product.reindex()
        # await database.Order.reindex()
        response = {}
        return web.json_response(response)
