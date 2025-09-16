from rest_framework import serializers
from .models import ProductReview, VendorReview, ProductReviewReply, VendorReviewReply

class ProductReviewReplySerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    
    class Meta:
        model = ProductReviewReply
        fields = ['id', 'vendor_name', 'reply', 'created_at', 'updated_at']
        read_only_fields = ['id', 'vendor_name', 'created_at', 'updated_at']

class ProductReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    vendor_reply = ProductReviewReplySerializer(read_only=True)  # Add this line
    
    class Meta:
        model = ProductReview
        fields = ['id', 'user', 'user_name', 'user_email', 'product', 'rating', 'comment', 'created_at', 'vendor_reply']  # Include vendor_reply
        read_only_fields = ['id', 'user', 'user_name', 'user_email', 'created_at', 'vendor_reply']
    
    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

class VendorReviewReplySerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    
    class Meta:
        model = VendorReviewReply
        fields = ['id', 'vendor_name', 'reply', 'created_at', 'updated_at']
        read_only_fields = ['id', 'vendor_name', 'created_at', 'updated_at']

class VendorReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    vendor_reply = VendorReviewReplySerializer(read_only=True)  # Add this line
    
    class Meta:
        model = VendorReview
        fields = ['id', 'user', 'user_name', 'user_email', 'vendor', 'rating', 'comment', 'created_at', 'vendor_reply']  # Include vendor_reply
        read_only_fields = ['id', 'user', 'user_name', 'user_email', 'created_at', 'vendor_reply']
    
    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value