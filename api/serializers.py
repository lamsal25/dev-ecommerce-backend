import random
from django.contrib.auth import get_user_model, authenticate
from django.core.mail import send_mail
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from api.models import EmailOTP
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.conf import settings
from users.serializers import UserProfileSerializer
from vendors.models import Vendor
from .models import CustomUser

User = get_user_model()

class CustomUserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)  # 👈 include the related profile

    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'username', 'profile','isEmailVerified','role']  #

class VerifyOTPSerializer(serializers.Serializer):
    token    = serializers.CharField()
    otp_code = serializers.CharField()

    def validate(self, data):
        signer = TimestampSigner()
        token  = data.get('token')
     
        # 1) Validate + unsign the token
        try:
            # max_age in seconds, e.g. 3600 → 1 hour
            user_pk = signer.unsign(token, max_age=getattr(settings, 'OTP_TOKEN_MAX_AGE', 3600))
        except SignatureExpired:
            raise serializers.ValidationError({'token': 'Verification link expired.'})
        except BadSignature:
            raise serializers.ValidationError({'token': 'Invalid verification link.'})

        # 2) Look up the user
        try:
            user = User.objects.get(pk=user_pk)
        except User.DoesNotExist:
            raise serializers.ValidationError({'token': 'Invalid verification link.'})

        # 3) Look up the OTP
        try:
            otp = EmailOTP.objects.get(user=user)
        except EmailOTP.DoesNotExist:
            raise serializers.ValidationError({
                'otp_code': 'No OTP found. Please request a new one.'
            })

        # 4) Check the OTP code
        if otp.otp_code != data.get('otp_code'):
            raise serializers.ValidationError({'otp_code': 'Incorrect OTP.'})

        # 5) All good → activate and clean up
        user.is_active          = True
        user.isEmailVerified  = True
        user.save()
        otp.delete()

        # Optionally, include the user on the validated_data
        data['user'] = user
        return data

class LoginSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField(write_only=True)

    
    def validate(self, data):
        identifier = data.get('email')
        try:
            user=CustomUser.objects.get(email=identifier)
        except User.DoesNotExist:
            raise serializers.ValidationError({"details": "User doesnt exist."}, code=401)
        if user.is_superuser==True:
            raise serializers.ValidationError({"details":"Admin cannot login from here."}, code=401)
        if user.role == "vendor":
            if user.vendor.isApproved==False:
                raise serializers.ValidationError({"details":"Your account is not approved yet."}, code=401)
       
        
        if user.isEmailVerified==False:
             raise serializers.ValidationError({"details":"Your Email Has Not Been Verified Yet. Please Verify Your Email"}, code=401)
        user = authenticate(username=data['email'], password=data['password'])      
        if user is None:
            raise serializers.ValidationError({"details":"Invalid credentials."}, code=401)
        
        data["user"] = user
        return data

    def create(self, validated_data):
        user = validated_data["user"]
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id":user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
            }
        }


class ResendOTPSerializer(serializers.Serializer):
    username = serializers.CharField()

    def validate(self, data):
        try:
            user = User.objects.get(username=data["username"])
        except User.DoesNotExist:
            raise serializers.ValidationError({"username": "User not found."})
        data["user"] = user
        return data

    def create(self, validated_data):
        user = validated_data["user"]
        otp_code = f"{random.randint(100000, 999999)}"
        EmailOTP.objects.update_or_create(user=user, defaults={"otp_code": otp_code})
        send_mail(
            subject="Your New OTP Code",
            message=f"Hello {user.username}, your new OTP is {otp_code}.",
            from_email="no-reply@yourapp.com",
            recipient_list=[user.email],
        )
        return {}

class ForgetPasswordSerializer(serializers.Serializer):
    email=serializers.EmailField()

    def validate(self, data):
        try:
            user= User.objects.get(email=data['email'])
        except User.DoesNotExist:
            raise serializers.ValidationError({"email":"User Not Found"})
        return user