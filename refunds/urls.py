# urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Existing URLs...
    
    # Refund URLs
    path('order/refund-request/', views.create_refund_request, name='create_refund_request'),
    path('order/refund-requests/', views.get_refund_requests, name='get_refund_requests'),
    path('vendor/refund-requests/', views.get_vendor_refund_requests, name='get_vendor_refund_requests'),
    path('vendor/approved-refund-requests/', views.get_approved_vendor_refund_requests, name='get_approved_vendor_refund_requests'),
    path('update-status/<int:refund_id>/', views.update_refund_status, name='update_refund_status'),
]