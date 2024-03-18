import os

from woocommerce import API

woo = API(
    url="https://icrtcont.icorrect.co.uk",
    consumer_key=os.environ['WOO_KEY'],
    consumer_secret=os.environ['WOO_SECRET'],
    version="wc/v3"
)


def adjust_price(product_id: str, new_price: str, name: str = ''):
    """adjust the price of a woo commerce product"""

    new_price = float(new_price)

    data = {
        "regular_price": str(new_price),
    }
    if name:
        data["name"] = str(name)

    res = woo.put(f"products/{product_id}", data)

    if res.status_code == 200:
        return res.json()
    else:
        raise Exception(f"Woo Commerce Product Update Failed: {res.json()}")
