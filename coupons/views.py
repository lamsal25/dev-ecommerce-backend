# views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from .models import Coupon, CouponUsage
from .serializers import CouponSerializer
from django.utils import timezone
import datetime
from django.utils.timezone import make_aware
# Create a coupon (admin only)
@api_view(['POST'])
@permission_classes([AllowAny])
def createCoupon(request):
    data = request.data
    print(data)
    serializer = CouponSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([AllowAny])
def deleteCoupon(request, id):
    print(id)
    try:
        coupon = Coupon.objects.get(id=id)
    except Coupon.DoesNotExist:
        return Response({'error': 'Coupon not found'}, status=status.HTTP_404_NOT_FOUND)
    coupon.delete()
    return Response({'message': 'Coupon deleted successfully'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def getCoupons(request):
    try:
        coupons = Coupon.objects.all()
        serializer = CouponSerializer(coupons, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"message": "Couldn't fetch coupons."}, status=status.HTTP_404_NOT_FOUND
        )

# Apply a coupon (authenticated users)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verifyCoupon(request):
    code = request.data['code']
    print(code)
    try:
        coupon = Coupon.objects.get(code=code)
        print("Coupon: ",coupon)
    except Coupon.DoesNotExist:
        return Response({'error': 'Invalid coupon code.'}, status=status.HTTP_404_NOT_FOUND)

        # Check if already used
    current_user = request.user
    if CouponUsage.objects.filter(user=current_user, coupon=coupon).exists():
        return Response({'error': 'Coupon already used by this user.', 'message': 'used_coupon'}, status=status.HTTP_400_BAD_REQUEST)

    # Check if valid
    if not coupon.is_valid():
        return Response({'error': 'Coupon is expired or usage limit reached.'},status=status.HTTP_400_BAD_REQUEST)

        # Mark as used
    # coupon.used_count += 1
    # coupon.save()
    # CouponUsage.objects.create(user=current_user, coupon=coupon)

    return Response({
            'message': 'Coupon verified successfully.',
            'discount_type': coupon.discount_type,
            'discount_value': coupon.discount_value
    }, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([AllowAny])  # You might want to use IsAdminUser in production
def updateCoupon(request, id):
    try:
        coupon = Coupon.objects.get(id=id)
    except Coupon.DoesNotExist:
        return Response({'error': 'Coupon not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = CouponSerializer(coupon, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
