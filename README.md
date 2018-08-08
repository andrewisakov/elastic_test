# BYM_elasticsearch
BYM Test task


# Python Test task
- Create a Python based application with REST CRUD methods for such entities: category, product, order and orderItem. 
- Category contains: name and a list of products. 
- Product contains: price, sku and name.
- Order item contains: “quantity” value and one-to-one connection to product.
- Order contains: a list of order items and sum of total charge for the order.
- Add report controller, which returns date and sum of income for each day (2016-08-22: 250.65, 2016-08.23: 571.12 ... etc) in JSON format.
- Add elasticsearch integration and search method for orders: by fragment of product name. 
- Bonus: make integration with Swagger. 
- Technology stack: Python {{Choose own framework for task}}, SQL-DB {{Choose db}}, ElasticSearch .

==========================================================
Technology stak: Python asyncio, aiohttp, elasticsearch-async, SQL-DB PostgreSQL (9.6), Elasticsearch

$ git clone https://github.com/andrewisakov/BYM_elasticsearch
$ cd BYM_elasticsearch
$ pip install pipenv
$ pipenv --python 3.6 (create venv)
$ pipenv install (install requirements)

$ docker run -p 9200:9200 -p 9300:9300 -e "discovery.type=single-node" docker.elastic.co/elasticsearch/elasticsearch:6.3.1 (or other method, or use exists)

$ docker run -p 5432:5432 postgres:9.6 (or other method, or use exists)

import setup/BYM.sql in postgres

$ pipenv shell
$ python main.py

in other console:
$ pipenv shell
$ cd BYM_elasticsearch
$ tests.py
$ python generate_data.py (generates order+items data)

use browser restapi plugin (on your liked) for tests
=========================================================
categories/products based on: ftp://ftp2.nix.ru/download/price/Nix3.ZIP

POST            Create order and return new order ID
path:           /orders/create
in parameters:  none
return:         {'id': new_order_id:int, 'date_time': datetime:str}

DELETE          Delete order by ID and return ID deleted order
path:           /orders/{order_id:\d+}
in parameters:  in path
return:         {'id': deleted_order_id:int}

GET             Get orders list
path:           /orders/list
in parameters:  none
return:         {'response': number_of_orders:int,'orders': [{'id': order_id:int,'date_time': datetime:str,'response': number_of_items_in_order,'items_cost': total_sum_of_order:decimal:str,},...]}

GET             Get items in order ID
path:           /orders/{order_id:\d+}
in parameters:  in path
return:         in json:
                [{'id': order_id:int, 
                  'date_time': datetime:str,
                  'items': [
                      {'product_id':int,
                       'sku':str,
                       'name':str,
                       'quantity':decimal:str,
                       'price':decimal:str,
                       'item_cost':decimal:str},...
                   ],
                  'response': int (number of items),
                  'items_cost': decimal:str (total of order)}]

POST            Add product (item) in order ID
path:           /orders/{order_id:\d+}/add_item
in parameters: in path
               in json:
               {'order_id':int,
                'product_id':int,
                'quantity: decimal:str}
return:         in json prameters + may be {... 'error': 'error'}

DELETE          Del product (item) from order
path:           /orders/{order_id:\d+}/del_item
in parameters:  in path
                in json: {'product_id': int,'prder_id': int}
return:         in json parameters + 'response': non-negative if success

POST            Create new product
path:           /products/create
in parameters:  in json {'name': str,'category_id': int,'sku': str,'price': decimal:str}
return:         in json parameters +{'response': int (>0 if success), 'error': str (if error)}

GET             Get product data
path:           /products/{product_id:\d+}
in parameters:  in path
return:         in json
                {'id': int,
                 'response': 1 (if success),
                 'product': 
                    {'id': product_id:int,
                     'category_id': category_id:int,
                     'name': product_name:str,
                     'sku': str,
                     'price': decimal:str
                    }
                }

PUT             Update product info
path:           /products/{product_id:\d+}
in parameters:  in path: as /product/create
                in json: as /product/create +
                        'id': product_id:int

POST            Create new category
path:           /categories/create
in parameters:  in json: {'name': category_name:str}
return:         in json: {'id': int, 'name': str,'resonse': int (1 if success)}

GET             Get category info
path:           /categories/{category_id:\d+}
in parameters:  in path
return:         {'id': int,'response': int (1 if success),
                 'categories': [{'id': int, 'name': str}]}

GET             Get products of category
path:           /categories/{category_id:\+}/products
in parameters:  in path
return:         in json:
                {'id': category_id:int,'name': category_name:str,
                 'response': int (number products in catrgory),
                 'products': [
                     {'id': product_id:int,'category_id': int,
                      'name': product_name:str,
                      'sku': str,
                      'price': decimal:str},{ .... }
                 ]
                }

GET             Get list of categories
path:           /categories/list
in parameters:  none
return:         in json:
                {'response': int (number categories),
                 'categories': [
                     {'id': category_id:int,'name': category_name:str},...
                  ]
                }

PUT             Update category (name)
path:           /categories/{category_id:\d+}
in parameters:  in path
                in json: {'name': new_name:str}
return:         in json:
                {'id': category_id:int,'response': int (1 if success),
                {'name': category_new_name:str}}


GET             Get report (as in task)
path:           /orders/report?date1=YYYYMMDD&date2=YYYYMMDD
in parameters:  in path
return:         in json:
                {'date_1': 'YYYY-MM-DD','date_2': 'YYYY-MM-DD',
                 'response': int (number of days in report),
                 'report':{'YYYY-MM-DD': decimal:str,...}}

GET             Search orders by fragment of product name
path:           /orders/search?query=urlencodedstring
in parameters:  in path
return:         in json:
                {'products': [
                    {
                        'id': product_id:int,
                        'category_id': int,
                        'name': product_name:str,
                        'sku': str,
                        'price': decimal,
                        '_score': float,
                        'orders': [order_id, ...]
                    }, ...
                 ],
                 'query': query:str (from GET)
                }
