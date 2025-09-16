from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view, parser_classes
from rest_framework.response import Response
from .models import Vendor
from .serializers import VendorRegistrationSerializer, VendorSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.core.signing import TimestampSigner
from rest_framework import status
from django.core.mail import send_mail
from django.conf import settings
from .models import VendorOrderItemStatus
from .serializers import VendorOrderItemStatusSerializer
from .pagination import StandardResultsSetPagination
from datetime import date
import os
import traceback
import uuid
from supabase import create_client, Client
from django.db.models import Sum, F
from datetime import datetime, timedelta
from django.utils.timezone import now


# gets value from .env
SUPABASE_URL = os.getenv("SUPABASE_URL") 
SUPABASE_KEY = os.getenv("SUPABASE_KEY") 
print("Supabase URL:",SUPABASE_URL)

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def upload_registration_document_to_supabase(document):
    """
    Uploads a registration document to Supabase Storage and returns its public URL as a string.
    """
    try:
        print(f"Starting upload for file: {document.name}")
        print(f"File size: {document.size} bytes")
        
        # Generate unique filename
        file_ext = document.name.split(".")[-1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
        file_path = f"registration_docs/{unique_filename}"

        print(f"Upload path: {file_path}")

        # Reset file pointer and read content
        document.seek(0)
        file_content = document.read()
        
        print(f"Read {len(file_content)} bytes from file")

        # Upload to Supabase
        response = supabase.storage.from_("documents").upload(
            path=file_path,
            file=file_content,
            file_options={
                "content-type": getattr(document, 'content_type', f'application/{file_ext}')
            }
        )
        
        print("Upload response:", type(response), response)
        
        # Check if upload was successful
        if response and not (hasattr(response, 'error') and response.error):
            # Get public URL
            public_url_response = supabase.storage.from_("documents").get_public_url(file_path)
            
            print(f"Public URL response type: {type(public_url_response)}")
            print(f"Public URL response: {public_url_response}")
            
            # Extract the URL string based on the response format
            if isinstance(public_url_response, str):
                return public_url_response
            elif isinstance(public_url_response, dict) and 'publicUrl' in public_url_response:
                return public_url_response['publicUrl']
            elif hasattr(public_url_response, 'publicURL'):
                return str(public_url_response.publicURL)
            elif hasattr(public_url_response, 'public_url'):
                return str(public_url_response.public_url)
            else:
                # Try to convert to string
                url_str = str(public_url_response)
                if url_str.startswith('http'):
                    return url_str
                else:
                    print(f"Could not extract URL string from response: {public_url_response}")
                    return None
        else:
            error_msg = getattr(response, 'error', 'Unknown upload error')
            print(f"Upload failed: {error_msg}")
            return None
            
    except Exception as e:
        print(f"Upload exception: {e}")
        import traceback
        traceback.print_exc()
        return None

@api_view(['POST'])
@permission_classes([AllowAny])
def createVendors(request):
    data = request.data.copy()

    print("=== VENDOR REGISTRATION DEBUG ===")
    print("Received data keys:", list(data.keys()))
    print("Files received:", list(request.FILES.keys()))

    # Handle document upload FIRST, before serializer validation
    document = request.FILES.get("registrationDocument")
    if document:
        print(f"Processing document: {document.name} (size: {document.size})")
        
        # Validate file size (10MB limit)
        max_size = 10 * 1024 * 1024
        if document.size > max_size:
            return Response({
                "error": "File too large", 
                "details": f"Maximum file size is {max_size/1024/1024}MB"
            }, status=400)
        
        # Validate file type
        allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx']
        file_ext = document.name.split('.')[-1].lower()
        if file_ext not in allowed_extensions:
            return Response({
                "error": "Invalid file type",
                "details": f"Allowed types: {', '.join(allowed_extensions)}"
            }, status=400)
        
        try:
            # Upload to Supabase and get URL
            public_url = upload_registration_document_to_supabase(document)
            if public_url:
                # Replace the file with the URL string in the data
                data["registrationDocument"] = public_url
                print(f"Document uploaded successfully: {public_url}")
            else:
                print("Document upload returned None")
                return Response({
                    "error": "Document upload failed",
                    "details": "Could not upload document to storage"
                }, status=400)
                
        except Exception as upload_error:
            print(f"Upload exception: {upload_error}")
            return Response({
                "error": "Document upload failed",
                "details": str(upload_error)
            }, status=400)
    else:
        # Set empty string if no document (your serializer allows blank)
        data["registrationDocument"] = ""
        print("No document provided, setting empty string")

    # Debug: Print what we're sending to serializer
    print("Data being sent to serializer:")
    for key, value in data.items():
        if key == 'registrationDocument':
            print(f"  {key}: {value[:50]}..." if len(str(value)) > 50 else f"  {key}: {value}")
        elif key == 'password':
            print(f"  {key}: [HIDDEN]")
        else:
            print(f"  {key}: {value}")

    try:
        # Now use your existing serializer
        serializer = VendorRegistrationSerializer(data=data)
        if serializer.is_valid():
            user = serializer.save()  # This returns the user object
            print(f"Vendor created successfully - User ID: {user.id}")
            
            # Generate registration token
            signer = TimestampSigner()
            reg_token = signer.sign(str(user.pk))
            
            return Response({
                "message": "Registration successful! Please check your email for verification instructions.",
                "user_id": user.id,
                "token": reg_token
            }, status=201)
        else:
            print("Serializer validation errors:", serializer.errors)
            return Response({
                "error": "Validation failed",
                "details": serializer.errors
            }, status=400)
            
    except Exception as e:
        print("Exception during vendor creation:", str(e))
        import traceback
        traceback.print_exc()
        return Response({
            "error": "An error occurred during registration",
            "details": str(e)
        }, status=500)
    


# fetch only pending vendors
@api_view(['GET'])
@permission_classes([AllowAny])
def listPendingVendors(request):
    vendors = Vendor.objects.filter(isApproved=False)
    serializer = VendorSerializer(vendors, many=True)
    return Response(serializer.data)

# fetch only Approved vendors
@api_view(['GET'])
@permission_classes([AllowAny])
def listApprovedVendors(request):
    vendors = Vendor.objects.filter(isApproved=True)
    serializer = VendorSerializer(vendors, many=True)
    return Response(serializer.data)

# fetch only approved vendors
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def approveVendor(request, vendor_id):
    try:
        vendor = Vendor.objects.get(id=vendor_id)
        vendor.isApproved = True
        vendor.save()
        return Response({'message': 'Vendor approved successfully'})
    except Vendor.DoesNotExist:
        return Response({'error': 'Vendor not found'}, status=status.HTTP_404_NOT_FOUND)


#reject vendor
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def rejectVendor(request, vendor_id):
    try:
        vendor = Vendor.objects.get(id=vendor_id)
        vendor.isApproved = False
        vendor.save()
        return Response({'message': 'Vendor rejected successfully'})
    except Vendor.DoesNotExist:
        return Response({'error': 'Vendor not found'}, status=status.HTTP_404_NOT_FOUND) 


# Get All Vendors
@api_view(['GET'])
@permission_classes([AllowAny])
def getVendors(request):
    vendors = Vendor.objects.all()
    serializer = VendorSerializer(vendors, many=True)
    return Response({
        "message": "Vendors fetched successfully", 
        "data": serializer.data
    }, status=status.HTTP_200_OK) 

# Get Single Vendor
@api_view(['GET'])
@permission_classes([AllowAny])
def getVendor(request, pk):
    try:
        vendor = Vendor.objects.get(pk=pk)
        serializer = VendorSerializer(vendor)
        return Response({
            "message": "Vendor fetched successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    except Vendor.DoesNotExist:
        return Response({
            "message": "Vendor not found"
        }, status=status.HTTP_404_NOT_FOUND)


# Get Vendor Profile
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getVendorProfile(request):
    try:
        vendor = Vendor.objects.get(user=request.user)
        serializer = VendorSerializer(vendor)
        return Response({
            "message": "Vendor profile fetched successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    except Vendor.DoesNotExist:
        return Response({
            "message": "Vendor profile not found"
        }, status=status.HTTP_404_NOT_FOUND)
    

# Update Vendor Profile
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def updateVendorProfile(request):
    try:
        vendor = Vendor.objects.get(user=request.user)
        serializer = VendorSerializer(vendor, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            "message": "Vendor profile updated successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    except Vendor.DoesNotExist:
        return Response({
            "message": "Vendor profile not found"
        }, status=status.HTTP_404_NOT_FOUND) 



@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def deleteVendor(request, pk):
    try:
        vendor = Vendor.objects.get(id=pk)
        vendorEmail = vendor.email
        vendorName = vendor.ownerName
        vendor.delete()

        # Send account deletion email to vendor
        subject = 'Your Vendor Account Has Been Deleted'
        message = f"""
Hello {vendorName},

We would like to inform you that your vendor account "{vendor.businessName}" has been deleted from our platform.

If you believe this was done in error or you wish to inquire further, feel free to contact our support team.

Thank you for your time and association with us.

Best regards,
The DCart Team
"""
        recipient_list = [vendorEmail]

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False
        )

        return Response({"message": "Vendor deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

    except Vendor.DoesNotExist:
        return Response({"error": "Vendor not found."}, status=status.HTTP_404_NOT_FOUND)
    

### Display Vendor Order Status
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getOrderStatus(request):
    vendor = request.user.vendor
    queryset = VendorOrderItemStatus.objects.filter(vendor=vendor).order_by('-createdAt')
    paginator = StandardResultsSetPagination()
    paginated_queryset = paginator.paginate_queryset(queryset, request)
    serializer = VendorOrderItemStatusSerializer(paginated_queryset, many=True)

    return paginator.get_paginated_response(serializer.data)

### Edit Vendor Order Item Status
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def updateVendorOrderItemStatus(request, item_id):
    try:
        item = VendorOrderItemStatus.objects.get(id=item_id, vendor=request.user.vendor)
        status_val = request.data.get('status')
        
        if status_val not in ['Pending', 'Dispatched']:
            return Response({"error": "Invalid status."}, status=400)
        
        item.status = status_val

        if status_val == "Dispatched":
            item.delivery_date = date.today()   # set dispatch date
        elif status_val == "Pending":
            item.delivery_date = None          

        item.save()

         # Update parent Order delivery_status
        order = item.order
        all_items = order.vendororderitemstatus_set.all()
        if all(i.status == 'Dispatched' for i in all_items):
            order.delivery_status = 'Delivered'
            order.save()
            
        return Response({"message": "Status updated."})
    except VendorOrderItemStatus.DoesNotExist:
        return Response({"error": "Item not found."}, status=404)
    


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getVendorSalesSummary(request):
    try:
        vendor = request.user.vendor
        total_sales = VendorOrderItemStatus.objects.filter(vendor=vendor).aggregate(
            total=Sum(F('quantity') * F('price'))
        )['total'] or 0

        return Response({"total_sales": total_sales})
    except Exception as e:
        return Response({"error": str(e)}, status=400)
    

## Sales report
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def salesReport(request):
    # Get start and end dates from request parameters
    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")
    
    # Validate date parameters
    if not start_date_str or not end_date_str:
        return Response({"error": "Both start_date and end_date parameters are required"}, status=400)
    
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError:
        return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=400)
    
    # Validate date range (1 day to 3 months)
    date_diff = (end_date - start_date).days
    if date_diff < 1:
        return Response({"error": "Date range must be at least 1 day"}, status=400)
    if date_diff > 90:
        return Response({"error": "Date range cannot exceed 3 months"}, status=400)
    
    # Ensure end date is not in the future
    today = now().date()
    if end_date > today:
        end_date = today
    
    # 🔹 Get the vendor directly from the logged-in user
    try:
        vendor = request.user.vendor
    except AttributeError:
        return Response({"error": "User is not associated with a vendor"}, status=400)

    # 🔹 Filter only that vendor's sales within the date range
    order_items = VendorOrderItemStatus.objects.filter(
        order__created_at__date__gte=start_date,
        order__created_at__date__lte=end_date,
        product__vendor=vendor
    )

    total_sales = sum(item.price * item.quantity for item in order_items)
    total_orders = order_items.values("order_id").distinct().count()

    # Group products by ID and sum quantities
    product_sales = {}
    for item in order_items.select_related("product"):
        product_id = item.product.id
        if product_id not in product_sales:
            product_sales[product_id] = {
                "id": product_id,
                "name": item.product.name,
                "quantity": 0,
                "price": float(item.price),
            }
        product_sales[product_id]["quantity"] += item.quantity

    products = list(product_sales.values())

    return Response({
        "total_sales": total_sales,
        "total_orders": total_orders,
        "products": products
    }) 