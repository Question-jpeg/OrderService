from datetime import datetime, timedelta
import random
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from api.models import Cart, CartItem, ProductSpecialInterval, Order, OrderItem, Product, ProductFile, UserPushNotificationToken

from django.conf import settings

from .utils.pushNotifications import send_push_message
from .smsaero import SmsAero


class ProductFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductFile
        fields = ['id', 'file']


class CreateProductFilesSerializer(serializers.Serializer):
    files = serializers.ListField(
        child=serializers.FileField(), allow_empty=False)

    def save(self, **kwargs):
        product_id = self.context['product_id']
        product = get_object_or_404(Product.objects.all(), pk=product_id)
        files = self.validated_data['files']

        list_for_create = [ProductFile(
            product=product, file=file) for file in files]

        ProductFile.objects.bulk_create(list_for_create)


class DeleteProductFilesSerializer(serializers.Serializer):
    files_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False)

    def save(self, **kwargs):
        product_id = self.context['product_id']
        product = get_object_or_404(Product.objects.all(), pk=product_id)
        files_ids = self.validated_data['files_ids']
        ProductFile.objects.filter(pk__in=files_ids, product=product).delete()


class ProductSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class ProductSpecialIntervalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSpecialInterval
        exclude = ['product']

    def save(self, **kwargs):
        start_datetime = self.validated_data['start_datetime']
        end_datetime = self.validated_data['end_datetime']
        is_weekends = self.validated_data['is_weekends']
        additional_price_per_unit = self.validated_data['additional_price_per_unit']
        product_id = self.context['product_id']
        product = get_object_or_404(Product.objects.all(), pk=product_id)

        if (start_datetime is None) and (end_datetime is None) and (not is_weekends):
            raise serializers.ValidationError(
                {'message': '???? ???????????????? ???? ???????? ???? ?????????????????? ????????????????????'})

        if ((start_datetime is not None) or (end_datetime is not None)) and is_weekends:
            raise serializers.ValidationError(
                {'message': '?????????????? ?????????????????????????? ??????????????????'})

        if ((start_datetime is not None) and (end_datetime is None)) or ((start_datetime is None) and (end_datetime is not None)):
            raise serializers.ValidationError(
                {'message': '???????? ???? ?????? ???? ??????????????????'})

        queryset = ProductSpecialInterval.objects.all()
        queryset = queryset.filter(~Q(pk=self.instance.pk)) if self.instance else queryset

        if not is_weekends:
            start_datetime = start_datetime.replace(
                hour=0, minute=0, second=0, microsecond=0)
            end_datetime = end_datetime.replace(
                hour=0, minute=0, second=0, microsecond=0)
            queryset = queryset.filter(
                condition_constructor(start_datetime, end_datetime))
        else:
            queryset = queryset.filter(is_weekends=True)

        if queryset.exists():
            raise serializers.ValidationError(
                {'message': '?????????????????????? ???????????????? ?????? ????????????????'})

        if self.instance:
            self.instance.start_datetime = start_datetime
            self.instance.end_datetime = end_datetime
            self.instance.is_weekends = is_weekends
            self.instance.additional_price_per_unit = additional_price_per_unit
            self.instance.save()
        else:
            self.instance = ProductSpecialInterval.objects.create(
                start_datetime=start_datetime, end_datetime=end_datetime, is_weekends=is_weekends, additional_price_per_unit=additional_price_per_unit, product=product)

        return self.instance

class DeleteSpecialIntervalsSerializer(serializers.Serializer):
    intervals_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)

    def save(self, **kwargs):
        product_id = self.context['product_id']
        product = get_object_or_404(Product.objects.all(), pk=product_id)
        intervals_ids = self.validated_data['intervals_ids']
        ProductSpecialInterval.objects.filter(pk__in=intervals_ids, product=product).delete()

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

    files = ProductFileSerializer(many=True)
    required_product = ProductSimpleSerializer()
    product_special_intervals = ProductSpecialIntervalSerializer(many=True)


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


def getStartEnd(start, end, use_hotel_booking_time):
    return [start.replace(hour=14, minute=0, second=0, microsecond=0), end.replace(hour=12, minute=0, second=0, microsecond=0), end.replace(hour=14, minute=0, second=0, microsecond=0)] if use_hotel_booking_time else [start, end, end]


def is_time_in_range(start, end, x):
    if start <= end:
        return start <= x <= end
    else:
        return start <= x or x <= end


