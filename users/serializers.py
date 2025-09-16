from rest_framework import serializers
from api.models import CustomUser, EmailOTP
from .models import UserProfile
from django.core.mail import send_mail
from django.core.signing import TimestampSigner
from django.conf import settings
import random

class RegisterSerializer(serializers.Serializer): 
    # User fields
    email = serializers.EmailField()
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=CustomUser.ROLE_CHOICES)

    # Profile fields
    firstName = serializers.CharField()
    lastName = serializers.CharField()
    mobile = serializers.CharField()
    dateOfBirth = serializers.DateTimeField()
    gender = serializers.CharField()
    address = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    country = serializers.CharField()
    postalCode = serializers.CharField()

    def validate(self, data):
        if CustomUser.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({"details": "This username already exists."})
        if CustomUser.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"details": "This email already exists."})
        return data

    def create(self, validated_data):
        #  Divide the data manually
        user_data = {
            "email": validated_data["email"],
            "username": validated_data["username"],
            "password": validated_data["password"],
            "role": validated_data["role"]
        }

        profile_data = {
            "firstName": validated_data["firstName"],
            "lastName": validated_data["lastName"],
            "mobile": validated_data["mobile"],
            "dateOfBirth": validated_data["dateOfBirth"],
            "gender": validated_data["gender"],
            "address": validated_data["address"],
            "city": validated_data["city"],
            "state": validated_data["state"],
            "country": validated_data["country"],
            "postalCode": validated_data["postalCode"]
        }

        #  Create the user
        user = CustomUser.objects.create_user(
            email=user_data["email"],
            username=user_data["username"],
            password=user_data["password"],
            role=user_data["role"],
            is_active=False  # Keep inactive until verified
        )

        #  Create the profile
        UserProfile.objects.create(user=user, **profile_data)

        #  Create OTP
        otp_code = f"{random.randint(100000, 999999)}"
        EmailOTP.objects.create(user=user, otp_code=otp_code)

        #  Verification token and email
        signer = TimestampSigner()
        token = signer.sign(str(user.pk))
        verification_url = f"{settings.FRONTEND_URL}/verifyotp/{token}/"

        send_mail(
            subject="Your Account Verification",
            message=f"""
            Hello {user.username},

            Your OTP code is: {otp_code}

            Click this link to verify: {verification_url}

            The code expires in 1 hour.
            """,
            html_message=f"""
            <h3>Hello {user.username},</h3>
            <p>Your OTP code is: <strong>{otp_code}</strong></p>
            <p>Or <a href="{verification_url}">click here</a> to verify your account.</p>
            <p>The code expires in 1 hour.</p>
            """,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )

        return user
    

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'

class UserListSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)  

    class Meta:
        model = CustomUser
        fields = ["id", "email", "username", "profile"]
