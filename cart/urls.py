from django.urls import path
from .views import *

urlpatterns = [
    # path('create/', createCheckout),
    # path('list/', listCheckout),
    path('', CartAPI.as_view(), name='cart'),
    path("<int:productID>/", CartAPI.as_view()),
]
