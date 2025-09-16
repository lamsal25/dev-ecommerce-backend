from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Advertisement(models.Model):
    POSITION_CHOICES = [
        ('above_navbar', 'Above Navbar'),
        ('homepage_middle', 'Homepage Middle'),
        ('homepage_bottom', 'Homepage Bottom'),
        ('productpage_sidebar', 'Productpage Sidebar'),
        ('marketplace', 'Marketplace'),
    ]

    vendor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="advertisements")
    title = models.CharField(max_length=255)
    image = models.CharField(max_length=500)  # now as CharField for public URL
    link = models.URLField()
    position = models.CharField(max_length=50, choices=POSITION_CHOICES)
    description = models.TextField(blank=True, null=True)
    startDate = models.DateTimeField()
    endDate = models.DateTimeField()
    isActive = models.BooleanField(default=False)
    paymentDone = models.BooleanField(default=False)
    isApproved = models.BooleanField(default=False)  # New field for approval status
    createdAt = models.DateTimeField(auto_now_add=True)


    def is_currently_active(self):
        now = timezone.now()
        return self.isActive and self.startDate <= now <= self.endDate and self.paymentDone

    def __str__(self): 
        return f"{self.title} by {self.vendor}"

    class Meta:
        ordering = ['-createdAt', 'startDate']
 