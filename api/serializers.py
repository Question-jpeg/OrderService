from datetime import datetime, timedelta
import decimal
import random
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from api.models import Cart, CartItem, Order, OrderCode, OrderItem, Product, ProductFile

class ProductFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductFile
        fields = ['id', 'file']


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

    files = ProductFileSerializer(many=True)


class CreateProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

    files = serializers.ListField(
        child=serializers.FileField(), allow_empty=False, write_only=True)

    def save(self, **kwargs):
        with transaction.atomic():
            list_of_files = self.validated_data['files']
            del self.validated_data['files']

            self.instance = Product.objects.create(**self.validated_data)

            list_to_create = [ProductFile(
                product=self.instance, file=file) for file in list_of_files]
            ProductFile.objects.bulk_create(list_to_create)

            return self.instance


class UpdateProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

    files = serializers.ListField(
        child=serializers.FileField(), allow_empty=False, write_only=True)

    def save(self, **kwargs):
        with transaction.atomic():
            list_of_files = self.validated_data['files']
            del self.validated_data['files']

            Product.objects.filter(pk=self.instance.pk).update(
                **self.validated_data)

            ProductFile.objects.filter(product=self.instance).delete()

            list_to_create = [ProductFile(
                product=self.instance, file=file) for file in list_of_files]
            ProductFile.objects.bulk_create(list_to_create)

            return self.instance


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = '__all__'

    product = ProductSerializer()


class OrderItemTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['start_datetime', 'end_datetime']


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = '__all__'

    items = OrderItemSerializer(many=True, read_only=True)


def condition_constructor(start_time, end_time):
            start_endpoint_condition = Q(start_datetime__gte=start_time) & Q(start_datetime__lte=end_time)
            end_endpoint_condition = Q(end_datetime__gte=start_time) & Q(end_datetime__lte=end_time)
            middle_condition_over = Q(start_datetime__lte=start_time) & Q(end_datetime__gte=end_time)
            middle_condition_under = Q(start_datetime__gte=start_time) & Q(end_datetime__lte=end_time)

            return (start_endpoint_condition |
                    end_endpoint_condition   |
                    middle_condition_over    |
                    middle_condition_under)

class CreateOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['cart_id', 'phone', 'name']

    cart_id = serializers.UUIDField()
    
    def validate_cart_id(self, cart_id):
        if not Cart.objects.filter(pk=cart_id).exists():
            raise serializers.ValidationError(
                'Корзина не найдена')
        if not CartItem.objects.filter(cart_id=cart_id).exists():
            raise serializers.ValidationError('Корзина пуста')
        return cart_id

    def save(self, **kwargs):
        with transaction.atomic():
            cart_id = self.validated_data['cart_id']
            phone = self.validated_data['phone']
            name = self.validated_data['name'].capitalize()

            cart = get_object_or_404(Cart.objects.all(), pk=cart_id)

            queryset = CartItem.objects.filter(cart=cart)

            list_for_filling = []
            total = 0

            for cart_item in queryset:
                product = cart_item.product
                start = cart_item.start_datetime
                end = cart_item.end_datetime
                total_price = cart_item.total_price

                if not product.is_available:
                    raise serializers.ValidationError(
                        {'error': {'product_id': product.pk, 'message': 'Продукт недоступен'}})

                start_extended = start - timedelta(minutes=29)
                end_extended = end + timedelta(minutes=29)

                if OrderItem.objects.filter(product=product).filter(condition_constructor(start_extended, end_extended)).exists():
                    raise serializers.ValidationError(
                        {'error': {'product_id': product.pk, 'message': 'Похоже, что кто то уже забронировал этот объект на введённое вами время'}})

                list_for_filling.append(
                    {'product': product, 'start_datetime': start, 'end_datetime': end, 'total_price': total_price})

                total += total_price

            self.instance = Order.objects.create(name=name, phone=phone, total_price=total)

            list_for_creating = [
                OrderItem(order=self.instance, **data) for data in list_for_filling]
            OrderItem.objects.bulk_create(list_for_creating)

            digits = '0123456789'
            code = ''.join(random.choices(digits, k=4))
            while OrderCode.objects.filter(code=code).exists():
                code = ''.join(random.choices(digits, k=4))

            OrderCode.objects.create(order=self.instance, code=code)

            cart.delete()

            return self.instance

class VerifyOrderWithCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderCode
        fields = ['code']

    code = serializers.CharField()

    def save(self, **kwargs):
        order_id = self.context['order_id']
        code = self.validated_data['code']

        order_code = get_object_or_404(OrderCode.objects.all(), order_id=order_id)
        
        if order_code.code == code:
            order = get_object_or_404(Order.objects.all(), pk=order_id)
            order.status = 'P'
            order.save()

            order_code.delete()
        else:
            raise serializers.ValidationError({'error': 'Неверный код верификации'})



class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        exclude = ['cart']

    product = ProductSerializer()

class CreateCartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        exclude = ['total_price', 'cart']

    def save(self, **kwargs):
        cart_id = self.context['cart_id']
        product = self.validated_data['product']
        start = self.validated_data['start_datetime']
        end = self.validated_data['end_datetime']

        time_difference = end - start

        if (time_difference.seconds % 3600 != 0) or (start >= end):
            raise serializers.ValidationError(
                {'error': 'Некорректный ввод даты'})

        if not product.is_available:
            raise serializers.ValidationError({'error': 'Продукт недоступен'})

        start_extended = start - timedelta(minutes=29)
        end_extended = end + timedelta(minutes=29)

        if OrderItem.objects.filter(product=product).filter(condition_constructor(start_extended, end_extended)).exists():
            raise serializers.ValidationError(
                {'error': {'product_id': product.pk, 'message': 'Похоже, что кто то уже забронировал этот объект на введённое вами время'}})

        start_shorten = start + timedelta(minutes=1)
        end_shorten = end - timedelta(minutes=1)

        if CartItem.objects.filter(cart_id=cart_id, product=product).filter(condition_constructor(start_shorten, end_shorten)).exists():
            raise serializers.ValidationError(
                {'error': {'product_id': product.pk, 'message': 'Время брони этого объекта пересекается с таким же объектом, который у вас уже в корзине'}})

        hours = decimal.Decimal(time_difference.seconds / 3600)
        total_price = product.price_per_hour * hours
        self.instance = CartItem.objects.create(
            **self.validated_data, cart_id=cart_id, total_price=total_price)
        return self.instance

class CartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart
        fields = '__all__'
        read_only_fields = ['id']

    items = CartItemSerializer(many=True, read_only=True)
