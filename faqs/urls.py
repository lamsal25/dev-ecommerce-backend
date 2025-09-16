from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_faq),
    path('update/<int:pk>/', views.update_faq),
    path('delete/<int:pk>/', views.delete_faq),
    path('all/', views.get_all_faqs),
]
