from django.db import models
from api.models import CustomUser


class Vendor(models.Model):
    ownerName = models.CharField(max_length=255, default='Unknown Vendor')
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="vendor", null=True, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True,unique=True)
    businessName = models.CharField(max_length=255, default='Unknown Vendor',unique=True)
    businessType = models.CharField(max_length=255)
    businessDescription = models.TextField(blank=True, null=True)
    image = models.CharField(max_length=255, blank=True, null=True, default='unknown url')
    registrationNumber = models.CharField(max_length=255, blank=True, null=True,unique=True)
    registrationDocument = models.URLField(max_length=500, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=255, default='Unknown City')
    country = models.CharField(max_length=255, default='Unknown Country')
    website = models.URLField(blank=True, null=True,unique=True)
    isApproved = models.BooleanField(default=False)
    appliedAt = models.DateTimeField(auto_now_add=True)
    createdAt = models.DateTimeField(auto_now_add=True)
 
    def __str__(self):
        return f"{self.businessName} ({self.ownerName})"



class VendorOrderItemStatus(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="order_statuses")
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=(('Pending', 'Pending'), ('Dispatched', 'Dispatched')), default='Pending')
    delivery_date = models.DateField(null=True, blank=True)  

    createdAt = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} - {self.status}"