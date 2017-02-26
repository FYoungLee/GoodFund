"""
    作者： Fyoung Lix
    日期： 2017年1月24日
    版本： v1.2
"""
# -*- coding: utf-8 -*-

import json
import re
from json import decoder
from datetime import datetime
from bs4 import BeautifulSoup
from threading import Timer
from PyQt5.QtCore import QProcess, pyqtSignal
import asyncio
import aiohttp
import requests

FUNDS_UPDATE_TIMER = 20
MARKETS_UPDATE_TIMER = 5


class Tasks:
    FundsFull = 1
    FundsEst = 2
    FundsVal = 3
    Stocks = 4
    StocksInFund = 5


class StockInFund:
    def __init__(self, market, _id, ratio, _name=None, price=None, pe=0, pb=0, qr=0):
        self.market = market
        self.id = _id
        self.ratio = ratio
        self.name = _name
        self.price = price
        self.QR = qr
        self.PE = pe
        self.PB = pb
        self.url_ptn = 'http://nuff.eastmoney.com/EM_Finance2015TradeInterface/JS.ashx?id={}'

    async def update(self):
        _n = '1' if self.market == 'sh' else '2'
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url_ptn.format(self.id + _n), timeout=6) as response:
                    raw_data = await response.text()
                    if not raw_data:
                        return
                    data = re.findall(r'\[(.*?)\]', raw_data)[1].replace('"', '').split(',')
                    self.name = data[2]
                    self.price = float(data[3])
                    self.QR = float(data[36])
                    try:
                        self.PE = float(data[38])
                    except ValueError:
                        pass
                    self.PB = float(data[43])
        except asyncio.TimeoutError:
            pass

    def __eq__(self, other):
        return self.id == other.id


