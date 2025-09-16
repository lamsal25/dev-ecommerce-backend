from rest_framework import serializers
from .models import Wishlist
from products.models import Product  # Adjust import if needed

class WishlistSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    product_id = serializers.ReadOnlyField(source='product.id')
    original_price = serializers.ReadOnlyField(source='product.originalPrice')
    discounted_price = serializers.ReadOnlyField(source='product.discountedPrice')
    product_image = serializers.ReadOnlyField(source='product.image')

    class Meta:
        model = Wishlist
        fields = [
            'id',
            'user',
            'product',
            'product_id',
            'product_name',
            'original_price',
            'discounted_price',
            'product_image',
            'added_at'
        ]
        read_only_fields = ['id', 'added_at', 'user']
