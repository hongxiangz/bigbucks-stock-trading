import numpy as np
import pandas as pd
import scipy
import matplotlib.pyplot as plt
from scipy.optimize import Bounds
from scipy.optimize import LinearConstraint
from scipy.optimize import minimize
import plotly
import plotly.graph_objs as go
from plotly.offline import iplot
import plotly.offline as pyo
from plotly.offline import plot

from model import Entity, Holding, Stock

def ret(r,w):
    return r.dot(w)
# Risk level - or volatility
def vol(w,covar):
    return np.sqrt(np.dot(w,np.dot(w,covar)))
def sharpe (ret,vol):
    return ret/vol

def graph_EF(data):
    df2 = data.pct_change()
    df=df2.iloc[1:len(df2.index),:]
    r = np.mean(df,axis=0)*252
    covar = df.cov()
    
    bounds = Bounds(0, 1)
    linear_constraint = LinearConstraint(np.ones((df2.shape[1],), dtype=int),1,1)
    weights = np.ones(df2.shape[1])
    x0 = weights/np.sum(weights)
    #Define a function to calculate volatility
    fun1 = lambda w: np.sqrt(np.dot(w,np.dot(w,covar)))
    res = minimize(fun1,x0,method='trust-constr',constraints = linear_constraint,bounds = bounds)

    #These are the weights of the stocks in the portfolio with the lowest level of risk possible.
    w_min = res.x

    np.set_printoptions(suppress = True, precision=2)
    fun2 = lambda w: np.sqrt(np.dot(w,np.dot(w,covar)))/r.dot(w)
    res_sharpe = minimize(fun2,x0,method='trust-constr',constraints = linear_constraint,bounds = bounds)

    w_sharpe = res_sharpe.x
    
    w = w_min
    num_ports = 100
    gap = (np.amax(r) - ret(r,w_min))/num_ports

    all_weights = np.zeros((num_ports, len(df.columns)))
    all_weights[0],all_weights[1]=w_min,w_sharpe
    ret_arr = np.zeros(num_ports)
    ret_arr[0],ret_arr[1]=ret(r,w_min),ret(r,w_sharpe)
    vol_arr = np.zeros(num_ports)
    vol_arr[0],vol_arr[1]=vol(w_min,covar),vol(w_sharpe,covar)

    for i in range(num_ports):
        port_ret = ret(r,w) + i*gap
        double_constraint = LinearConstraint([np.ones(df2.shape[1]),r],[1,port_ret],[1,port_ret])
    
        #Create x0: initial guesses for weights.
        x0 = w_min
        #Define a function for portfolio volatility.
        fun = lambda w: np.sqrt(np.dot(w,np.dot(w,covar)))
        a = minimize(fun,x0,method='trust-constr',constraints = double_constraint,bounds = bounds)
    
        all_weights[i,:]=a.x
        ret_arr[i]=port_ret
        vol_arr[i]=vol(a.x,covar)

    sharpe_arr = ret_arr/vol_arr 
    df_analysis = pd.DataFrame()
    df_analysis['Rate of Return'] = ret_arr
    df_analysis['Volatility'] = vol_arr
    df_analysis['Sharpe Ratio'] = sharpe_arr

    return df_analysis.values.tolist(), np.min(sharpe_arr), np.max(sharpe_arr)



def get_stock_prices(name, start_date, end_date):
    stocks_ = Entity.filter(
        Stock, f'name=\'{name}\' and date >= \'{start_date}\' and date <= \'{end_date}\'', 'order by date')

    returns = dict()
    for index, stock_ in enumerate(stocks_):
        
        returns[stock_.date.strftime('%Y-%m-%d')] = float(stock_.price)

    return returns


def calculate_sharpe_volatility(username, start_date, current_date):
    stock_names = []
    stock_set = set()
    total = 0
    for holding in Entity.filter(Holding, f'username=\'{username}\' and date <= \'{current_date}\'', 'order by pk DESC'):
        if holding.stock in stock_set:
            continue

        stock_set.add(holding.stock)
        stock_names.append((holding.stock, holding.shares * holding.price))
        total += holding.shares * holding.price

    data = dict()
    current_weights = []
    for name, value in stock_names:
        current_weights.append(round(float(value / total), 2))
        data[name] = get_stock_prices(name, start_date, current_date)

    data = pd.DataFrame.from_dict(data, orient='columns')
    return graph_EF(data)
    
    


if __name__ == '__main__':

    username = 'palydawn'
    start_date = "2023-03-19"
    end_date = "2023-04-19"

    calculate_sharpe_volatility(username, start_date, end_date)
