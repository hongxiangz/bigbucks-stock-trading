from datetime import timedelta
from re import I
import time
from ef_package import calculate_sharpe_volatility
from flask import Flask, redirect, render_template, request, session
import datetime
import hashlib
import os
from model import *
import numpy as np
import pandas as pd

app = Flask(__name__)
app.jinja_env.auto_reload = True
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SECRET_KEY'] = os.urandom(24)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=5)

def get_user():
    pk = session.get('user')['pk']
    return Entity.filter(User, where_cause=f'pk=\'{pk}\'')[0]

@app.before_request
def must_login():
    if request.path == "/login" or request.path == "/logout" or request.path.startswith("/static") or request.path == "/register":
        return None
    
    if not session.get("user"):
        return redirect("/login")

    user = get_user()
    if request.path not in ('/', '/set_date') and user.current_date is None:
        session['msg'] = 'current data not set'
        return redirect("/")

    return None


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html', session=session)
    elif request.method == 'POST':
        # get login argument
        username = request.form.get('username')
        password = request.form.get('password')
        password2 = request.form.get('password2')
        session.clear()
        if password != password2:
            session['msg'] = 'password not the same!'
            return redirect("/register")
        
        # hash the password for safety
        password_md5 = hashlib.md5(password.encode()).hexdigest()

        # create a new user
        new_user = User()
        new_user.username = username
        new_user.password = password_md5
        new_user.balance = 1000000
        new_user.role = 'user'
        new_user.save()
        session['msg'] = f'register accout {username} success, login now!'
    
        return redirect("/login")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html', session=session)
    elif request.method == 'POST':
        # get login argument
        username = request.form.get('username')
        password = request.form.get('password')
        password_md5 = hashlib.md5(password.encode()).hexdigest()

        session.clear()
        user_where_cause = f'username=\'{username}\' and password=\'{password_md5}\''
        users = Entity.filter(User, user_where_cause)
        if len(users) == 0:
            session['msg'] = 'invalid username or password'
            return redirect("/login")

        user = users[0]
        session['user'] = user.__dict__
        return redirect("/")


@app.route('/logout', methods=['GET'])
def logout():
    session.clear()
    return redirect("/login")


@app.route('/set_date', methods=['POST'])
def set_date():
    user = get_user()
    new_date = request.form.get('current_date')
    datetime_obj = datetime.datetime.strptime(new_date, '%Y-%m-%d').date()  
    if user.current_date is None:
        user.current_date = new_date
    else:
        if user.role != 'admin' and user.current_date > datetime_obj:
            session['msg'] = 'Date does not allow rollback'
            return redirect("/")
    
        user.current_date = new_date

    user.save()
    session['msg'] = 'update current_date success'
    return redirect("/")


def get_current_price(stock):
    user = get_user()
    current_date = user.current_date
    stock = Entity.filter(Stock, f'name=\'{stock}\'  and date <= \'{current_date}\'', 'order by pk DESC')[0]
    return stock.price


@app.route('/', methods=['GET'])
def index():
    user = get_user()
    current_date = user.current_date
    if current_date is not None:
        holdings = Entity.filter(Holding, full_sql=f'SELECT pk, username, stock, shares, cost, date, price FROM Holdings s1 WHERE pk = (SELECT MAX(pk) FROM Holdings s2 WHERE s1.stock = s2.stock and username=\'{user.username}\' and date <= \'{current_date}\');')

        for holding in holdings:
            if holding.shares != 0:
                holding.average_price = round(holding.cost / holding.shares, 2)
            else:
                holding.average_price = '-'
            stock = Entity.filter(Stock, f'name=\'{holding.stock}\'  and date <= \'{current_date}\'', 'order by pk DESC')[0]
            holding.current_price = stock.price
    else:
        holdings = []

    return render_template('index.html', session=session, holdings=holdings, user=user, date=current_date)


@app.route('/stocks/', methods=['GET'])
def stocks_all():
    user = get_user()
    current_date = user.current_date
    stocks_ = Entity.filter(Stock, f'date = \'{current_date}\'')
    return render_template('stocks.html', stocks=stocks_, stocks_active="active")


