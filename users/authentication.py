# authentication.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.middleware.csrf import CsrfViewMiddleware

class JWTCookieAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # Get JWT from HTTP-only cookie
        raw_token = request.COOKIES.get('access_token')
        print("JWT token:", raw_token)
        
        if not raw_token:
            # No JWT token found, let other authentication methods handle it
            return None
        
        try:
            validated_token = self.get_validated_token(raw_token)
            return self.get_user(validated_token), validated_token
        except Exception as e:
            print(f"JWT authentication error: {str(e)}")
            return None