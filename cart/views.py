from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from .service import Cart
from products.models import Product, ProductSize
from products.models import MarketPlaceProduct
from rest_framework.permissions import AllowAny

class CartAPI(APIView):
    permission_classes=[AllowAny]
    def get(self, request):
        cart = Cart(request)
        try:
            data = list(cart.__iter__())  # already has product_type
            return Response({"data": data}, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # permission_classes=[AllowAny]
    # def post(self, request):
    #     cart = Cart(request)
    #     if "clear" in request.data:
    #         print("Cart clear")
    #         cart.clear()
    #         return Response({"message": "Cart cleared successfully"}, status=200)
    #     else:
    #         try:
    #             productID = request.data.get("productID")
    #             quantity = int(request.data.get("quantity") or 1) 
    #             override_quantity = bool(request.data.get("overide_quantity", False))

    #             product = None
    #             product_type = None

    #             # Try normal product
    #             try:
    #                 product = Product.objects.get(id=productID)
    #                 product_type = "normal"

    #                 size = request.data.get("size")  # Optional; required if has_sizes=True
    #                 result = cart.checkExistsInCart(product, size=size if product_type=="normal" else None, product_type=product_type)
    #                 if result == "exists":
    #                     return Response({"message": "Item Exits"}, status=200)
    #                 cart_quantity = cart.get_quantity(product, size=size)
    #                 intended_quantity = quantity if override_quantity else cart_quantity + quantity

    #                 if product.has_sizes:
    #                     if not size:
    #                         return Response({"error": "Size is required for this product."}, status=400)

    #                     try:
    #                         size_entry = ProductSize.objects.get(product=product, size=size)
    #                     except ProductSize.DoesNotExist:
    #                         return Response({"error": f"Size {size} not found for this product."}, status=404)

    #                     if intended_quantity > size_entry.stock:
    #                         return Response({
    #                             "error": f"Only {size_entry.stock} items available in size {size}."
    #                         }, status=400)

    #                 else:
    #                     available_stock = int(product.totalStock or 0)
    #                     if intended_quantity > available_stock:
    #                         return Response({
    #                             "error": f"Only {available_stock} items available."
    #                         }, status=400)

    #             except Product.DoesNotExist:
    #                 pass


    #             # Try marketplace product
    #             if product is None:
    #                 try:
    #                     product = MarketPlaceProduct.objects.get(id=productID)
    #                     product_type = "marketplace"
    #                     result = cart.checkExistsInCart(product, size=size if product_type=="normal" else None, product_type=product_type)
    #                     if result == "exists":
    #                         return Response({"message": "Item Exits"}, status=200)
    #                 except MarketPlaceProduct.DoesNotExist:
    #                     pass

    #             if product is None:
    #                 return Response({"error": "Product not found"}, status=404)

    #             if product_type == "marketplace" and quantity > 1:
    #                 return Response(
    #                     {"error": "Marketplace product quantity cannot be increased"},
    #                     status=400
    #                 )
    #             # Pass product_type to cart.add so it still knows how to store it
    #             # cart.add(product=product, quantity=quantity, overide_quantity=override_quantity)
    #             if product_type == "normal":
    #                 cart.add(
    #                     product=product,
    #                     quantity=quantity,
    #                     overide_quantity=override_quantity,
    #                     size=size if product.has_sizes else None
    #                 )
                    
    #                 return Response({"message": f"{product_type} product updated successfully", "product_type": product_type})
    #             elif product_type == "marketplace":
    #                 cart.add(
    #                     product=product,
    #                     quantity=quantity,
    #                     overide_quantity=override_quantity,
    #                     size=None
    #                 )
                    
    #                 return Response({"message": f"{product_type} product updated successfully", "product_type": product_type})


    #             return Response({
    #                 "message": f"{product_type} product updated successfully",
    #                 "product_type": product_type
    #             })

    #         except Exception as e:
    #             import traceback
    #             traceback.print_exc()
    #             return Response({"error": str(e)}, status=500)

    def post(self, request):
        """
        Add product to cart. If product already exists, increment quantity.
        """
        cart = Cart(request)
        if "clear" in request.data:
            cart.clear()
            return Response({"message": "Cart cleared successfully"}, status=200)

        try:
            productID = request.data.get("productID")
            quantity = int(request.data.get("quantity") or 1)
            size = request.data.get("size")

            product, product_type = self._get_product(productID)

            if not product:
                return Response({"error": "Product not found"}, status=404)
            if cart.checkExistsInCart(product, size, product_type) == "exists":
                return Response(
                {"message": "Item Exits"},
                status=200
                )
            # For marketplace: only 1 allowed
            if product_type == "marketplace" and quantity > 1:
                return Response(
                    {"error": "Marketplace product quantity cannot be increased"},
                    status=400
                )

            # Stock checks (similar to before)
            if product_type == "normal":
                self._check_stock(product, size, quantity, cart, override=False)

            cart.add(product, quantity=quantity, size=size, product_type=product_type)

            return Response(
                {"message": f"{product_type} product added to cart successfully"},
                status=201
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)
        
    def put(self, request):
        """
        Update/override product quantity in cart.
        """
        cart = Cart(request)
        try:
            productID = request.data.get("productID")
            quantity = int(request.data.get("quantity") or 1)
            size = request.data.get("size")

            product, product_type = self._get_product(productID)
            if not product:
                return Response({"error": "Product not found"}, status=404)

            if product_type == "marketplace":
                return Response({"error": "Marketplace product quantity cannot be updated"}, status=400)

            # Stock checks
            self._check_stock(product, size, quantity, cart, override=True)

            cart.add(product, quantity=quantity, overide_quantity=True, size=size, product_type=product_type)

            return Response(
                {"message": f"{product_type} product quantity updated successfully"},
                status=200
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)
        
    def delete(self, request, productID):
        cart = Cart(request)
        if productID:
            cart.remove(productID)
            return Response({"message": "Product removed from cart"}, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"error": "Product ID required"}, status=status.HTTP_400_BAD_REQUEST)

    def _get_product(self, productID):
        try:
            return Product.objects.get(id=productID), "normal"
        except Product.DoesNotExist:
            pass
        try:
            return MarketPlaceProduct.objects.get(id=productID), "marketplace"
        except MarketPlaceProduct.DoesNotExist:
            return None, None

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
    













