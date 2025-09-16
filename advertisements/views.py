import os
# Vendor can create ads
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from .models import Advertisement
from .serializers import AdvertisementSerializer, SponsoredAdSerializer
import traceback
import uuid
from supabase import create_client, Client
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.pagination import PageNumberPagination


# gets value from .env
SUPABASE_URL = os.getenv("SUPABASE_URL") 
SUPABASE_KEY = os.getenv("SUPABASE_KEY") 
 
# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


#Upload image to Supabase
def upload_image_to_supabase(image):
    """
    Uploads an image to Supabase Storage and returns its public URL.
    """
    try:
        file_name = f"{uuid.uuid4().hex}_{image.name}"
        file_path = f"advertisements/{file_name}"

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



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def createAdvertisement(request):
    try:
        # print("Received data:", request.data)

        title = request.data.get("title")
        image = request.FILES.get("image")
        link = request.data.get("link")
        position = request.data.get("position")
        description = request.data.get("description")
        startDate = request.data.get("startDate")
        endDate = request.data.get("endDate")
        isActive = request.data.get("isActive", False)
        paymentDone = request.data.get("paymentDone", False)
        isApproved = request.data.get("isApproved", False)

        public_url = upload_image_to_supabase(image) if image else None
        if not public_url:
            return Response({"error": "Image upload failed."}, status=status.HTTP_400_BAD_REQUEST)

        ad = Advertisement.objects.create(
            vendor=request.user,
            title=title,
            image=public_url,
            link=link,
            position=position,
            description=description,
            startDate=startDate,
            endDate=endDate,
            isActive=isActive,
            paymentDone=paymentDone,
            isApproved=isApproved,
        )

        serializer = AdvertisementSerializer(ad)
        return Response({
            "message": "Advertisement created successfully",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        print(f"Error in create_advertisement: {str(e)}")
        traceback.print_exc()
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

class AdPagination(PageNumberPagination):
    page_size_query_param = 'page_size'
    max_page_size = 100

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getAdvertisementsByVendor(request):
    try:
        ads = Advertisement.objects.filter(vendor=request.user)
        paginator = AdPagination()
        result_page = paginator.paginate_queryset(ads, request)
        serializer = AdvertisementSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# List all active ads by position
@api_view(['GET'])
@permission_classes([AllowAny])
def activeAdvertisements(request):
    now = timezone.now()
    activeAds = Advertisement.objects.filter(
        isApproved=True,
        paymentDone=True,
        startDate__lte=now,
        endDate__gte=now
    ).order_by('-createdAt') # show latest created ads first

    serializer = AdvertisementSerializer(activeAds, many=True)
    # print("Active advertisements:", serializer.data)
    return Response(serializer.data)



@api_view(['GET'])
@permission_classes([AllowAny])
def getAdsByPosition(request, position):
    now = timezone.now()
    ads = Advertisement.objects.filter(
        position=position,
        isApproved=True,
        startDate__lte=now,
        endDate__gte=now,
        paymentDone=True,
    ).order_by('-createdAt')
    serializer = AdvertisementSerializer(ads, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def getSponsoredAds(request):
    try:
        ads = Advertisement.objects.filter(isApproved=True, paymnentDone=True)
        serializer = AdvertisementSerializer(ads, many=True)
        return Response(serializer.data)
    except Exception as e:
        print(f"Error fetching sponsored ads: {str(e)}")
        traceback.print_exc()
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#get pending ads
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pendingAds(request):
    ads = Advertisement.objects.filter(vendor=request.user, isApproved=False)
    serializer = AdvertisementSerializer(ads, many=True)
    return Response(serializer.data)


#get all pending ads
@api_view(['GET'])
@permission_classes([IsAuthenticated])  
def getAllPendingAds(request):
    try:
        ads = Advertisement.objects.filter(isApproved=False)
        serializer = AdvertisementSerializer(ads, many=True)
        print("All pending advertisements:", serializer.data)
        return Response(serializer.data)
    except Exception as e:
        print(f"Error fetching all pending ads: {str(e)}")
        traceback.print_exc()
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


## Approve advertisement
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def approveAdvertisement(request, ad_id):
    try:
        ad = Advertisement.objects.get(id=ad_id)
        ad.isApproved = True
        ad.save()

        # Send approval email to vendor
        subject = 'Your Advertisement Has Been Approved!'
        message = f"Hello {ad.vendor.first_name},\n\nCongratulations🎉\n\n Your advertisement titled '{ad.title}' has been approved and is now ready to be displayed based on its schedule.\n\nThank you for advertising with us!"
        recipient_list = [ad.vendor.email]

        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list)

        return Response({'message': 'Advertisement approved successfully'})
    except Advertisement.DoesNotExist:
        return Response({'error': 'Advertisement not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error approving advertisement: {str(e)}")
        traceback.print_exc()
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
   


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def rejectAdvertisement(request, ad_id):
    try:
        ad = Advertisement.objects.get(id=ad_id)

        # Extract file path from the full URL
        public_url = ad.image
        if public_url:
            # Assuming your public URL is like: https://xyz.supabase.co/storage/v1/object/public/images/advertisements/abc.jpg
            parts = public_url.split("/object/public/")
            if len(parts) == 2:
                file_path = parts[1]
                print(f"Deleting file from Supabase: {file_path}")
                delete_response = supabase.storage.from_("images").remove([file_path])

                if hasattr(delete_response, "error") and delete_response.error:
                    print(f"Error deleting image from Supabase: {delete_response.error}")

        # Delete the advertisement record
        ad.delete()

        return Response({'message': 'Advertisement rejected and deleted successfully'})

    except Advertisement.DoesNotExist:
        return Response({'error': 'Advertisement not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error rejecting advertisement: {str(e)}")
        traceback.print_exc()
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ad = Advertisement.objects.first()
# serializer = AdvertisementSerializer(ad)
# print(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def updatePaymentStatus(request, pk):
    try:
        ad = Advertisement.objects.get(id=pk)
        ad.paymentDone =  True
        ad.save()
        return Response({"message": "Payment status updated."}, status=200)
    except Advertisement.DoesNotExist:
        return Response({"error": "Advertisement not found."}, status=404)
