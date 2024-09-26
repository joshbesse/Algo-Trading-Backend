from django.contrib import admin
from .models import ModelType, Trade, Portfolio

# Register your models here.
admin.site.register(ModelType)
admin.site.register(Trade)
admin.site.register(Portfolio)
