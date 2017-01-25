"""
    从天天基金网，根据基金的排名情况，选出业绩长期优良的基金，然后下载其数据，最后制作成html文件以供查阅。
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
from PyQt5.QtCore import QProcess, pyqtSignal
import os
import asyncio
import aiohttp

FUNDS_UPDATE_TIMER = 30
STOCKS_UPDATA_TIMER = 5


class Tasks:
    FundsFull = 1
    FundsEst = 2
    FundsVal = 3
    Stocks = 4


class FundsManager(QProcess):
    response_feedback = pyqtSignal(tuple, name='')

    def __init__(self):
        super().__init__()
        self.__update_list = []
        self.funds_timer = self.startTimer(FUNDS_UPDATE_TIMER*1000)
        self.stocks_timer = self.startTimer(STOCKS_UPDATA_TIMER*1000)

    def set_update_list(self, _list):
        self.__update_list = _list

    def funds_init_info(self, tasks):
        if not isinstance(tasks, list):
            return
        # result 返回的是含有tuple的list，tuple 0为fund代码， 1为页面的binary。
        result = []
        asyncio.get_event_loop() \
            .run_until_complete(FundsManager.doasytask(tasks, result, 'http://fund.eastmoney.com/pingzhongdata/{}.js'))
        rawinfos = {each[0]: [each[1], ] for each in result}
        result.clear()
        asyncio.get_event_loop() \
            .run_until_complete(FundsManager.doasytask(tasks, result, 'http://fund.eastmoney.com/{}.html'))
        for each in result:
            rawinfos[each[0]].append(each[1])

        def beautiful_pages(text):
            """
                对下载的基金详细情况进行裁减处理
            """
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

        ret = []
        for fid in rawinfos:
            sobj0, sobj1 = beautiful_pages(rawinfos[fid][0].decode()), BeautifulSoup(rawinfos[fid][1], 'lxml')
            ret.append({
                'fund_id': fid,
                'fund_name': sobj1.find('div', {'class': 'fundDetail-tit'}).text.split('(')[0],
                'est_change': sobj1.find('dl', {'class': 'dataItem01'}).find('dd', {'class': 'dataNums'}).findAll('span')[-1].text[:-1],
                'current_val': sobj1.find('dl', {'class': 'dataItem02'}).find('dd', {'class': 'dataNums'}).span.text,
                'latest_change': sobj1.find('dl', {'class': 'dataItem02'}).find('dd', {'class': 'dataNums'}).findAll('span')[-1].text[:-1],
                'total_val': sobj1.find('dl', {'class': 'dataItem03'}).find('dd', {'class': 'dataNums'}).span.text,
                'performance': [x.text[:-1].strip() for x in sobj1.find('li', {'id': 'increaseAmount_stage'}).findAll('tr')[1].findAll('td')][1:],
                'fund_score': sobj0['Data_performanceEvaluation']['avr'],
                'managers': [(each['id'], each['name'], each['power']['avr']) for each in sobj0['Data_currentFundManager']],
                'scales': sobj0['Data_fluctuationScale']['series'][-1]['y']})
        self.response_feedback.emit((Tasks.FundsFull, ret))

    def timer_control(self, status):
        if status:
            if not self.funds_timer:
                self.funds_timer = self.startTimer(FUNDS_UPDATE_TIMER * 1000)
            if not self.stocks_timer:
                self.stocks_timer = self.startTimer(STOCKS_UPDATA_TIMER * 1000)
        else:
            if self.funds_timer:
                self.killTimer(self.funds_timer)
                self.funds_timer = None
            if self.stocks_timer:
                self.killTimer(self.stocks_timer)
                self.stocks_timer = None

    def timerEvent(self, QTimerEvent):
        # result 返回的是含有tuple的list，tuple 0为fund代码， 1为页面的binary。
        result = []
        # timer 编号判断
        if QTimerEvent.timerId() == self.funds_timer and self.__update_list:
            # 交易时段判断
            if self.isTradingTime():
                asyncio.get_event_loop().run_until_complete(
                    self.doasytask(self.__update_list, result, 'http://fundgz.1234567.com.cn/js/{}.js'))
                ret = []
                for each in result:
                    try:
                        est_val = re.search(r'"gszzl":"(.*?)"', each[1].decode(errors='ignore')).group(1)
                        ret.append((each[0], est_val))
                    except AttributeError:
                        continue
                self.response_feedback.emit((Tasks.FundsEst, ret))
            else:
                asyncio.get_event_loop().run_until_complete(
                    self.doasytask(self.__update_list, result, 'http://fund.eastmoney.com/{}.html'))
                ret = []
                for each in result:
                    try:
                        _t = re.search(
                            r'<dl class="dataItem02">.+?<p>.+?(\d{4}-\d{2}-\d{2}).*?dataNums.*?(\d+\.\d+).*?([+|-]?\d+\.\d+)%',
                            each[1].decode(errors='ignore')).groups()
                    except TypeError:
                        continue
                    if datetime.now().strftime('%Y-%m-%d') == _t[0]:
                        ret.append((each[0], _t[1], _t[2]))
                if ret:
                    self.response_feedback.emit((Tasks.FundsVal, ret))
        elif QTimerEvent.timerId() == self.stocks_timer:
            if not self.isTradingTime():
                return
            asyncio.get_event_loop().run_until_complete(
                self.doasytask((None, ), result,
                               'http://hq.sinajs.cn/list=s_sh000001,s_sz399001,s_sz399006,s_sz399905,s_sz399300,s_sz399401'))
            ret = ''
            raws = [x.split(',')[:4] for x in re.findall(r'"(.*)"', result[0][1].decode('GBK', errors='ignore'))]
            for each in raws:
                color = 'red'
                if '-' in each[2]:
                    color = 'green'
                else:
                    each[3] = '+' + each[3]
                each[2] = '[{}]'.format(each[2])
                ret += '{}: <font color="{}">{}%</font>{}'.format(each[0], color, '&nbsp;'.join(each[1:]), '&nbsp;'*4)
            self.response_feedback.emit((Tasks.Stocks, ret))

    def get_filtered_list(self, kw, rank):
        result = []
        asyncio.get_event_loop().run_until_complete(
            self.doasytask((None,), result, 'http://fund.eastmoney.com/data/rankhandler.aspx?op=ph&pn=10000'))
        try:
            fr = FundsFilter(kw, rank, result[0][1].decode())
            rst = fr.filter()
            tasks = [x[0] for x in rst if x[0] not in self.__update_list]
            self.funds_init_info(tasks)
        except TypeError:
            self.response_feedback.emit((Tasks.FundsFull, None))

    @staticmethod
    async def doasytask(tasks, result, url):
        async def geturl(sem, fid):
            async with sem:
                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.get(url.format(fid), timeout=10) as resp:
                            ret = await resp.read()
                            return fid, ret
                    except (asyncio.TimeoutError, aiohttp.errors.ClientError):
                        pass
        resps = []
        sem = asyncio.Semaphore(8)
        for fid in tasks:
            resps.append(asyncio.ensure_future(geturl(sem, fid)))
        result.extend(await asyncio.gather(*resps))

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
