import requests
import aiohttp
import asyncio
import time
import re
import json
from bs4 import BeautifulSoup as bsoup
from datetime import datetime, timedelta
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

# url = 'http://fund.eastmoney.com/f10/FundArchivesDatas.aspx?type=jjcc&code={}&topline=500'

FUNDS_UPDATE_TIMER = 30
MARKETS_UPDATE_TIMER = 5
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
    def __init__(self):
        super().__init__()
        self.the_markets = ['s_sh000001', 's_sz399001', 's_sz399300', 's_sz399905', 's_sz399401', 's_sz399006']
        self.stocks_id = []
        self.current_market = {}
        self.url = 'http://hq.sinajs.cn/list='
        self.timer = self.startTimer(MARKETS_UPDATE_TIMER * 1000)

    def timerEvent(self, QTimerEvent):
        if QTimerEvent.timerId() == self.timer:
            if isTradingTime() or not self.current_market:
                self.update()

    def update(self):
        url = self.url + ','.join(self.the_markets) + ',' + ','.join(self.stocks_id)
        try:
            req = requests.get(url, timeout=TIMEOUT)
            if req.ok:
                lines = req.text.split('\n')
                for line in lines[:6]:
                    try:
                        code, name, price, change = re.search(r'_(s_.*)="(.*?),(.*?),.*?,(.*?),', line).groups()
                    except AttributeError:
                        continue
                    self.current_market[code] = {'name': name, 'price': float(price), 'change': float(change)}
                for line in lines[6:]:
                    try:
                        code, name, price, change = re.search(r'_s_\w\w(.*)="(.*?),(.*?),.*?,(.*?),', line).groups()
                    except AttributeError:
                        continue
                    self.current_market[code] = {'name': name, 'price': float(price), 'change': float(change)}
        except requests.exceptions.RequestException:
            self.update()

    def cook_the_markets(self):
        markets_str = ''
        if self.current_market:
            for each in self.the_markets:
                try:
                    this = self.current_market[each]
                except KeyError:
                    continue
                color = 'black'
                sig = ''
                if this['change'] > 0:
                    color = 'red'
                    sig = '+'
                elif this['change'] < 0:
                    color = 'green'
                markets_str += '{}:&nbsp;<font color="{}">{}{}{}{}%</font>{}'\
                    .format(this['name'], color, this['price'], '&nbsp;'*2, sig, this['change'], '&nbsp;'*6)
        return markets_str

    def extend_stocks(self, stocks):
        def cook_code(scode):
            if '60' in scode[:2]:
                return 's_sh' + scode
            else:
                return 's_sz' + scode
        cooked_codes = [cook_code(x) for x in stocks]
        cooked_codes.sort()
        self.stocks_id.extend(cooked_codes)
        self.update()


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
    funds_obj_signals = pyqtSignal(dict, list)
    progress_signals = pyqtSignal(str)

    def __init__(self, fdb, sdb):
        super().__init__()
        self.funds = []
        self.fdb = fdb
        self.sdb = sdb

    def run(self):
        while True:
            if self.funds:
                self.buildup_funds(self.funds, self.fdb, self.sdb)
            time.sleep(1)

    def buildup_funds(self, funds, fdb, sdb):
        funds_obj = {}
        share_codes = []
        for n, fund_id in enumerate(funds):
            _f = TheFund(fund_id, fdb[fund_id], sdb['datas'])
            if _f.bad:
                continue
            funds_obj[fund_id] = _f
            share_codes.extend(_f.get_shares_code())
            self.progress_signals.emit('{} 加载完毕 ({}/{})'.format(_f.details['SHORTNAME'], n + 1, len(funds)))
        self.funds_obj_signals.emit(funds_obj, share_codes)
        self.funds.clear()


