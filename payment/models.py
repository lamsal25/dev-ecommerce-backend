from django.db import models
from coupons.models import Coupon  # Import your coupon model

class PartialOrder(models.Model):
    transaction_id = models.CharField(max_length=100, unique=True)
    pidx = models.CharField(max_length=100, blank=True, null=True)  # Khalti PIDX
    payment_url = models.URLField(blank=True, null=True)  # Khalti payment URL
    expires_at = models.DateTimeField(blank=True, null=True)  # Khalti expiration

    cart = models.JSONField()
    billing_name = models.CharField(max_length=255)
    billing_email = models.EmailField()
    billing_phone = models.CharField(max_length=20)
    billing_address = models.CharField(max_length=300)
    billing_city = models.CharField(max_length=60)
    total_amount = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    coupons = models.ManyToManyField(Coupon, blank=True)
    reward_points_used = models.IntegerField(default=0)



    def __str__(self):
        return f"PartialOrder {self.pidx} - {self.total_amount/100:.2f} NPR"
