"""
    从天天基金网，根据基金的排名情况，选出业绩长期优良的基金，然后下载其数据，最后制作成html文件以供查阅。
    作者： Fyoung Lix
    日期： 2016年11月2日
    版本： v1.0
"""
# -*- coding: utf-8 -*-
import requests
import json
import re
import time
from json import decoder
from datetime import datetime
from bs4 import BeautifulSoup as bsoup
from PyQt5.QtCore import QThread, pyqtSignal


class FundsDownloader(QThread):
    result_broadcast = pyqtSignal(list)
    send_to_display_info = pyqtSignal(str)
    send_to_display_info2 = pyqtSignal(tuple)

    def __init__(self, fid=None, favored=False, parent=None):
        super(FundsDownloader, self).__init__(parent)
        self.fid = fid
        self.favored = favored

    def run(self):
        self.result_broadcast.emit(self.fromFundID(self.fid))
        self.emitInfo('处理完毕')

    def _get_favorite(self):
        try:
            with open('favorite.json', 'r') as f:
                all_fvr_from_file = json.loads(f.read())
        except FileExistsError:
            with open('favorite.json', 'w') as f:
                return
        self.emitInfo('开始加载收藏基金数据')
        ret = self.fromFundID(all_fvr_from_file)
        for each in ret:
            each.append('已收藏')
        return ret

    def fromFundID(self, ids):
        ret = []
        n_ids = 0
        self.send_to_display_info2.emit((n_ids, len(ids)))
        for fvr in ids:
            while True:
                try:
                    req = requests.get('http://fund.eastmoney.com/{}.html'.format(fvr))
                    break
                except (ConnectionError, TimeoutError):
                    print('Bad connection, try again.')
            if req.ok is False:
                return []
            soup = bsoup(req.content, 'lxml')
            _inc = [x.text[:-1] for x in soup.find('li', {'id': 'increaseAmount_stage'}).findAll('tr')[1].findAll('td')]
            tp = [fvr, soup.find('div', {'class': 'fundDetail-tit'}).text.split('(')[0], '', '']
            tp.extend([soup.find('dl', {'class': 'dataItem02'}).find('dd', {'class': 'dataNums'}).span.text,
                       soup.find('dl', {'class': 'dataItem03'}).find('dd', {'class': 'dataNums'}).span.text,
                       soup.find('dl', {'class': 'dataItem02'}).find('dd', {
                           'class': 'dataNums'}).span.find_next_sibling().text[:-1]])
            for _n in range(1, 9):
                if _n == 5:
                    continue
                try:
                    tp.append(_inc[_n])
                except IndexError:
                    tp.append('')
            ret.append(tp)
            n_ids += 1
            self.send_to_display_info2.emit((n_ids, len(ids)))
        return self._get_addition_info(ret)

    def _get_addition_info(self, funds):
        n_finished = 0
        self.send_to_display_info2.emit((n_finished, len(funds)))
        for each in funds:
            self.emitInfo('获取 {} 详细信息'.format(each[1]))
            add = self._dl_fund_info(each[0])
            each[2] = add['score']
            each[3] = add['manager']
            each.insert(6, 'null')
            each.append(add['scale'])
            if self.favored:
                each.append('已收藏')
            n_finished += 1
            self.send_to_display_info2.emit((n_finished, len(funds)))
        return funds

    def _dl_fund_info(self, fid):
        """
            下载基金详细情况
        """
        cooked_info = None
        while True:
            try:
                cooked_info = self._beautiful_pages(requests.get("http://fund.eastmoney.com/pingzhongdata/{}.js"
                                                             .format(fid), timeout=5).text)
                break
            except (ConnectionError, TimeoutError):
                print('Bad connection, try again.')
        # 业绩评分
        fund_score = cooked_info['Data_performanceEvaluation']['avr']
        # 基金经理, 经理评分
        managers = [(each['id'], each['name'], each['power']['avr']) for each in cooked_info['Data_currentFundManager']]
        # 基金规模
        scales = cooked_info['Data_fluctuationScale']['series'][-1]['y']
        return {'score': fund_score, 'manager': managers, 'scale': scales}

    def _beautiful_pages(self, text):
        """
            对下载的基金详细情况进行裁减处理
        """
        ret = text.split(';')
        retDict = {}
        for each in ret:
            try:
                e_list = each.split('var')[1].strip().split('=')
                try:
                    retDict[e_list[0].strip()] = json.loads(e_list[1].strip())
                except decoder.JSONDecodeError:
                    retDict[e_list[0].strip()] = e_list[1].strip()
            except IndexError:
                continue
        return retDict

    def emitInfo(self, text):
        self.send_to_display_info.emit('[{}] {}'.format(datetime.now().strftime('%H:%M:%S'), text))


