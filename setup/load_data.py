import xlrd
import psycopg2
import re


SKU_MASKS = (
    '(.*)(\<.*\>)(.*)',
    '(.*)(\(.*\))(.*)',
)


def insert_category(category_name, db):
    while True:
        try:
            category_name = category_name.replace('\'', '´')
            c = db.cursor()
            c.execute(
                f'insert into categories (name) values (\'{category_name}\') returning id;')
            last_id = c.fetchone()
            c.close()
            break
        except psycopg2.IntegrityError as e:
            # Дубликаты...
            print(f'category: {e}')
            db.rollback()
            category_name += '+'
            print(f'try category: {category_name}')
            c.close()
    return last_id[0]


def insert_product(cat_id, product_name, product_price, product_sku, db):
    c = db.cursor()
    product_name = product_name.replace('\'', '´')
    c.execute(f'insert into products(category_id, name, price, sku) '
            f'values({cat_id}, \'{product_name}\', {product_price}, \'{product_sku}\') '
            #'on conflict do nothing;'
            )
    c.close()


def load_data(xls_book):
    """ Загрузка данных из .xls
    xls_book: str file path
    """
    PRODUCT_GROUP = ''
    b = xlrd.open_workbook(xls_book)
    db = psycopg2.connect(dsn="host='172.17.0.3' dbname='BYM' user='postgres' password='postgres'")
    # regex = re.compile(SKU_MASKS)
    for r in range(0, b.sheets()[0].nrows):
        # print(b.sheets()[0].row(r))
        if isinstance(b.sheets()[0].row(r)[0].value, (str, )):  # Категория
            PRODUCT_GROUP = b.sheets()[0].row(r)[0].value
            print(PRODUCT_GROUP)
            db.commit()
            cat_id = insert_category(PRODUCT_GROUP, db)
        else:
            if PRODUCT_GROUP:
                # print(b.sheets()[0].row(r))
                product_name = None
                product_sku = None
                product_price = None
                for mask in SKU_MASKS:
                    # print(f'Строка: {b.sheets()[0].row(r)[1].value}')
                    try:
                        sku_groups = re.search(mask, b.sheets()[0].row(r)[1].value.replace('-->', '→'))
                        # print(f'Группы: {sku_groups.groups()}')
                        if sku_groups and sku_groups[3]:
                            product_sku = sku_groups[2][1:-1]
                            if ',' not in product_sku:
                                product_name = re.sub(r'\s+', ' ', (sku_groups[1] + sku_groups[3]))
                                product_price = b.sheets()[0].row(r)[2].value
                                # print(f'Результат: {product_sku} | {product_name} | {product_price}')
                                break
                            else:
                                product_sku = None
                    except:
                        pass
                if isinstance(product_price, (float,)):
                    insert_product(cat_id, product_name, product_price, product_sku, db)

    db.commit()
    db.close()


if __name__ == '__main__':
    load_data('nix3.xlsx')
