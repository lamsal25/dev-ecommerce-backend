from django.contrib import admin
from .models import Advertisement

@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ('title', 'vendor', 'position', 'startDate', 'endDate', 'isActive')
    list_filter = ('position', 'isActive')
    search_fields = ('title', 'vendor__email')
