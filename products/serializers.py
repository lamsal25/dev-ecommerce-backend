from rest_framework import serializers

from api.serializers import CustomUserSerializer
from .models import Product, Category, ProductSize


class RecursiveField(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data


class CategorySerializer(serializers.ModelSerializer):
    subcategories = RecursiveField(many=True, read_only=True)
    image = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'parent', 'image','slug', 'subcategories']

    def validate_parent(self, value):
        if value and value == self.instance:
            raise serializers.ValidationError("A category cannot be its own parent.")
        return value


class CategoryNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class ProductSizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSize
        fields = ['id', 'size', 'stock'] 
class ProductSerializer(serializers.ModelSerializer):
    # Read-only nested category representation
    category = CategoryNameSerializer(read_only=True)
    
    # Write-only field for setting category
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )

    sizes = ProductSizeSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description','has_sizes','slug','category', 'category_id', 
            'originalPrice', 'discountPercentage', 'discountedPrice',
            'isAvailable', 'image', 'topImage', 
            'bottomImage', 'leftImage', 'rightImage',
            'totalStock','vendor','sizes'
        ]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        
        # NEW: Only include sizes if the product has sizes
        if not instance.has_sizes:
            data['sizes'] = []  # Return empty array for products without sizes
            
        return data



