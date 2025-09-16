from django.db import models
from api.models import CustomUser

class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="profile")
    firstName = models.CharField(max_length=30)
    lastName = models.CharField(max_length=30)
    mobile = models.CharField(max_length=20)
    dateOfBirth = models.DateField()
    gender = models.CharField(max_length=10)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postalCode = models.CharField(max_length=20)