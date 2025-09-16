from django.urls import path
from .views import *

urlpatterns = [
    # Product Review URLs
    path('getReviews/', get_product_reviews, name='get_product_reviews'),
    path('create/', create_product_review, name='create_product_review'),
    path('batch-product-review-stats/', batch_product_review_stats, name='batch-product-review-stats'),
    path('deleteReview/<int:review_id>/', delete_product_review, name='delete_review'),
    
    # Vendor Review URLs
    path('vendor-reviews/create/', create_vendor_review, name='create-vendor-review'),
    path('vendor-reviews/', get_vendor_reviews, name='get-vendor-reviews'),
    path('vendor-reviews/delete/<int:review_id>/', delete_vendor_review, name='delete-vendor-review'),
    
    # Product Review Reply URLs
    path('product-reviews/<int:review_id>/replies/create/', create_product_review_reply, name='create-product-review-reply'),
    path('replies/<int:reply_id>/update/', update_product_review_reply, name='update-product-review-reply'),
    path('replies/<int:reply_id>/delete/', delete_product_review_reply, name='delete-product-review-reply'),
]