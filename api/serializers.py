from datetime import datetime, timedelta
import random
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from api.models import Cart, CartItem, ProductSpecialInterval, Order, OrderItem, Product, ProductFile

from django.conf import settings
from .smsaero import SmsAero


class ProductFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductFile
        fields = ['id', 'file']

class RequiredProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

    files = ProductFileSerializer(many=True)
    required_product = RequiredProductSerializer()


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

    universal_query = Q(start_datetime__lte=end_time) & Q(
        end_datetime__gte=start_time)

    return universal_query

def count_of_weekends(start_time, end_time):

    weekends = 0

    for day in range(1, (end_time - start_time).days + 1):
        if (start_time + timedelta(days=day)).weekday() > 4:
            weekends += 1

    return weekends

def overlapping(r1_start_time, r1_end_time, r2_start_time, r2_end_time, days=True):
    delta = 0

    latest_start = max(r1_start_time, r2_start_time)
    earliest_end = min(r1_end_time, r2_end_time)
    delta = (earliest_end - latest_start)
    difference = delta.days if days else delta.seconds // 3600

    return difference



class CreateOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['cart_id', 'phone', 'name', 'agreement']

    cart_id = serializers.UUIDField()
    agreement = serializers.BooleanField()

    def validate_cart_id(self, cart_id):
        if not Cart.objects.filter(pk=cart_id).exists():
            raise serializers.ValidationError({
                'message': 'Корзина не найдена'})
        if not CartItem.objects.filter(cart_id=cart_id).exists():
            raise serializers.ValidationError({'message': 'Корзина пуста'})
        return cart_id

    def validate_agreement(self, agreement):
        if not agreement:
            raise serializers.ValidationError(
                {'message': 'Чтобы оформить заказ, вы должны согласиться с условиями оферты'})
        return agreement

    def save(self, **kwargs):

        cart_id = self.validated_data['cart_id']
        phone = self.validated_data['phone']
        name = self.validated_data['name'].capitalize()

        cart = get_object_or_404(Cart.objects.all(), pk=cart_id)
        cart_persons = cart.persons
        queryset = CartItem.objects.filter(
            cart=cart).select_related('product__required_product')

        list_for_filling = []
        total = 0
        cart_items_total = 0
        total_max_persons = 0
        required_product_cart_items = []
        cart_item_ids = []

        for cart_item in queryset:
            product = cart_item.product

            title = product.title
            unit_price = product.unit_price
            time_unit = product.time_unit
            min_unit = product.min_unit
            max_unit = product.max_unit
            min_hour = product.min_hour
            max_hour = product.max_hour
            use_hotel_booking_time = product.use_hotel_booking_time
            required_product = product.required_product
            max_persons = product.max_persons

            start = cart_item.start_datetime
            end = cart_item.end_datetime
            price = cart_item.price

            if not product.is_available:
                raise serializers.ValidationError(
                    {'product_id': product.pk, 'message': 'Товар недоступен'})

            # product total price calculator
            if use_hotel_booking_time:
                start = start.replace(
                    hour=14, minute=0, second=0, microsecond=0)
                end = end.replace(hour=12, minute=0, second=0, microsecond=0)

                time_difference = end.replace(hour=14) - start
                units = time_difference.days
            else:
                time_difference = end - start
                if time_unit == 'H':
                    seconds = 3600
                else:
                    seconds = (60*60*24)
                units = int(time_difference.seconds / seconds)

            if (not use_hotel_booking_time and time_difference.seconds % seconds != 0) or \
            (not use_hotel_booking_time and (start.time() < min_hour or start.time() >= max_hour or end.time() <= min_hour or end.time() > max_hour )) or \
            (start >= end) or (units < min_unit) or (units > max_unit):
                raise serializers.ValidationError(
                    {'product_id': product.pk, 'message': 'Параметры брони изменились. Пожалуйста, перебронируйте товар'})
                    
            extra_price = 0
            interval_queryset = ProductSpecialInterval.objects.filter(
                    condition_constructor(start, end)).filter(product=product)
            weekends_queryset = ProductSpecialInterval.objects.filter(common_type='E', product=product)
            fixed_end = end.replace(hour=14) if use_hotel_booking_time else end
            if interval_queryset.exists():
                interval = interval_queryset.get()
                interval_start = interval.start_datetime
                interval_end = interval.end_datetime

                if time_unit == 'H':
                    extra_price += interval.additional_price_per_unit * overlapping(interval_start, interval_end, start, fixed_end, days=False)
                else:
                    extra_price += overlapping(interval_start, interval_end, start, fixed_end) * interval.additional_price_per_unit
                    if weekends_queryset.exists():
                        weekends_price = weekends_queryset.get()
                        interval_weekends = count_of_weekends(interval_start, interval_end)
                        user_weekends = count_of_weekends(start, fixed_end)
                        extra_price += weekends_price.additional_price_per_unit * max(0, (user_weekends - interval_weekends))

            elif weekends_queryset.exists():
                weekends_price = weekends_queryset.get()
                if time_unit == 'H' and start.weekday() > 4:
                    extra_price += weekends_price.additional_price_per_unit * units
                elif time_unit == 'D':
                    extra_price += count_of_weekends(start, fixed_end) * weekends_price.additional_price_per_unit


            total_price = unit_price * units + extra_price
            # /product total price calculator

            if (required_product):
                if not CartItem.objects.filter(cart_id=cart_id, product=required_product).exists():
                    raise serializers.ValidationError(
                        {'product_id': required_product.pk, 'message': 'Бронь этого товара невозможна без брони основного'})

            else:
                required_product_cart_items.append(title)

            if OrderItem.objects.filter(~Q(order__status='F')).filter(product=product).filter(condition_constructor(start, end)).exists():
                raise serializers.ValidationError(
                    {'product_id': product.pk, 'message': 'Похоже, что кто то уже забронировал этот товар на введённое вами время'})

            list_for_filling.append(
                {'product': product, 'start_datetime': start, 'end_datetime': end, 'total_price': total_price})

            total += total_price
            cart_items_total += price
            if use_hotel_booking_time:
                total_max_persons += max_persons
            cart_item_ids.append(product.pk)

            if price != total_price:
                cart_item.price = total_price
                cart_item.save()

        if total != cart_items_total:
            raise serializers.ValidationError(
                {'message': 'Цены на товары изменились, пожалуйста, перепроверьте корзину'})

        if cart_persons > total_max_persons:
            query_total_max = Product.objects.filter(max_persons__gt=0).aggregate(
                Sum('max_persons'))['max_persons__sum']
            if cart_persons > query_total_max:
                raise serializers.ValidationError(
                    {'message': f'Максимально возможное заселение: {query_total_max} чел'})
            else:
                queryset = Product.objects.filter(max_persons__gt=0).filter(
                    ~Q(pk__in=cart_item_ids)).prefetch_related('files')
                raise serializers.ValidationError({'products': ProductSerializer(
                    queryset, many=True).data, 'message': 'В вашем заказе недостаточно спальных мест. Предлагаем добавить товары'})

        with transaction.atomic():
            digits = '0123456789'
            code = ''.join(random.choices(digits, k=4))

            self.instance = Order.objects.create(
                name=name, phone=phone, total_price=total, code=code, ip_address=self.context['ip'], persons=cart_persons, attempts_left=3, resends_left=3)

            list_for_creating = [
                OrderItem(order=self.instance, **data) for data in list_for_filling]
            OrderItem.objects.bulk_create(list_for_creating)

            cart.delete()

            if not settings.DEBUG:
                smsApi = SmsAero(settings.SMSAERO_LOGIN,
                                 settings.SMSAERO_API_KEY)
                send = smsApi.send(
                    phone, f'Подтвердите бронирование. Код верификации: {code}')

            return self.instance


class VerifyOrderWithCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['code']

    def save(self, **kwargs):
        order_id = self.context['order_id']
        code = self.validated_data['code']

        try:
            order = Order.objects.get(status='W', pk=order_id)
            if order.code == code:
                order.status = 'P'
                order.save()
            else:
                if order.attempts_left == 0:
                    order.status = 'F'
                    order.save()
                    raise serializers.ValidationError({'message': 'Вы превысили количество попыток ввода верификационного кода. Заказ помечен как недействительный. Позвоните нам чтобы верифицировать заказ.'})
                order.attempts_left = order.attempts_left - 1    
                order.save()
                raise serializers.ValidationError(
                {'message': 'Неверный код верификации'})
        except Order.DoesNotExist:
            raise serializers.ValidationError({'message':
                                               'Заказ со статусом "Ожидает верификационный код" не найден'})

class GetNewOrderCodeSerializer(serializers.Serializer):
    def save(self, **kwargs):
        order_id = self.context['order_id']
        try:
            order = Order.objects.get(pk=order_id, status='W')
            if order.resends_left == 0:
                raise serializers.ValidationError({'message': 'Вы превысили количество отправок верификационного кода. Позвоните нам если Вам не удалось верифицировать заказ'})

            digits = '0123456789'
            code = ''.join(random.choices(digits, k=4))

            if not settings.DEBUG:
                smsApi = SmsAero(settings.SMSAERO_LOGIN,
                                    settings.SMSAERO_API_KEY)
                send = smsApi.send(
                    order.phone, f'Подтвердите бронирование. Код верификации: {code}')

            order.code = code
            order.resends_left = order.resends_left - 1
            order.save()
        except Order.DoesNotExist:
            raise serializers.ValidationError({'message': 'Заказ со статусом "Ожидает верификационный код" не найден'})
                

