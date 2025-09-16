from rest_framework import serializers
from .models import Vendor, VendorOrderItemStatus
from django.core.mail import send_mail
from django.core.signing import TimestampSigner
from django.conf import settings
from api.models import CustomUser, EmailOTP
import random
from supabase import create_client, Client
import os
from products.views import upload_image_to_supabase

SUPABASE_URL = os.getenv("SUPABASE_URL") 
SUPABASE_KEY = os.getenv("SUPABASE_KEY") 

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = '__all__'
        read_only_fields = ['isApproved', 'appliedAt']

    def create(self, validated_data):
        return super().create(validated_data)   


class VendorRegistrationSerializer(serializers.Serializer):
    # User fields
    email = serializers.EmailField()
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    # Vendor fields
    ownerName = serializers.CharField(max_length=255)
    phone = serializers.CharField(max_length=20)
    businessName = serializers.CharField(max_length=255)
    businessType = serializers.CharField(max_length=255)
    businessDescription = serializers.CharField(required=False, allow_blank=True)
    registrationNumber = serializers.CharField(max_length=255, required=False, allow_blank=True)
    registrationDocument = serializers.URLField(required=False, allow_blank=True)
    image = serializers.CharField(required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(max_length=255)
    country = serializers.CharField(max_length=255)
    website = serializers.URLField(required=False, allow_blank=True)

    def validate(self, data):
        # Validate user fields
        if CustomUser.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({"details": "This username already exists."})
        if CustomUser.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"details": "This email already exists."})
        
        # Validate vendor fields
        if Vendor.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"details": "This email is already registered as a vendor."})
        if data.get('phone') and Vendor.objects.filter(phone=data['phone']).exists():
            raise serializers.ValidationError({"details": "This phone number is already registered."})
        if Vendor.objects.filter(businessName=data['businessName']).exists():
            raise serializers.ValidationError({"details": "This business name is already registered."})
        if data.get('registrationNumber') and Vendor.objects.filter(registrationNumber=data['registrationNumber']).exists():
            raise serializers.ValidationError({"details": "This registration number is already registered."})
        if data.get('website') and Vendor.objects.filter(website=data['website']).exists():
            raise serializers.ValidationError({"details": "This website is already registered."})
        return data

    def create(self, validated_data):
        # Create user
        user = CustomUser.objects.create_user(
            email=validated_data["email"],
            username=validated_data["username"],
            password=validated_data["password"],
            role="vendor",
            is_active=False
        )
        request = self.context.get("request")
        logo_file = request.FILES.get("businessLogo")
        if logo_file:
            image_url = upload_image_to_supabase(logo_file)

        # Create vendor linked to user
        vendor = Vendor.objects.create(
            user=user,
            ownerName=validated_data["ownerName"],
            email=validated_data["email"],
            phone=validated_data.get("phone"),
            businessName=validated_data["businessName"],
            businessType=validated_data["businessType"],
            businessDescription=validated_data.get("businessDescription", ""),
            registrationNumber=validated_data.get("registrationNumber", ""),
            registrationDocument=validated_data.get("registrationDocument", ""),
            address=validated_data.get("address", ""),
            city=validated_data["city"],
            country=validated_data["country"],
            website=validated_data.get("website", ""),
            image=image_url
        )
    


        # Create OTP for email verification
        otp_code = f"{random.randint(100000, 999999)}"
        EmailOTP.objects.create(user=user, otp_code=otp_code)

        # Generate verification token
        signer = TimestampSigner()
        token = signer.sign(str(user.pk))
        verification_url = f"{settings.FRONTEND_URL}/verifyotp/{token}/"

        # Send email with OTP
        send_mail(
            subject="Verify Your Vendor Account",
            message=f"""
            Hello {vendor.ownerName},

            Your vendor application for {vendor.businessName} has been submitted successfully.
            
            Your OTP code is: {otp_code}
            
            Click this link to verify your email: {verification_url}
            
            The code expires in 1 hour.
            
            After verification, your application will be reviewed by our team.
            """,
            html_message=f"""
            <h3>Hello {vendor.ownerName},</h3>
            <p>Your vendor application for <strong>{vendor.businessName}</strong> has been submitted successfully.</p>
            <p>Your OTP code is: <strong>{otp_code}</strong></p>
            <p>Or <a href="{verification_url}">click here</a> to verify your email.</p>
            <p>The code expires in 1 hour.</p>
            <p>After verification, your application will be reviewed by our team.</p>
            """,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )

        # Notify admins about new vendor application 
        admin_emails = [admin.email for admin in CustomUser.objects.filter(role='admin', is_active=True)]
        if admin_emails:
            send_mail(
                subject="New Vendor Application Received",
                message=f"""
                A new vendor application has been received:
                
                Business Name: {vendor.businessName}
                Owner: {vendor.ownerName}
                Username: {user.username}
                Email: {user.email}
                Phone: {vendor.phone}
                Business Type: {vendor.businessType}
                
                This vendor needs to verify their email before the application can be reviewed.
                
                Please check the admin dashboard for full details.
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=admin_emails,
            )

        return user
    



## vendor order item list
class VendorOrderItemStatusSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name')
    order_id = serializers.IntegerField(source='order.id')
    delivery_status = serializers.CharField(source='order.delivery_status')
    payment_status = serializers.CharField(source='order.payment_status')   # ✅ from Order
    delivery_date = serializers.DateField(required=False)       
    
    class Meta:
        model = VendorOrderItemStatus
        fields = [
            'id', 'order_id', 'product_name', 'quantity', 'price',
            'status', 'delivery_status', 'payment_status',
            'delivery_date', 'createdAt'
        ]