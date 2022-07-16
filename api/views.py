from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.viewsets import ModelViewSet
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, AllowAny, SAFE_METHODS
from rest_framework.decorators import action

from api.models import Cart, CartItem, ProductSpecialInterval, Order, OrderItem, Product, UserPushNotificationToken
from api.permissions import IsAdminUserOrPostOnly, IsOwner
from api.serializers import CartItemSerializer, CartSerializer, CreateCartItemSerializer, CreateOrderSerializer, CreateProductSerializer, GetNewOrderCodeSerializer, MarkOrderAsFailedSerializer, ProductSpecialIntervalSerializer, GetOrderSerializer, UpdateCartItemSerializer, UserPushNotificationTokenSerializer, VerifyOrderWithCodeSerializer, OrderItemSerializer, OrderItemTimeSerializer, OrderSerializer, ProductSerializer, UpdateProductSerializer


class OrderViewSet(ModelViewSet):
    queryset = Order.objects.prefetch_related('items__product__files')

    def create(self, request, *args, **kwargs):
        serializer = CreateOrderSerializer(
            data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    def get_permissions(self):
        if (self.action == 'mark_order_as_failed') or (self.request.method != 'POST'):
            return [IsAdminUser()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.action == 'get_new_code':
            return GetNewOrderCodeSerializer
        if self.action == 'mark_order_as_failed':
            return MarkOrderAsFailedSerializer
        if self.action == 'get_order':
            return GetOrderSerializer
        if self.action == 'verify_order':
            return VerifyOrderWithCodeSerializer
        if self.request.method == 'POST':
            return CreateOrderSerializer
        return OrderSerializer

    def get_serializer_context(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ipaddress = x_forwarded_for.split(',')[-1].strip()
        else:
            ipaddress = self.request.META.get('REMOTE_ADDR')
        return {'request': self.request, 'ip': ipaddress}

    @action(detail=True, methods=['post'])
    def verify_order(self, request, pk):
        serializer = VerifyOrderWithCodeSerializer(
            data=request.data, context={'order_id': pk})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response('Заказ принят', status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def get_new_code(self, request, pk):
        serializer = GetNewOrderCodeSerializer(
            data=request.data, context={'order_id': pk})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response('Новый код отправлен', status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def get_order(self, request, pk):
        serializer = GetOrderSerializer(
            data=request.data, context={'order_id': pk})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def mark_order_as_failed(self, request, pk):
        serializer = MarkOrderAsFailedSerializer(
            data=request.data, context={'order_id': pk})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response('Заказ отмечен как недействительный', status=status.HTTP_200_OK)


class OrderItemViewSet(ModelViewSet):
    serializer_class = OrderItemSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return OrderItem.objects.filter(order=self.kwargs['order_pk']).prefetch_related('product__files', 'product__product_special_intervals').select_related('product__required_product')

class AllOrderItemsViewSet(ModelViewSet):
    http_method_names = ['get']
    serializer_class = OrderItemSerializer
    permission_classes = [IsAdminUser]
    queryset = OrderItem.objects.filter(Q(order__status='P')) .prefetch_related('product__files', 'product__product_special_intervals').select_related('product__required_product')

class ProductViewSet(ModelViewSet):
    queryset = Product.objects.prefetch_related(
        'files', 'product_special_intervals').select_related('required_product')

    def get_serializer_class(self):
        method = self.request.method

        if method in SAFE_METHODS:
            return ProductSerializer
        if method == 'POST':
            return CreateProductSerializer
        return UpdateProductSerializer

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [IsAdminUser()]

    @action(detail=True, methods=['get'])
    def timeView(self, request, pk):
        queryset = OrderItem.objects.filter(product_id=pk)
        serializer = OrderItemTimeSerializer(queryset, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def productSpecialIntervalView(self, request, pk):
        queryset = ProductSpecialInterval.objects.filter(product_id=pk)
        serializer = ProductSpecialIntervalSerializer(queryset, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


class CartViewSet(ModelViewSet):
    queryset = Cart.objects.prefetch_related('items__product__files')
    serializer_class = CartSerializer

    def get_permissions(self):
        if self.detail:
            return [AllowAny()]
        return [IsAdminUserOrPostOnly()]


class CartItemViewSet(ModelViewSet):
    def get_queryset(self):
        return CartItem.objects.filter(cart=self.kwargs['cart_pk']).prefetch_related('product__files')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateCartItemSerializer
        if self.request.method == 'PUT':
            return UpdateCartItemSerializer
        return CartItemSerializer

    def get_serializer_context(self):
        return {'request': self.request, 'cart_id': self.kwargs['cart_pk']}

class UserPushNotificationTokenViewSet(ModelViewSet):
    permission_classes = [IsAdminUser, IsOwner]
    serializer_class = UserPushNotificationTokenSerializer
    queryset = UserPushNotificationToken.objects.all()