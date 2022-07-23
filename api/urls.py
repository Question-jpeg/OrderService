from rest_framework_nested import routers
from . import views

router = routers.DefaultRouter()
router.register('products', views.ProductViewSet, basename='products')
router.register('orders', views.OrderViewSet, basename='orders')
router.register('order-items', views.AllOrderItemsViewSet, basename='all-order-items')
router.register('push-tokens', views.UserPushNotificationTokenViewSet, basename='push-tokens')
router.register('carts', views.CartViewSet, basename='carts')

products_router = routers.NestedDefaultRouter(router, 'products', lookup='product')
products_router.register('intervals', views.ProductSpecialIntervalViewSet, basename='product-intervals')
products_router.register('files', views.ProductFileViewSet, basename='product-files')

orders_router = routers.NestedDefaultRouter(router, 'orders', lookup='order')
orders_router.register('items', views.OrderItemViewSet, basename='order-items')

carts_router = routers.NestedDefaultRouter(router, 'carts', lookup='cart')
carts_router.register('items', views.CartItemViewSet, basename='cart-items')

urlpatterns = router.urls + products_router.urls + orders_router.urls + carts_router.urls