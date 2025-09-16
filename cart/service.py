from products.models import Product
from products.models import MarketPlaceProduct
from products.serializers import ProductSerializer, MarketPlaceProductSerializer
from django.conf import settings
# from decimal import Decimal

class Cart:
    def __init__(self, request):
         #Initializing the cart
        self.session = request.session
        print("Request Session: ", request.session)
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            # save an empty cart in session
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def save(self):
        self.session.modified = True


    def checkExistsInCart(self, product, size=None, product_type="product"):
        product_id = str(product.id)

        # If product not in cart at all
        if product_id not in self.cart:
            return "not exists"

        cart_item = self.cart[product_id]

        # Marketplace product (no sizes, just unique)
        if cart_item.get("product_type") == "marketplace":
            return "exists"

        # Normal product with sizes
        if cart_item.get("has_sizes", False):
            sizes = cart_item.get("sizes", {})
            if size in sizes:
                return "exists"
            else:
                return "not exists"

        # Normal product without sizes
        return "exists"

    
    def add(self, product, quantity=1, overide_quantity=False, size=None, product_type="product"):
        quantity = int(quantity)
        product_id = str(product.id)
        price = getattr(product, 'discountedPrice', None) or getattr(product, 'price', None)
        if price is None:
            raise ValueError("Product does not have a price field.")

        # --- New: branch by product type ---
        if product_type == "marketplace":
            self.cart[product_id] = {
                "quantity": 1,
                "price": str(price),
                "has_sizes": False,
                "product_type": "marketplace"
            }
        else:  # normal product
            if getattr(product, "has_sizes", False):
                if not size:
                    raise ValueError("Size is required for this product.")
                
                if product_id not in self.cart:
                    self.cart[product_id] = {
                        "sizes": {size: quantity},
                        "price": str(price),
                        "has_sizes": True,
                        "product_type": "product"
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
                        "product_type": "product"
                    }
                elif overide_quantity:
                    self.cart[product_id]["quantity"] = quantity
                else:
                    self.cart[product_id]["quantity"] += quantity

        self.save()




    def remove(self, productID):
    #   Remove product from cart
        productID = str(productID)
        print("ID", productID)
        if productID in self.cart:
            del self.cart[productID]
            self.save()

    def clear(self):
        del self.session[settings.CART_SESSION_ID]
        self.save()
        print("Cart Cleared Successfully")

  
    def __iter__(self):
        cart = self.cart.copy()

        # Separate product IDs by type
        product_ids = []
        marketplace_ids = []

        for key in cart.keys():
            try:
                product_id = int(key)
                product_ids.append(product_id)
            except ValueError:
                pass  # in case keys are weird

        # Fetch both types of products
        products = Product.objects.filter(id__in=product_ids)
        marketplace_products = MarketPlaceProduct.objects.filter(id__in=product_ids)

        # Combine into a single list
        all_products = list(products) + list(marketplace_products)

        # Build a lookup dict
        product_lookup = {str(p.id): p for p in all_products}

        result = []
        for pid, item in cart.items():
            product = product_lookup.get(pid)
            if not product:
                continue

            # Serialize product
            if isinstance(product, Product):
                serialized = ProductSerializer(product).data
                serialized["product_type"] = "product"
            else:
                serialized = MarketPlaceProductSerializer(product).data
                serialized["product_type"] = "marketplace"

            item["product"] = serialized
            item["price"] = float(item["price"])

            # For products with sizes, set selected_size and quantity at top-level
            if serialized.get("has_sizes") and "sizes" in item:
                # Assuming only one size selected per cart item
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