class TheFund:
    url_shares_of_fund = 'http://fund.eastmoney.com/f10/FundArchivesDatas.aspx?type=jjcc&code={}&topline=500'
    url_fund_detail = 'http://fund.eastmoney.com/pingzhongdata/{}.js'
    # url_share_info = 'http://nuff.eastmoney.com/EM_Finance2015TradeInterface/JS.ashx?id={}'

    def __init__(self, fcode, fdb, sdb):
        self.details = fdb
        self.known_shares = {}
        self.shares_in_total = None
        self.shares_earning_details = {}
        if self.build_shares_detail(fcode, sdb):
            self.bad = False
        else:
            self.bad = True

    def build_shares_detail(self, scode, sdb):
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
            page1 = requests.get(self.url_shares_of_fund.format(scode), timeout=5)
            page2 = requests.get(self.url_fund_detail.format(scode), timeout=5)
            pagesoup = bsoup(page1.content, 'html5lib')
            shareobj = pagesoup.find('tbody').find_all('tr')
            for share in shareobj:
                r = float(share.find_all('td')[6].text[:-1]) / 100
                share_url = share.find_all('td')[1].a['href']
                share_id = share_url.split('/')[-1].split('.')[0][-6:]
                self.known_shares[share_id] = r
            details_dict = beautiful_pages(page2.text)
            self.shares_in_total = details_dict['Data_assetAllocation']['series'][0]['data'][-1]/100
            self.details['LJJZ'] = details_dict['Data_ACWorthTrend'][-1][-1]
            try:
                self.details['Score'] = float(details_dict['Data_performanceEvaluation']['avr'])
            except ValueError:
                self.details['Score'] = 0.0
            self.details['Managers'] = details_dict['Data_currentFundManager']
            self.details['Scale'] = details_dict['Data_fluctuationScale']['series'][-1]['y']
            for s_id in self.known_shares.keys():
                self.shares_earning_details[s_id] = sdb[s_id]
            return True
        except (AttributeError, requests.exceptions.RequestException):
            self.build_shares_detail(scode, sdb)
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
        for share_id in self.shares_earning_details:
            if share_id not in shares_value_DB.keys():
                continue
            timestamps = list(self.shares_earning_details[share_id].keys())
            timestamps.sort(reverse=True)
            latest = self.shares_earning_details[share_id][timestamps[0]]
            latest_date = datetime.fromtimestamp(float(timestamps[0]))
            if latest_date.month != 12:
                last_ts = datetime(latest_date.year-1, latest_date.month, latest_date.day).timestamp()
                last_year_dec_ts = datetime(latest_date.year-1, 12, 31).timestamp()
                last_year_dec_pe = self.shares_earning_details[share_id][str(last_year_dec_ts)]
                latest = last_year_dec_pe - self.shares_earning_details[share_id][str(last_ts)] + latest
            tips += '{:^8} \t{:.2f} [{:.1%}]\n'.format(shares_value_DB[share_id]['name'],
                                                        shares_value_DB[share_id]['price'] / latest,
                                                        self.known_shares[share_id])
            shares_profits_list[share_id] = latest
        sum_of_profits = 0
        sum_of_prices = 0
        for share_id in shares_profits_list:
            if shares_value_DB[share_id]['price']:
                sum_of_profits += shares_profits_list[share_id] * self.known_shares[share_id]
                sum_of_prices += shares_value_DB[share_id]['price'] * self.known_shares[share_id]
            
        try:
            return (round(sum_of_prices/ sum_of_profits, 2), tips)
        except ZeroDivisionError:
            return

    def estimate(self, shares_value_DB):
        tempo = 0
        total_known_shares_ratio = 0
        for share in self.known_shares:
            if share in shares_value_DB.keys() and shares_value_DB[share]:
                tempo += shares_value_DB[share]['change'] * self.known_shares[share]
                total_known_shares_ratio += self.known_shares[share]
        return tempo / total_known_shares_ratio * self.shares_in_total

    def get_shares_code(self):
        return list(self.known_shares.keys())


def scratch_shares(scodes):
    def cook_code(scode):
        if '60' in scode[:2]:
            return 's_sh' + scode
        else:
            return 's_sz' + scode
    cooked_codes = [cook_code(x) for x in scodes]
    cooked_codes.sort()
    try:
        url = 'http://hq.sinajs.cn/list=' + ','.join(cooked_codes)
        _share_data = requests.get(url)
    except requests.exceptions.RequestException:
        return
    if not _share_data.ok:
        return
    sdb = {}
    lines = _share_data.text.split('\n')
    for line in lines:
        try:
            code, price, change = re.search(r'_s_\w\w(.*)=".*?,(.*?),.*?,(.*?),', line).groups()
            sdb[code] = {'price': float(price), 'change': float(change)}
        except AttributeError:
            pass
    return sdb


def scratch_all_funds():
    try:
        page = requests.get('https://fundmobapi.eastmoney.com/FundMApi/FundRankNewList.ashx?'
                            'pagesize=10000&deviceid=Wap&plat=Wap&product=EFund&version=2.0.0', timeout=10).content
        funds = json.loads(page)
        return {x['FCODE']: x for x in funds['Datas'] if x['FUNDTYPE'] in ('001', '002')}
        # ret = []
        # for each in funds['Datas']:
        #     if each['FUNDTYPE'] in ('001', '002') and each['BUY']:
        #         ret.append(each)
        # return ret
    except requests.exceptions.RequestException:
        scratch_all_funds()