def calculateProductTotalPrice(start, end, fixed_end, product, quantity, error_message):

    if OrderItem.objects.filter(~Q(order__status='F')).filter(product=product).filter(condition_constructor(start, end)).exists():
        raise serializers.ValidationError(
            {'product_id': product.pk, 'message': '????????????, ?????? ?????? ???? ?????? ???????????????????????? ???????? ?????????? ???? ?????????????????? ???????? ??????????'})

    unit_price = product.unit_price
    time_unit = product.time_unit
    min_unit = product.min_unit
    max_unit = product.max_unit
    min_hour = product.min_hour
    max_hour = product.max_hour
    use_hotel_booking_time = product.use_hotel_booking_time

    # product total price calculator
    time_difference = fixed_end - start

    if time_unit == 'H':
        seconds = 3600
    else:
        seconds = (60*60*24)

    units = int(time_difference.seconds / seconds)

    if (time_difference.seconds % seconds != 0) or \
        (not use_hotel_booking_time and (not is_time_in_range(min_hour, max_hour, start.time()) or
                                         not is_time_in_range(min_hour, max_hour, end.time()))) or \
            (start >= end) or (units < min_unit) or (units > max_unit):
        raise serializers.ValidationError(
            {'product_id': product.pk, 'message': error_message})

    extra_price = 0
    interval_queryset = ProductSpecialInterval.objects.filter(
        condition_constructor(start, end)).filter(product=product)
    weekends_queryset = ProductSpecialInterval.objects.filter(
        is_weekends=True, product=product)
    if interval_queryset.exists():
        interval = interval_queryset.get()
        interval_start = interval.start_datetime
        interval_end = interval.end_datetime

        if time_unit == 'H':
            extra_price += interval.additional_price_per_unit * \
                overlapping(interval_start, interval_end,
                            start, fixed_end, days=False)
        else:
            extra_price += overlapping(interval_start, interval_end,
                                       start, fixed_end) * interval.additional_price_per_unit
            if weekends_queryset.exists():
                weekends_price = weekends_queryset.get()
                interval_weekends = count_of_weekends(
                    interval_start, interval_end)
                user_weekends = count_of_weekends(start, fixed_end)
                extra_price += weekends_price.additional_price_per_unit * \
                    max(0, (user_weekends - interval_weekends))

    elif weekends_queryset.exists():
        weekends_price = weekends_queryset.get()
        if time_unit == 'H' and start.weekday() > 4:
            extra_price += weekends_price.additional_price_per_unit * units
        elif time_unit == 'D':
            extra_price += count_of_weekends(
                start, fixed_end) * weekends_price.additional_price_per_unit

    total_price = (unit_price * units + extra_price) * quantity
    return total_price
    # /product total price calculator


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = '__all__'

    product = ProductSerializer()

class OrderItemTimeInnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['start_datetime', 'end_datetime']

class OrderItemTimeSerializer(serializers.Serializer):
    current_datetime = serializers.DateTimeField()

    def save(self, **kwargs):
        current_datetime = self.validated_data['current_datetime']
        product_id = self.context['product_id']
        queryset = OrderItem.objects.filter(end_datetime__gt=current_datetime, product_id=product_id)
        return OrderItemTimeInnerSerializer(queryset, many=True).data


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = '__all__'

    items = OrderItemSerializer(many=True, read_only=True)


class CreateOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['cart_id', 'phone', 'name', 'agreement']

    cart_id = serializers.UUIDField()
    agreement = serializers.BooleanField()

    def validate_cart_id(self, cart_id):
        if not Cart.objects.filter(pk=cart_id).exists():
            raise serializers.ValidationError({
                'message': '?????????????? ???? ??????????????'})
        if not CartItem.objects.filter(cart_id=cart_id).exists():
            raise serializers.ValidationError({'message': '?????????????? ??????????'})
        return cart_id

    def validate_agreement(self, agreement):
        if not agreement:
            raise serializers.ValidationError(
                {'message': '?????????? ???????????????? ??????????, ???? ???????????? ?????????????????????? ?? ?????????????????? ????????????'})
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
        cart_item_ids = []

        for cart_item in queryset:
            product = cart_item.product

            use_hotel_booking_time = product.use_hotel_booking_time
            required_product = product.required_product
            max_persons = product.max_persons

            start_dat = cart_item.start_datetime
            end_dat = cart_item.end_datetime
            quantity = cart_item.quantity
            price = cart_item.price

            start, end, fixed_end = getStartEnd(
                start_dat, end_dat, use_hotel_booking_time)

            if not product.is_available:
                raise serializers.ValidationError(
                    {'product_id': product.pk, 'message': '?????????? ????????????????????'})

            if (required_product):
                if not CartItem.objects.filter(cart_id=cart_id, product=required_product).exists():
                    raise serializers.ValidationError(
                        {'product_id': required_product.pk, 'message': '?????????? ?????????? ???????????? ???????????????????? ?????? ?????????? ??????????????????'})

            total_price = calculateProductTotalPrice(
                start, end, fixed_end, product, quantity, '?????????????? ?????????? ????????????????????, ????????????????????, ???????????????????????????? ??????????')

            list_for_filling.append(
                {'product': product, 'start_datetime': start, 'end_datetime': end, 'total_price': total_price, 'quantity': quantity})

            total += total_price
            cart_items_total += price
            if max_persons:
                total_max_persons += max_persons
            cart_item_ids.append(product.pk)

            if price != total_price:
                cart_item.price = total_price
                cart_item.save()

        if total != cart_items_total:
            raise serializers.ValidationError(
                {'message': '???????? ???? ???????????? ????????????????????, ????????????????????, ?????????????????????????? ??????????????'})

        if cart_persons > total_max_persons:
            query_total_max = Product.objects.filter(max_persons__gt=0).aggregate(
                Sum('max_persons'))['max_persons__sum']
            if cart_persons > query_total_max:
                raise serializers.ValidationError(
                    {'message': f'?????????????????????? ?????????????????? ??????????????????: {query_total_max} ??????'})
            else:
                queryset = Product.objects.filter(max_persons__gt=0).filter(
                    ~Q(pk__in=cart_item_ids)).prefetch_related('files', 'product_special_intervals').select_related('required_product')
                raise serializers.ValidationError({'products': ProductSerializer(
                    queryset, many=True).data, 'message': '?? ?????????? ???????????? ???????????????????????? ???????????????? ????????. ???????????????????? ???????????????? ????????????'})

        with transaction.atomic():
            digits = '0123456789'
            code = ''.join(random.choices(digits, k=4))

            self.instance = Order.objects.create(
                name=name, phone=phone, code=code, ip_address=self.context['ip'], persons=cart_persons, attempts_left=3, resends_left=3)

            list_for_creating = [
                OrderItem(order=self.instance, **data) for data in list_for_filling]
            OrderItem.objects.bulk_create(list_for_creating)

            cart.delete()

            if not settings.DEBUG:
                smsApi = SmsAero(settings.SMSAERO_LOGIN,
                                 settings.SMSAERO_API_KEY)
                send = smsApi.send(
                    phone, f'Forest House. ?????????????????????? ????????????????????????. ?????? ??????????????????????: {code}')

            try:
                sending = [send_push_message(tokenObj.push_token, 'Forest House', '???????????????? ?????????? ??????????!')
                           for tokenObj in UserPushNotificationToken.objects.all()]
            except:
                pass

            return self.instance


class VerifyOrderWithCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['code', 'phone']

    def save(self, **kwargs):
        order_id = self.context['order_id']
        code = self.validated_data['code']
        phone = self.validated_data['phone']

        try:
            order = Order.objects.get(status='W', pk=order_id, phone=phone)
            if order.code == code:
                order.status = 'P'
                order.save()
            else:
                order.attempts_left = order.attempts_left - 1
                if order.attempts_left == 0:
                    order.status = 'F'
                    order.save()
                    raise serializers.ValidationError(
                        {'message': '???? ?????????????????? ???????????????????? ?????????????? ?????????? ???????????????????????????????? ????????. ?????????? ?????????????? ?????? ????????????????????????????????. ?????????????????? ?????? ?????????? ???????????????????????????? ??????????.'})
                order.save()
                raise serializers.ValidationError(
                    {'message': '???????????????? ?????? ??????????????????????'})
        except Order.DoesNotExist:
            raise serializers.ValidationError({'message':
                                               '?????????? ???? ???????????????? "?????????????? ?????????????????????????????? ??????" ???? ????????????'})


class GetNewOrderCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['phone']

    def save(self, **kwargs):
        order_id = self.context['order_id']
        phone = self.validated_data['phone']
        try:
            order = Order.objects.get(pk=order_id, status='W', phone=phone)
            if order.resends_left == 0:
                raise serializers.ValidationError(
                    {'message': '???? ?????????????????? ???????????????????? ???????????????? ???????????????????????????????? ????????. ?????????????????? ?????? ???????? ?????? ???? ?????????????? ???????????????????????????? ??????????'})

            digits = '0123456789'
            code = ''.join(random.choices(digits, k=4))

            if not settings.DEBUG:
                smsApi = SmsAero(settings.SMSAERO_LOGIN,
                                 settings.SMSAERO_API_KEY)
                send = smsApi.send(
                    order.phone, f'Forest House. ?????????? ?????? ??????????????????????: {code}')

            order.code = code
            order.resends_left = order.resends_left - 1
            order.save()
        except Order.DoesNotExist:
            raise serializers.ValidationError(
                {'message': '?????????? ???? ???????????????? "?????????????? ?????????????????????????????? ??????" ???? ????????????'})


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


class CreateOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['product', 'start_datetime', 'end_datetime', 'quantity']

    def save(self, **kwargs):
        order_id = self.context['order_id']
        order = get_object_or_404(Order.objects.all(), pk=order_id)
        product = self.validated_data['product']
        quantity = self.validated_data['quantity']
        start_dat = self.validated_data['start_datetime']
        end_dat = self.validated_data['end_datetime']

        start, end, fixed_end = getStartEnd(
            start_dat, end_dat, product.use_hotel_booking_time)
        price = calculateProductTotalPrice(
            start, end, fixed_end, product, quantity, '???????????????????????? ???????? ????????')

        self.instance = OrderItem.objects.create(
            order=order, product=product, start_datetime=start, end_datetime=end, quantity=quantity, total_price=price)
        return self.instance


class UpdateOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['product', 'start_datetime', 'end_datetime', 'quantity']

    def save(self, **kwargs):
        order_item = self.instance

        product = self.validated_data['product']
        quantity = self.validated_data['quantity']
        start_dat = self.validated_data['start_datetime']
        end_dat = self.validated_data['end_datetime']

        start, end, fixed_end = getStartEnd(
            start_dat, end_dat, product.use_hotel_booking_time)

        price = calculateProductTotalPrice(
            start, end, fixed_end, product, quantity, '???????????????????????? ???????? ????????')

        order_item.product = product
        order_item.quantity = quantity
        order_item.start_datetime = start
        order_item.end_datetime = end
        order_item.total_price = price
        order_item.save()

        self.instance = order_item
        return self.instance


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
            raise serializers.ValidationError({'message': '?????????? ?????????????? ??????'})

        product = self.validated_data['product']
        start = self.validated_data['start_datetime']
        end = self.validated_data['end_datetime']
        quantity = self.validated_data['quantity']

        # product properties
        required_product = product.required_product
        is_available = product.is_available
        use_hotel_booking_time = product.use_hotel_booking_time
        # /product properties

        start, end, fixed_end = getStartEnd(start, end, use_hotel_booking_time)

        if not is_available:
            raise serializers.ValidationError({'message': '?????????? ????????????????????'})

        if required_product:
            if not CartItem.objects.filter(cart_id=cart_id, product=required_product).exists():
                raise serializers.ValidationError(
                    {'product_id': required_product.pk, 'message': '?????????? ?????????? ???????????? ???????????????????? ?????? ?????????? ??????????????????'})

            required_product_cart_item = CartItem.objects.get(
                cart_id=cart_id, product=required_product)
            if (start < required_product_cart_item.start_datetime) or (end > required_product_cart_item.end_datetime):
                raise serializers.ValidationError(
                    {'product_id': product.pk,
                        'message': '???? ???? ???????????? ?????????????????????????? ?????????? ???? ?????????????? ????????????????, ?????? ???????????????? ??????????'}
                )

        if CartItem.objects.filter(cart_id=cart_id, product=product).filter(condition_constructor(start, end)).exists():
            raise serializers.ValidationError(
                {'product_id': product.pk, 'message': '?????????? ?????????? ?????????? ?????????????? ???????????????????????? ?? ?????????? ???? ????????????????, ?????????????? ?? ?????? ?????? ?? ??????????????'})

        price = calculateProductTotalPrice(
            start, end, fixed_end, product, quantity, '???????????????????????? ???????? ????????')
        self.instance = CartItem.objects.create(
            cart_id=cart_id, product=product, start_datetime=start, end_datetime=end, price=price, quantity=quantity)
        return self.instance


class UpdateCartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ['start_datetime', 'end_datetime',
                  'product', 'price', 'quantity']
        read_only_fields = ['price']

    product = ProductSerializer(read_only=True)

    def save(self, **kwargs):
        with transaction.atomic():
            cart_item = self.instance
            start = self.validated_data['start_datetime']
            end = self.validated_data['end_datetime']
            quantity = self.validated_data['quantity']
            cart = cart_item.cart
            product = cart_item.product

            cart_item.delete()

            serializer = CreateCartItemSerializer(
                data={'product': product.pk, 'start_datetime': start, 'end_datetime': end, 'quantity': quantity}, context={'cart_id': cart.pk})
            serializer.is_valid(raise_exception=True)
            self.instance = serializer.save()

            return self.instance


class CartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart
        fields = '__all__'
        read_only_fields = ['id']

    items = CartItemSerializer(many=True, read_only=True)


class UserPushNotificationTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPushNotificationToken
        fields = '__all__'
        read_only_fields = ['user']

    def save(self, **kwargs):
        push_token = self.validated_data['push_token']
        request = self.context['request']
        user = request.user

        obj, created = UserPushNotificationToken.objects.get_or_create(
            user=user, defaults={'push_token': push_token, 'user': user})
        if not created:
            obj.push_token = push_token
            obj.save()
        self.instance = obj
        return self.instance