class TheFund:
    def __init__(self, fid):
        self.id = fid
        self.name = None
        self.estimate = None
        self.current_value = None
        self.fresh = False
        self.latest_change = None
        self.total_value = None
        self.perform = []
        self.score = None
        self.managers = {}
        self.scales = None
        self.stocks = []
        self.avg_PE = 0
        self.avg_PB = 0

    @property
    def initialized(self):
        return self.name is not None and self.score is not None

    def calculate_averages(self):
        _ratio = _tt_pe = _tt_pb = 0
        if _ratio:
            return
        for each in self.stocks:
            _ratio += each.ratio
            _tt_pe += each.PE * each.ratio
            _tt_pb += each.PB * each.ratio
        self.avg_PE = _tt_pe / _ratio
        self.avg_PB = _tt_pb / _ratio

    def update_baseinfo(self, raw_data):
        data = BeautifulSoup(raw_data, 'lxml')
        self.name = data.find('div', {'class': 'fundDetail-tit'}).text.split('(')[0]
        self.estimate = data.find('dl', {'class': 'dataItem01'}).find('dd', {'class': 'dataNums'}).findAll('span')[-1].text[:-1]
        re_ptn = r'<dl class="dataItem02">.+?<p>.+?(\d{4}-\d{2}-\d{2}).*?dataNums.*?(\d+\.\d+).*?([+|-]?\d+\.\d+)%'
        date, val, changed = re.search(re_ptn, raw_data).groups()
        self.fresh = True if datetime.now().strftime('%Y-%m-%d') == date else False
        self.current_value = val
        self.latest_change = changed
        self.total_value = data.find('dl', {'class': 'dataItem03'}).find('dd', {'class': 'dataNums'}).span.text
        self.perform = [x.text[:-1].strip() for x in data.find('li', {'id': 'increaseAmount_stage'}).findAll('tr')[1].findAll('td')][1:]
        top10_stocks = re.findall(r'<a href="http://quote.eastmoney.com/(\w{2})(\d{6})\.html" title=".*?">.*?</a>.+?<td class="alignRight bold">(.*?)%</td>', raw_data)
        for each in top10_stocks:
            stock = StockInFund(each[0], each[1], float(each[2]))
            if stock not in self.stocks:
                self.stocks.append(stock)

    async def initialize(self):
        async with aiohttp.ClientSession() as session:
            await asyncio.wait((self.get_baseinfo(session), self.get_scores(session)))

    async def update_stocks(self, session):
        futures = []
        for each in self.stocks:
            future = asyncio.ensure_future(each.update(session))
            futures.append(future)
            futures.append(self.get_scores(session))
        await asyncio.gather(*futures)

    async def get_baseinfo(self, session):
        url_ptn = 'http://fund.eastmoney.com/{}.html'
        try:
            async with session.get(url_ptn.format(self.id), timeout=6) as response:
                raw_data = await response.text()
                self.update_baseinfo(raw_data)
        except asyncio.TimeoutError:
            pass

    async def get_scores(self, session):
        url_ptn = 'http://fund.eastmoney.com/pingzhongdata/{}.js'

        def beautiful_pages(text):
            retDict = {}
            for each in text.split(';'):
                try:
                    e_list = each.split('var')[1].strip().split('=')
                    try:
                        retDict[e_list[0].strip()] = json.loads(e_list[1].strip())
                    except decoder.JSONDecodeError:
                        retDict[e_list[0].strip()] = e_list[1].strip()
                except IndexError:
                    continue
            return retDict

        try:
            async with session.get(url_ptn.format(self.id), timeout=6) as response:
                raw_data = await response.read()
                data = beautiful_pages(raw_data.decode(errors='ignore'))
                self.score = data['Data_performanceEvaluation']['avr'] \
                    if '暂无数据' not in data['Data_performanceEvaluation']['avr'] else ''
                for each in data['Data_currentFundManager']:
                    self.managers[each['id']] = {'name': each['name'],
                                                 'score': each['power']['avr'] if '暂无数据' not in each['power']['avr'] else ''}
                self.scales = data['Data_fluctuationScale']['series'][-1]['y']
        except asyncio.TimeoutError:
            pass

    async def update_offtime(self):
        url_ptn = 'http://fund.eastmoney.com/{}.html'
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url_ptn.format(self.id), timeout=6) as resp:
                    raw_data = await resp.text()
                    re_ptn = r'<dl class="dataItem02">.+?<p>.+?(\d{4}-\d{2}-\d{2}).*?dataNums.*?(\d+\.\d+).*?([+|-]?\d+\.\d+)%'
                    date, val, changed = re.search(re_ptn, raw_data).groups()
                    self.fresh = True if datetime.now().strftime('%Y-%m-%d') == date else False
                    self.current_value = val
                    self.latest_change = changed
        except (asyncio.TimeoutError, aiohttp.errors.ServerDisconnectedError):
            pass

    async def update_ontime(self):
        url_ptn = 'http://fundgz.1234567.com.cn/js/{}.js'
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url_ptn.format(self.id), timeout=6) as resp:
                    raw = await resp.text()
                    self.estimate = re.search(r'"gszzl":"(.*?)"', raw).group(1)
        except (asyncio.TimeoutError, aiohttp.errors.ServerDisconnectedError):
            pass

    def __eq__(self, other):
        return self.id == other.id


