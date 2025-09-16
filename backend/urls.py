"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from api.views import  validate_google_token

# from users.views import GoogleLogin, GoogleLoginURL

urlpatterns = [
    path('admin/', admin.site.urls),
    path('products/', include('products.urls')),
    path('vendors/', include('vendors.urls')),
    path('cart/', include('cart.urls')),
    path('users/', include('users.urls')),
    path('api/', include('api.urls')),
    path('api-auth/', include('rest_framework.urls')),
    path('accounts/', include('allauth.urls')),
    path('api/google/validate_token/', validate_google_token, name='validate_token'),
    path('coupons/', include('coupons.urls')),
    path('payment/', include('payment.urls')),
    path('order/', include('orders.urls')),
    path('reviews/', include('reviews.urls')),
    path('advertisements/', include('advertisements.urls')),
    path('wishlist/', include('wishlist.urls')),
    path('rewards/', include('rewards.urls')),
    path('faqs/', include('faqs.urls')),
    path('refunds/', include('refunds.urls')),


]
