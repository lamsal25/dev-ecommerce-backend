from django.urls import path
from .views import *

urlpatterns = [    
    path('register/', user_register, name='registerUser'),
    path('', UserManagementView.as_view()),               # GET all users
    path('<int:pk>/', UserManagementView.as_view()),   
    path('updateuser/<int:pk>/', update_user_profile, name='update_user_profile'),   

]
