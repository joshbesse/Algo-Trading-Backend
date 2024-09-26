from django.core.management.base import BaseCommand
from trades.models import ModelType, Trade, Portfolio

import pandas as pd 
import numpy as np 
import joblib
import xgboost as xgb

class Command(BaseCommand):
    help = "Simulate trades and update portfolio using XGBoost models"
    
    def handle(self, *args, **kwargs):
        # simulate trades and update portfolio for each model
        models = [6, 24, 48]
        for model in models:
            # load data and model
            df = pd.read_pickle('./data_and_models/XGB_data.pkl')
            current_model = joblib.load(f'./data_and_models/XGB_model{model}.pkl')

            # convert inf values in RSI columns to nan then drop 
            df.replace([np.inf, -np.inf], np.nan, inplace=True)
            df.dropna(inplace=True)

            # generate predictions  
            features = ["Open", "High", "Low", "Close", "Adj Close", "Volume", "Pivot", "Resistance 1", "Support 1", 
                "Resistance 2", "Support 2", "Resistance 3", "Support 3", "SMA10", "SMA20", "SMA50", "SMA100", 
                "EMA9", "EMA21", "Upper Band 10", "Lower Band 10", "Upper Band 20", "Lower Band 20", "RSI 7", 
                "RSI 14", "RSI 21"]
            
            X = xgb.DMatrix(df[features])
            predictions = current_model.predict(X)
            df["Predicted Signal"] = predictions

            # group data by date to calculate portfolio value per date  
            df.reset_index(inplace=True)
            grouped_by_date = df.groupby("Date")

            # initialize trading variables
            initial_capital = 10000
            position_size = 0.1
            money = initial_capital
            portfolio = {}
            portfolio_value = []
            num_buys = 0
            num_sells = 0
            model_type = ModelType.objects.get(model_name=f"XGBOOST_{model}H")

            price_lookup = df.groupby(["Date", "Ticker"])["Close"].first().to_dict()

            # simulation loop
            for current_date, date_group in grouped_by_date:
                for index, row in date_group.iterrows():
                    stock = row["Ticker"]
                    price = row["Close"]
                    signal = row["Predicted Signal"]

                    if stock not in portfolio:
                        portfolio[stock] = 0

                    if signal == 2 and money > 0:
                        shares_to_buy = (money * position_size) / price
                        money -= price * shares_to_buy
                        portfolio[stock] += shares_to_buy
                        num_buys += 1

                        # save the trade
                        Trade.objects.create(
                            model_type=model_type,
                            ticker=stock,
                            trade_type="BUY",
                            trade_date=current_date,
                            price=price,
                            shares=shares_to_buy
                        )

                    elif signal == 0 and portfolio[stock] > 0:
                        money += price * portfolio[stock]
                        portfolio[stock] = 0
                        num_sells += 1

                        # save the trade
                        Trade.objects.create(
                            model_type=model_type,
                            ticker=stock,
                            trade_type="SELL",
                            trade_date=current_date,
                            price=price,
                            shares=portfolio[stock]
                        )
                
                current_portfolio_value = money + sum(portfolio[s] * price_lookup.get((current_date, s), 0) for s in portfolio)
                portfolio_value.append(current_portfolio_value)
                
                # save the portfolio
                Portfolio.objects.create(
                    model_type=model_type,
                    value=current_portfolio_value,
                    date=current_date
                )
                
            self.stdout.write(self.style.SUCCESS(f"XGBoost {model}H Simulation Complete: Buys: {num_buys}, Sells: {num_sells}"))