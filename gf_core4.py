from tools import *
# import requests
# import aiohttp
# import asyncio
# import time
# import re
# import json
from bs4 import BeautifulSoup as bsoup
from PyQt5.QtCore import QProcess, QThread, pyqtSignal

# APIs:
# 基金明细地址格式 "http://fund.eastmoney.com/pingzhongdata/{}.js"
# 基金持股明细 'http://fund.eastmoney.com/f10/FundArchivesDatas.aspx?type=jjcc&code={}&topline=500'
# 基金持股明细 WAP版
#   https://fundmobapi.eastmoney.com/FundMApi/FundInverstPositionDetail.ashx?FCODE=540006&deviceid=Wap&plat=Wap&product=EFund&version=2.0.0&DATE=2017-03-31
# 股票实况1 "http://hq.sinajs.cn/list={},{},{}..." (s_sh000001, sh000001)
# 股票实况2 "http://api.money.126.net/data/feed/{},{}" (0000001)
# wap版基金大全 "https://fundmobapi.eastmoney.com/FundMApi/FundRankNewList.ashx?pagesize=10000&deviceid=Wap&plat=Wap&product=EFund&version=2.0.0"
#   FUNDTYPE = {001: 指数, 002: 混合, 003: 债券， 006: 保本, 007: QDII, 008: 定开债, 202: 分级债券, 205: 货币}
# 基金经理 "http://fund.eastmoney.com/Data/FundDataPortfolio_Interface.aspx?dt=14&pn=5000"
# 经理详情 "https://fundmobapi.eastmoney.com/FundMApi/FundMangerBase.ashx?deviceid=fundmanager2016&version=4.3.0&product=EFund&plat=Iphone&MGRID=30325983"

# url = 'http://fund.eastmoney.com/f10/FundArchivesDatas.aspx?type=jjcc&code={}&topline=500'

FUNDS_UPDATE_TIMER = 30
MARKETS_UPDATE_TIMER = 10
TIMEOUT = 10


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


class Market_Updater(QThread):
    markets_singal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.the_markets = ['s_sh000001', 's_sz399001', 's_sz399300', 's_sz399905', 's_sz399401', 's_sz399006']
        self.results = {}
        self.stocks_id = []
        self.need_update = True
        self.update()
        self.timer = self.startTimer(MARKETS_UPDATE_TIMER * 1000)

    def timerEvent(self, QTimerEvent):
        if QTimerEvent.timerId() == self.timer and self.need_update:
            self.update()

    def update(self):
        try:
            q_list = self.the_markets + self.stocks_id
            for index in range(0, len(q_list), 700):
                url = 'http://hq.sinajs.cn/list=' + ','.join(q_list[index:index+700])
                req = requests.get(url, timeout=TIMEOUT)
                if req.ok:
                    rst = re.findall('_?s?_\w{2}(\d{5,6})="(.*)";', req.text)
                    for row in rst:
                        code = row[0]
                        _data = row[1].split(',')
                        if len(code) == 6:
                            name, price, change = _data[0], _data[1], _data[3]
                            if name in ['深证成指', '沪深300', '中证 500', '中小盘', '创业板指']:
                                code = 's_sz' + code
                            elif name == '上证指数':
                                code = 's_sh' + code
                        else:
                            name, price, change = _data[1], _data[6], _data[8]
                        self.results[code] = {'name': name, 'price': float(price), 'change': float(change)}
            if not isTradingTime():
                self.need_update = False
        except requests.exceptions.RequestException:
            self.update()

    def extend_stocks(self, stocks):
        def cook_code(scode):
            if len(scode) == 5:
                return 'hk' + scode
            elif '60' in scode[:2]:
                return 's_sh' + scode
            else:
                return 's_sz' + scode
        cooked_codes = [cook_code(x) for x in stocks]
        cooked_codes.sort()
        self.stocks_id.extend(cooked_codes)
        self.need_update = True

