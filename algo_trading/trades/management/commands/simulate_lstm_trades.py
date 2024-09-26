from django.core.management.base import BaseCommand
from trades.models import ModelType, Trade, Portfolio

import pandas as pd 
import numpy as np
import joblib
from tensorflow.keras.models import load_model

class Command(BaseCommand):
    help = "Simulate trades and update portfolio using LSTM models"

    def handle(self, *args, **kwargs):
        # function to create 48 hour sequences for LSTM input 
        def create_sequences(df, features, window_size=48):
            sequences = []
            for i in range(len(df) - window_size):
                X_sequence = df[features].iloc[i:i + window_size].values
                sequences.append(X_sequence)
            return np.array(sequences)
        
        # simulate trades and update portfolio for each model
        models = ["CE", "FL"]
        for model in models:
            # load data, scaler, and model
            df = pd.read_pickle('./data_and_models/LSTM_data.pkl')
            current_scaler = joblib.load(f'./data_and_models/LSTM_{model}_feature_scaler.pkl')
            current_model = load_model(f'./data_and_models/LSTM_{model}_model.keras', compile=False)

            # convert inf values in RSI columns to nan then drop
            df.replace([np.inf, -np.inf], np.nan, inplace=True)
            df.dropna(inplace=True)
            
            # normalize the features
            features = ["Open", "High", "Low", "Close", "Adj Close", "Volume", "Pivot", "Resistance 1", "Support 1", 
                "Resistance 2", "Support 2", "Resistance 3", "Support 3", "SMA10", "SMA20", "SMA50", "SMA100", 
                "EMA9", "EMA21", "Upper Band 10", "Lower Band 10", "Upper Band 20", "Lower Band 20", "RSI 7", 
                "RSI 14", "RSI 21"]
            
            df_scaled = df.copy()
            df_scaled.drop(["6 Hour Condition", "24 Hour Condition", "48 Hour Condition"], axis=1, inplace=True)
            df_scaled[features] = current_scaler.transform(df_scaled[features])

            # generate sequences for prediction
            X_sequences = create_sequences(df_scaled, features)

            # generate predictions
            y6_preds, y24_preds, y48_preds = current_model.predict(X_sequences)
            y6_preds_labels, y24_preds_labels, y48_preds_labels = np.argmax(y6_preds, axis=1), np.argmax(y24_preds, axis=1), np.argmax(y48_preds, axis=1)

            df[["6 Hour Prediction", "24 Hour Prediction", "48 Hour Prediction"]] = np.nan
            df.iloc[:48, df.columns.get_indexer(["6 Hour Prediction", "24 Hour Prediction", "48 Hour Prediction"])] = 0
            df.iloc[48:, df.columns.get_loc("6 Hour Prediction")] = y6_preds_labels
            df.iloc[48:, df.columns.get_loc("24 Hour Prediction")] = y24_preds_labels
            df.iloc[48:, df.columns.get_loc("48 Hour Prediction")] = y48_preds_labels

            # group data by date to calculate portfolio value per date
            grouped_by_date = df.groupby(df.index)

            # simulate trades and update portfolio for each model for each time want to predict
            hours = [6, 24, 48]
            for hour in hours: 
                # initialize trading variables
                initial_capital = 10000
                position_size = 0.1
                money = initial_capital
                portfolio = {}
                portfolio_value = []
                num_buys = 0
                num_sells = 0
                model_type = ModelType.objects.get(model_name=f"LSTM_{model}_{hour}H")

                price_lookup = {(date, ticker): price for date, ticker, price in zip(df.index, df['Ticker'], df['Close'])}

                # simulation loop
                for current_date, date_group in grouped_by_date:
                    for index, row in date_group.iterrows():
                        stock = row["Ticker"]
                        price = row["Close"]
                        signal = row[f"{hour} Hour Prediction"]

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
                            shares_to_sell = portfolio[stock]
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
                                shares=shares_to_sell
                            )

                    current_portfolio_value = money + sum(portfolio[s] * price_lookup.get((current_date, s), 0) for s in portfolio)
                    portfolio_value.append(current_portfolio_value)

                    # save the portfolio
                    Portfolio.objects.create(
                        model_type=model_type,
                        value=current_portfolio_value,
                        date=current_date
                    )
                    
                self.stdout.write(self.style.SUCCESS(f"LSTM {model} {hour}H Simulation Complete: Buys: {num_buys}, Sells: {num_sells}"))