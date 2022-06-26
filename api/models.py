from uuid import uuid4
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.db import models
 
""" Whenever ANY model is deleted, if it has a file field on it, delete the associated file too."""
@receiver(post_delete)
def delete_files_when_row_deleted_from_db(sender, instance, **kwargs):
    for field in sender._meta.concrete_fields:
        if isinstance(field,models.FileField):
            instance_file_field = getattr(instance,field.name)
            delete_file_if_unused(sender,instance,field,instance_file_field)
            
""" Delete the file if something else get uploaded in its place"""
@receiver(pre_save)
def delete_files_when_file_changed(sender,instance, **kwargs):
    # Don't run on initial save
    if not instance.pk:
        return
    for field in sender._meta.concrete_fields:
        if isinstance(field,models.FileField):
            #its got a file field. Let's see if it changed
            try:
                instance_in_db = sender.objects.get(pk=instance.pk)
            except sender.DoesNotExist:
                # We are probably in a transaction and the PK is just temporary
                # Don't worry about deleting attachments if they aren't actually saved yet.
                return
            instance_in_db_file_field = getattr(instance_in_db,field.name)
            instance_file_field = getattr(instance,field.name)
            if instance_in_db_file_field.name != instance_file_field.name:
                delete_file_if_unused(sender,instance,field,instance_in_db_file_field)

""" Only delete the file if no other instances of that model are using it"""    
def delete_file_if_unused(model,instance,field,instance_file_field):
    dynamic_field = {}
    dynamic_field[field.name] = instance_file_field.name
    other_refs_exist = model.objects.filter(**dynamic_field).exclude(pk=instance.pk).exists()
    if not other_refs_exist:
        instance_file_field.delete(False)




class Product(models.Model):
    title = models.CharField(max_length=255)
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)

class ProductFile(models.Model):
    product = models.ForeignKey(to=Product, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='api/products/files')

class Order(models.Model):

    PAYMENT_STATUS_WAITING = 'W'
    PAYMENT_STATUS_PENDING = 'P'
    PAYMENT_STATUS_COMPLETE = 'C'
    PAYMENT_STATUS_FAILED = 'F'
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_STATUS_WAITING, 'Waiting For Phone Verification'),
        (PAYMENT_STATUS_PENDING, 'Pending'),
        (PAYMENT_STATUS_COMPLETE, 'Complete'),
        (PAYMENT_STATUS_FAILED, 'Failed')
    ]

    phone = models.CharField(max_length=15)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=1, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_STATUS_WAITING)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    code = models.CharField(max_length=4)

class OrderItem(models.Model):
    order = models.ForeignKey(to=Order, on_delete=models.PROTECT, related_name='items')
    product = models.ForeignKey(to=Product, on_delete=models.PROTECT, related_name='order_items')
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)

class CartItem(models.Model):
    cart = models.ForeignKey(to=Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(to=Product, on_delete=models.PROTECT, related_name='+')
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