# class Updater(QThread):
#     fund_sender = pyqtSignal(list, name='fund')
#     market_sender = pyqtSignal(str, name='market')
#
#     def __init__(self, funds_id):
#         super().__init__()
#         self.the_funds, self.the_shares = buildup_funds(funds_id)
#         self.fundtimer = self.startTimer(FUNDS_UPDATE_TIMER * 1000)
#         self.markettimer = self.startTimer(MARKETS_UPDATE_TIMER * 1000)
#         self.markets_string = ''
#
#     def timerEvent(self, QTimerEvent):
#         if QTimerEvent.timerId() == self.fundtimer:
#             self.funds_updater()
#         if QTimerEvent.timerId() == self.markettimer:
#             self.markets_updater()
#
#     def funds_updater(self):
#         if self.isTradingTime():
#             s = scratch_shares(self.the_shares)
#         else:
#             f = scratch_all_funds()
#             if f:
#                 self.fund_sender.emit(f)
#
#     def markets_updater(self):
#         if not self.isTradingTime() and self.markets_string is not '':
#             return
#         try:
#             raw_data = requests.get('http://hq.sinajs.cn/list=s_sh000001,s_sz399001,s_sz399300,s_sz399905,s_sz399401,s_sz399006',
#                                     timeout=TIMEOUT)
#             raws = [x.split(',')[:4] for x in re.findall(r'"(.*)"', raw_data.text)]
#             self.markets_string = ''
#             for each in raws:
#                 color = 'red'
#                 if '-' in each[2]:
#                     color = 'green'
#                 else:
#                     each[3] = '+' + each[3]
#                 each[2] = '[{}]'.format(each[2])
#                 self.markets_string += '{}: <font color="{}">{}%</font>{}'.format(each[0], color, '&nbsp;'.join(each[1:]), '&nbsp;' * 4)
#                 self.market_sender.emit(self.markets_string)
#         except (TypeError, requests.exceptions.RequestException):
#             pass
class FundsBuilder(QThread):
    funds_obj_signals = pyqtSignal(dict)
    stocks_appender = pyqtSignal(list)
    progress_signals = pyqtSignal(str)

    def __init__(self, fdb):
        super().__init__()
        self.funds = []
        self.fdb = fdb

    def run(self):
        while True:
            if self.funds:
                self.buildup_funds(self.funds, self.fdb)
            time.sleep(1)

    def buildup_funds(self, funds, fdb):
        funds_obj = {}
        for n, fund_id in enumerate(funds):
            _f = TheFund(fund_id, fdb[fund_id])
            if _f.bad:
                continue
            funds_obj[fund_id] = _f
            self.stocks_appender.emit(_f.get_shares_code())
            self.progress_signals.emit('{} 加载完毕 ({}/{})'.format(_f.details['SHORTNAME'], n + 1, len(funds)))
        self.funds_obj_signals.emit(funds_obj)
        self.funds.clear()


