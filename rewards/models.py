from django.db import models
from django.conf import settings
from api.models import CustomUser

class RewardPoint(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="reward_points")
    totalPoints = models.PositiveIntegerField(default=0)
    redeemedPoints = models.PositiveIntegerField(default=0)

    def availablePoints(self):
        return self.totalPoints - self.redeemedPoints

    def __str__(self):
        return f"{self.user.email} - {self.totalPoints} points" 
 