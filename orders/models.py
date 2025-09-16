from django.db import models
from django.contrib.postgres.fields import JSONField 
from api.models import CustomUser
from coupons.models import Coupon  

class Order(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='orders')  # <- Link to user
    pidx = models.CharField(max_length=100, null=True, blank=True)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    billing_details = models.JSONField()
    cart_items = models.JSONField()
    total_amount = models.FloatField()
    payment_status = models.CharField(max_length=50, choices=[('Paid', 'Paid'), ('Pending', 'Pending')])
    order_status = models.CharField(max_length=50, choices=[('completed', 'Completed'), ('pending', 'Pending')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    delivery_status = models.CharField(
        max_length=50,
        choices=[
            ('Pending', 'Pending'),
            ('Dispatched', 'Dispatched'),
            ('Delivered', 'Delivered'),
            ('Received', 'Received'),
        ],
        default='Pending'
    )

    
    def __str__(self):
        return f"Order {self.id} - {self.payment_status}"
