import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

cc = 'no'
lc = 'no'
contract_header = '37249'
consumer_header = 'MAMMUT'


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

        print(product_ids_string)

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


if __name__ == '__main__':
    session = start_session()

    store_names = ['Slependen', 'Furuset']

    products = ['00454557']

    stores = get_store_info(store_names)

    product_info = get_product_info(products)

    # parse_availability()
    available = []
    for product_id in products:
        for store in stores:
            store_name = store['StoreName']
            avail = (get_product_availability(store['StoreNo'], product_id))
            stock = int(avail['StockAvailability']['RetailItemAvailability']['AvailableStock']['$'])
            print(f'{stock} of {product_id} available at IKEA {store_name}')

            if not stock > 0:
                restock_datetime = avail['StockAvailability']['RetailItemAvailability']['RestockDateTime'].get('$')
                print(f'{product_id} expected at IKEA {store_name} at {restock_datetime}')
