from uuid import uuid4
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.db import models
from django.contrib.auth.models import User
 
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

    TIME_UNIT_HOUR = 'H'
    TIME_UNIT_DAY = 'D'
    TIME_UNIT_CHOICES = [
        (TIME_UNIT_HOUR, 'Hour'),
        (TIME_UNIT_DAY, 'Day')
    ]

    title = models.CharField(max_length=255)
    unit_price = models.IntegerField()
    min_unit = models.PositiveSmallIntegerField()
    max_unit = models.PositiveSmallIntegerField()
    time_unit = models.CharField(max_length=1, choices=TIME_UNIT_CHOICES)
    min_hour = models.TimeField(null=True, blank=True)
    max_hour = models.TimeField(null=True, blank=True)
    required_product = models.ForeignKey(to='self', on_delete=models.SET_NULL, null=True, blank=True)
    is_available = models.BooleanField(default=True)
    use_hotel_booking_time = models.BooleanField()
    description = models.TextField(null=True, blank=True)
    max_persons = models.SmallIntegerField()

    def __str__(self) -> str:
        return self.title

class ProductFile(models.Model):
    product = models.ForeignKey(to=Product, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='files')

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
    total_price = models.IntegerField()
    code = models.CharField(max_length=4)
    attempts_left = models.SmallIntegerField()
    resends_left = models.SmallIntegerField()
    persons = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()

class OrderItem(models.Model):
    order = models.ForeignKey(to=Order, on_delete=models.PROTECT, related_name='items')
    product = models.ForeignKey(to=Product, on_delete=models.PROTECT, related_name='order_items')
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    total_price = models.IntegerField()

class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    persons = models.PositiveSmallIntegerField()

class ProductSpecialInterval(models.Model):
    COMMON_TYPE_WEEKENDS = 'E'
    COMMON_TYPE_CHOICES = [
        (COMMON_TYPE_WEEKENDS, 'Выходные')
    ]
    start_datetime = models.DateTimeField(null=True, blank=True)
    end_datetime = models.DateTimeField(null=True, blank=True)
    common_type = models.CharField(null=True, blank=True, choices=COMMON_TYPE_CHOICES, max_length=1)
    product = models.ForeignKey(to=Product, on_delete=models.CASCADE, related_name='product_special_intervals')
    additional_price_per_unit = models.IntegerField()

class CartItem(models.Model):
    cart = models.ForeignKey(to=Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(to=Product, on_delete=models.PROTECT, related_name='+')
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    price = models.IntegerField()

class UserPushNotificationToken(models.Model):
    user = models.ForeignKey(to=User, on_delete=models.CASCADE, related_name='push_token')
    push_token = models.CharField(max_length=255)
