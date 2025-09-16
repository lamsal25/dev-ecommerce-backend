from rest_framework import serializers
from .models import RewardPoint

class RewardPointSerializer(serializers.ModelSerializer):
    availablePoints = serializers.IntegerField()

    class Meta:
        model = RewardPoint
        fields = ['totalPoints', 'redeemedPoints', 'availablePoints']
