from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QComboBox, QSlider, QLabel, QTableWidget, \
    QTableWidgetItem, QPushButton, QHeaderView, QLineEdit, QMessageBox
from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.Qt import QDesktopServices
import gf_core4
import json, re
from datetime import datetime


class GF_MainWindow(QWidget):
    with open('Managers.json') as f:
        Managers = json.loads(f.read())
    FUNDS_DETAIL = gf_core4.scratch_all_funds()

    def __init__(self, parent=None):
        super(GF_MainWindow, self).__init__(parent)
        self.setWindowTitle('搞个好基基 by 羊习习')
        # self.setMinimumSize(1440, 480)
        # 当前显示基金池
        self.Funds_Pool = {}
        self.Favorite_Funds = []
        self.marketsDB = {}

        # 开始GUI布局
        mlayout = QVBoxLayout()
        optionlayout = QHBoxLayout()
        optionlayout.addWidget(QLabel('历史排名'))
        self.history_combox = QComboBox()
        for each in ('一周', '一月', '季度', '半年', '一年', '两年', '三年', '五年'):
            self.history_combox.addItem(each)
        optionlayout.addWidget(self.history_combox)
        optionlayout.addWidget(QLabel('排名比率'))
        self.rank_slider = QSlider(Qt.Horizontal)
        self.rank_slider.setRange(10, 80)
        self.rank_slider.setValue(25)
        self.rank_slider.valueChanged.connect(lambda x: self.rank_label.setText(str(x)))
        optionlayout.addWidget(self.rank_slider)
        self.rank_label = QLabel()
        self.rank_label.setFixedWidth(30)
        self.rank_label.setText(str(self.rank_slider.value()))
        optionlayout.addWidget(self.rank_label)
        self.start_btn = QPushButton('开始筛选')
        self.start_btn.setFixedWidth(100)
        self.start_btn.clicked.connect(self.startClicked)
        optionlayout.addWidget(self.start_btn)
        self.manager_filter_btn = QPushButton('按经理筛选')
        self.manager_filter_btn.setFixedWidth(100)
        self.manager_filter_btn.clicked.connect(self.manager_filter)
        optionlayout.addWidget(self.manager_filter_btn)
        optionlayout.addStretch(1)

        midlayout = QHBoxLayout()
        # self.syn_btn = QPushButton('更新中...')
        # self.syn_btn.setFixedWidth(100)
        # self.syn_btn.clicked.connect(self.synClicked)
        # midlayout.addWidget(self.syn_btn)
        self.refresh_funds_details_btn = QPushButton('刷新净值')
        self.refresh_funds_details_btn.setFixedWidth(100)
        self.refresh_funds_details_btn.clicked.connect(self.refresh_funds_details)
        midlayout.addWidget(self.refresh_funds_details_btn)
        self.load_favor_btn = QPushButton('加载收藏')
        self.load_favor_btn.setFixedWidth(100)
        self.load_favor_btn.clicked.connect(self.loadFavor)
        midlayout.addWidget(self.load_favor_btn)
        self.clear_btn = QPushButton('清空')
        self.clear_btn.setFixedWidth(100)
        self.clear_btn.clicked.connect(self.clearAll)
        midlayout.addWidget(self.clear_btn)
        self.info_display = QLabel()
        self.info_display2 = QLabel()
        self.info_display2.setFixedWidth(50)
        midlayout.addWidget(self.info_display)
        midlayout.addWidget(self.info_display2)
        fid_label = QLabel('基金代码')
        fid_label.setFixedWidth(70)
        midlayout.addWidget(fid_label)
        self.search_line = QLineEdit()
        self.search_line.setFixedWidth(100)
        self.search_btn = QPushButton('添加')
        self.search_btn.setFixedWidth(50)
        self.search_btn.clicked.connect(self.searchFund)
        midlayout.addWidget(self.search_line)
        midlayout.addWidget(self.search_btn)

        self.display_table = MyTable()

        self.display_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.display_table.setSortingEnabled(True)
        self.display_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.display_table.itemClicked.connect(self.displaySelectedFund)
        self.display_table.itemClicked.connect(self.tableItemClicked)
        self.display_table.rightClicked.connect(self.tableItemClicked)
        self.display_table.setSelectionMode(QTableWidget.SingleSelection)
        self.display_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.display_table.setColumnCount(17)
        self.display_table.setHorizontalHeaderLabels(['基金名称', '评分', '经理', '净值', '估算',
                                                      '日涨', '周涨', '月涨', '季涨', '半年', '一年',
                                                      '两年', '三年', '五年', '规模', '市盈', '收藏'])

        mlayout.addLayout(optionlayout)
        mlayout.addLayout(midlayout)
        mlayout.addWidget(self.display_table)

        self.marketsDisplay = QLabel()
        mlayout.addWidget(self.marketsDisplay)

        self.setLayout(mlayout)

        self.the_markets_updater = gf_core4.Market_Updater()
        self.the_markets_updater.markets_singal.connect(lambda x: self.marketsDB.update(x))
        self.fund_builder = gf_core4.FundsBuilder(self.FUNDS_DETAIL)
        self.fund_builder.funds_obj_signals.connect(self.placeFunds)
        self.fund_builder.stocks_appender.connect(self.the_markets_updater.extend_stocks)
        self.fund_builder.progress_signals.connect(lambda x: self.info_display.setText(x))
        self.fund_builder.start()
        self.the_markets_timer = self.startTimer(10000)
        # # 载入收藏基金
        # self.updater = gf_core4.Updater()
        # self.updater.fund_sender.connect(self.placeFunds)
        # self.updater.market_sender.connect(lambda x: self.marketsDisplay.setText(x))
        # self.updater.start()

    def cook_the_markets(self):
        markets_str = ''
        if self.marketsDB:
            for each in ['s_sh000001', 's_sz399001', 's_sz399300', 's_sz399905', 's_sz399401', 's_sz399006']:
                try:
                    this = self.marketsDB[each]
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

    def timerEvent(self, QTimerEvent):
        if QTimerEvent.timerId() == self.the_markets_timer:
            self.marketsDB = self.the_markets_updater.results
            text = self.cook_the_markets()
            self.marketsDisplay.setText(text)
            if self.Funds_Pool:
                self.updateFunds()

    def refresh_funds_details(self):
        self.FUNDS_DETAIL = gf_core4.scratch_all_funds()
        self.start_btn.setEnabled(True)
        self.load_favor_btn.setEnabled(True)
        self.display_table.setSortingEnabled(False)
        self.display_table.setRowCount(len(self.Funds_Pool))
        for fund_id in self.Funds_Pool:
            row = self.isFundInTable(fund_id)
            if row == -1:
                continue
            fund = self.Funds_Pool[fund_id]

            cur_val = MyTableItem('{} [{}]'.format(fund.details['DWJZ'], fund.details['LJJZ']))
            self.display_table.setItem(row, 3, cur_val)

            is_new = 'NEW' if fund.details['FSRQ'] in datetime.now().isoformat() else ''
            latest_chg = MyTableItem('{}% {}'.format(fund.details['RZDF'], is_new))
            color = self.setValueColor(float(fund.details['RZDF']))
            latest_chg.setForeground(color)
            cur_val.setForeground(color)
            self.display_table.setItem(row, 5, latest_chg)

        self._resizeTable()
        self.display_table.setSortingEnabled(True)

    def loadFavor(self):
        self.load_favor_btn.setEnabled(False)
        # 从json文档中加载已经保存的基金代码
        try:
            with open('Favorite_Funds.json', 'r') as f:
                favors = json.loads(f.read())
                self.Favorite_Funds = favors
        except FileExistsError:
            return
        favors = [x for x in favors if x not in self.Funds_Pool.keys()]
        self.fund_builder.funds.extend(favors)

    def displaySelectedFund(self, fund_item):
        # TODO display fund information locally
        pass

    def startClicked(self):
        self.start_btn.setEnabled(False)
        steps = ('SYL_Z', 'SYL_Y', 'SYL_3Y', 'SYL_6Y', 'SYL_1N', 'SYL_2N', 'SYL_3N', 'SYL_5N')
        step = self.history_combox.currentIndex()
        percent = self.rank_slider.value()
        ret = [self.FUNDS_DETAIL[x] for x in self.FUNDS_DETAIL]
        for _n, _s in enumerate(steps):
            if _n >= step and ret:
                break
            ret.sort(key=lambda x: x[_s], reverse=True)
            ret = ret[:int(percent / 100 * len(ret))]
        self.fund_builder.funds.extend([x['FCODE'] for x in ret if x['BUY']])

    def manager_filter(self):
        m_filter = gf_core4.ManFilter()
        m_filter.funds_signal.connect(lambda x: self.fund_builder.funds.extend(x))
        m_filter.display_managers_signal.connect(lambda x: self.info_display.setText(x))
        m_filter.start()

    # def synClicked(self):
    #     if '更新中' in self.syn_btn.text():
    #         self.syn_btn.setText('更新停止')
    #         self.updater.stopTimer()
    #     else:
    #         self.syn_btn.setText('更新中...')
    #         self.updater.startUpdateTimer()

    def placeFunds(self, funds_obj):
        self.Funds_Pool.update(funds_obj)
        self.display_table.setSortingEnabled(False)
        self.display_table.setRowCount(len(self.Funds_Pool))
        # starting_row = self.display_table.rowCount()
        for row, fund_id in enumerate(self.Funds_Pool):
            # 单条基金信息, 按column位置铺
            fund = self.Funds_Pool[fund_id]
            name = QTableWidgetItem('[{}] {}'.format(fund_id, fund.details['SHORTNAME']))
            name.setToolTip(fund.style())
            name.setData(1000, fund_id)
            self.display_table.setItem(row, 0, name)

            score = MyTableItem()
            score.setText(str(fund.details['Score']))
            score.setTextAlignment(Qt.AlignCenter)
            self.display_table.setItem(row, 1, score)

            manager = MyTableItem()
            man_text_tooltip = ''
            best = fund.details['Managers'][0]
            def cook_manager(mid):
                ret = ''
                ret += '[{}] {} ({})'\
                    .format(mid, self.Managers[mid]['Datas']['MGRNAME'], self.Managers[mid]['Datas']['JJGS'])
                ret += '\n\t管理规模: {}亿\n\t经验: {}天'\
                    .format(round(float(self.Managers[mid]['Datas']['NETNAV'])/100000000, 2),
                            self.Managers[mid]['Datas']['TOTALDAYS'])
                ret += '\n\t最大回报: {:.2%}\n\t最大回撤: {:.2%}\n\t平均年化: {}%\n'\
                    .format(float(self.Managers[mid]['Datas']['FMAXEARN1']),
                            float(self.Managers[mid]['Datas']['FMAXRETRA1']),
                            self.Managers[mid]['Datas']['YIELDSE'])
                ret += '\n'
                return ret
            for man in fund.details['Managers']:
                man_text_tooltip += cook_manager(man['id'])
                if man['power']['data'][1] and best['power']['data'][1]:
                    if man['power']['data'][1] > best['power']['data'][1]:
                        best = man
                elif best['power']['data'][1] is None:
                    best = man
            man_text_display = '{} {}'.format(best['name'], best['power']['data'][1]) \
                if best['power']['data'][1] else '{} 0.0'.format(best['name'])
            if len(fund.details['Managers']) > 1:
                man_text_display += ' +'
            manager.setText(man_text_display)
            manager.setToolTip(man_text_tooltip[:-1])
            # manager.setData(1000, fund['Managers'])
            self.display_table.setItem(row, 2, manager)

            cur_val = MyTableItem('{} [{}]'.format(fund.details['DWJZ'], fund.details['LJJZ']))
            self.display_table.setItem(row, 3, cur_val)

            es, missing = fund.estimate(self.marketsDB)
            if missing:
                self.the_markets_updater.extend_stocks(missing)
                print('Missing stocks:', missing)
            est_chg = MyTableItem('{}%'.format(es))
            est_chg.setForeground(self.setValueColor(es))
            est_chg.setTextAlignment(Qt.AlignCenter)
            self.display_table.setItem(row, 4, est_chg)

            is_new = 'NEW' if fund.details['FSRQ'] in datetime.now().isoformat() else ''
            latest_chg = MyTableItem('{}% {}'.format(fund.details['RZDF'], is_new))
            color = self.setValueColor(float(fund.details['RZDF']))
            latest_chg.setForeground(color)
            cur_val.setForeground(color)
            self.display_table.setItem(row, 5, latest_chg)

            for _col, _each in enumerate(('SYL_Z', 'SYL_Y', 'SYL_3Y', 'SYL_6Y', 'SYL_1N', 'SYL_2N', 'SYL_3N', 'SYL_5N')):
                if fund.details[_each]:
                    color = self.setValueColor(float(fund.details[_each]))
                    if not color:
                        continue
                    pf = MyTableItem('{}%'.format(round(float(fund.details[_each]), 2)))
                    pf.setForeground(color)
                    pf.setTextAlignment(Qt.AlignCenter)
                    self.display_table.setItem(row, _col + 6, pf)

            fund_scale = MyTableItem('{}亿'.format(fund.details['Scale']))
            fund_scale.setTextAlignment(Qt.AlignCenter)
            self.display_table.setItem(row, 14, fund_scale)

            avg, tips = fund.pe(self.marketsDB)
            fund_pe = MyTableItem(str(avg))
            fund_pe.setTextAlignment(Qt.AlignCenter)
            fund_pe.setToolTip(tips)
            self.display_table.setItem(row, 15, fund_pe)

            # fund_pb = MyTableItem(str(fund_id.avg_PB))
            # fund_pb.setTextAlignment(Qt.AlignCenter)
            # self.display_table.setItem(row, 17, fund_pb)

            is_favored = '收藏' if fund.details['FCODE'] not in self.Favorite_Funds else '已收藏'
            favored = QTableWidgetItem(is_favored)
            if is_favored == '已收藏':
                name.setForeground(Qt.darkRed)
                favored.setForeground(Qt.lightGray)
            self.display_table.setItem(row, 16, favored)
        self._resizeTable()
        self.display_table.setSortingEnabled(True)
        self.start_btn.setEnabled(True)
        self.load_favor_btn.setEnabled(True)

    def updateFunds(self):
        self.start_btn.setEnabled(True)
        self.load_favor_btn.setEnabled(True)
        self.display_table.setSortingEnabled(False)
        self.display_table.setRowCount(len(self.Funds_Pool))
        for fund_id in self.Funds_Pool:
            row = self.isFundInTable(fund_id)
            if row == -1:
                continue
            fund = self.Funds_Pool[fund_id]

            es, missing = fund.estimate(self.marketsDB)
            if missing:
                self.the_markets_updater.extend_stocks(missing)
                print('({}) Missing stocks:'.format(fund_id), missing)
            est_chg = MyTableItem('{}%'.format(es))
            est_chg.setForeground(self.setValueColor(es))
            est_chg.setTextAlignment(Qt.AlignCenter)
            self.display_table.setItem(row, 4, est_chg)

            avg, tips = fund.pe(self.marketsDB)
            fund_pe = MyTableItem(str(avg))
            fund_pe.setTextAlignment(Qt.AlignCenter)
            fund_pe.setToolTip(tips)
            self.display_table.setItem(row, 15, fund_pe)

        self._resizeTable()
        self.display_table.setSortingEnabled(True)

    def isFundInTable(self, fund_id):
        rows = self.display_table.rowCount()
        for row in range(rows):
            if fund_id == self.display_table.item(row, 0).data(1000):
                return row
        return -1
    #
    # def updateFundItem(self, row, fund):
    #     fund.calculate_averages()
    #     self.display_table.item(row, 5).setText(fund.estimate)
    #     color = self.setValueColor(fund.estimate)
    #     self.display_table.item(row, 5).setForeground(color)
    #     is_new = 'NEW' if fund.fresh else ''
    #     self.display_table.item(row, 6).setText(fund.latest_change + '%' + is_new)
    #     color = self.setValueColor(fund.latest_change)
    #     self.display_table.item(row, 6).setForeground(color)
    #     self.display_table.item(row, 3).setText(fund.current_value)
    #     self.display_table.item(row, 3).setForeground(color)
    #     self.display_table.item(row, 4).setText(fund.total_value)
    #     self.display_table.item(row, 4).setForeground(color)
    #     self.display_table.item(row, 16).setText(str(round(fund.avg_PE, 2)))
    #     self.display_table.item(row, 17).setText(str(round(fund.avg_PB, 2)))
    #     stocks_tooltip = ''
    #     for stock in fund.stocks:
    #         stocks_tooltip += '({}) [{}] {} 价格:{}\t市盈率:{:.1f}\t市净率:{:.1f}\t量比:{}\n'\
    #             .format(stock.ratio, stock.id, stock.name, stock.price, stock.PE, stock.PB, stock.QR)
    #     self.display_table.item(row, 16).setToolTip(stocks_tooltip)
    #     self.display_table.item(row, 17).setToolTip(stocks_tooltip)

    # def placeNewFund(self, row, fund):
    #     pass

    def tableItemClicked(self, _item):
        self.display_table.setSortingEnabled(False)
        # 当表格被点击时
        if isinstance(_item, int):
            # 接收到右键自定义信号，删除
            row = _item
            del_id = self.display_table.item(row, 0).data(1000)
            if '已收藏' in self.display_table.item(row, 16).text():
                self.Favorite_Funds.remove(del_id)
            self.Funds_Pool.pop(del_id)
            self.display_table.removeRow(row)
        elif isinstance(_item, QTableWidgetItem):
            if _item.column() == 0:
                # 打开基金的详细信息链接 (本地打开, 开发中...)
                QDesktopServices().openUrl(QUrl('http://fund.eastmoney.com/{}.html'.format(_item.data(1000))))
            elif _item.column() == 2:
                QMessageBox().information(self, '经理信息', _item.toolTip(), QMessageBox.Ok)
            elif _item.column() == 16:
                # 收藏功能
                if _item.text() == '已收藏':
                    _item_0 = self.display_table.item(_item.row(), 0)
                    self.Favorite_Funds.remove(_item_0.data(1000))
                    with open('Favorite_Funds.json', 'w') as f:
                        f.write(json.dumps(self.Favorite_Funds))
                    _item_0.setForeground(Qt.black)
                    _item.setText('收藏')
                    _item.setForeground(Qt.black)
                elif _item.text() == '收藏':
                    _item_0 = self.display_table.item(_item.row(), 0)
                    self.Favorite_Funds.append(_item_0.data(1000))
                    with open('Favorite_Funds.json', 'w') as f:
                        f.write(json.dumps(self.Favorite_Funds))
                    _item_0.setForeground(Qt.darkRed)
                    _item.setText('已收藏')
                    _item.setForeground(Qt.gray)
        self.display_table.setSortingEnabled(True)

    def searchFund(self):
        # 搜索功能
        fid = self.search_line.text()
        if re.match(r'\d{6}', fid) is None:
            # 判断是否为有效6位代码
            self.info_display.setText('[{}] 基金代码不正确, 请重新输入.'.format(datetime.now().strftime('%H%M%S')))
            return
        if fid in self.Favorite_Funds:
            # 判断显示列表中有无这个基金
            self.info_display.setText('[{}] 基金已经在列表中'.format(datetime.now().strftime('%H%M%S')))
            return
        self.fund_builder.funds.append(fid)

    @staticmethod
    def setValueColor(val):
        # 给数据上色, 红或者绿
        try:
            if val > 0:
                return Qt.red
            elif val < 0:
                return Qt.darkGreen
            else:
                return Qt.darkBlue
        except (TypeError, ValueError):
            return

    def _resizeTable(self):
        for n in range(1, self.display_table.columnCount()):
            self.display_table.horizontalHeader().setSectionResizeMode(n, QHeaderView.ResizeToContents)

    def clearAll(self):
        self.display_table.clear()
        self.Funds_Pool.clear()
        self.the_markets_updater.stocks_id.clear()
        self.marketsDB.clear()
        self.display_table.setRowCount(0)
        self.display_table.setColumnCount(0)


class MyTable(QTableWidget):
    rightClicked = pyqtSignal(int)

    def mousePressEvent(self, *args, **kwargs):
        if args[0].button() == Qt.RightButton:
            try:
                row_clicked = self.itemAt(args[0].x(), args[0].y()).row()
                self.rightClicked.emit(row_clicked)
            except AttributeError:
                pass
        else:
            super().mousePressEvent(*args, **kwargs)


class MyTableItem(QTableWidgetItem):
    # 继承一个新的item类型, 用以将数据float化排序(父类是按str排序)
    def __lt__(self, other):
        if isinstance(other, QTableWidgetItem):
            try:
                my_value = float(re.search(r'([+|-]?\d+\.\d+|0)', self.text()).group(1))
                other_value = float(re.search(r'([+|-]?\d+\.\d+|0)', other.text()).group(1))
                return my_value < other_value
            except (AttributeError, TypeError):
                return super(MyTableItem, self).__lt__(other)

