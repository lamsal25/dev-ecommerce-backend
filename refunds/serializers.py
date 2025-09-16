from rest_framework import serializers
from .models import RefundRequest, Product, Vendor, Order
import json
from api.serializers import CustomUserSerializer 

class RefundRequestSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
    user = CustomUserSerializer(read_only=True) 
    
    class Meta:
        model = RefundRequest
        fields = [
            'id', 'order', 'product', 'user', 'vendor', 'reason', 
            'status', 'admin_notes', 'created_at', 'updated_at',
            'product_name', 'vendor_name',
        ]
        read_only_fields = ['user', 'vendor', 'created_at', 'updated_at']

class RefundRequestCreateSerializer(serializers.Serializer):
    orderId = serializers.IntegerField()
    productId = serializers.IntegerField()
    reason = serializers.CharField(max_length=1000)
    
    def validate(self, data):
        try:
            order = Order.objects.get(id=data['orderId'])
            product = Product.objects.get(id=data['productId'])
            
            # Check if the product is in the order
            product_found = False
            
            # Method 1: If you have OrderItem model (recommended)
            try:
                from .models import OrderItem
                if OrderItem.objects.filter(order=order, product=product).exists():
                    product_found = True
            except ImportError:
                pass
            
            # Method 2: If cart_items is JSON field and contains product IDs
            if not product_found:
                cart_items = order.cart_items
                
                # If cart_items is a string (JSON), parse it
                if isinstance(cart_items, str):
                    try:
                        cart_items = json.loads(cart_items)
                    except json.JSONDecodeError:
                        cart_items = []
                
                # If cart_items is a list, check for product ID
                if isinstance(cart_items, list):
                    for item in cart_items:
                        # Check different possible structures
                        if isinstance(item, dict):
                            # Check for various key names that might contain product ID
                            product_id_keys = ['id', 'product_id', 'productID', 'product']
                            for key in product_id_keys:
                                if key in item and str(item[key]) == str(data['productId']):
                                    product_found = True
                                    break
                        elif str(item) == str(data['productId']):
                            # If cart_items is just a list of product IDs
                            product_found = True
                        
                        if product_found:
                            break
            
            if not product_found:
                raise serializers.ValidationError("Product not found in this order.")
                
            # Check if refund request already exists
            if RefundRequest.objects.filter(
                order=order, 
                product=product, 
                user=self.context['request'].user
            ).exists():
                raise serializers.ValidationError("Refund request already exists for this product.")
                
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found.")
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found.")
            
        return data