class Updater(QProcess):
    fund_sender = pyqtSignal(list, name='fund')
    market_sender = pyqtSignal(str, name='market')

    def __init__(self):
        super().__init__()
        self.funds = []
        self.markets = ''
        self.fundtimer = self.startTimer(FUNDS_UPDATE_TIMER*1000)
        self.markettimer = self.startTimer(MARKETS_UPDATE_TIMER*1000)

    def timerEvent(self, QTimerEvent):
        if QTimerEvent.timerId() == self.fundtimer:
            self.funds_updater()
        if QTimerEvent.timerId() == self.markettimer:
            self.markets_updater()

    def add_fund_to_update(self, fid):
        fund = TheFund(fid)
        if fund not in self.funds:
            self.funds.append(fund)

    def remove(self, fid):
        for fund in self.funds:
            if fund.id == fid:
                self.funds.remove(fund)
                return

    def init_checker(self):
        uninit_list = []
        for fund in self.funds:
            if not fund.initialized:
                uninit_list.append(fund)
        if uninit_list:
            self.funds_init(uninit_list)
        Timer(1, self.init_checker).start()

    def funds_updater(self):
        futures = []
        start = datetime.now().timestamp()
        for each in self.funds:
            # 交易时段判断
            if each.initialized:
                if self.isTradingTime():
                    futures.append(asyncio.ensure_future(each.update_ontime()))
                    for stock in each.stocks:
                        futures.append(stock.update())
                else:
                    if each.avg_PE == 0 and each.avg_PB == 0:
                        for stock in each.stocks:
                            futures.append(stock.update())
                    futures.append(asyncio.ensure_future(each.update_offtime()))
            else:
                futures.append(asyncio.ensure_future(each.initialize()))
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*futures))
        pak = []
        for each in self.funds:
            if each.initialized:
                pak.append(each)
        self.fund_sender.emit(pak)
        print('[{}]Fund update time cost: {}'.format(datetime.now().ctime(), datetime.now().timestamp() - start))

    def markets_updater(self):
        if not self.isTradingTime() and self.markets is not '':
            return
        raw_data = requests.get('http://hq.sinajs.cn/list=s_sh000001,s_sz399001,s_sz399006,s_sz399905,s_sz399300,s_sz399401')
        try:
            raws = [x.split(',')[:4] for x in re.findall(r'"(.*)"', raw_data.text)]
            self.markets = ''
            for each in raws:
                color = 'red'
                if '-' in each[2]:
                    color = 'green'
                else:
                    each[3] = '+' + each[3]
                each[2] = '[{}]'.format(each[2])
                self.markets += '{}: <font color="{}">{}%</font>{}'.format(each[0], color, '&nbsp;'.join(each[1:]), '&nbsp;' * 4)
                self.market_sender.emit(self.markets)
        except TypeError:
            return

    def get_filtered_list(self, kw, rank):
        raw_data = requests.get('http://fund.eastmoney.com/data/rankhandler.aspx?op=ph&pn=10000')
        try:
            rst = FundsFilter(kw, rank, raw_data.text).filter()
            for fund in rst:
                self.add_fund_to_update(fund[0])
        except TypeError:
            pass

    @staticmethod
    def isTradingTime():
        weekday = datetime.now().isoweekday()
        if weekday in (6, 7):
            return False
        hour = datetime.now().hour
        if hour >= 15 or hour < 9:
            return False
        if hour == 11 and datetime.now().minute > 30:
            return False
        if hour == 12:
            return False
        return True


class FundsFilter:
    def __init__(self, kw, rank, funds):
        self.kw = kw
        self.rank = rank
        self.funds_dat = funds

    def filter(self):
        datas = [x.split(',') for x in re.findall(r'"(.*?)"', self.funds_dat)]
        datas = self._funds_filter(datas)
        his = ['周涨幅', '月涨幅', '季涨幅', '半年涨幅', '今年涨幅', '一年涨幅', '两年涨幅', '三年涨幅']
        compr = None
        for each in his[:his.index(self.kw) + 1]:
            if compr is None:
                compr = self._trunc_data(self.rank, len(datas), self._rank_fund(each, datas))
            else:
                compr = self._compare_data(compr, self._trunc_data(self.rank, len(datas), self._rank_fund(each, datas)))
        return compr

    @staticmethod
    def _rank_fund(rankey, datas):
        """
            根据关键字对基金进行排序
        """
        k = {'周涨幅': 7, '月涨幅': 8, '季涨幅': 9, '半年涨幅': 10, '今年涨幅': 14, '一年涨幅': 11, '两年涨幅': 12, '三年涨幅': 13}
        filtered_list = filter(lambda x: x[k[rankey]], datas)
        return sorted(filtered_list, key=lambda x: float(x[k[rankey]]), reverse=True)

    @staticmethod
    def _funds_filter(funds):
        # 去掉不想要的基金类型，以后可增加成可选功能，现在暂时不用
        f = []
        for each in funds:
            if 'QDII' in each[1] or '纳斯达克' in each[1] or '标普' in each[1] or '全球' in each[1] or '美国' in each[1] \
                    or '德国' in each[1] or '国际' in each[1]:
                continue
            if '债' in each[1]:
                continue
            if '保本' in each[1]:
                continue
            # 统一保存成所需要的长度，以区别是否收藏了该基金
            f.append(each)
        return f

    @staticmethod
    def _trunc_data(rank, length, data):
        """
            根据提供的排名情况，进行靠前百分比筛选
        """
        return data[:int(length / 100 * rank)]

    @staticmethod
    def _compare_data(datal, datar):
        """
            比较两个List，返回其交集
        """
        return [ea for ea in datal if ea in datar]

