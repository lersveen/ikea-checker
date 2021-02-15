import os

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from yagmail import SMTP

cc = 'no'
lc = 'no'
contract_header = '37249'
consumer_header = 'MAMMUT'

gmail_user = os.environ.get('GMAIL_USER')
gmail_password = os.environ.get('GMAIL_PASSWORD')


def start_session(retries=None, session=None, backoff_factor=0, status_forcelist=(500, 502, 503, 504)):
    session = session or requests.Session()

    if retries:
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            method_whitelist=frozenset(['GET', 'POST'])
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

    session.headers.update({
        'Accept': 'application/vnd.ikea.iows+json;version=1.0',
        'Contract': contract_header,
        'Consumer': consumer_header
        })
    return session


def get_store_info(store_names: list) -> dict:
    stores = []
    try:
        r = session.get(
            url=f'https://securema2.ikea.com/stores/v1/{cc}/{lc}/',
            )
        r.raise_for_status()

        r_stores = r.json()['StoreRefList']['StoreRef']

        all_store_names = []
        all_store_names += [r_store['StoreName'] for r_store in r_stores]

        print(f'Found stores: {all_store_names}')

        stores += [r_store for r_store in r_stores
                   if r_store['StoreName'] in store_names]

        if stores:
            found_store_names = [s['StoreName'] for s in stores]
            diff = set(store_names) - set(found_store_names)

            if diff:
                print(f'Found no matching store IDs for {diff} – only {found_store_names}')
            else:
                print(f'Succeeded getting IDs for all stores – {found_store_names}')
            return stores
        else:
            print(f'Found no matching store IDs for {store_names}')
            return None
    except Exception:
        print('Failed getting store IDs – unknown error')
        return None


def get_product_info(product_ids):
    try:
        product_ids_string = ';'.join(['ART,'+p for p in product_ids])

        r = session.get(
            url=f'https://securema2.ikea.com/catalog/v2/{cc}/{lc}/product/{product_ids_string}',
            )
        r.raise_for_status()

        product_info = r.json()

        if product_info:

            return product_info
        else:
            print('Found no info for products')
            return None
    except Exception:
        print('Failed getting product info – unknown error')
        return None


def send_mail(subject, body):
    SMTP(gmail_user, gmail_password).send(
        to=gmail_user,
        subject=subject,
        contents=body)


def get_product_availability(store_id, product_id):
    try:
        r = session.get(
            f'https://iows.ikea.com/retail/iows/{cc}/{lc}/stores/{store_id}/availability/ART/{product_id}'
            )
        r.raise_for_status()
        return r.json()

    except Exception as e:
        print(f'Failed getting product availability – unknown error – {e}')
        return None


def build_result(products, stores):
    items = []
    for product in products:
        item = {
                'product_id': product['ItemNo'],
                'product_name': f'{product["ProductName"]} ({product["ProductTypeName"]}, {product["ValidDesignText"]})',
                'available': False,
                'stock': []
                }

        for store in stores:
            avail = (get_product_availability(store['StoreNo'], product['ItemNo']))
            stock = int(avail['StockAvailability']['RetailItemAvailability']['AvailableStock']['$'])

            store_stock = {
                'store_id': store['StoreNo'],
                'store_name': store['StoreName'],
                'stock': stock
            }

            if stock > 0:
                item['available'] = True
            else:
                restock_datetime = avail['StockAvailability']['RetailItemAvailability']['RestockDateTime'].get('$')
                if restock_datetime:
                    store_stock['restock_datetime'] = restock_datetime

            item['stock'].append(store_stock)
        items.append(item)
    return items


if __name__ == '__main__':
    session = start_session()

    store_names = ['Slependen', 'Furuset']
    product_ids = ['00454557', '00324325', '10457329']

    stores = get_store_info(store_names)

    products = get_product_info(product_ids)

    result = build_result(products, stores)
    
    available_items = []
    unavailable_items = []
    for item in result:
        if item['available']:
            available_items.append(item)
        else:
            unavailable_items.append(item)

    if available_items:
        available_items_string = ''
        for item in available_items:
            stock_string = ''
            for store in item['stock']:
                if store.get('restock_datetime'):
                    restock_string =  f'– expected {store["restock_datetime"]}'
                else:
                    restock_string = ''
                stock_string += \
                    f'  IKEA {store["store_name"]}: {store["stock"]} in stock{restock_string}\n'

            available_items_string += \
                f'{item["product_id"]} - {item["product_name"]}\n' \
                f'{stock_string}\n'

        if unavailable_items:
            unavailable_items_string = ''
            for item in unavailable_items:
                stock_string = ''
                for store in item['stock']:
                    if store.get('restock_datetime'):
                        restock_string =  f'– expected {store["restock_datetime"]}'
                    else:
                        restock_string = ''
                    stock_string += \
                        f'  IKEA {store["store_name"]}: {store["stock"]} in stock{restock_string}\n'

                unavailable_items_string += \
                    f'{item["product_id"]} - {item["product_name"]}\n' \
                    f'{stock_string}\n'
                    


        body = \
            'Hey, me!\n\n' \
            'Now available:\n' \
            f'{available_items_string}\n\n' \
            'Still not available:\n' \
            f'{unavailable_items_string}'

        print(body)
        # send_mail('Ikea Availability', body)


    print(result)

    # send_mail('test')
