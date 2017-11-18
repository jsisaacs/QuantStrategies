import quantopian.experimental.optimize as opt
import random

def initialize(context):
    context.symbols = [symbol('DD'),symbol('DIS'),symbol('WMT'),symbol('VZ'),symbol('UNH'),symbol('UTX'),symbol('TRV'),symbol('PG'),symbol('PFE'),symbol('MSFT'),\
                symbol('MRK'),symbol('MCD'),symbol('JPM'),symbol('JNJ'),symbol('IBM'),symbol('INTC'),symbol('HPQ'),symbol('GE'),symbol('XOM'),symbol('KO'),\
                    symbol('CSCO'),symbol('CVX'),symbol('CAT'),symbol('BA'),symbol('BAC'),symbol('T'),symbol('AXP'),symbol('MMM'),symbol('HD')]
   
    context.names = ['DD', 'DIS', 'WMT', 'VZ', 'UNH', 'UTX', 'TRV', 'PG', 'PFE', 'MSFT',\
                     'MRK', 'MCD', 'JPM', 'JNJ', 'IBM', 'INTC', 'HPQ', 'GE', 'XOM', 'KO',\
                     'CSCO', 'CVX', 'CAT', 'BA', 'BAC', 'T', 'AXP', 'MMM', 'HD']
         
    fetch_csv('https://dl.dropboxusercontent.com/s/o3bfcyyea2ruk72/DJIA.csv?dl=0', 
               date_column = 'Date',
               date_format = '%y-%m-%d',
               symbol = "Sentiment") 
    
    schedule_function(
        check_signal,
        date_rules.every_day(),
        time_rules.market_open(minutes=15)
    )      
    
    context.counter = 0
    context.sentiment = []
    
    set_benchmark(sid(2174)) #Set DJIA as benchmark
        
def check_signal(context,data):
    if context.counter != 0: #We only want to check after the first day 
        sentiment = context.sentiment
        
        scores = {} #Holds the scores for the stock to invest in
        for i in range(len(context.names)):
            name = context.names[i]
            symbol = context.symbols[i]
            
            s = sentiment[name]
            if s > 7: 
                scores[symbol] = s

        weights = get_weights(scores)
        print weights

        objective = opt.TargetPortfolioWeights(weights)
        order_optimal_portfolio(objective,[])
    
    context.sentiment = data["Sentiment"] #Pull in todays sentiment for use on the next day
    context.counter += 1
    
def get_weights(scores):
    #Converts the scores into weights for portfolio
    weights = {}
        
    totalScore = 0.0
    for key in scores.keys():
        totalScore += abs(scores[key])
            
    for key in scores.keys():
        weights[key] = scores[key]/totalScore
            
    return weights
    
def n_largest(n,scores):
    symbols = scores.keys()
    
    if len(symbols) <= n:
        return scores
    
    s = []
    for symbol in symbols:
        s.append(abs(scores[symbol]))
        
    s,symbols = zip(*sorted(zip(s,symbols),reverse=True))
    
    newScores = {}
    for i in range(n):
        symbol = symbols[i]
        newScores[symbol] = scores[symbol]
    
    return newScores

def n_random(n,scores):
    symbols = scores.keys()
    
    if len(symbols) <= n:
        return scores
    
    s = []
    for symbol in symbols:
        s.append(scores[symbol])
        
    merged = zip(symbols,s)
    merged = random.sample(merged,n)
    
    newScores = {}
    for element in merged:
        symbol = element[0]
        value = element[1]
        newScores[symbol] = value
    
    return newScores        
           
    #HANNAH COMMENT    
        
    