class GetOrderSerializer(serializers.Serializer):
    code = serializers.CharField()

    def save(self, **kwargs):
        return get_object_or_404(Order.objects.all(), **self.validated_data, pk=self.context['order_id'])


class MarkOrderAsFailedSerializer(serializers.Serializer):
    def save(self, **kwargs):
        id = self.context['order_id']
        order = get_object_or_404(Order.objects.all(), pk=id)
        order.status = 'F'
        order.save()


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        exclude = ['cart']
        read_only_fields = ['price']

    product = ProductSerializer(read_only=True)


class CreateCartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        exclude = ['cart', 'price']

    def save(self, **kwargs):
        cart_id = self.context['cart_id']

        try:
            Cart.objects.get(pk=cart_id)
        except Cart.DoesNotExist:
            raise serializers.ValidationError({'message': 'Такой корзины нет'})

        product = self.validated_data['product']
        start = self.validated_data['start_datetime']
        end = self.validated_data['end_datetime']

        # product properties
        unit_price = product.unit_price
        min_unit = product.min_unit
        max_unit = product.max_unit
        min_hour = product.min_hour
        max_hour = product.max_hour
        time_unit = product.time_unit
        required_product = product.required_product
        is_available = product.is_available
        use_hotel_booking_time = product.use_hotel_booking_time
        # /product properties

        if not is_available:
            raise serializers.ValidationError({'message': 'Товар недоступен'})

        if required_product:
            if not CartItem.objects.filter(cart_id=cart_id, product=required_product).exists():
                raise serializers.ValidationError(
                    {'product_id': required_product.pk, 'message': 'Бронь этого товара невозможна без брони основного'})

            required_product_cart_item = CartItem.objects.get(
                cart_id=cart_id, product=required_product)
            if (start < required_product_cart_item.start_datetime) or (end > required_product_cart_item.end_datetime):
                raise serializers.ValidationError(
                    {'product_id': product.pk,
                        'message': 'Вы не можете забронировать товар на больший интервал, чем основной товар'}
                )

        if use_hotel_booking_time:
            start = start.replace(hour=14, minute=0, second=0, microsecond=0)
            end = end.replace(hour=12, minute=0, second=0, microsecond=0)

            time_difference = end.replace(hour=14) - start
            units = time_difference.days
        else:
            time_difference = end - start
            if time_unit == 'H':
                seconds = 3600
            else:
                seconds = (60*60*24)
            units = int(time_difference.seconds / seconds)

        if (not use_hotel_booking_time and time_difference.seconds % seconds != 0) or \
        (not use_hotel_booking_time and (start.time() < min_hour or start.time() >= max_hour or end.time() <= min_hour or end.time() > max_hour )) or \
        (start >= end) or (units < min_unit) or (units > max_unit):
            raise serializers.ValidationError(
                {'message': 'Некорректный ввод даты'})

        if OrderItem.objects.filter(~Q(order__status='F')).filter(product=product).filter(condition_constructor(start, end)).exists():
            raise serializers.ValidationError(
                {'product_id': product.pk, 'message': 'Похоже, что кто то уже забронировал этот объект на введённое вами время'})

        if CartItem.objects.filter(cart_id=cart_id, product=product).filter(condition_constructor(start, end)).exists():
            raise serializers.ValidationError(
                {'product_id': product.pk, 'message': 'Время брони этого объекта пересекается с таким же объектом, который у вас уже в корзине'})

        extra_price = 0
        interval_queryset = ProductSpecialInterval.objects.filter(
                condition_constructor(start, end)).filter(product=product)
        weekends_queryset = ProductSpecialInterval.objects.filter(common_type='E', product=product)
        fixed_end = end.replace(hour=14) if use_hotel_booking_time else end
        if interval_queryset.exists():
            interval = interval_queryset.get()
            interval_start = interval.start_datetime
            interval_end = interval.end_datetime

            if time_unit == 'H':
                extra_price += interval.additional_price_per_unit * overlapping(interval_start, interval_end, start, fixed_end, days=False)
            else:
                extra_price += overlapping(interval_start, interval_end, start, fixed_end) * interval.additional_price_per_unit
                if weekends_queryset.exists():
                    weekends_price = weekends_queryset.get()
                    interval_weekends = count_of_weekends(interval_start, interval_end)
                    user_weekends = count_of_weekends(start, fixed_end)
                    extra_price += weekends_price.additional_price_per_unit * max(0, (user_weekends - interval_weekends))

        elif weekends_queryset.exists():
            weekends_price = weekends_queryset.get()
            if time_unit == 'H' and start.weekday() > 4:
                extra_price += weekends_price.additional_price_per_unit * units
            elif time_unit == 'D':
                extra_price += count_of_weekends(start, fixed_end) * weekends_price.additional_price_per_unit

        price = unit_price * units + extra_price
        self.instance = CartItem.objects.create(
            cart_id=cart_id, product=product, start_datetime=start, end_datetime=end, price=price)
        return self.instance


class UpdateCartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ['start_datetime', 'end_datetime', 'product', 'price']
        read_only_fields = ['price']

    product = ProductSerializer(read_only=True)

    def save(self, **kwargs):
        with transaction.atomic():
            cart_item = self.instance
            start = self.validated_data['start_datetime']
            end = self.validated_data['end_datetime']
            cart = cart_item.cart
            product = cart_item.product

            cart_item.delete()

            serializer = CreateCartItemSerializer(
                data={'product': product.pk, 'start_datetime': start, 'end_datetime': end}, context={'cart_id': cart.pk})
            serializer.is_valid(raise_exception=True)
            self.instance = serializer.save()

            return self.instance


class CartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart
        fields = '__all__'
        read_only_fields = ['id']

    items = CartItemSerializer(many=True, read_only=True)


class ProductSpecialIntervalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSpecialInterval
        fields = ['start_datetime', 'end_datetime', 'common_type']
