from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import CustomFactor

# The sample version available from 15 Oct 2012 - 11 Jan 2016
from quantopian.pipeline.data.sentdex import sentiment_free as sentdex
# The premium version found at https://www.quantopian.com/data/sentdex/sentiment
# from quantopian.pipeline.data.sentdex import sentiment as sentdex

import pandas as pd
import numpy as np


# Calculates the average impact of the sentiment over the window length
class AvgSentiment(CustomFactor):
    
    def compute(self, today, assets, out, impact):
        np.mean(impact, axis=0, out=out)

        
class AvgDailyDollarVolumeTraded(CustomFactor):
    
    inputs = [USEquityPricing.close, USEquityPricing.volume]
    window_length = 20
    
    def compute(self, today, assets, out, close_price, volume):
        out[:] = np.mean(close_price * volume, axis=0)

        
# Put any initialization logic here.  The context object will be passed to
# the other methods in your algorithm.
def initialize(context):
    window_length = 3    
    pipe = Pipeline()
    pipe = attach_pipeline(pipe, name='sentiment_metrics')    
    dollar_volume = AvgDailyDollarVolumeTraded()

    # Add our AvgSentiment factor to the pipeline using a 3 day moving average
    pipe.add(AvgSentiment(inputs=[sentdex.sentiment_signal], window_length=window_length), "avg_sentiment")    

    # Screen out low liquidity securities.
    pipe.set_screen((dollar_volume > 10**7))
    context.shorts = None
    context.longs = None
    # context.spy = sid(8554)
    
    # Set commissions and slippage to zero to evaluate alpha generation
    # of the strategy
    schedule_function(rebalance, date_rules.every_day(), time_rules.market_open(hours=1))
    set_commission(commission.PerShare(cost=0, min_trade_cost=0))
    set_slippage(slippage.FixedSlippage(spread=0))
    
    
def before_trading_start(context, data):
    results = pipeline_output('sentiment_metrics').dropna()

    # Separate securities into longs and shorts
    longs = results[results['avg_sentiment'] > 0]
    shorts = results[results['avg_sentiment'] < 0]

    # Order them in their individual segments
    long_ranks = longs["avg_sentiment"].rank().order()
    short_ranks = shorts['avg_sentiment'].rank().order()
    
    num_stocks = min([25, len(long_ranks.index), len(short_ranks.index)])

    # Find the top 25 stocks to long and bottom 25 to short
    context.shorts = short_ranks.tail(num_stocks)
    context.longs = long_ranks.head(num_stocks)
    
    # The pipe character "|" is the pandas union operator
    update_universe(context.longs.index | context.shorts.index)
    

# Will be called on every trade event for the securities you specify. 
def handle_data(context, data):
    num_positions = [pos for pos in context.portfolio.positions
                     if context.portfolio.positions[pos].amount != 0]
    record(lever=context.account.leverage,
           exposure=context.account.net_leverage,
           num_pos=len(context.portfolio.positions),
           oo=len(get_open_orders()))
        
    
def rebalance(context, data):
    
    for security in context.shorts.index:
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

