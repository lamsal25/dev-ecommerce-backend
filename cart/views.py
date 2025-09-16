from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from .service import Cart
from products.models import Product, ProductSize
from rest_framework.permissions import AllowAny

class CartAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cart = Cart(request)
        try:
            data = list(cart.__iter__())
            return Response({"data": data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        cart = Cart(request)
        if "clear" in request.data:
            cart.clear()
            return Response({"message": "Cart cleared successfully"}, status=200)

        try:
            productID = request.data.get("productID")
            quantity = int(request.data.get("quantity") or 1)
            size = request.data.get("size")

            try:
                product = Product.objects.get(id=productID)
            except Product.DoesNotExist:
                return Response({"error": "Product not found"}, status=404)

            if cart.checkExistsInCart(product, size) == "exists":
                return Response({"message": "Item Exists"}, status=200)

            self._check_stock(product, size, quantity, cart, override=False)
            cart.add(product, quantity=quantity, size=size)

            return Response({"message": "Product added to cart successfully"}, status=201)

        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def put(self, request):
        cart = Cart(request)
        try:
            productID = request.data.get("productID")
            quantity = int(request.data.get("quantity") or 1)
            size = request.data.get("size")

            try:
                product = Product.objects.get(id=productID)
            except Product.DoesNotExist:
                return Response({"error": "Product not found"}, status=404)

            self._check_stock(product, size, quantity, cart, override=True)

            cart.add(product, quantity=quantity, overide_quantity=True, size=size)

            return Response({"message": "Product quantity updated successfully"}, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def delete(self, request, productID):
        cart = Cart(request)
        if productID:
            cart.remove(productID)
            return Response({"message": "Product removed from cart"}, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"error": "Product ID required"}, status=status.HTTP_400_BAD_REQUEST)

    def _check_stock(self, product, size, quantity, cart, override):
        cart_quantity = cart.get_quantity(product, size=size)
        intended_quantity = quantity if override else cart_quantity + quantity

        if product.has_sizes:
            if not size:
                raise ValueError("Size is required for this product.")
            size_entry = ProductSize.objects.get(product=product, size=size)
            if intended_quantity > size_entry.stock:
                raise ValueError(f"Only {size_entry.stock} items available in size {size}.")
        else:
            available_stock = int(product.totalStock or 0)
            if intended_quantity > available_stock:
                raise ValueError(f"Only {available_stock} items available.")