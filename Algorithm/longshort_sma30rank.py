# This algorithm implements the long-short equity strategy ranked on the 
# 30 day Sentiment Moving Average.

# Imports
import numpy as np
import pandas as pd
from quantopian.pipeline.filters import Q1500US
import quantopian.optimize as opt
from quantopian.algorithm import attach_pipeline, pipeline_output, order_optimal_portfolio
from quantopian.pipeline import Pipeline
from quantopian.pipeline.factors import SimpleMovingAverage, AverageDollarVolume, RollingLinearRegressionOfReturns
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.data import morningstar
from quantopian.pipeline.filters.morningstar import IsPrimaryShare
from quantopian.pipeline.classifiers.morningstar import Sector
from quantopian.pipeline.data.psychsignal import stocktwits
from quantopian.pipeline.data.sentdex import sentiment_free

# Constraint Parameters
MAX_GROSS_EXPOSURE = 1.0
NUM_LONG_POSITIONS = 300
NUM_SHORT_POSITIONS = 300

# Max Position Size
MAX_SHORT_POSITION_SIZE = 2*1.0/(NUM_LONG_POSITIONS + NUM_SHORT_POSITIONS)
MAX_LONG_POSITION_SIZE = 2*1.0/(NUM_LONG_POSITIONS + NUM_SHORT_POSITIONS)

# Risk Exposures
MAX_SECTOR_EXPOSURE = 0.10
MAX_BETA_EXPOSURE = 0.20
        
def make_pipeline():
    
    # Sector
    sector = Sector()
   
    # Equity Filters
    mkt_cap_filter = morningstar.valuation.market_cap.latest >= 500000000 
    price_filter = USEquityPricing.close.latest >= 5
    nan_filter = sentiment_free.sentiment_signal.latest.notnull()
    
    # Universe
    universe = Q1500US() & price_filter & mkt_cap_filter & nan_filter

    # Rank
    sentiment_signal = sentiment_free.sentiment_signal.latest
    sma_30 = SimpleMovingAverage(inputs=
                     [sentiment_free.sentiment_signal],
                     window_length=30, mask=universe)
    
    combined_rank = (
        sentiment_signal +
        sma_30.rank(mask=universe).zscore())

    # Long and Short Positions
    longs = combined_rank.top(NUM_LONG_POSITIONS)
    shorts = combined_rank.bottom(NUM_SHORT_POSITIONS)

    long_short_screen = (longs | shorts)
    
    # Bloomberg Beta Implementation
    beta = 0.66*RollingLinearRegressionOfReturns(
                    target=sid(8554),
                    returns_length=5,
                    regression_length=260,
                    mask=long_short_screen).beta + 0.33*1.0
    
    pipe = Pipeline()
    pipe.add(longs, 'longs')
    pipe.add(shorts, 'shorts')
    pipe.add(combined_rank, 'combined_rank')
    pipe.add(sentiment_free.sentiment_signal.latest, 'sentiment_signal')
    pipe.add(sma_30, 'sma_30')
    pipe.add(sector, 'sector')
    pipe.add(beta, 'market_beta')
    pipe.set_screen(universe)
    
    return pipe
    

def initialize(context):
    # Slippage and Commissions
    set_commission(commission.PerShare(cost=0.0, min_trade_cost=0))
    set_slippage(slippage.VolumeShareSlippage(volume_limit=1, price_impact=0))
    context.spy = sid(8554)

    attach_pipeline(make_pipeline(), 'longshort_sma30rank')

    # Rebalance Function
    schedule_function(func=rebalance,
                      date_rule=date_rules.month_start(),              
                time_rule=time_rules.market_open(hours=0,minutes=30),
                      half_days=True)
    
    # End of the day portfolio variables
    schedule_function(func=recording_statements,
                      date_rule=date_rules.every_day(),
                      time_rule=time_rules.market_close(),
                      half_days=True)


def before_trading_start(context, data):
    # Call pipeline_output to get the output
    # Note: this is a dataframe where the index is the SIDs for all
    # securities to pass my screen and the columns are the factors
    # added to the pipeline object above
    context.pipeline_data = pipeline_output('longshort_sma30rank')


def recording_statements(context, data):
    # Plot the number of positions over time.
    record(num_positions=len(context.portfolio.positions))


# Called at the start of every month in order to rebalance
# the longs and shorts lists
def rebalance(context, data):
    ### Optimize API
    pipeline_data = context.pipeline_data

    ### Extract from pipeline any specific risk factors you want 
    # to neutralize that you have already calculated 
    risk_factor_exposures = pd.DataFrame({
            'market_beta':pipeline_data.market_beta.fillna(1.0)
        })
    # We fill in any missing factor values with a market beta of 1.0.
    # We do this rather than simply dropping the values because we have
    # want to err on the side of caution. We don't want to exclude
    # a security just because it's missing a calculated market beta,
    # so we assume any missing values have full exposure to the market.
    
    
    ### Here we define our objective for the Optimize API. We have
    # selected MaximizeAlpha because we believe our combined factor
    # ranking to be proportional to expected returns. This routine
    # will optimize the expected return of our algorithm, going
    # long on the highest expected return and short on the lowest.
    objective = opt.MaximizeAlpha(pipeline_data.combined_rank)
    
    ### Define the list of constraints
    constraints = []
    # Constrain our maximum gross leverage
    constraints.append(opt.MaxGrossExposure(MAX_GROSS_EXPOSURE))
    # Require our algorithm to remain dollar neutral
    constraints.append(opt.DollarNeutral())
    # Add a sector neutrality constraint using the sector
    # classifier that we included in pipeline
    constraints.append(
        opt.NetGroupExposure.with_equal_bounds(
            labels=pipeline_data.sector,
            min=-MAX_SECTOR_EXPOSURE,
            max=MAX_SECTOR_EXPOSURE,
        ))
    # Take the risk factors that you extracted above and
    # list your desired max/min exposures to them -
    # Here we selection +/- 0.01 to remain near 0.
    neutralize_risk_factors = opt.FactorExposure(
        loadings=risk_factor_exposures,
        min_exposures={'market_beta':-MAX_BETA_EXPOSURE},
        max_exposures={'market_beta':MAX_BETA_EXPOSURE}
    )
    constraints.append(neutralize_risk_factors)
    
    # With this constraint we enforce that no position can make up
    # greater than MAX_SHORT_POSITION_SIZE on the short side and
    # no greater than MAX_LONG_POSITION_SIZE on the long side. This
    # ensures that we do not overly concentrate our portfolio in
    # one security or a small subset of securities.
    constraints.append(
        opt.PositionConcentration.with_equal_bounds(
            min=-MAX_SHORT_POSITION_SIZE,
            max=MAX_LONG_POSITION_SIZE
        ))

    # Put together all the pieces we defined above by passing
    # them into the order_optimal_portfolio function. This handles
    # all of our ordering logic, assigning appropriate weights
    # to the securities in our universe to maximize our alpha with
    # respect to the given constraints.
    order_optimal_portfolio(
        objective=objective,
        constraints=constraints,
    )