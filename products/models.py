from django.db import models
from api.models import CustomUser
from vendors.models import Vendor
from django.utils.text import slugify

# Category model
class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(blank=True, null=True)      # slug field for SEO-friendly URLs in frontend

    image = models.TextField(blank=True, null=True)  # Use TextField for long URLs
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        related_name='subcategories', 
        blank=True, 
        null=True
    )
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            unique_slug = base_slug
            counter = 1
            while Category.objects.filter(slug=unique_slug).exclude(pk=self.pk).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = unique_slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name if not self.parent else f"{self.parent.name} -> {self.name}"


# Product model
class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=255)

    # slug field for SEO-friendly URLs in frontend
    slug = models.SlugField(blank=True, null=True)  
    description = models.TextField()

    #size checking field
    has_sizes = models.BooleanField(default=False)

    # Price fields1
    originalPrice = models.CharField(max_length=255)
    discountedPrice = models.CharField(max_length=255, blank=True, null=True)
    discountPercentage = models.CharField(max_length=255, blank=True, null=True)

    # Product images
    image = models.CharField(max_length=255, default='Unknown url')
    topImage = models.CharField(max_length=255, default='Unknown url')
    bottomImage = models.CharField(max_length=255, default='Unknown url')
    leftImage = models.CharField(max_length=255, default='Unknown url')
    rightImage = models.CharField(max_length=255, default='Unknown url')
    
    totalStock = models.CharField(max_length=10, default='0')  # Available stock quantity

    isAvailable = models.BooleanField(default=True)
    # isFeatured = models.BooleanField(default=False)
    
    
    ### Adding the slug field and making it unique
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            unique_slug = base_slug
            counter = 1
            while Product.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = unique_slug
        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.name} ({self.category.name})"


#product size model    
class ProductSize(models.Model):
    SIZE_CHOICES = [
        ('XS', 'Extra Small'),
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'Extra Large'),
        ('FX', 'Fixed Size')
    ]

    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='sizes')
    size = models.CharField(max_length=2, choices=SIZE_CHOICES)
    stock = models.PositiveIntegerField(default=0)  # Optional: manage size-wise stock

    def __str__(self):
        return f"{self.product.name} - {self.size}"

