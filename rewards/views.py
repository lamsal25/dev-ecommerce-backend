from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import RewardPoint
from .serializers import RewardPointSerializer


# getRewardPoints view retrieves the user's reward points.
# It checks if the user has an existing RewardPoint record, and if not, creates one.
# The response includes the total points, redeemed points, and available points.
@api_view(['GET'])
def getRewardPoints(request):
    reward, created = RewardPoint.objects.get_or_create(user=request.user)
    serializer = RewardPointSerializer(reward)
    return Response(serializer.data)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def applyRewardPoints(request):
    """
    Preview reward discount before placing order.
    Conversion rate = 1000 points = Rs. 1
    """
    # Points user wants to apply
    requested_points = int(request.data.get("appliedReward", 0))
    order_total = float(request.data.get("order_total", 0))  # optional: cap discount at total

    try:
        reward = RewardPoint.objects.get(user=request.user)
    except RewardPoint.DoesNotExist:
        return Response({"message": "No reward points found."}, status=status.HTTP_404_NOT_FOUND)

    available_points = reward.availablePoints()

    # Clamp requested points to available points
    points_to_use = min(requested_points, available_points)

    # Conversion rate
    conversion_rate = 1000  # 1000 points = Rs. 1
    discount = points_to_use / conversion_rate

    # Cap discount to order total
    if order_total > 0:
        discount = min(discount, order_total)
        points_to_use = int(discount * conversion_rate)  # adjust points if capped by order total

    return Response({
        "available_points": available_points,
        "used_points": points_to_use,
        "discount": discount,
        "conversion_rate": conversion_rate
    })


# redeemPoints view allows users to redeem their reward points.
# It checks if the user has enough available points to redeem the requested amount.
# If successful, it updates the redeemed points and returns a success message.
# If not enough points are available, it returns an error message.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def redeemPoints(request):
    pointsToRedeem = int(request.data.get('points', 0))
    reward, created = RewardPoint.objects.get_or_create(user=request.user)

    if reward.availablePoints() >= pointsToRedeem:
        reward.redeemedPoints += pointsToRedeem
        reward.save()
        return Response({'success': True, 'message': f'{pointsToRedeem} points redeemed successfully.'})
    else:
        return Response({'success': False, 'message': 'Not enough available points.'}, status=status.HTTP_400_BAD_REQUEST)


