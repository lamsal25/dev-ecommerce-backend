from django.urls import path
from .views import *

urlpatterns = [
    path('active-ads/', activeAdvertisements, name='active-ads'),
    path('vendor/create/', createAdvertisement, name='create-ad'),
    # path('vendor/my-ads/', vendor_ads, name='my-ads'),
    # path('sponsored/', get_sponsored_ads, name='sponsored-ads'),
    path('pending-ads/', pendingAds, name='pending-ads'),
    path('approve/<int:ad_id>/', approveAdvertisement, name='approve-ad'),
    path('reject/<int:ad_id>/', rejectAdvertisement, name='reject-ad'),
    path("sponsoredAds/", getSponsoredAds, name="get-sponsored-ads"),
    path("getAdsByVendor/", getAdvertisementsByVendor, name="get-ads-by-vendor"),
    path("getAllPendingAds/", getAllPendingAds, name="get-all-pending-ads"),
    path("getAdsByPosition/<str:position>/", getAdsByPosition, name="get-ads-by-position"),
    path('updatePaymentStatus/<int:pk>/', updatePaymentStatus, name='update-payment-status'),
]
 