def get_returns(name, start_date, end_date):
    stocks_ = Entity.filter(Stock, f'name=\'{name}\' and date >= \'{start_date}\' and date <= \'{end_date}\'', 'order by date')
    # calculate daily return
    returns = []
    rates = []
    return_pairs = []
    acc_returns_dict = dict()
    for index, stock_ in enumerate(stocks_):
        if index == 0:
            continue

        last_stock = stocks_[index - 1]
        rate = float((stock_.price - last_stock.price) / last_stock.price)
        returns.append({
            'date': stock_.date,
            'rate': rate
        })
        rates.append(rate)

        acc_returns_dict[stock_.date] = float((stock_.price - stocks_[0].price) / stocks_[0].price)

        if index < 2:
            continue
        
        last_stock_2 = stocks_[index - 2]
        rate_2 = float((stock_.price - last_stock_2.price) / last_stock_2.price)
        return_pairs.append({
            'rate':rate,
            'rate_2':rate_2,
        })

    return stocks_, rates, returns, return_pairs, acc_returns_dict


@app.route('/stocks/<name>', methods=['GET', 'POST'])
def stock_detail(name):
    user = get_user()
    current_date = user.current_date
    if request.method == 'GET':
        start_date = (current_date - timedelta(days=30)).strftime('%Y-%m-%d')
        end_date = user.current_date.strftime('%Y-%m-%d')
    else:
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        end_date_obj = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
        if end_date_obj > current_date:
            end_date = current_date.strftime('%Y-%m-%d')
        
    stocks_, rates, returns, return_pairs, acc_returns_dict = get_returns(name, start_date, end_date)
    _, _, spy_returns, _, spy_acc_returns_dict = get_returns("SPY", start_date, end_date)
    data = np.array(rates)
    bins = np.arange(-0.006, 0.006 + 0.0005, 0.0005)
    cuts = pd.cut(data, bins=bins)
    histogram = []
    for index, value in cuts.value_counts().items():
        print(f"{index.right} : {value}")
        histogram.append({
            'range_left': round(index.right, 3),
            'count': value
        })

    dates = [item['date'] for item in returns]
    return_dict = {item['date']: item['rate'] for item in returns}
    spy_dict = {item['date']: item['rate'] for item in spy_returns}

    return_compares = []
    acc_compares = []
    for date in dates:
        return_compares.append({
            'stock': return_dict[date],
            'spy': spy_dict.get(date, 0)
        })

        acc_compares.append({
            'stock': acc_returns_dict[date],
            'spy': spy_acc_returns_dict.get(date, 0)
        })

    return render_template('stock_detail.html', return_pairs=return_pairs, 
                           histogram=histogram, stocks=stocks_, 
                           stocks_active="active", stock=name, 
                           start_date=start_date, end_date=end_date, 
                           returns=returns, 
                           dates=dates,
                           return_compares=return_compares,
                           acc_compares=acc_compares
                           )


def get_price_of_stock(name, end_date):
    stocks_ = Entity.filter(Stock, f'name=\'{name}\' and date <= \'{end_date}\'', 'order by date desc')
    if len(stocks_) == 0:
        return None
    
    return stocks_[0].price


def get_user_balance(current_date):
    user = get_user()
    transactions_ = Entity.filter(Transaction, f'username=\'{user.username}\' and date <= \'{current_date}\'', 'order by pk DESC')
    if len(transactions_) == 0:
        return 1000000

    return transactions_[0].balance