# def scratch_pe(scodes, limits=10):
#     # url = 'http://quotes.money.163.com/f10/zycwzb_{}.html'
#     url = 'http://data.eastmoney.com/bbsj/stock{}/yjbb.html'
#     ret = {}
#
#     async def fetch(session, s_url, scode):
#         try:
#             async with session.get(s_url) as resp:
#                 pbytes = await resp.read()
#                 page_content = pbytes.decode('gb2312')
#                 data = re.search(r'pages:\d,data:(\[.*\])', page_content).group(1)
#                 data = [x.split(',') for x in data]
#                 _ret = {}
#                 for each in data:
#                     yy, mm, dd = each[-2].split('-')
#                     date_ts = datetime(int(yy), int(mm), int(dd)).timestamp()
#                     _ret[date_ts] = float(each[2])
#                 ret[scode] = _ret
#                 # reqbytes = await resp.read()
#                 # _ret = {}
#                 # psoup = bsoup(reqbytes, 'html5lib')
#                 # chart = psoup.find('table', {'class': 'scr_table'}).find_all('tr')
#                 # for date_str, profits in zip(chart[0].find_all('th'), chart[1].find_all('td')):
#                 #     if profits.text == '--':
#                 #         continue
#                 #     year, month, day = date_str.text.split('-')
#                 #     datestamp = datetime(year=int(year), month=int(month), day=int(day))
#                 #     _ret[datestamp.timestamp()] = float(profits.text)
#                 # ret[scode] = _ret
#         except Exception as err:
#             print('{} fetching err: {}; link: {}'.format(scode, err, s_url))
#             await fetch(session, s_url, scode)
#
#     async def loader(sem, session, scode):
#         s_url = url.format(scode[-6:])
#         async with sem:
#             await fetch(session, s_url, scode)
#
#     async def run():
#         tasks = []
#         sem = asyncio.Semaphore(limits)
#         async with aiohttp.ClientSession() as session:
#             for each in scodes:
#                 task = asyncio.ensure_future(loader(sem, session, each))
#                 tasks.append(task)
#             await asyncio.gather(*tasks)
#
#     loop = asyncio.get_event_loop()
#     future = asyncio.ensure_future(run())
#     loop.run_until_complete(future)
#
#     return ret

def filter_goodfund(funds, step, percent):
    ret = funds
    steps = ('SYL_Z', 'SYL_Y', 'SYL_3Y', 'SYL_6Y', 'SYL_1N', 'SYL_2N', 'SYL_3N', 'SYL_5N')
    for _n, _s in enumerate(steps):
        if _n >= step and ret:
            break
        ret.sort(key=lambda x: x[_s], reverse=True)
        ret = ret[:int(percent / 100 * len(ret))]
    return ret


def display_funds(funds):
    print(('{:28}' + '{:16}' * 9).format('名称', '日涨', '周涨', '月涨', '季度', '半年', '一年', '两年', '三年', '五年'))
    for each in funds:
        change = []
        for _step in ('RZDF', 'SYL_Z', 'SYL_Y', 'SYL_3Y', 'SYL_6Y', 'SYL_1N', 'SYL_2N', 'SYL_3N', 'SYL_5N'):
            try:
                change.append(float(each[_step]) / 100)
            except ValueError:
                change.append(0)
        print(('{:15}' + '{:17.2%}' * 9).format(
            '{}({})'.format(each['SHORTNAME'][:6], each['FCODE']),
            *change))
    print('Totally {} funds matches'.format(len(funds)))


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

if __name__ == '__main__':
    # with open('Stock_Finatial_Reports.json') as f:
    #     F_STOCKS_DB = json.loads(f.read())
    #
    # fund, shares = catch_shares_from_funds(('420003', '001938', '001811', '000478', '001662', '163110', '001897', '540006',
    #                                         '233009', '229002', '161005', '519983', '210004', '000577', '001592', '210009',
    #                                         '160212', '519066', '519156'))
    # shares_db = scratch_shares(shares)
    # for each in [(x.name, round(x.pe(shares_db), 4)) for x in fund]:
    #     print(each)

    # men = scratch_managers()
    # men.sort(key=lambda x: x[2])
    # for each in men:
    #     print(each)

    # focused_funds = ('540006', '001938', '001811', '000577', '420003', '160212', '000478', '210009')
    # funds_obj, share_codes = catch_shares_from_funds(focused_funds)
    #
    # while True:
    #     shares_db = scratch_shares(share_codes)
    #     print(time.asctime().split(' ')[3], end='  ')
    #     for each in funds_obj:
    #         print('[{}] ({:.2%})'.format(each.name[:6], each.estimate(shares_db)), end=' | ')
    #     print()
    #     time.sleep(10)

    m = ManFilter()
    m.start()
