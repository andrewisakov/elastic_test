from aiohttp import web
from aiohttp_swagger import setup_swagger
import handlers


def setup(app):
    app.add_routes([web.post(r'/orders/create', handlers.Order, name='new_order'),  # C +
                    web.delete(r'/orders/{order_id:\d+}', handlers.Order, name='delete_order'),  # +
                    web.get(r'/orders/list', handlers.Order, name='get_orders_list'),  # +
                    web.get(r'/orders/{order_id:\d+}', handlers.Order, name='get_order'),  # +
                    web.post(r'/orders/{order_id:\d+}/add_item', handlers.Order, name='order_add_item'),  #+
                    web.delete(r'/orders/{order_id:\d+}/del_item', handlers.Order, name='order_del_item'),  # +
                    ])  # D

    app.add_routes([web.post(r'/products/create', handlers.Product, name='create_product'),  # +
                    web.get(r'/products/{product_id:\d+}', handlers.Product, name='get_product'),  # +
                    web.put(r'/products/{product_id:\d+}', handlers.Product, name='update_product'),  # +
                    ])

    app.add_routes([web.post(r'/categories/create', handlers.Category, name='create_category'),  # +
                    web.get(r'/categories/{category_id:\d+}', handlers.Category, name='get_category'),  #+
                    web.get(r'/categories/{category_id:\d+}/products', handlers.Category, name='get_category_products'),  #+
                    web.get(r'/categories/list', handlers.Category, name='get_categories_list'),  #+
                    web.put(r'/categories/{category_id:\d+}', handlers.Category, name='update_category'),  # +
                    ])  # + ?

    app.add_routes([web.get(r'/orders/report', handlers.Report, name='report'), ])

    app.add_routes([web.post(r'/orders/reindex', handlers.ES, name='reindex_orders'),
                    web.get(r'/orders/search', handlers.ES, name='product_search'),
                    ])

#     setup_swagger(app, swagger_url='/api/doc', contact='andrew.isakov@gmail.com', swagger_from_file='swagger.json')
