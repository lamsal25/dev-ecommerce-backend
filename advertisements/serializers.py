from rest_framework import serializers
from django.utils import timezone
from .models import Advertisement

class AdvertisementSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()   
    vendorName = serializers.CharField(source='vendor.vendor.businessName', read_only=True)
    class Meta:
        model = Advertisement
        fields = [
            'id', 'title', 'image', 'link', 'position', 'description',
            'startDate', 'endDate', 'isActive', 'paymentDone', 'isApproved',
            'createdAt', 'vendor', 'vendorName', 'status'
        ]
        read_only_fields = ('vendor','businessName', 'createdAt')

    # Move get_status inside the class
    def get_status(self, obj):
        now = timezone.now()
        if not obj.isApproved or not obj.paymentDone:
            return "pending" 
        elif obj.startDate <= now <= obj.endDate:
            return "active"
        elif now > obj.endDate:
            return "closed"
        else:
            return "scheduled"


class SponsoredAdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Advertisement
        fields = ['image']
