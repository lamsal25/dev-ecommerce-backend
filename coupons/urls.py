from django.urls import path
from .views import *

urlpatterns = [
    # path('verifyCoupon/',verifyCoupon , name='verifyCoupon'),
    path('createCoupon/', createCoupon, name='createCoupon'),
    path('getCoupons/', getCoupons, name='getCoupons'),
    path('verifyCoupon/', verifyCoupon, name='verifyCoupon'),
    path('deleteCoupon/<int:id>/', deleteCoupon, name='deleteCoupon'),
    path('updateCoupon/<int:id>/', updateCoupon, name='update-coupon'),
]