def get_portfolio_returns(start_date, end_date):
    # get user holdings
    user = get_user()
    start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    delta = timedelta(days=1)

    portfolios = []
    while start <= end:
        current_date = start.strftime("%Y-%m-%d")
        stock_set = set()
        portfolio = get_user_balance(current_date)
        for holding in Entity.filter(Holding, f'username=\'{user.username}\' and date <= \'{current_date}\'', 'order by pk DESC'):
            if holding.stock in stock_set:
                continue
            
            stock_set.add(holding.stock)
            portfolio += get_price_of_stock(holding.stock, current_date) * holding.shares

        portfolios.append({
            'date': current_date,
            'portfolio': portfolio
        })

        print(f'{current_date}, {portfolio}, {get_user_balance(current_date)}')
        # increase date
        start += delta

    # calculate daily return
    returns = []
    rates = []
    return_pairs = []
    acc_returns_dict = dict()
    for index, portfolio in enumerate(portfolios):
        if index == 0:
            continue

        last_portfolio = portfolios[index - 1]
        rate = float((portfolio['portfolio'] - last_portfolio['portfolio']) / last_portfolio['portfolio'])
        returns.append({
            'date': portfolio['date'],
            'rate': rate
        })
        rates.append(rate)

        acc_returns_dict[portfolio['date']] = float((portfolio['portfolio'] - portfolios[0]['portfolio']) / portfolios[0]['portfolio'])

        if index < 2:
            continue
        
        last_portfolio_2 = portfolios[index - 2]
        rate_2 = float((portfolio['portfolio'] - last_portfolio_2['portfolio']) / last_portfolio_2['portfolio'])
        return_pairs.append({
            'rate':rate,
            'rate_2':rate_2,
        })

    return portfolios, rates, returns, return_pairs, acc_returns_dict


@app.route('/portfolio', methods=['GET', 'POST'])
def portfolio():
    user = get_user()
    current_date = user.current_date
    if request.method == 'GET':
        start_date = (current_date - timedelta(days=30)).strftime('%Y-%m-%d')
        end_date = user.current_date.strftime('%Y-%m-%d')
    else:
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        end_date_obj = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
        if end_date_obj > current_date:
            end_date = current_date.strftime('%Y-%m-%d')
        
    portfolios, rates, returns, return_pairs, acc_returns_dict = get_portfolio_returns(start_date, end_date)
    _, _, spy_returns, _, spy_acc_returns_dict = get_returns("SPY", start_date, end_date)

    data = np.array(rates)
    bins = np.arange(-0.006, 0.006 + 0.0005, 0.0005)
    cuts = pd.cut(data, bins=bins)
    histogram = []
    for index, value in cuts.value_counts().items():
        print(f"{index.right} : {value}")
        histogram.append({
            'range_left': round(index.right, 3),
            'count': value
        })

    dates = [item['date'].strftime("%Y-%m-%d") for item in spy_returns]
    return_dict = {item['date']: item['rate'] for item in returns}
    spy_dict = {item['date'].strftime("%Y-%m-%d"): item['rate'] for item in spy_returns}

    spy_acc_new_dict = {}
    for date, value in spy_acc_returns_dict.items():
        new_date = date.strftime('%Y-%m-%d')
        spy_acc_new_dict[new_date] = value

    return_compares = []
    acc_compares = []
    for date in dates:
        if return_dict.get(date, None) is None:
            continue

        return_compares.append({
            'stock': return_dict[date],
            'spy': spy_dict.get(date, 0)
        })

        acc_compares.append({
            'stock': acc_returns_dict[date],
            'spy': spy_acc_new_dict.get(date, 0)
        })

    return render_template('portfolio.html', return_pairs=return_pairs, 
                           histogram=histogram, portfolios=portfolios, 
                           portfolio_active="active", 
                           start_date=start_date, end_date=end_date, 
                           returns=returns, 
                           dates=dates,
                           return_compares=return_compares,
                           acc_compares=acc_compares
                           )


@app.route('/report', methods=['GET', 'POST'])
def report():
    user = get_user()
    current_date = user.current_date
    if request.method == 'GET':
        start_date = (current_date - timedelta(days=30)).strftime('%Y-%m-%d')
        end_date = user.current_date.strftime('%Y-%m-%d')
    else:
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        end_date_obj = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
        if end_date_obj > current_date:
            end_date = current_date.strftime('%Y-%m-%d')
        
    # calculate sharpe

    port_s,port_re,port_v,points, min_sharp, max_sharp = calculate_sharpe_volatility(user.username, start_date, current_date)
    result = {
        'points': points,
        'min_sharp': min_sharp,
        'max_sharp': max_sharp,
        'port_ret' : port_re,
        'port_sigma':port_v,
        'port_s':port_s
    }

    return render_template('report.html', result=result, result_active="active", start_date=start_date, end_date=end_date)



@app.route('/holdings/<stock>', methods=['GET'])
def holding_detail(stock):
    user = get_user()
    current_date = user.current_date
    holdings_ = Entity.filter(Holding, f'username=\'{user.username}\' and stock=\'{stock}\' and date <= \'{current_date}\'', 'order by pk DESC')
    return render_template('holdings.html', holdings=holdings_, holdings_active="active")


@app.route('/holdings/', methods=['GET'])
def holdings():
    user = get_user()
    current_date = user.current_date
    if user.role == 'user':
        holdings_ = Entity.filter(Holding, f'username=\'{user.username}\' and date <= \'{current_date}\'', 'order by pk DESC')
    else:
        holdings_ = Entity.filter(Holding, f'date <= \'{current_date}\'', 'order by pk DESC')

    return render_template('holdings.html', holdings=holdings_, holdings_active="active")


@app.route('/summary/', methods=['GET'])
def summary():
    user = get_user()
    current_date = user.current_date
    # get all transaction tody
    stocks = []
    for transaction in Entity.filter(Transaction, f'date=\'{current_date}\''):
        if transaction.stock in stocks:
            continue

        stocks.append(transaction.stock)

    summaries_ = []
    for stock in stocks:
        buy_shares = 0
        sell_shares = 0
        for transaction in Entity.filter(Transaction, f'date=\'{current_date}\' and stock=\'{stock}\''):
            if transaction.type == 'Buy':
                buy_shares += transaction.shares
            else:
                sell_shares += transaction.shares
        
        summaries_.append({
            'stock': stock,
            'buy_shares': buy_shares,
            'sell_shares': sell_shares,
        })

    return render_template('summary.html', summaries=summaries_, summary_active="active")


@app.route('/transactions', methods=['GET'])
def transactions():
    user = get_user()
    current_date = user.current_date
    if user.role == 'admin':
        transactions_ = Entity.filter(Transaction, f'date <= \'{current_date}\'', 'order by pk DESC')
    else:
        transactions_ = Entity.filter(Transaction, f'username=\'{user.username}\' and date <= \'{current_date}\'', 'order by pk DESC')
    return render_template('transactions.html', transactions=transactions_, transactions_active="active")

@app.route('/trade', methods=['POST'])
def trade():
    transaction = Transaction()
    # stock name
    transaction.stock = request.form.get('stock')
    transaction.date = request.form.get('date')
    transaction.type = request.form.get('type')
    transaction.shares = int(request.form.get('shares'))
    transaction.price = float(request.form.get('price'))
    transaction.cost = transaction.shares * transaction.price
    user = get_user()
    current_date = user.current_date

    transaction.username = user.username
    holdings = Entity.filter(Holding, where_cause=f'stock = \'{transaction.stock}\' and date <= \'{current_date}\'', order_cause='order by pk desc')

    session.pop('msg', '')
    if transaction.type == 'Buy':
        # check banlance
        if user.balance >= transaction.cost:
            user.balance -= transaction.cost
            # update holdings
            if len(holdings) > 0:
                old_holding = holdings[0]
                new_holding = Holding()
                new_holding.username = user.username
                new_holding.stock = transaction.stock
                new_holding.shares = old_holding.shares + transaction.shares
                new_holding.cost = old_holding.cost + transaction.cost
                new_holding.date = current_date
                new_holding.price = get_current_price(transaction.stock)
                new_holding.save()
            else:
                new_holding = Holding()
                new_holding.username = user.username
                new_holding.stock = transaction.stock
                new_holding.shares = transaction.shares
                new_holding.cost = transaction.cost
                new_holding.date = current_date
                new_holding.price = get_current_price(transaction.stock)
                new_holding.save()

        else:
            session['msg'] = 'balance not enough'
            return redirect("/stocks/")
    else:
        # check holding
        
        if len(holdings) > 0 and holdings[0].shares >= transaction.shares:
            old_holding = holdings[0]

            new_holding = Holding()
            new_holding.username = user.username
            new_holding.stock = transaction.stock
            new_holding.shares = old_holding.shares - transaction.shares
            new_holding.cost = old_holding.cost - transaction.cost
            new_holding.date = current_date
            new_holding.price = get_current_price(transaction.stock)
            new_holding.save()
            
            # increase balance
            user.balance += transaction.cost

        else:
            session['msg'] = 'shares not enough'
            return redirect(f"/")

    transaction.balance = user.balance
    transaction.save()

    user.save()
    return redirect(f"/")


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True, port=5001)
