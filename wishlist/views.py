from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Wishlist
from .serializers import WishlistSerializer
from products.models import Product  # Adjust if your Product model is in another app

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_wishlist(request):
    """Get all wishlist items for the authenticated user."""
    wishlist_items = Wishlist.objects.filter(user=request.user)
    serializer = WishlistSerializer(wishlist_items, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def add_to_wishlist(request):
    """Add a product to the authenticated user's wishlist."""
    product_id = request.data.get('product_id')

    if not product_id:
        return Response({'error': 'Product ID is required.'}, status=400)

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found.'}, status=404)

    wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)

    if not created:
        return Response({'message': 'Product already in wishlist.'}, status=200)

    serializer = WishlistSerializer(wishlist_item)
    return Response(serializer.data, status=201)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_from_wishlist(request, wishlist_id):
    try:
        wishlist_item = Wishlist.objects.get(id=wishlist_id)
        wishlist_item.delete()
        return Response({'message': 'Product removed from wishlist.'}, status=204)
    except Wishlist.DoesNotExist:
        return Response({'error': 'Wishlist item not found.'}, status=404)
    