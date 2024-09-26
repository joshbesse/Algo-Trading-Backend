from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import TradeViewSet, PortfolioViewSet

router = DefaultRouter()
router.register(r'trades', TradeViewSet, basename='trade')
router.register(r'portfolios', PortfolioViewSet, basename='portfolio')

urlpatterns = [
    path('', include(router.urls)),
]