from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.db.models import Avg, Count
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import get_user_model

# Import models
from .models import ProductReview, VendorReview, ProductReviewReply, VendorReviewReply
from products.models import Product
from vendors.models import Vendor

# Import serializers
from .serializers import ProductReviewSerializer, VendorReviewSerializer, ProductReviewReplySerializer

User = get_user_model()

@api_view(['POST'])
@permission_classes([AllowAny])
def create_product_review(request):
    print(request.data)
    try:
        product_id = request.data.get('product')
        rating = request.data.get('rating')
        comment = request.data.get('comment', '')

        user = request.user
        if not user or user.is_anonymous:
            return Response({"error": "Please log in first"}, status=status.HTTP_400_BAD_REQUEST)

        if not Product.objects.filter(id=product_id).exists():
            return Response({"error": f"Product with id {product_id} not found."}, status=status.HTTP_404_NOT_FOUND)

        data = {
            'product': product_id,
            'rating': rating,
            'comment': comment,
        }

        serializer = ProductReviewSerializer(data=data)
        if serializer.is_valid():
            serializer.save(user=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            print("Serializer errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        print("Exception occurred:", e)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_product_reviews(request):
    product_id = request.query_params.get('product_id')
    print(product_id)
    if not product_id:
        return Response({"error": "Product ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        reviews = ProductReview.objects.filter(product=product_id).order_by('-created_at')
        serializer = ProductReviewSerializer(reviews, many=True)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_product_review(request, review_id):
    user = request.user
    try:
        review = ProductReview.objects.get(id=review_id)
    except ProductReview.DoesNotExist:
        return Response({"error": "Review not found."}, status=status.HTTP_404_NOT_FOUND)

    # Only the review owner or staff can delete the review
    if review.user != user and not user.is_staff:
        return Response({"error": "Not authorized to delete this review."}, status=status.HTTP_403_FORBIDDEN)

    review.delete()
    return Response({"message": "Review deleted successfully."}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_vendor_review(request):
    print(request.data)
    try:
        vendor_id = request.data.get('vendor')
        rating = request.data.get('rating')
        comment = request.data.get('comment', '')

        user = request.user
        print(user)
        if not user or user.is_anonymous:
            return Response({"error": "Please log in first"}, status=status.HTTP_400_BAD_REQUEST)

        data = {
            'vendor': vendor_id,
            'rating': rating,
            'comment': comment,
        }

        serializer = VendorReviewSerializer(data=data)
        if serializer.is_valid():
            serializer.save(user=user)
            response_data = serializer.data
            response_data['user_name'] = user.username
            response_data['user_email'] = user.email
            return Response(response_data, status=status.HTTP_201_CREATED)
        else:
            print("Serializer errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        print("Exception occurred:", e)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_vendor_reviews(request):
    vendor_id = request.query_params.get('vendor_id')
    print(vendor_id)
    if not vendor_id:
        return Response({"error": "Vendor ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        reviews = VendorReview.objects.filter(vendor=vendor_id).order_by('-created_at')
        serializer = VendorReviewSerializer(reviews, many=True)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['GET'])
@permission_classes([AllowAny])
def batch_product_review_stats(request):
    ids = request.GET.getlist('product_ids')  # e.g., ?product_ids=1&product_ids=2
    stats = (
        ProductReview.objects
        .filter(product_id__in=ids)
        .values('product_id')
        .annotate(avg_rating=Avg('rating'), total_reviews=Count('id'))
    )

    response_data = {str(entry['product_id']): {
        'avg_rating': entry['avg_rating'] or 0,
        'total_reviews': entry['total_reviews']
    } for entry in stats}

    return JsonResponse(response_data)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_vendor_review(request, review_id):
    user = request.user
    try:
        review = VendorReview.objects.get(id=review_id)
    except VendorReview.DoesNotExist:
        return Response({"error": "Review not found."}, status=status.HTTP_404_NOT_FOUND)

    if review.user != user and not user.is_staff:
        return Response({"error": "Not authorized to delete this review."}, status=status.HTTP_403_FORBIDDEN)

    review.delete()
    return Response({"message": "Review deleted successfully."}, status=status.HTTP_200_OK)

# VENDOR REPLY FUNCTIONS (Updated versions)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_product_review_reply(request, review_id):
    """
    Create a vendor reply to a product review
    """
    try:
        review = get_object_or_404(ProductReview, id=review_id)
        
        # Check if user is a vendor and owns the product
        try:
            vendor = Vendor.objects.get(user=request.user)
            if review.product.vendor != vendor:
                return Response(
                    {'error': 'You can only reply to reviews of your own products'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        except Vendor.DoesNotExist:
            return Response(
                {'error': 'Only vendors can reply to reviews'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if reply already exists
        if hasattr(review, 'vendor_reply'):
            return Response(
                {'error': 'A reply already exists for this review'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reply_text = request.data.get('reply', '').strip()
        if not reply_text:
            return Response(
                {'error': 'Reply text is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create the reply
        reply = ProductReviewReply.objects.create(
            review=review,
            vendor=vendor,
            reply=reply_text
        )
        
        serializer = ProductReviewReplySerializer(reply)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        print(f"Error creating reply: {str(e)}")  # For debugging
        return Response(
            {'error': 'An error occurred while creating the reply'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_product_review_reply(request, reply_id):
    """
    Update a vendor reply to a product review
    """
    try:
        reply = get_object_or_404(ProductReviewReply, id=reply_id)
        
        # Check if user owns this reply
        try:
            vendor = Vendor.objects.get(user=request.user)
            if reply.vendor != vendor:
                return Response(
                    {'error': 'You can only update your own replies'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        except Vendor.DoesNotExist:
            return Response(
                {'error': 'Only vendors can update replies'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        reply_text = request.data.get('reply', '').strip()
        if not reply_text:
            return Response(
                {'error': 'Reply text is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reply.reply = reply_text
        reply.save()
        
        serializer = ProductReviewReplySerializer(reply)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error updating reply: {str(e)}")  # For debugging
        return Response(
            {'error': 'An error occurred while updating the reply'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_product_review_reply(request, reply_id):
    """
    Delete a vendor reply to a product review
    """
    try:
        reply = get_object_or_404(ProductReviewReply, id=reply_id)
        
        # Check if user owns this reply
        try:
            vendor = Vendor.objects.get(user=request.user)
            if reply.vendor != vendor:
                return Response(
                    {'error': 'You can only delete your own replies'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        except Vendor.DoesNotExist:
            return Response(
                {'error': 'Only vendors can delete replies'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        reply.delete()
        return Response(
            {'message': 'Reply deleted successfully'}, 
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        print(f"Error deleting reply: {str(e)}")  # For debugging
        return Response(
            {'error': 'An error occurred while deleting the reply'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )