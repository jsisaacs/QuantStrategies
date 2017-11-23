
# coding: utf-8

# # Research
# 
# by Joshua Isaacson and Hannah Isaacson 
# 
# For our Fall 2017 SICE@IU undergraduate research project, *A Sentiment-Based Long-Short Equity Strategy*.

# ## Components
# 
# 1. Universe Selection
# 2. Alphalens Factor Analysis
# 3. Rebalancing
# 4. Portfolio
# 5. Pipeline

# ##  Universe Selection
# 
# This component covers our process of defining the trading universe for which the algorithm operates.

# ### Imports 

# In[97]:


import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from quantopian.pipeline.filters import Q1500US
from quantopian.research import run_pipeline
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.psychsignal import stocktwits
from quantopian.pipeline.data import Fundamentals
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.filters.fundamentals import IsPrimaryShare
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import CustomFactor, Returns
from quantopian.pipeline.classifiers.fundamentals import Sector
from quantopian.pipeline.data.sentdex import sentiment_free
from quantopian.pipeline.factors import SimpleMovingAverage
from time import time
import alphalens as al


# ### Universe
# 
# WHY DID WE CHOOSE THIS
# WHAT EQUITIES ARE IN IT

# In[98]:


universe = Q1500US()


# ## Factor Analysis
# 
# We want to test to see how good our alpha factors are at predicting relative price movements. A wide range of factors that are independent of each other yield a better ranking scheme.
# 
# The factors we are going to evaluate are:
# * bearish_intensity
# * bullish_intensity
# * sentiment_signal
# * sentiment moving average (10, 20, 30, 50, 80 day)
#     * simple and exponential

# ### Fields in PsychSignal Dataset

# In[99]:


def print_fields(dataset):
    print "Dataset: %s\n" % dataset.__name__
    print "Fields:"
    for field in list(dataset.columns):
        print "%s - %s" % (field.name, field.dtype)
    print "\n"

for data in (stocktwits,):
    print_fields(data)


# ### Fields in Sentdex Sentiment Analysis Dataset

# In[100]:


def print_fields(dataset):
    print "Dataset: %s\n" % dataset.__name__
    print "Fields:"
    for field in list(dataset.columns):
        print "%s - %s" % (field.name, field.dtype)
    print "\n"

for data in (sentiment_free,):
    print_fields(data)


# ### Sentiment Signal Moving Averages
# 
# Simple Moving Averages

# In[101]:


sma_10 = SimpleMovingAverage(inputs=[sentiment_free.sentiment_signal], window_length=10, mask=universe)
sma_20 = SimpleMovingAverage(inputs=[sentiment_free.sentiment_signal], window_length=20, mask=universe)
sma_30 = SimpleMovingAverage(inputs=[sentiment_free.sentiment_signal], window_length=30, mask=universe)
sma_50 = SimpleMovingAverage(inputs=[sentiment_free.sentiment_signal], window_length=50, mask=universe)
sma_80 = SimpleMovingAverage(inputs=[sentiment_free.sentiment_signal], window_length=80, mask=universe)


# ### Sector Codes

# In[102]:


MORNINGSTAR_SECTOR_CODES = {
     -1: 'Misc',
    101: 'Basic Materials',
    102: 'Consumer Cyclical',
    103: 'Financial Services',
    104: 'Real Estate',
    205: 'Consumer Defensive',
    206: 'Healthcare',
    207: 'Utilities',
    308: 'Communication Services',
    309: 'Energy',
    310: 'Industrials',
    311: 'Technology' ,
}


# ### Getting Data

# In[103]:


pipe = Pipeline()

pipe.add(stocktwits.bearish_intensity.latest, 'bearish_intensity')
pipe.add(stocktwits.bullish_intensity.latest, 'bullish_intensity')
pipe.add(sentiment_free.sentiment_signal.latest, 'sentiment_signal')
pipe.add(sma_10, 'sma_10')
pipe.add(sma_20, 'sma_20')
pipe.add(sma_30, 'sma_30')
pipe.add(sma_50, 'sma_50')
pipe.add(sma_80, 'sma_80')
pipe.add(Sector(), 'Sector')

pipe.set_screen(universe)

start_timer = time()
results = run_pipeline(pipe, '2015-01-01', '2016-01-01')
end_timer = time()

print("Time to run pipeline %.2f secs" % (end_timer - start_timer))


# ### Dealing with NaN Values

# In[104]:


