from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import RewardPoint

## This view allows the user to increase their reward points by a specified amount.
# It retrieves the number of points to add from the request data, updates the user's total points,
# and returns a success message.


# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
def increaseRewardPoints(user, order_total):
    points_earned = int(order_total)  # 1 ₹ = 1 point
    reward, created = RewardPoint.objects.get_or_create(user=user)
    # Add earned points to totalPoints
    reward.totalPoints += points_earned
    reward.save()