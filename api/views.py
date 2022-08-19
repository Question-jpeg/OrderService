from multiprocessing import context
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.viewsets import ModelViewSet
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, AllowAny, SAFE_METHODS
from rest_framework.decorators import action

from api.models import Cart, CartItem, ProductFile, ProductSpecialInterval, Order, OrderItem, Product, UserPushNotificationToken
from api.pagination import DefaultPagination
from api.permissions import IsAdminUserOrPostOnly, IsOwner
from api.serializers import CartItemSerializer, CartSerializer, CheckAffectedInCart, CheckAffectedInOrder, CreateCartItemSerializer, CreateOrderItemSerializer, CreateOrderSerializer, CreateProductFilesSerializer, DeleteOrderItemsSerializer, DeleteProductFilesSerializer, DeleteSpecialIntervalsSerializer, GetAllowedIntervalInCart, GetAllowedIntervalInOrder, GetNewOrderCodeSerializer, GetProductPriceSerializer, IsCartValid, MakeFilePrimarySerializer, MarkOrderAsFailedSerializer, ProductFileSerializer, ProductSpecialIntervalSerializer, GetOrderSerializer, UpdateCartItemSerializer, UpdateOrderItemSerializer, UserPushNotificationTokenSerializer, VerifyOrderWithCodeSerializer, OrderItemSerializer, OrderItemTimeSerializer, OrderSerializer, ProductSerializer, ProductSimpleSerializer


class OrderViewSet(ModelViewSet):
    pagination_class = DefaultPagination
    queryset = Order.objects.prefetch_related(
        'items__product__files', 'items__product__product_special_intervals', 'items__product__required_product').order_by('-created_at')

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


