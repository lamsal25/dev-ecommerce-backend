from rest_framework import serializers
from .models import Order

class OrderSerializer(serializers.ModelSerializer):
    billing_details = serializers.JSONField()
    cart_items = serializers.JSONField()
    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ['user']
        extra_kwargs = {
            'payment_status': {'required': False},
            'order_status': {'required': False},
            'pidx': {'required': False},
            'transaction_id': {'required': False},

        }
    