class TheFund:
    S_Bonus = recalc_bonus()
    # url_share_info = 'http://nuff.eastmoney.com/EM_Finance2015TradeInterface/JS.ashx?id={}'

    def __init__(self, fcode, fdb):
        self.details = fdb
        self.known_shares = {}
        self.shares_in_total = None
        if self.build_shares_detail(fcode):
            self.bad = False
        else:
            self.bad = True

    def build_shares_detail(self, scode):
        def beautiful_pages(text):
            retDict = {}
            for each in text.split(';'):
                try:
                    e_list = each.split('var')[1].strip().split('=')
                    try:
                        retDict[e_list[0].strip()] = json.loads(e_list[1].strip())
                    except json.decoder.JSONDecodeError:
                        retDict[e_list[0].strip()] = e_list[1].strip()
                except IndexError:
                    continue
            return retDict

        try:
            page1 = requests.get('http://fund.eastmoney.com/f10/FundArchivesDatas.aspx?type=jjcc&code={}&topline=500'.format(scode), timeout=5)
            page2 = requests.get('http://fund.eastmoney.com/pingzhongdata/{}.js'.format(scode), timeout=5)
            pagesoup = bsoup(page1.content, 'html5lib')
            shareobj = pagesoup.find('tbody').find_all('tr')
            for share in shareobj:
                r = float(share.find_all('td')[6].text[:-1]) / 100
                share_url = share.find_all('td')[1].a['href']
                share_id = share_url.split('/')[-1].split('.')[0][-6:]
                self.known_shares[share_id] = r
            details_dict = beautiful_pages(page2.text)
            self.details['code'] = details_dict['fS_name']
            self.details['name'] = details_dict['fS_code']
            self.shares_in_total = details_dict['Data_assetAllocation']['series'][0]['data'][-1]/100
            self.details['LJJZ'] = details_dict['Data_ACWorthTrend'][-1][-1]
            try:
                self.details['Score'] = float(details_dict['Data_performanceEvaluation']['avr'])
            except ValueError:
                self.details['Score'] = 0.0
            self.details['Managers'] = details_dict['Data_currentFundManager']
            self.details['Scale'] = details_dict['Data_fluctuationScale']['series'][-1]['y']
            return True
        except (AttributeError, requests.exceptions.RequestException):
            self.build_shares_detail(scode)
        except KeyError:
            return False

    def style(self):
        rank = {'沪A': 0, '深A': 0, '中小': 0, '创业': 0, '沪B': 0, '深B': 0}
        for s_id in self.known_shares.keys():
            if s_id[:3] in ('600', '601', '603'):
                rank['沪A'] += self.known_shares[s_id]*100
            elif s_id[:3] in ('000',):
                rank['深A'] += self.known_shares[s_id]*100
            elif s_id[:3] in ('002',):
                rank['中小'] += self.known_shares[s_id]*100
            elif s_id[:3] in ('300',):
                rank['创业'] += self.known_shares[s_id]*100
            elif s_id[:3] in ('900',):
                rank['沪B'] += self.known_shares[s_id]*100
            elif s_id[:3] in ('200',):
                rank['深B'] += self.known_shares[s_id]*100
        rank = [(x, round(rank[x], 1)) for x in rank if rank[x]]
        rank.sort(key=lambda x: x[1], reverse=True)
        ret = ''
        for each in rank:
            ret += '{} : {}%\n'.format(str(each[0]), str(each[1]))
        return ret

    def pe(self, shares_value_DB):
        shares_profits_list = {}
        tips = ''
        for s_id in self.known_shares.keys():
            if s_id not in shares_value_DB.keys() or s_id not in self.S_Bonus.keys():
                continue
            bonus = self.S_Bonus[s_id]
            date = sorted(list(bonus.keys()), reverse=True)[0]
            latest = bonus[date]
            pe = shares_value_DB[s_id]['price'] / latest if latest else 0
            tips += '{:^8} \t{:.2f} [{:.1%}]\n'.format(shares_value_DB[s_id]['name'], pe, self.known_shares[s_id])
            shares_profits_list[s_id] = latest
        sum_of_profits = 0
        sum_of_prices = 0
        for s_id in shares_profits_list:
            if shares_value_DB[s_id]['price']:
                sum_of_profits += shares_profits_list[s_id] * self.known_shares[s_id]
                sum_of_prices += shares_value_DB[s_id]['price'] * self.known_shares[s_id]
            
        try:
            return (round(sum_of_prices/ sum_of_profits, 2), tips)
        except ZeroDivisionError:
            return (0, tips)

    def estimate(self, shares_value_DB):
        tempo = 0
        total_known_shares_ratio = 0
        missing_stocks = []
        for share in self.known_shares:
            if share in shares_value_DB.keys() and shares_value_DB[share]:
                tempo += shares_value_DB[share]['change'] * self.known_shares[share]
                total_known_shares_ratio += self.known_shares[share]
            else:
                missing_stocks.append(share)
        try:
            return round(tempo / total_known_shares_ratio * self.shares_in_total, 2), missing_stocks
        except ZeroDivisionError:
            return 0, []

    def get_shares_code(self):
        return list(self.known_shares.keys())