class OrderItemViewSet(ModelViewSet):
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.action == 'check_affected':
            return CheckAffectedInOrder
        if self.action == 'get_allowed_interval':
            return GetAllowedIntervalInOrder
        if self.action == 'deleteIds':
            return DeleteOrderItemsSerializer
        if self.request.method == 'POST':
            return CreateOrderItemSerializer
        if self.request.method == 'PUT':
            return UpdateOrderItemSerializer
        return OrderItemSerializer

    def get_serializer_context(self):
        return {'request': self.request, 'order_id': self.kwargs['order_pk']}

    def get_queryset(self):
        return OrderItem.objects.filter(order=self.kwargs['order_pk']).prefetch_related('product__files', 'product__product_special_intervals', 'product__required_product')

    @action(methods=['post'], detail=False)
    def get_allowed_interval(self, request, order_pk):
        serializer = GetAllowedIntervalInOrder(
            data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        data = serializer.save()

        return Response(data, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False)
    def check_affected(self, request, order_pk):
        serializer = CheckAffectedInOrder(
            context=self.get_serializer_context())
        data = serializer.save()

        return Response({}, status=status.HTTP_404_NOT_FOUND) if data.get('not_found') else Response(data, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False)
    def deleteIds(self, request, order_pk):
        serializer = DeleteOrderItemsSerializer(
            data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({}, status=status.HTTP_204_NO_CONTENT)


class AllOrderItemsViewSet(ModelViewSet):
    pagination_class = DefaultPagination
    http_method_names = ['get']
    serializer_class = OrderItemSerializer
    permission_classes = [IsAdminUser]
    queryset = OrderItem.objects.filter(Q(order__status='P')).prefetch_related(
        'product__files', 'product__product_special_intervals', 'product__required_product').order_by('-start_datetime')


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.prefetch_related(
        'files', 'product_special_intervals').select_related('required_product')

    def get_serializer_class(self):
        if self.action == 'getPrice':
            return GetProductPriceSerializer
        if self.action == 'timeView':
            return OrderItemTimeSerializer
        if self.request.method in SAFE_METHODS:
            return ProductSerializer
        return ProductSimpleSerializer

    def get_permissions(self):
        method = self.request.method
        if (method in SAFE_METHODS) or (self.action == 'timeView') or (self.action == 'getPrice'):
            return [AllowAny()]
        return [IsAdminUser()]

    @action(detail=True, methods=['post'])
    def timeView(self, request, pk):
        serializer = OrderItemTimeSerializer(
            data=request.data, context={'product_id': pk})
        serializer.is_valid(raise_exception=True)
        data = serializer.save()

        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def getPrice(self, request, pk):
        serializer = GetProductPriceSerializer(
            data=request.data, context={'product_id': pk})
        serializer.is_valid(raise_exception=True)
        data = serializer.save()

        return Response(data, status=status.HTTP_200_OK)


class ProductFileViewSet(ModelViewSet):
    permission_classes = [IsAdminUser]

    def get_serializer_context(self):
        return {'request': self.request, 'product_id': self.kwargs['product_pk']}

    def get_serializer_class(self):
        if self.action == 'makePrimary':
            return MakeFilePrimarySerializer
        if self.action == 'deleteIds':
            return DeleteProductFilesSerializer
        if self.request.method == 'POST':
            return CreateProductFilesSerializer
        return ProductFileSerializer

    def get_queryset(self):
        return ProductFile.objects.filter(product=self.kwargs['product_pk'])

    @action(methods=['post'], detail=False)
    def deleteIds(self, request, product_pk):
        serializer = DeleteProductFilesSerializer(
            data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({}, status=status.HTTP_204_NO_CONTENT)

    @action(methods=['post'], detail=False)
    def makePrimary(self, request, product_pk):
        serializer = MakeFilePrimarySerializer(
            data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)


class ProductSpecialIntervalViewSet(ModelViewSet):
    def get_serializer_class(self):
        if self.action == 'deleteIds':
            return DeleteSpecialIntervalsSerializer
        return ProductSpecialIntervalSerializer

    def get_serializer_context(self):
        return {'request': self.request, 'product_id': self.kwargs['product_pk']}

    def get_permissions(self):
        if self.request.method not in SAFE_METHODS:
            return [IsAdminUser()]
        return [AllowAny()]

    def get_queryset(self):
        return ProductSpecialInterval.objects.filter(product_id=self.kwargs['product_pk'])

    @action(methods=['post'], detail=False)
    def deleteIds(self, request, product_pk):
        serializer = DeleteSpecialIntervalsSerializer(
            data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({}, status=status.HTTP_204_NO_CONTENT)


class CartViewSet(ModelViewSet):
    pagination_class = DefaultPagination
    queryset = Cart.objects.prefetch_related(
        'items__product__files', 'items__product__product_special_intervals', 'items__product__required_product')
    serializer_class = CartSerializer

    def get_permissions(self):
        if self.detail:
            return [AllowAny()]
        return [IsAdminUserOrPostOnly()]


class CartItemViewSet(ModelViewSet):
    def get_queryset(self):
        return CartItem.objects.filter(cart=self.kwargs['cart_pk']).prefetch_related('product__files', 'product__product_special_intervals', 'product__required_product')

    def get_serializer_class(self):
        if self.action == 'is_valid':
            return IsCartValid
        if self.action == 'get_allowed_interval':
            return GetAllowedIntervalInCart
        if self.request.method == 'POST':
            return CreateCartItemSerializer
        if self.request.method == 'PUT':
            return UpdateCartItemSerializer
        return CartItemSerializer

    def get_serializer_context(self):
        return {'request': self.request, 'cart_id': self.kwargs['cart_pk']}

    @action(methods=['get'], detail=False)
    def is_valid(self, request, cart_pk):
        serializer = IsCartValid(context=self.get_serializer_context())
        data = serializer.save()

        return Response(data, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False)
    def get_allowed_interval(self, request, cart_pk):
        serializer = GetAllowedIntervalInCart(
            data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        data = serializer.save()

        return Response(data, status=status.HTTP_200_OK)


class UserPushNotificationTokenViewSet(ModelViewSet):
    permission_classes = [IsAdminUser, IsOwner]
    serializer_class = UserPushNotificationTokenSerializer
    queryset = UserPushNotificationToken.objects.all()

    @action(methods=['get'], detail=False, permission_classes=[IsAdminUser])
    def is_token(self, request):
        return Response(UserPushNotificationToken.objects.filter(user=request.user).exists(), status=status.HTTP_200_OK)

    @action(methods=['delete'], detail=False, permission_classes=[IsAdminUser])
    def delete_token(self, request):
        UserPushNotificationToken.objects.filter(user=request.user).delete()
        return Response({}, status=status.HTTP_204_NO_CONTENT)
