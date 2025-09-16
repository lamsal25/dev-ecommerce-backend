from products.models import Product, ProductSize
from products.serializers import ProductSerializer
from django.conf import settings

class Cart:
    def __init__(self, request):
        # Initializing the cart
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def save(self):
        self.session.modified = True

    def checkExistsInCart(self, product, size=None):
        product_id = str(product.id)

        if product_id not in self.cart:
            return "not exists"

        cart_item = self.cart[product_id]

        # Normal product with sizes
        if cart_item.get("has_sizes", False):
            sizes = cart_item.get("sizes", {})
            if size in sizes:
                return "exists"
            else:
                return "not exists"

        # Normal product without sizes
        return "exists"

    def add(self, product, quantity=1, overide_quantity=False, size=None):
        quantity = int(quantity)
        product_id = str(product.id)
        price = getattr(product, 'discountedPrice', None) or getattr(product, 'price', None)
        if price is None:
            raise ValueError("Product does not have a price field.")

        if getattr(product, "has_sizes", False):
            if not size:
                raise ValueError("Size is required for this product.")
            
            if product_id not in self.cart:
                self.cart[product_id] = {
                    "sizes": {size: quantity},
                    "price": str(price),
                    "has_sizes": True,
                }
            else:
                sizes = self.cart[product_id].setdefault("sizes", {})
                if size in sizes and not overide_quantity:
                    sizes[size] += quantity
                else:
                    sizes[size] = quantity
        else:
            if product_id not in self.cart:
                self.cart[product_id] = {
                    "quantity": quantity,
                    "price": str(price),
                    "has_sizes": False,
                }
            elif overide_quantity:
                self.cart[product_id]["quantity"] = quantity
            else:
                self.cart[product_id]["quantity"] += quantity

        self.save()

    def remove(self, productID):
        productID = str(productID)
        if productID in self.cart:
            del self.cart[productID]
            self.save()

    def clear(self):
        del self.session[settings.CART_SESSION_ID]
        self.save()

    def __iter__(self):
        cart = self.cart.copy()

        product_ids = [int(pid) for pid in cart.keys()]

        products = Product.objects.filter(id__in=product_ids)

        product_lookup = {str(p.id): p for p in products}

        result = []
        for pid, item in cart.items():
            product = product_lookup.get(pid)
            if not product:
                continue

            serialized = ProductSerializer(product).data
            serialized["product_type"] = "product"

            item["product"] = serialized
            item["price"] = float(item["price"])

            if serialized.get("has_sizes") and "sizes" in item:
                size_key = list(item["sizes"].keys())[0]
                item["selected_size"] = size_key
                item["quantity"] = item["sizes"][size_key]
            else:
                item["quantity"] = int(item.get("quantity", 1))

            result.append(item)

        return result

    def get_quantity(self, product, size=None):
        product_id = str(product.id)
        item = self.cart.get(product_id)
        if not item:
            return 0

        if product.has_sizes:
            if not size:
                return 0
            return item.get("sizes", {}).get(size, 0)

        return item.get("quantity", 0)
