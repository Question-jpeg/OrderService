import json
from rest_framework.viewsets import ModelViewSet
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, AllowAny, SAFE_METHODS
from rest_framework.decorators import action

from api.models import Cart, CartItem, Order, OrderItem, Product
from api.serializers import CartItemSerializer, CartSerializer, CreateCartItemSerializer, CreateOrderSerializer, CreateProductSerializer, GetOrderSerializer, VerifyOrderWithCodeSerializer, OrderItemSerializer, OrderItemTimeSerializer, OrderSerializer, ProductSerializer, UpdateProductSerializer

from django.conf import settings
from .smsaero import SmsAero
import urllib3

class OrderViewSet(ModelViewSet):
    queryset = Order.objects.prefetch_related('items__product__files')

    def create(self, request, *args, **kwargs):
        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    def get_permissions(self):
        if self.request.method == 'POST':
            return [AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.action == 'get_order':
            return GetOrderSerializer
        if self.action == 'verify_order':
            return VerifyOrderWithCodeSerializer
        if self.request.method == 'POST':
            return CreateOrderSerializer
        return OrderSerializer

    @action(detail=True, methods=['post'])
    def verify_order(self, request, pk):
        serializer = VerifyOrderWithCodeSerializer(data=request.data, context={'order_id': pk})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({'Заказ принят'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def get_order(self, request, pk):
        serializer = GetOrderSerializer(data=request.data, context={'order_id': pk})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)

        
class OrderItemViewSet(ModelViewSet):
    serializer_class = OrderItemSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return OrderItem.objects.filter(order=self.kwargs['order_pk']).prefetch_related('product__files')

class ProductViewSet(ModelViewSet):
    queryset = Product.objects.prefetch_related('files')  

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
        queryset = OrderItem.objects.filter(product=pk)
        serializer = OrderItemTimeSerializer(queryset, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)



class CartViewSet(ModelViewSet):
    queryset = Cart.objects.prefetch_related('items__product__files')
    serializer_class = CartSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [AllowAny()]
        return [IsAdminUser()]

class CartItemViewSet(ModelViewSet):
    def get_queryset(self):
        return CartItem.objects.filter(cart=self.kwargs['cart_pk']).prefetch_related('product__files')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateCartItemSerializer
        return CartItemSerializer

    def get_serializer_context(self):
        return { 'request': self.request, 'cart_id': self.kwargs['cart_pk'] }