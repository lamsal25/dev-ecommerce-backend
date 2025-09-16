from django.urls import path
from .views import *

urlpatterns = [
    path('getRewardPoints/', getRewardPoints, name='get_reward_points'),
    path('rewardPoints/redeem/', redeemPoints, name='redeem_points'),
    path("applyRewardPoints/", applyRewardPoints, name="apply-reward-points"),
    # path('increaseRewardPoints/', increaseRewardPoints, name='increase_reward_points'),
 ]
