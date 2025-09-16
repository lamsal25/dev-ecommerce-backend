from django.urls import path
from .views import get_user_wishlist, add_to_wishlist,remove_from_wishlist

urlpatterns = [
    path('get/', get_user_wishlist, name='get_wishlist'),         # GET: user's wishlist
    path('add/', add_to_wishlist, name='add_to_wishlist'),    # POST: add to wishlist
    path('remove/<int:wishlist_id>/', remove_from_wishlist, name='remove_from_wishlist'),
]
