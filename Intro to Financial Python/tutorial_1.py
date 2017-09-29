import quandl
import numpy as np
import quandl

quandl.ApiConfig.api_key = 'zNXvSaz2oX5afVGKjf6o'

#get quandl data
aapl_table = quandl.get('WIKI/AAPL')
aapl = aapl_table.loc['2017-3',['Open','Close']]

#take log return
aapl['log_price'] = np.log(aapl.Close)
aapl['log_return'] = np.log_price.diff()

print(aapl)
