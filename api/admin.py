from django.contrib import admin
from django.db.models import F, Sum
from . import models

@admin.register(models.OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'start_datetime', 'end_datetime', 'total_price']

class OrderItemInline(admin.TabularInline):
    model = models.OrderItem
    extra = 3

@admin.register(models.Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]
    list_display = ['id', 'phone', 'name', 'status', 'total_price']

@admin.register(models.OrderCode)
class OrderCodeAdmin(admin.ModelAdmin):
    list_display = ['order', 'code']

class ProductFileInline(admin.TabularInline):
    model = models.ProductFile
    extra = 3

@admin.register(models.Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductFileInline]
    list_display = ['title', 'price_per_hour', 'is_available']

class CartItemInline(admin.TabularInline):
    model = models.CartItem
    extra = 3

@admin.register(models.Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id']
    inlines = [CartItemInline]

@admin.register(models.CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'start_datetime', 'end_datetime', 'total_price']