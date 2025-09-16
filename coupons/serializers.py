# serializers.py
from rest_framework import serializers
from .models import Coupon, CouponUsage

class CouponSerializer(serializers.ModelSerializer):
    expiry_date = serializers.DateTimeField(format="%Y-%m-%d %H:%M")
    class Meta:
        model = Coupon
        fields = '__all__'