class ManFilter(QProcess):
    funds_signal = pyqtSignal(list)
    display_managers_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def start(self):
        all_funds = scratch_all_funds()
        m = self.scratch_managers(20)
        b_funds = [x['best'] for x in m]
        b_funds = [all_funds[x] for x in b_funds if x in all_funds.keys()]
        b_funds = filter_goodfund(b_funds, 4, 50)
        b_funds = [x['FCODE'] for x in b_funds]
        pass
        self.funds_signal.emit(b_funds)

    def scratch_managers(self, rank):
        url = 'http://fund.eastmoney.com/Data/FundDataPortfolio_Interface.aspx?dt=14&pn=5000'
        rawpage = requests.get(url)
        cleantext = re.search(r'data:(\[.*\])', rawpage.text).groups()[0]
        managers = json.loads(cleantext)
        # 第一层筛选： 最高业绩大于0的选手
        men = [[x[0], x[1], float(x[-1][:-1])] for x in managers if '-' not in x[-1] and float(x[-1][:-1]) > 0]
        # 按业绩高低排序后，前10％的选手
        men = sorted(men, key=lambda x: x[-1], reverse=True)[:len(men)//(100//rank)]
        # 重新组装成 dict 模式
        men = {x[0]: {'name': x[1]} for x in men}
        count = [0]
        self.display_managers_signal.emit('{} great players found'.format(len(men)))

        # def get_performance(mid):
        #     url = 'http://fund.eastmoney.com/manager/{}.html'
        #     try:
        #         rawpage = requests.get(url.format(mid))
        #     except requests.exceptions.RequestException:
        #         return
        #     pgsoup = bsoup(rawpage.content.decode(), 'html5lib')
        #     try:
        #         funds = pgsoup.find('table', {'class': 'ftrs'}).find('tbody').find_all('tr')
        #     except AttributeError:
        #         return
        #     perf = 0
        #     n = 0
        #     for fund in funds:
        #         pieces = fund.find_all('td')
        #         try:
        #             if pieces[3].text in ('理财型', '货币型', '债券指数', '债券型'):
        #                 continue
        #             scales = float(pieces[4].text)
        #             period = pieces[6].text.replace('天', '')
        #             days = 0
        #             if '年又'in period:
        #                 y, d = period.split('年又')
        #                 days = int(y) * 365 + int(d)
        #             else:
        #                 days = int(period)
        #             change = float(pieces[7].text[:-1])
        #             perf += change / days
        #             n += 1
        #         except ValueError:
        #             continue
        #     try:
        #         return round(perf/n, 6), url.format(mid)
        #     except ZeroDivisionError:
        #         return
        #
        # for n, m in enumerate(men):
        #     ret = get_performance(m[0])
        #     if ret:
        #         m.extend(ret)
        #     print('{} / {} finished'.format(n, len(men)))
        # men = [x for x in men if len(x) > 2]

        async def task(session, man_id):
            url = 'http://fund.eastmoney.com/manager/{}.html'
            try:
                async with session.get(url.format(man_id)) as resp:
                    content = await resp.read()
                    pgsoup = bsoup(content, 'lxml')
                    funds = pgsoup.find('table', {'class': 'ftrs'}).find('tbody').find_all('tr')
                    perf = []
                    score = 0
                    n = 0
                    for fund in funds:
                        pieces = fund.find_all('td')
                        try:
                            if pieces[3].text in ('理财型', '货币型', '债券指数', '债券型'):
                                continue
                            scales = float(pieces[4].text)
                            period = pieces[6].text.replace('天', '')
                            days = 0
                            if '年又' in period:
                                y, d = period.split('年又')
                                days = int(y) * 365 + int(d)
                            else:
                                days = int(period)
                            change = float(pieces[7].text[:-1])
                            perf.append((pieces[0].text, change / days))
                            score += change / days
                            n += 1
                        except ValueError:
                            continue
                    perf.sort(key=lambda x: x[1], reverse=True)
                    men[man_id].update({'score': round(score / n, 6), 'url': url.format(man_id), 'best': perf[0][0]})
                    count[0] += 1
                    print('{} ({}/{})'.format(men[man_id]['name'], count[0], len(men)))
                    self.display_managers_signal.emit('{} ({}/{})'.format(men[man_id]['name'], count[0], len(men)))
            except Exception:
                return

        async def run():
            async with aiohttp.ClientSession() as session:
                tasks = []
                for m in men.keys():
                    tasks.append(asyncio.ensure_future(task(session, m)))
                await asyncio.gather(*tasks)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(run())

        men = [men[x] for x in men.keys() if 'score' in men[x].keys()]
        men.sort(key=lambda x: x['score'], reverse=True)
        return men


# def scratch_managers():
#     url = 'http://fund.eastmoney.com/Data/FundDataPortfolio_Interface.aspx?dt=14&pn=5000'
#     rawpage = requests.get(url)
#     cleantext = re.search(r'data:(\[.*\])', rawpage.text).groups()[0]
#     managers = json.loads(cleantext)
#     men = [[x[0], x[1]] for x in managers]
#     print('{} managers found'.format(len(men)))
#
#     async def get_performance(session, mid):
#         url = 'http://fund.eastmoney.com/manager/{}.html'
#         async with session.get(url.format(mid)) as resp:
#             rawpage = await resp.read()
#             pgsoup = bsoup(rawpage.decode(), 'html5lib')
#             funds = pgsoup.find('table', {'class': 'ftrs'}).find('tbody').find_all('tr')
#             perf = 0
#             for fund in funds:
#                 pieces = fund.find_all('td')
#                 try:
#                     if pieces[3].text in ('理财型', '货币型', '债券指数', '债券型'):
#                         continue
#                     scales = float(pieces[4].text)
#                     period = pieces[6].text.replace('天', '')
#                     days = 0
#                     if '年又'in period:
#                         y, d = period.split('年又')
#                         days = int(y) * 365 + int(d)
#                     else:
#                         days = int(period)
#                     change = float(pieces[7].text[:-1])
#                     perf += scales * (change / days)
#                 except ValueError:
#                     continue
#             for each in men:
#                 if each[0] == mid:
#                     each.append(round(perf, 2))
#                     each.append(url.format(mid))
#                     print(mid, 'finished!')
#                     break
#
#     async def run():
#         tasks = []
#         with aiohttp.ClientSession() as session:
#             for m in men:
#                 task = asyncio.ensure_future(get_performance(session, m[0]))
#                 tasks.append(task)
#             await asyncio.gather(*tasks)
#
#     loop = asyncio.get_event_loop()
#     future = asyncio.ensure_future(run())
#     loop.run_until_complete(future)
#
#     return men

