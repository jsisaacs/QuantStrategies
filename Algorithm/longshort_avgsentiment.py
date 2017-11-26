from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import CustomFactor
from quantopian.pipeline.data.sentdex import sentiment_free as sentdex

import pandas as pd
import numpy as np

class AverageSentiment(CustomFactor):
    def compute(self, today, assets, out, impact):
        np.mean(impact, axis=0, out=out)
        
class AverageDailyDollarVolumeTraded(CustomFactor):
    window_length = 20
    inputs = [USEquityPricing.close, USEquityPricing.volume]
    def compute(self, today, assets, out, close_price, volume):
        out[:] = np.mean(close_price * volume, axis=0)

def initialize(context):
    window_length = 3    
    pipe = Pipeline()
    pipe = attach_pipeline(pipe, name='Sentiment_Pipe')    
    dollar_volume = AverageDailyDollarVolumeTraded()
    filter = (dollar_volume > 10**7)

    pipe.add(AverageSentiment(inputs=[sentdex.sentiment_signal],
                          window_length=window_length), 'Average_Sentiment')    
    pipe.set_screen(filter)
    context.longs = None
    context.shorts = None
    
    schedule_function(rebalance, date_rules.every_day(), time_rules.market_open(hours=1))
    set_commission(commission.PerShare(cost=0, min_trade_cost=0))
    set_slippage(slippage.FixedSlippage(spread=0))
    
def before_trading_start(context, data):
    results = pipeline_output('Sentiment_Pipe').dropna()

    longs = results[results['Average_Sentiment'] > 0]
    shorts = results[results['Average_Sentiment'] < 0]

    long_ranks = longs['Average_Sentiment'].rank().order()
    short_ranks = shorts['Average_Sentiment'].rank().order()
    
    num_stocks = min([25, len(long_ranks.index), len(short_ranks.index)])

    context.longs = long_ranks.head(num_stocks)
    context.shorts = short_ranks.tail(num_stocks)

    update_universe(context.longs.index | context.shorts.index)

def handle_data(context, data):
    #num_positions = [pos for pos in context.portfolio.positions
    #                 if context.portfolio.positions[pos].amount != 0]
    record(lever=context.account.leverage,
           exposure=context.account.net_leverage,
           num_pos=len(context.portfolio.positions),
           oo=len(get_open_orders()))
        
    
def rebalance(context, data):
    
    for secuhttps://www.quantopian.com/algorithmsrity in context.shorts.index:
        if get_open_orders(security):
            continue
        if security in data:
            order_target_percent(security, -1.0 / len(context.shorts))
            
    for security in context.longs.index:
        if get_open_orders(security):
            continue
        if security in data:
            order_target_percent(security, 1.0 / len(context.longs))
            
    for security in context.portfolio.positions:
        if get_open_orders(security):
            continue
        if security in data:
            if security not in (context.longs.index | context.shorts.index):
                    order_target_percent(security, 0)