adjusted_dataset = results.interpolate()
adjusted_dataset.head()
#len(adjusted_dataset)


# ### Filtering for Unique Equities

# # TODO
# 
# * first name the equity column, the drop duplicates based on it
# * Alphalens tearsheet for:
#     * bearish_intensity
#     * bullish_intensity
#     * sentiment_signal
#     * sentiment moving averages
# * choose factors
# * choose how to distribute long and short
# * backtest
# * analyze portfolio
# * repeat backtests

# ### Factor Output from Pipeline
# 
# All factors are from the pipeline's output, adjusted to interpolate the NaNs.

# In[105]:


bearish_intensity_factor = adjusted_dataset['bearish_intensity']
print(bearish_intensity_factor.head())


# In[106]:


bullish_intensity_factor = adjusted_dataset['bullish_intensity']
print(bullish_intensity_factor.head())


# In[107]:


sentiment_signal_factor = adjusted_dataset['sentiment_signal']
print(sentiment_signal_factor.head())


# In[108]:


sma_10_factor = adjusted_dataset['sma_10']
print(sma_10_factor.head())


# In[109]:


sma_20_factor = adjusted_dataset['sma_20']
print(sma_20_factor.head())


# In[110]:


sma_30_factor = adjusted_dataset['sma_30']
print(sma_30_factor.head())


# In[111]:


sma_50_factor = adjusted_dataset['sma_50']
print(sma_50_factor.head())


# In[112]:


sma_80_factor = adjusted_dataset['sma_80']
print(sma_80_factor.head())


# We also want to see equity performance broken down by sector.

# In[113]:


sectors = adjusted_dataset['Sector']


# Grab the pricing data for the unique equities in our pipeline.

# In[114]:


asset_list = adjusted_dataset.index.levels[1].unique()
prices = get_pricing(asset_list, start_date='2015-01-01', end_date='2016-01-01', fields='price')
len(asset_list)


# In[115]:


prices.head()


# ## Alphalens Factor Analysis
# 
# Now that we have created the pipeline to filter and gather the equities, we will use the Alphalens tool provided by Quantopian to analyze the alpha factors that we want to test. Ultimately, we will use this tool and the metrics it gives us to understand each alpha factor's inherent ability to predict future price. We are looking for a high Alpha, a Beta close to 0, a high Sharpe Ratio, and a high Spearman Correlation.

# In[121]:


sma_10_factor_data = al.utils.get_clean_factor_and_forward_returns(
                                                            factor=sma_10_factor,
                                                            prices=prices,
                                                            groupby=sectors,
                                                            groupby_labels=MORNINGSTAR_SECTOR_CODES,
                                                            periods=(1, 5, 10))
sma_10_factor_data.head()
al.tears.create_full_tear_sheet(sma_10_factor_data)


# In[122]:


sma_20_factor_data = al.utils.get_clean_factor_and_forward_returns(
                                                            factor=sma_20_factor,
                                                            prices=prices,
                                                            groupby=sectors,
                                                            groupby_labels=MORNINGSTAR_SECTOR_CODES,
                                                            periods=(1, 5, 10))

al.tears.create_full_tear_sheet(sma_20_factor_data)


# In[123]:


sma_30_factor_data = al.utils.get_clean_factor_and_forward_returns(
                                                            factor=sma_30_factor,
                                                            prices=prices,
                                                            groupby=sectors,
                                                            groupby_labels=MORNINGSTAR_SECTOR_CODES,
                                                            periods=(1, 5, 10))

al.tears.create_full_tear_sheet(sma_30_factor_data)


# In[124]:


sma_50_factor_data = al.utils.get_clean_factor_and_forward_returns(
                                                            factor=sma_50_factor,
                                                            prices=prices,
                                                            groupby=sectors,
                                                            groupby_labels=MORNINGSTAR_SECTOR_CODES,
                                                            periods=(1, 5, 10))
sma_50_factor_data.head()
al.tears.create_full_tear_sheet(sma_50_factor_data)


# In[126]:


sma_80_factor_data = al.utils.get_clean_factor_and_forward_returns(
                                                            factor=sma_80_factor,
                                                            prices=prices,
                                                            groupby=sectors,
                                                            groupby_labels=MORNINGSTAR_SECTOR_CODES,
                                                            periods=(1, 5, 10))
sma_80_factor_data.head()
al.tears.create_full_tear_sheet(sma_80_factor_data)

