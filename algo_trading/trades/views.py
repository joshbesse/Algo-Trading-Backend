from rest_framework.response import Response
from rest_framework import viewsets
from .models import Trade, Portfolio
from .serializers import TradeSerializer, PortfolioSerializer
from django.db.models import Min, Max

# Create your views here.
class TradeViewSet(viewsets.ModelViewSet):
    queryset = Trade.objects.all()
    serializer_class = TradeSerializer

    def list(self, request):
        model_type = request.query_params.get("model_type")
        trades = Trade.objects.filter(model_type__model_name=model_type)

        if not trades.exists():
            return Response({"error": "No trade data found for this model"}, status=404)
        
        total_buys = trades.filter(trade_type="BUY").count()
        total_sells = trades.filter(trade_type="SELL").count()

        return Response({
            'total_buys': total_buys,
            'total_sells': total_sells,
            'trades': TradeSerializer(trades, many=True).data,
        })

class PortfolioViewSet(viewsets.ModelViewSet):
    queryset = Portfolio.objects.all()
    serializer_class = PortfolioSerializer

    def list(self, request):
        model_type = request.query_params.get("model_type")
        portfolios = Portfolio.objects.filter(model_type__model_name=model_type)

        if not portfolios.exists():
            return Response({"error": "No portfolio data found for this model"}, status=404)
        
        starting_value = portfolios.order_by("date").first().value
        current_value = portfolios.order_by("-date").first().value
        highest_value = portfolios.aggregate(Max("value"))["value__max"]
        lowest_value = portfolios.aggregate(Min("value"))["value__min"]

        return Response({
            'starting_value': starting_value,
            'current_value': current_value,
            'highest_value': highest_value,
            'lowest_value': lowest_value,
            'portfolio': PortfolioSerializer(portfolios, many=True).data,
        })
