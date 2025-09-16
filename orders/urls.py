from django.urls import path
from .views import *

urlpatterns = [
    path('createOrder/', createOrder, name="createOrder"),
    path('getOrders/', getOrders, name="getOrders"),
    path('getOrder/<int:orderID>/',getOrder, name='getOrder'),
    path('downloadReceipt/<int:orderID>/', downloadReceipt, name='downloadReceipt'),
    path('updateStatus/<int:order_id>/received/', markOrderReceived, name='markOrderReceived'),

]
