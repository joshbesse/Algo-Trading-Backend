from rest_framework import serializers
from .models import ModelType, Trade, Portfolio

class ModelTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelType
        fields = '__all__'

class TradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trade
        fields = '__all__'

class PortfolioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portfolio
        fields = '__all__'
    