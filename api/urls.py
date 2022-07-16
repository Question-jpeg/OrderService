from rest_framework_nested import routers
from . import views

router = routers.DefaultRouter()
router.register('products', views.ProductViewSet, basename='products')
router.register('orders', views.OrderViewSet, basename='orders')
router.register('order-items', views.AllOrderItemsViewSet, basename='all-order-items')
router.register('push-tokens', views.UserPushNotificationTokenViewSet, basename='push-tokens')
router.register('carts', views.CartViewSet, basename='carts')

orders_router = routers.NestedDefaultRouter(router, 'orders', lookup='order')
orders_router.register('items', views.OrderItemViewSet, basename='order-items')

carts_router = routers.NestedDefaultRouter(router, 'carts', lookup='cart')
carts_router.register('items', views.CartItemViewSet, basename='cart-items')

urlpatterns = router.urls + orders_router.urls + carts_router.urls