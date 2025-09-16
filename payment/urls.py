from django.urls import path
from .views import *

urlpatterns = [
    path('initKhalti/', initKhalti, name="initiateKhalti"),
    path('initEsewa/', initEsewa, name="initiateEsewa"),
    path('verifyKhalti/', verifyKhalti, name="verifyKhalti"),
    path('verifyEsewa/', verifyEsewa, name="initiateEsewa"),
]