class FundSelctor(FundsDownloader):
    def __init__(self, kw, rank, favor, parent=None):
        super(FundSelctor, self).__init__(parent=parent)
        self.history_kw = kw
        self.rank = rank
        self.all_funds = None
        self.num_funds = 0
        self.favor_funds = favor
        self.selected_funds = []

    def run(self):
        self._dl_data()
        self._get_list()
        self.selected_funds = self._get_addition_info(self.selected_funds)
        self.result_broadcast.emit(self.selected_funds)
        self.emitInfo('处理完毕')

    def _dl_data(self):
        """
            搜索所有基金数据
        """
        self.emitInfo('下载所有基金数据')
        while True:
            try:
                req = requests.post('http://fund.eastmoney.com/data/rankhandler.aspx', data={'op': 'ph', 'pn': 10000}).text
                break
            except BaseException:
                print('Bad connection, try again.')
        self.emitInfo('下载完毕')
        req = req.split('=')[1]
        # 截出[]之间的数据，然后去头去尾，最后根据","来分切成一个list
        datas = req[req.find('['):req.rfind(']') + 1][2:-2].split('","')
        self.all_funds = self._funds_filter([e.split(',') for e in datas])
        self.num_funds = len(self.all_funds)

    def _funds_filter(self, funds):
        # 去掉不想要的基金类型，以后可增加成可选功能，现在暂时不用
        f = []
        for each in funds:
            if 'QDII' in each[1] or '纳斯达克' in each[1] or '标普' in each[1] or '全球' in each[1] or '美国' in each[1]\
                    or '德国' in each[1] or '国际' in each[1]:
                continue
            if '债' in each[1]:
                continue
            if '保本' in each[1]:
                continue
            # 统一保存成所需要的长度，以区别是否收藏了该基金
            f.append(each[:14])
        return f

    def _get_list(self):
        """
            接收一个排名百分比数值，一个List的搜索关键字
            返回一个提炼基金名单
        """
        his = ['周涨幅', '月涨幅', '季涨幅', '半年涨幅', '一年涨幅', '两年涨幅', '三年涨幅']
        compr = None
        for each in his[:his.index(self.history_kw)+1]:
            self.emitInfo('{} 排名中'.format(each))
            if compr is None:
                compr = self._trunc_data(self._rank_fund(each))
            else:
                compr = self._compare_data(compr, self._trunc_data(self._rank_fund(each)))
        # 排查已经在favor 列表里面的
        for each in compr:
            if each[0] in self.favor_funds:
                continue
            self.selected_funds.append(each)

    def _rank_fund(self, rankey):
        """
            根据关键字对基金进行排序
        """
        k = {'周涨幅': 7, '月涨幅': 8, '季涨幅': 9, '半年涨幅': 10, '一年涨幅': 11, '两年涨幅': 12, '三年涨幅': 13}
        filtered_list = filter(lambda x: x[k[rankey]], self.all_funds)
        return sorted(filtered_list, key=lambda x: float(x[k[rankey]]), reverse=True)

    def _trunc_data(self, data):
        """
            根据提供的排名情况，进行靠前百分比筛选
        """
        return data[:int(self.num_funds / 100 * self.rank)]

    def _compare_data(self, datal, datar):
        """
            比较两个List，返回其交集
        """
        return [ea for ea in datal if ea in datar]


class FundRefresher(QThread):
    result_feedback = pyqtSignal(tuple)

    def __init__(self, parent=None):
        super(FundRefresher, self).__init__(parent)
        self.funds = []

    def run(self):
        while True:
            self.result_feedback.emit(('Show Me New',))
            time.sleep(0.5)
            for each in self.funds:
                while True:
                    try:
                        url = 'http://fundgz.1234567.com.cn/js/{}.js'.format(each)
                        req_text = requests.get(url, timeout=5).text
                        break
                    except (ConnectionError, TimeoutError):
                        print('Bad connection, try again.')
                json_d = json.loads(req_text[req_text.find('{'):req_text.rfind(')')])
                self.result_feedback.emit((each, json_d['gszzl'], json_d['dwjz'], json_d['jzrq']))
            time.sleep(2.5)
            if isTradingTime() is False:
                self.result_feedback.emit((None,))
                break

    def setFunds(self, funds):
        self.funds = funds


class StockRefresher(QThread):
    stock_val_brodcast = pyqtSignal(str, name='stock_value')

    def __init__(self, parent=None):
        super(StockRefresher, self).__init__(parent)
        self.stockUrl = \
            'http://hq.sinajs.cn/list=s_sh000001,s_sz399001,s_sz399006,s_sz399905,s_sz399300,s_sz399401'

    def run(self):
        self.refreshing()

    def refreshing(self):
        while True:
            ret = ''
            while True:
                try:
                    rst = requests.get(self.stockUrl, timeout=5).text.split(';\n')
                    rst = [x[x.find('"')+1:x.rfind('"')].split(',') for x in rst]
                    break
                except (ConnectionError, TimeoutError):
                    print('Bad connection, try again.')
            for index, each in enumerate(['sh000001', 'sz399001', 'sz399006', 'sz399905', 'sz399300', 'sz399401']):
                ret += self.drawColor(rst[index], each)
            self.stock_val_brodcast.emit(ret)
            if isTradingTime() is False:
                return
            time.sleep(5)

    def drawColor(self, val, code):
        name = {'sh000001': '上证', 'sz399001': '深证', 'sz399006': '创业',
                'sz399905': '中证500', 'sz399300': '沪深300', 'sz399401': '中小'}
        color = 'red'
        if '-' in val[3]:
            color = 'green'
            val[3] = val[3].replace('-', '↓')
        else:
            val[3] = '↑' + val[3]
        return '{}: <font color="{}">{}{}{}%</font>{}'\
            .format(name[code], color, round(float(val[1]), 2), '&nbsp;'*4, val[3], '&nbsp;'*8)


def isTradingTime():
    if datetime.now().isoweekday() is 6 or datetime.now().isoweekday() is 7:
        return False
    if datetime.now().hour >= 15 or datetime.now().hour < 9:
        return False
    return True