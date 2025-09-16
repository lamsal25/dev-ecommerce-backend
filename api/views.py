from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework import status
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.contrib.auth import logout
from django.http import JsonResponse

from google.oauth2 import id_token
from google.auth.transport import requests
import os
from django.core.mail import send_mail
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired

from users.models import UserProfile
from .serializers import (
    CustomUserSerializer,
    VerifyOTPSerializer,
    LoginSerializer,
    ResendOTPSerializer,
    ForgetPasswordSerializer,
    User
)

# -------------------------------------------
# Endpoint to set CSRF cookie for frontend
# -------------------------------------------
@api_view(['GET'])
@ensure_csrf_cookie  # Ensures a CSRF cookie is set on response
@permission_classes([AllowAny])  # Publicly accessible
def set_csrf(request):
    # Debug: print authenticated user (will be AnonymousUser for most cases)
    print(request.user)
    response = Response({"detail": "CSRF cookie set"})
    # Allow CORS for local React dev server
    response["Access-Control-Allow-Origin"] = "http://localhost:3000"
    response["Access-Control-Allow-Credentials"] = "true"
    return response

# --------------------------------------------------
# Custom JWT refresh view storing tokens in cookies
# --------------------------------------------------
class CookieTokenRefreshView(TokenRefreshView):
    """
    POST /api/token/refresh/
    • Reads old refresh token from cookie
    • Returns new access token and optionally new refresh token
    • Sets both tokens as HttpOnly cookies
    """
    serializer_class = TokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        # Extract refresh token from cookie or header
        old_rt = request.COOKIES.get('refresh_token')
        
        # If not in cookies, try to get from Authorization header
        if not old_rt:
            auth_header = request.META.get('HTTP_AUTHORIZATION')
            if auth_header and auth_header.startswith('Bearer '):
                old_rt = auth_header.split(' ')[1]
        
        # If still not found, try request body (for compatibility)
        if not old_rt:
            old_rt = request.data.get('refresh')
        
        if not old_rt:
            return Response(
                {'error': 'Refresh token not found in cookies, headers, or request body'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Validate and potentially rotate the refresh token
        serializer = self.get_serializer(data={'refresh': old_rt})
        serializer.is_valid(raise_exception=True)
        new_access = serializer.validated_data['access']
        new_refresh = serializer.validated_data.get('refresh', None)

        # Calculate cookie lifetimes from settings
        access_max_age = settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()
        refresh_max_age = settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()

        # Build response and set cookies
        resp = Response({'access': new_access,'refresh':new_refresh}, status=status.HTTP_200_OK)
        resp.set_cookie(
        key="access_token",
        value=new_access,
        httponly=True,
        secure=True,
        samesite="Lax",
        max_age=int(access_max_age)
        )
        if new_refresh:
            # Only set rotated refresh token if rotation is enabled
            resp.set_cookie(
                key="refresh_token",
        value=new_refresh,
        httponly=True,
        secure=True,
        samesite="Lax",
        max_age=int(refresh_max_age)
            )
        return resp
# ---------------------------------------------------
# Validate Google OAuth2 token and login/register user
# ---------------------------------------------------
@api_view(["POST"])
@permission_classes([AllowAny])
def validate_google_token(request):
    # Validate token presence
    token = request.data.get("token")
    if not token:
        return Response(
            {"error": "Google token is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    print(token)
    try:
        # Verify token
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            os.getenv("GOOGLE_CLIENT_ID"),
            clock_skew_in_seconds=10  # Allow 10s clock skew
        )
        print(idinfo)
        # Validate email
        email = idinfo.get("email")
        print("email:", email)
        if not email or not idinfo.get("email_verified", False):
            return Response(
                {"error": "Verified email is required"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check user existence
        try:
            print("Checking if user exists...")
            user = User.objects.get(email=email)         
            print("user found:", user)
                
        except User.DoesNotExist:
            print("Creating new user...")
            try:
               

                user = User.objects.create_user(
                    email=email,
                    username=email,
                    first_name=idinfo.get("given_name", ""),
                    last_name=idinfo.get("family_name", ""),
                    isEmailVerified=True,
                )
                profile_data = {
                    "firstName": idinfo.get("given_name", ""),
                    "lastName": idinfo.get("family_name", ""),
            
                }
                print(profile_data)
                UserProfile.objects.create(user=user, **profile_data)

                
                # Set unusable password for OAuth users
                user.set_unusable_password()
                user.save()
                
                print("New user created successfully:", user)
                        
            except Exception as create_error:
                print(f"User creation error: {str(create_error)}")
                import traceback
                traceback.print_exc()
                return Response(
                    {"error": f"Failed to create user: {str(create_error)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        response_data = {
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "isEmailVerified": user.isEmailVerified,
                "refresh": str(refresh),
                "access": str(refresh.access_token)
            }
        }
        print(response_data)
        # Set secure cookies
        response = Response(response_data)
        set_jwt_cookies(response, str(refresh.access_token), str(refresh))
        return response

    except ValueError as e:
        return Response(
            {"error": "Invalid Google token: " + str(e)},
            status=status.HTTP_401_UNAUTHORIZED
        )
    except Exception as e:
        return Response(
            {"error": "Authentication failed"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def set_jwt_cookies(response, access_token, refresh_token):
    """Helper to set secure JWT cookies"""
    secure_flag = not settings.DEBUG
    response.set_cookie(
        key='access_token',
        value=access_token,
        httponly=True,
        secure=secure_flag,
        samesite='Lax',
        max_age=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds(),
        domain=settings.SESSION_COOKIE_DOMAIN or None
    )
    response.set_cookie(
        key='refresh_token',
        value=refresh_token,
        httponly=True,
        secure=secure_flag,
        samesite='Lax',
        max_age=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds(),
        domain=settings.SESSION_COOKIE_DOMAIN or None
    )
def set_jwt_cookies(response, access_token, refresh_token):
    """Helper to set secure JWT cookies"""
    secure_flag = not settings.DEBUG
    response.set_cookie(
        key='access_token',
        value=access_token,
        httponly=True,
        secure=secure_flag,
        samesite='Lax',
        max_age=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds(),
        domain=settings.SESSION_COOKIE_DOMAIN or None
    )
    response.set_cookie(
        key='refresh_token',
        value=refresh_token,
        httponly=True,
        secure=secure_flag,
        samesite='Lax',
        max_age=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds(),
        domain=settings.SESSION_COOKIE_DOMAIN or None
    )
# --------------------------------------------
# OTP verification endpoint
# --------------------------------------------
@api_view(["POST"])
@permission_classes([AllowAny])
def verify_otp_view(request, token):
    print(token)  # Debug incoming token from URL
    data = request.data.copy()
    data['token'] = token
    try:
        serializer = VerifyOTPSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        # Generate tokens upon successful verification
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        response = Response(
            {'detail': 'Verified and logged in!', 'user': {'username': user.username, 'email': user.email},'access': access_token, 'refresh': refresh_token},
            status=status.HTTP_200_OK
        )
        # Set JWT cookies
        response.set_cookie(
            key='refresh_token', value=refresh_token,
            httponly=True, secure=not settings.DEBUG, samesite='Lax',
            max_age=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()
        )
        response.set_cookie(
            key='access_token', value=access_token,
            httponly=True, secure=not settings.DEBUG, samesite='Lax',
            max_age=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()
        )
        return response
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# --------------------------------------------
# Traditional username/password login view
# --------------------------------------------
@api_view(["POST"])
@permission_classes([AllowAny])
def login_user(request):
    """
    Authenticates user via serializer and returns JWT tokens in cookies and response body.
    Also sets a readable user_id cookie for frontend convenience.
    """
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    tokens = serializer.save()
    access = tokens["access"]
    refresh = tokens["refresh"]
    user = tokens["user"]
    print(user)

    access_max_age = settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()
    refresh_max_age = settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()

    # Build response with tokens and user info
    resp = Response({
        "user": {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"]
        },
        "access": access,
        "refresh": refresh
    }, status=status.HTTP_200_OK)

    # Set HttpOnly cookies
    resp.set_cookie(
        key="access_token",
        value=access,
        httponly=True,
        secure=True,
        samesite="Lax",
        max_age=int(access_max_age)
    )
    resp.set_cookie(
        key="refresh_token",
        value=refresh,
        httponly=True,
        secure=True,
        samesite="Lax",
        max_age=int(refresh_max_age)
    )

    # Set non-HttpOnly cookie for frontend JS access
    resp.set_cookie(
        key="user_id",
        value=user["id"],
        httponly=False,
        secure=False,
        samesite="Lax",
        max_age=int(refresh_max_age)
    )

    return resp




@api_view(["POST"])
@permission_classes([AllowAny])
def login_superadmin(request):
    """
    Authenticates superadmin and returns JWT tokens in cookies and response body.
    Ensures only superusers can log in through this endpoint.
    """
    email = request.data.get("email")
    password = request.data.get("password")

    user = authenticate(username=email, password=password)
    print(user)

    if user is None:
        return Response({"error": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

    if not user.is_superuser:
        return Response({"error": "Not authorized as superadmin."}, status=status.HTTP_403_FORBIDDEN)

    # Generate tokens
    refresh = RefreshToken.for_user(user)
    access = str(refresh.access_token)
    refresh = str(refresh)

    access_max_age = settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()
    refresh_max_age = settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()

    resp = Response({
        "user": {
            "id": user.id,
            "email": user.email,
            "role": "superadmin"
        },
        "access": access,
        "refresh": refresh
    }, status=status.HTTP_200_OK)

    # HttpOnly secure cookies
    resp.set_cookie(
        key="access_token",
        value=access,
        httponly=True,
        secure=True,
        samesite="Lax",
        max_age=int(access_max_age)
    )
    resp.set_cookie(
        key="refresh_token",
        value=refresh,
        httponly=True,
        secure=True,
        samesite="Lax",
        max_age=int(refresh_max_age)
    )
    # JS-accessible cookie
    resp.set_cookie(
        key="user_id",
        value=user.id,
        httponly=False,
        secure=False,
        samesite="Lax",
        max_age=int(refresh_max_age)
    )

    return resp


# --------------------------------------------
# OTP resend endpoint
# --------------------------------------------
@api_view(["POST"])
@permission_classes([AllowAny])
def resend_otp_view(request):
    serializer = ResendOTPSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response({"message": "OTP resent to your email."})

# --------------------------------------------
# Generate and email password reset token
# --------------------------------------------
@api_view(["POST"])
@permission_classes([AllowAny])
def forget_password_token(request):
    data = request.data.copy()
    email = data.get("email")
    if not email:
        return Response({"error": "Email is required"}, status=400)
    user = User.objects.get(email=email)
    serializer = ForgetPasswordSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    signer = TimestampSigner()
    token = signer.sign(str(user.pk))
    password_url = f"{settings.FRONTEND_URL}/resetpassword/{token}/"
    # Send reset link via email
    send_mail(
        subject="password change",
        message=f"Hello {user.username},\nClick this link to reset your password: {password_url}\nThe code expires in 1 hour.",
        html_message=(
            f"<html><body>...<a href=\"{password_url}\">Reset Your Password</a>..."  # Simplified for brevity
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
    return Response({"message": "Password reset link sent to your email."}, status=200)

# --------------------------------------------
# Reset password using signed token
# --------------------------------------------
@api_view(["PUT"])
@permission_classes([AllowAny])
def reset_password(request, token):
    try:
        signer = TimestampSigner()
        user_id = signer.unsign(token, max_age=3600)  # 1 hour max age
        user = User.objects.get(pk=user_id)
    except (BadSignature, SignatureExpired, User.DoesNotExist):
        return Response({"error": "Invalid or expired token"}, status=400)
    new_password = request.data.get("password")
    if not new_password:
        return Response({"error": "New password is required"}, status=400)
    user.set_password(new_password)
    user.save()
    return Response({"message": "Password reset successfully"}, status=200)

# --------------------------------------------
# Retrieve current authenticated user data
# --------------------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_data(request):
    user = request.user  # From JWT authentication
    serializer = CustomUserSerializer(user)
    return Response(serializer.data, status=200)





@api_view(["POST"])
def logout_view(request):
    logout(request)  # Clear Django session if using session auth
    
    response = Response(
        {"detail": "Successfully logged out"}, 
        status=200
    )
    
    # Clear all auth cookies
    cookies_to_delete = [
        'sessionid',       # Django session cookie
        'csrftoken',       # CSRF token
        'access_token',    # JWT access token
        'refresh_token',   # JWT refresh token
        'access',          # Alternative JWT cookie name
        'refresh'          # Alternative JWT cookie name
    ]
    
    for cookie in cookies_to_delete:
        response.delete_cookie(cookie)
    
    # Additional security headers (optional)
    response["Cache-Control"] = "no-store"
    response["Pragma"] = "no-cache"
    
    return response


