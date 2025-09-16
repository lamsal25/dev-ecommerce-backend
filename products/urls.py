from django.urls import path
from .views import *

urlpatterns = [
    # Category URLs
    path('createCategory/', createCategory, name='createCategory'),
    path('updateCategory/<int:pk>/', updateCategory, name='update_category'),
    path('deleteCategory/<int:pk>/', deleteCategory, name='delete_category'),
    path('getCategories/', getCategories, name='getCategories'),
    
    
    # Product URLs
    path('getAllProducts/', getAllProducts, name='getProducts'),
    path('getProduct/<int:pk>/', getProductbyID, name='getProductbyID'),
    path('updateProduct/<int:pk>/', updateProduct, name='update-product'),
    path('createProduct/', createProduct, name='createProduct'),
    path('location/<str:location>/', productByLocation, name='products-by-location'),
    path('deleteProduct/<int:id>/', delete_product, name='delete_product'),

    path('getProductByCategory/<int:category_id>/', getProductByCategory, name='getProductByCategory'),
    path('createMarketPlaceProduct/',createMarketplaceProduct,name="createMarketplaceProduct"),
    #Search product
    path('searchProduct/', searchProducts, name='searchProduct'),
    path('getMarketplaceProductByCategory/<int:category_id>/', getMarketPlaceProductByCategory, name='getMarketplaceProductByCategory'),
    path('getMarketplaceProductById/<int:pk>/', getMarketPlaceProductbyID, name='getMarketplaceProductById'),
    path('getMarketplaceProductsByUser/',getMarketplaceProductByUser, name='getMarketplaceProductsByUser'),
    path('deleteMarketplaceProducts/<int:pk>/',deleteMarketplaceProduct, name='deleteMarketplaceProducts'),
    path('updateMarketplaceProduct/<int:pk>/', updateMarketplaceProduct, name='updateMarketplaceProduct'),
    path('getApprovedMarketplaceProducts/<int:category_id>', getApprovedMarketplaceProductsByCategory, name='getApprovedMarketplaceProducts'),
    path('getUnapprovedMarketplaceProducts/', getUnapprovedMarketplaceProducts, name='getUnapprovedMarketplaceProducts'),
    path('approveMarketplaceProduct/<int:pk>/', approveMarketplaceProduct, name='approveMarketplaceProduct'),
    path('getProductsByVendor/', getProductsByVendor, name='getProductsByVendor'),
    path('getProductsByVendorId/<int:pk>/', getProductsByVendorId, name='getProductsByVendorId'),
]
