from django.urls import path
from .views import *

urlpatterns = [

    path('setcsrf/', set_csrf, name='set_csrf_token'),
    path('token/refresh/', CookieTokenRefreshView.as_view(),  name='token_refresh'),
    path('login/', login_user, name='loginUser'),
    path('loginsuperadmin/', login_superadmin, name='loginsuperadmin'),
    path('otp/<str:token>/', verify_otp_view, name='verify_token'),
    path('forgot-password-token/',forget_password_token,name='forget_password_token'),
    path('reset-password/<str:token>/',reset_password,name='reset_password'),
    path('getuser/',get_user_data,name='get_user_data'),
    path('logout/',logout_view, name='logout_view'),
]
