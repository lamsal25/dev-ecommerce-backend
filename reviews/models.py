from django.db import models
from django.contrib.auth import get_user_model
from products.models import Product  # Adjust the import based on your project
from vendors.models import Vendor    # Assuming you have a Vendor model

User = get_user_model()

class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Review by {self.user} for {self.product.name}"

    # class Meta:
    #     unique_together = ('product', 'user')  # One review per product per user

class VendorReview(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Vendor review by {self.user} for {self.vendor.name}"

    # class Meta:
    #     unique_together = ('vendor', 'user')  # One review per vendor per user

class ProductReviewReply(models.Model):
    """Model for vendor replies to product reviews"""
    review = models.OneToOneField(
        ProductReview, 
        on_delete=models.CASCADE, 
        related_name='vendor_reply'
    )
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    reply = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Vendor reply by {self.vendor.name} to review #{self.review.id}"

    def save(self, *args, **kwargs):
        # Ensure the vendor replying is the owner of the product
        if self.review.product.vendor != self.vendor:
            raise ValueError("Vendor can only reply to reviews of their own products")
        super().save(*args, **kwargs)

class VendorReviewReply(models.Model):
    """Model for vendor replies to vendor reviews"""
    review = models.OneToOneField(
        VendorReview, 
        on_delete=models.CASCADE, 
        related_name='vendor_reply'
    )
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    reply = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Vendor reply by {self.vendor.name} to vendor review #{self.review.id}"

    def save(self, *args, **kwargs):
        # Ensure the vendor replying is the one being reviewed
        if self.review.vendor != self.vendor:
            raise ValueError("Vendor can only reply to their own vendor reviews")
        super().save(*args, **kwargs)