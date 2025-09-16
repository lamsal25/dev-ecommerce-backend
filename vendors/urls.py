from django.urls import path
# from . import views
from .views import *

urlpatterns = [
    path('createVendor/', createVendors, name='createVendors'),
    path('getVendors/', getVendors, name='getVendors'),
    path('getVendor/<int:pk>/', getVendor, name='get-vendor'),
    # path('apply/', applyAsVendor),
    path('pending/', listPendingVendors),
    path('approved/', listApprovedVendors),
    path('approve/<int:vendor_id>/', approveVendor),
    path('reject/<int:vendor_id>/', rejectVendor),
    path('getVendorProfile/', getVendorProfile, name='get-vendor-profile'),
    path('updateVendorProfile/', updateVendorProfile, name='update-vendor-profile'),
    path('deleteVendor/<int:pk>/', deleteVendor, name='delete-vendor'),
    path('orders/', getOrderStatus, name='getOrderStatus'),
    path('orders/<int:item_id>/update/', updateVendorOrderItemStatus, name='update-vendor-order-status'),
    path('salesSummary/', getVendorSalesSummary, name='vendor-sales-summary'),
    path('salesReport/', salesReport, name='vendor-sales-report'),
]
 