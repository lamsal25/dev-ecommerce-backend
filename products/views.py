import time
import json
import uuid
import traceback
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import Category, Product, ProductSize,Vendor
from .serializers import CategorySerializer, ProductSerializer, ProductSizeSerializer
from rest_framework import status
from django.core.mail import send_mail
import time
from django.http import JsonResponse
from api.permissions import IsAdmin, IsVendor, IsUser
from django.shortcuts import get_object_or_404
from supabase import create_client, Client
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import Product, ProductSize
import os
from django.conf import settings
from .models import MarketPlaceProduct
from .serializers import MarketPlaceProductSerializer
from api.models import  CustomUser  # Adjust import paths if needed
import traceback

# gets value from .env
SUPABASE_URL = os.getenv("SUPABASE_URL") 
SUPABASE_KEY = os.getenv("SUPABASE_KEY") 

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Create Category
@api_view(['POST'])
def createCategory(request):
    user = request.user
    print(user.id)
    try:
        print("Received data:", request.data)
        name = request.POST.get("name")
        image = request.FILES.get("image")
        parent_id = request.POST.get("parent")  # Note: using request.POST instead of request.data

        public_url = upload_image_to_supabase(image) if image else None
        # Create the category
        category = Category.objects.create(
            name=name,
            image=public_url,
            parent_id=parent_id if parent_id else None
        )
         
        serializer = CategorySerializer(category)
        return Response({
            "message": "Category created successfully",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        print(f"Error in createCategory: {str(e)}")
        traceback.print_exc()
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Get Categories
@api_view(['GET'])
@permission_classes([AllowAny])
def getCategories(request):
    top_categories = Category.objects.filter(parent__isnull=True)
    serializer = CategorySerializer(top_categories, many=True)
    return Response({
        "message": "Categories fetched successfully",
        "data": serializer.data
    }, status=status.HTTP_200_OK)



#Edit Category 
# Note: This will only update the category if it has no subcategories. If it does, it will return an error message.
@api_view(['PUT'])
@permission_classes([AllowAny])
def updateCategory(request, pk):
    try:
        category = Category.objects.get(pk=pk)
    except Category.DoesNotExist:
        return Response({"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        name = request.data.get("name")
        image = request.FILES.get("image")
        parent_id = request.data.get("parent")
        
        # Update name if provided
        if name:
            category.name = name
        
        # Update parent if provided
        if parent_id:
            # Check that parent isn't self
            if int(parent_id) == category.id:
                return Response({"error": "A category cannot be its own parent"}, status=status.HTTP_400_BAD_REQUEST)
            category.parent_id = parent_id
        elif parent_id == "":
            category.parent_id = None
        
        # Update image if provided
        if image:
            file_name = f"{int(time.time())}_{image.name}"
            print(f"Uploading updated category image: {file_name} to Supabase...")
            upload_result = supabase.storage.from_("images").upload(file_name, image.read())
            
            public_url_data = supabase.storage.from_("images").get_public_url(file_name)
            category.image = public_url_data
        
        category.save()
        serializer = CategorySerializer(category)
        return Response({
            "message": "Category updated successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        print("Category update exception:")
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)


# Delete Category
# Note: This will only delete the category if it has no subcategories. If it does, it will return an error message.
@api_view(['DELETE'])
@permission_classes([AllowAny])
def deleteCategory(request, pk):
    try:
        category = Category.objects.get(pk=pk)
    except Category.DoesNotExist:
        return Response({"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        # Check if category has subcategories
        if category.subcategories.exists():
            return Response({
                "error": "Cannot delete category with subcategories. Please delete or reassign subcategories first."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # TODO: If you need to delete the image from Supabase storage, do it here
        #If you have the file path/name stored, you can use:
        if category.image:
            file_name = category.image.split('/')[-1]
            supabase.storage.from_("images").remove([file_name])
        
        category_name = category.name
        category.delete()
        return Response({
            "message": f"Category '{category_name}' deleted successfully"
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        print("Category delete exception:")
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)





########################## Product ###############################

#Upload image to Supabase
def upload_image_to_supabase(image):
    """
    Uploads an image to Supabase Storage and returns its public URL.
    """
    try:
        file_name = f"{uuid.uuid4().hex}_{image.name}"
        file_path = f"products/{file_name}"

        print("Uploading image to Supabase...")
        upload_result = supabase.storage.from_("images").upload(file_path, image.read())

        # Handle errors
        if hasattr(upload_result, "error") and upload_result.error:
            print("Upload error:", upload_result.error)
            return None

        # Get the public URL properly
        public_url = supabase.storage.from_("images").get_public_url(file_path)
        return public_url  # Just return the URL directly

    except Exception as e:
        print("Upload exception:", e)
        traceback.print_exc()  # Add this to get more detailed error info
        return None


# Create Product
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def createProduct(request):
    print("Received data:", request.data)
    try:
        name = request.data.get("name")
        description = request.data.get("description")
        category_id = request.data.get("category_id")
        originalPrice = request.data.get("originalPrice")
        discountPercentage = request.data.get("discountPercentage")
        isAvailable = request.data.get("isAvailable") == "true"
        totalStock = request.data.get("totalStock")
        
        # NEW: Check if product has sizes
        has_sizes = request.data.get("has_sizes") == "true"
        sizes = request.data.getlist("sizes[]") or request.data.getlist("sizes") or []
        
        # Validation: If has_sizes is True, sizes array should not be empty
        if has_sizes and not sizes:
            return JsonResponse({"error": "Sizes are required when has_sizes is true"}, status=400)
        
        # If has_sizes is False, clear any sizes data
        if not has_sizes:
            sizes = []
        
        op = float(request.data.get("originalPrice"))
        dp = float(request.data.get("discountPercentage"))
        discountedPrice = op * (1 - dp / 100)
        
        print("Parsing sizes...")
        parsed_sizes = []
        for size_str in sizes:
            try:
                parsed_sizes.append(json.loads(size_str))
            except json.JSONDecodeError as e:
                print("Error decoding size:", size_str, e)

        user_id = request.user.id
        print("Vendor ID:", user_id)
        vendor = Vendor.objects.get(user_id=user_id)
        print("Vendor:", vendor.id)
        vendor_id = vendor.id

        # Handle image uploads
        def get_image_url(img):
            return upload_image_to_supabase(img) if img else 'Unknown url'

        image_urls = {
            'image': get_image_url(request.FILES.get("image")),
            'topImage': get_image_url(request.FILES.get("topImage")),
            'bottomImage': get_image_url(request.FILES.get("bottomImage")),
            'leftImage': get_image_url(request.FILES.get("leftImage")),
            'rightImage': get_image_url(request.FILES.get("rightImage")),
        }
        print("url is"+ str(image_urls))

        print("Creating product...")
        product = Product.objects.create(
            name=name,
            description=description,
            category_id=category_id,
            originalPrice=originalPrice,   
            discountedPrice=str(discountedPrice),
            discountPercentage=(discountPercentage),   
            isAvailable=isAvailable,
            totalStock=totalStock,
            vendor_id=vendor_id,
            has_sizes=has_sizes,  # NEW: Set the has_sizes field
            **image_urls
        )

        # Only create ProductSize objects if the product has sizes
        if has_sizes:
            for size_obj in parsed_sizes:
                ProductSize.objects.create(
                    product=product,
                    size=size_obj.get("size"),
                    stock=size_obj.get("stock", 0)
                )

        return JsonResponse({
            "message": "Product created successfully",
            "product_id": product.id,
            "has_sizes": has_sizes
        })

    except Vendor.DoesNotExist:
        return JsonResponse({"error": "Vendor not found for the user"}, status=400)
    except Exception as e:
        print("Exception occurred:", e)
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)

# Get All Products by ID 
@api_view(['GET'])
@permission_classes([AllowAny])
def getProductbyID(request, pk):
    """
    Fetch a single product by its primary key (ID)
    """
    try:
        product = Product.objects.get(pk=pk)
        serializer = ProductSerializer(product)
        print("Fetched product:", serializer.data)
        return Response({
            "message": "Product fetched successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    except Product.DoesNotExist:
        return Response({
            "error": "Product not found"
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print("Product fetch exception:")
        traceback.print_exc()
        return Response({
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




# Get All Products
@api_view(['GET'])
@permission_classes([AllowAny])
def getAllProducts(request):
    try:
        products = Product.objects.all()
        serializer = ProductSerializer(products, many=True)
        # print("Fetched products:", serializer.data)
        return Response({
            "message": "Products fetched successfully",
            "data": serializer.data
            
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#fetch products by location
@api_view(['GET'])
@permission_classes([AllowAny])
def productByLocation(request, location):
    products = Product.objects.filter(vendor__address__iexact=location).exclude(vendor__isApproved=False)
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)


## Update Product
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def updateProduct(request, pk):
    print("Received data:", request.data)
    try:
        # Get the product instance
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return JsonResponse({"error": "Product not found"}, status=404)

        # Extract fields from request
        name = request.data.get("name")
        description = request.data.get("description")
        category_id = request.data.get("category_id")
        originalPrice = request.data.get("originalPrice")
        discountPercentage = request.data.get("discountPercentage")
        isAvailable = request.data.get("isAvailable") == "true"
        totalStock = request.data.get("totalStock")
        
        # NEW: Handle has_sizes field
        has_sizes = request.data.get("has_sizes")
        if has_sizes is not None:
            has_sizes = has_sizes == "true"
        else:
            has_sizes = product.has_sizes  # Keep existing value if not provided
            
        sizes = request.data.getlist("sizes[]") or request.data.getlist("sizes") or []

        # Validation: If has_sizes is True, sizes array should not be empty (unless keeping existing)
        if has_sizes and not sizes and not product.sizes.exists():
            return JsonResponse({"error": "Sizes are required when has_sizes is true"}, status=400)

        # Calculate discounted price
        if originalPrice and discountPercentage:
            op = float(originalPrice)
            dp = float(discountPercentage)
            discountedPrice = op * (1 - dp / 100)
        else:
            discountedPrice = product.discountedPrice

        print("Parsing sizes...")
        parsed_sizes = []
        for size_str in sizes:
            try:
                parsed_sizes.append(json.loads(size_str))
            except json.JSONDecodeError as e:
                print("Error decoding size:", size_str, e)

        # Verify vendor ownership
        user_id = request.user.id
        vendor = Vendor.objects.get(user_id=user_id)
        
        if product.vendor_id != vendor.id:
            return JsonResponse({"error": "You don't have permission to update this product"}, status=403)

        # Handle image uploads
        def get_image_url(img, existing_url):
            return upload_image_to_supabase(img) if img else existing_url

        image_urls = {
            'image': get_image_url(request.FILES.get("image"), product.image),
            'topImage': get_image_url(request.FILES.get("topImage"), product.topImage),
            'bottomImage': get_image_url(request.FILES.get("bottomImage"), product.bottomImage),
            'leftImage': get_image_url(request.FILES.get("leftImage"), product.leftImage),
            'rightImage': get_image_url(request.FILES.get("rightImage"), product.rightImage),
        }

        print("Updating product...")
        # Update product fields
        product.name = name if name else product.name
        product.description = description if description else product.description
        product.category_id = category_id if category_id else product.category_id
        product.originalPrice = originalPrice if originalPrice else product.originalPrice
        product.discountedPrice = str(discountedPrice)
        product.discountPercentage = discountPercentage if discountPercentage else product.discountPercentage
        product.isAvailable = isAvailable
        product.totalStock = totalStock if totalStock else product.totalStock
        product.has_sizes = has_sizes  # NEW: Update has_sizes field
        
        # Update image URLs
        for field, url in image_urls.items():
            setattr(product, field, url)

        # Save the updated product
        product.save()

        # NEW: Handle sizes based on has_sizes field
        if has_sizes:
            # If product should have sizes, update them
            if parsed_sizes:
                # Delete existing sizes and create new ones
                ProductSize.objects.filter(product=product).delete()
                
                for size_obj in parsed_sizes:
                    ProductSize.objects.create(
                        product=product,
                        size=size_obj.get("size"),
                        stock=size_obj.get("stock", 0)
                    )
        else:
            # If product should not have sizes, delete all existing sizes
            ProductSize.objects.filter(product=product).delete()

        return JsonResponse({
            "message": "Product updated successfully",
            "product_id": product.id,
            "has_sizes": has_sizes
        })

    except Vendor.DoesNotExist:
        return JsonResponse({"error": "Vendor not found for the user"}, status=400)
    except Exception as e:
        print("Exception occurred:", e)
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)


### Delete Product ###
@api_view(['DELETE'])
def delete_product(request, id):
    product = get_object_or_404(Product, id=id)
    product.delete()
    return JsonResponse({'message': 'Product deleted successfully'}, status=200)

### Check Product Availability ###
@api_view(['GET'])
@permission_classes([AllowAny])
def checkProductAvailability(request, pk):
    """
    Check if a product is available and return stock information
    """
    try:
        product = Product.objects.get(pk=pk)
        
        response_data = {
            "product_id": product.id,
            "name": product.name,
            "is_available": product.isAvailable,
            "has_sizes": product.has_sizes,
        }
        
        if product.has_sizes:
            # For products with sizes, return size-specific stock
            sizes_data = []
            for size in product.sizes.all():
                sizes_data.append({
                    "size": size.size,
                    "stock": size.stock,
                    "available": size.stock > 0
                })
            response_data["sizes"] = sizes_data
            response_data["total_stock"] = sum(size.stock for size in product.sizes.all())
        else:
            # For products without sizes, return total stock
            response_data["total_stock"] = int(product.totalStock)
            response_data["in_stock"] = int(product.totalStock) > 0
        
        return Response({
            "message": "Product availability checked successfully",
            "data": response_data
        }, status=status.HTTP_200_OK)
        
    except Product.DoesNotExist:
        return Response({
            "error": "Product not found"
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print("Product availability check exception:")
        traceback.print_exc()
        return Response({
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Get Products by Category
@api_view(['GET'])
@permission_classes([AllowAny])
def getProductByCategory(request, category_id):
    print("Category ID:", category_id)
    try:
        products = Product.objects.filter(category_id=category_id)
        serializer = ProductSerializer(products, many=True)
        print("Fetched products:", serializer.data)  # Debugging line
        return Response({
            "message": "Products fetched successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        print("Product fetch by category exception:")
        traceback.print_exc()
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)    
    
    

# get products by vendor
@api_view(['GET'])
@permission_classes([IsAuthenticated])  # should not be AllowAny if you're fetching based on logged-in user
def getProductsByVendor(request):
    try:
        user_id = request.user.id
        print("user ID:", user_id)

        # check if vendor exists
        if not Vendor.objects.filter(user_id=user_id).exists():
            return Response({
                "message": "Vendor does not exist."
            }, status=status.HTTP_404_NOT_FOUND)

        vendor = Vendor.objects.get(user_id=user_id)
        print("Vendor:", vendor.id)

        # fetch products for vendor
        products = Product.objects.filter(vendor=vendor)
        if not products.exists():
            return Response({
                "message": "No products found for this vendor."
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductSerializer(products, many=True)
        return Response({
            "message": "Products fetched successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print("Product fetch by vendor exception:")
        traceback.print_exc()
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])  # Can be AllowAny since we're fetching by vendor ID, not user-specific data
def getProductsByVendorId(request, pk):
    try:
        print("Vendor ID:", pk)

        # check if vendor exists
        if not Vendor.objects.filter(id=pk).exists():
            return Response({
                "message": "Vendor does not exist."
            }, status=status.HTTP_404_NOT_FOUND)

        vendor = Vendor.objects.get(id=pk)
        print("Vendor:", vendor.name if hasattr(vendor, 'name') else vendor.id)

        # fetch products for vendor
        products = Product.objects.filter(vendor=vendor)
        if not products.exists():
            return Response({
                "message": "No products found for this vendor."
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductSerializer(products, many=True)
        return Response({
            "message": "Products fetched successfully",
            "data": serializer.data,
            "vendor": {
                "id": vendor.id,
                "name": vendor.name if hasattr(vendor, 'name') else None,
                # Add other vendor fields you want to include
            }
        }, status=status.HTTP_200_OK)

    except Vendor.DoesNotExist:
        return Response({
            "message": "Vendor not found."
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print("Product fetch by vendor ID exception:")
        traceback.print_exc()
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

