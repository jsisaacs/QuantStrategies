# Equity Trading with Sentiment
### A long-short equity quantitative trading strategy based on sentiment data. 

We sought to develop a profitable long-short equity strategy that uses sentiment analysis data as the ranking factor.  To do so, many factors were analyzed using Quantopian’s Alphalens tool which generates a tear-sheet of relevant statistics.  An ideal factor has perfect predictive power of relative price movements.  The averaged sentiment signal with a window length of 3 days was considered the most viable out 8 other candidates tested.  Backtesting the strategy from early 2014 to late 2017 yielded a cumulative return of 42.5% and a Sharpe ratio of 1.33.

## Built With
* Python
* Jupyter Notebooks
* [Quantopian](https://www.quantopian.com/)

## Authors 
* [Josh Isaacson](https://github.com/jsisaacs) 
* [Hannah Isaacson](https://github.com/hannahisaacson)