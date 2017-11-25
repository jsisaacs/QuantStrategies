from quantopian.pipeline import Pipeline
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline.filters.morningstar import Q1500US
from quantopian.pipeline.data.sentdex import sentiment_free

def initialize(context):
    """
    Called once at the start of the algorithm.
    """   
    # Rebalance every day, 1 hour after market open.
    schedule_function(my_rebalance, date_rules.every_day(), time_rules.market_open(hours=1))
     
    # Record tracking variables at the end of each day.
    schedule_function(my_record_vars, date_rules.every_day(), time_rules.market_close())
     
    # Create our dynamic stock selector.
    attach_pipeline(make_pipeline(), 'my_pipeline')
    
    set_commission(commission.PerTrade(cost=0.001))



def make_pipeline():
    
    # 5-day sentiment moving average factor.
    sentiment_factor = sentiment_free.sentiment_signal.latest
    
    # Our universe is made up of stocks that have a non-null sentiment signal and are in the Q1500US.
    universe = (Q1500US() 
                & sentiment_factor.notnull())
    
    # A classifier to separate the stocks into quantiles based on sentiment rank.
    sentiment_quantiles = sentiment_factor.rank(mask=universe, method='average').quantiles(2)
    
    # Go short the stocks in the 0th quantile, and long the stocks in the 2nd quantile.
    pipe = Pipeline(
        columns={
            'sentiment': sentiment_quantiles,
            'longs': (sentiment_factor >=5),
            'shorts': (sentiment_factor<=-2),
        },
        screen=universe
    )
    
    return pipe



def before_trading_start(context, data):
    try:
        """
        Called every day before market open.
        """
        context.output = pipeline_output('my_pipeline')

        # These are the securities that we are interested in trading each day.
        context.security_list = context.output.index.tolist()
    except Exception as e:
        print(str(e))
    
 
def my_rebalance(context,data):
    """
    Place orders according to our schedule_function() timing.
    """
    
    # Compute our portfolio weights.
    long_secs = context.output[context.output['longs']].index
    long_weight = 0.5 / len(long_secs)
    
    short_secs = context.output[context.output['shorts']].index
    short_weight = -0.5 / len(short_secs)

    # Open our long positions.
    for security in long_secs:
        if data.can_trade(security):
            order_target_percent(security, long_weight)
    
    # Open our short positions.
    for security in short_secs:
        if data.can_trade(security):
            order_target_percent(security, short_weight)

    # Close positions that are no longer in our pipeline.
    for security in context.portfolio.positions:
        if data.can_trade(security) and security not in long_secs and security not in short_secs:
            order_target_percent(security, 0)
    
 
def my_record_vars(context, data):
    """
    Plot variables at the end of each day.
    """
    long_count = 0
    short_count = 0

    for position in context.portfolio.positions.itervalues():
        if position.amount > 0:
            long_count += 1
        if position.amount < 0:
            short_count += 1
            
    # Plot the counts
    record(num_long=long_count, num_short=short_count, leverage=context.account.leverage)