from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QComboBox, QSlider, QLabel, QTableWidget, \
    QTableWidgetItem, QPushButton, QHeaderView, QMessageBox, QLineEdit
from PyQt5.QtCore import Qt, QUrl
from PyQt5.Qt import QDesktopServices
import gf_core
import json, re
from datetime import datetime


class GF_MainWindow(QWidget):
    def __init__(self, parent=None):
        super(GF_MainWindow, self).__init__(parent)
        self.setWindowTitle('好基基 by Fyoung')
        self.setFixedWidth(1280)
        self.setMinimumSize(1280, 640)
        # 初始化基金更新线程
        self.fundRefresher = gf_core.FundRefresher()
        self.fundRefresher.result_feedback.connect(self.reckonFeadback)
        self.fundRefresher.infot_text_broadcast.connect(self.infoReceived)
        # 初始化股票更新线程
        self.stockRefresher = gf_core.StockRefresher()
        self.stockRefresher.stock_val_brodcast.connect(self.stockReceived)
        # 当前显示基金池
        self.the_funds_should_in_the_table = {}

        # 开始GUI布局
        mlayout = QVBoxLayout()

        optionlayout = QHBoxLayout()
        optionlayout.addWidget(QLabel('历史排名'))
        self.history_combox = QComboBox()
        self.history_combox.addItem('三年涨幅')
        self.history_combox.addItem('两年涨幅')
        self.history_combox.addItem('一年涨幅')
        self.history_combox.addItem('半年涨幅')
        self.history_combox.addItem('季涨幅')
        self.history_combox.addItem('月涨幅')
        self.history_combox.addItem('周涨幅')
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
        self.start_btn.setFixedWidth(200)
        self.start_btn.clicked.connect(self.startClicked)
        optionlayout.addWidget(self.start_btn)

        midlayout = QHBoxLayout()
        self.syn_btn = QPushButton('更新中...')
        self.syn_btn.setFixedWidth(100)
        self.syn_btn.clicked.connect(self.synClicked)
        midlayout.addWidget(self.syn_btn)
        self.manual_syn_btn = QPushButton('手动更新')
        self.manual_syn_btn.setFixedWidth(100)
        self.manual_syn_btn.clicked.connect(lambda: self.fundRefresher.changeState(2))
        midlayout.addWidget(self.manual_syn_btn)
        self.load_favor_btn = QPushButton('加载收藏')
        self.load_favor_btn.setFixedWidth(100)
        self.load_favor_btn.clicked.connect(self.loadFavor)
        midlayout.addWidget(self.load_favor_btn)
        self.clear_btn = QPushButton('清空')
        self.clear_btn.setFixedWidth(100)
        self.clear_btn.clicked.connect(self.clearTable)
        midlayout.addWidget(self.clear_btn)
        self.info_display = QLabel()
        self.info_display2 = QLabel()
        self.info_display2.setFixedWidth(50)
        midlayout.addWidget(self.info_display)
        midlayout.addWidget(self.info_display2)
        fid_label = QLabel('基金代码')
        fid_label.setFixedWidth(50)
        midlayout.addWidget(fid_label)
        self.search_line = QLineEdit()
        self.search_line.setFixedWidth(100)
        self.search_btn = QPushButton('添加')
        self.search_btn.setFixedWidth(50)
        self.search_btn.clicked.connect(self.searchFund)
        midlayout.addWidget(self.search_line)
        midlayout.addWidget(self.search_btn)

        self.display_table = QTableWidget()

        self.display_table.itemClicked.connect(self.displaySelectedFund)
        self.display_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.display_table.setSortingEnabled(True)
        self.display_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.display_table.itemClicked.connect(self.tableItemClicked)
        self.display_table.setSelectionMode(QTableWidget.SingleSelection)
        self.display_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        mlayout.addLayout(optionlayout)
        mlayout.addLayout(midlayout)
        mlayout.addWidget(self.display_table)

        self.stockDisplay = QLabel()
        mlayout.addWidget(self.stockDisplay)

        self.setLayout(mlayout)
        # 载入收藏基金
        self.loadFavor()
        # 启动大盘更新线程
        self.stockRefresher.start()
        # 启动基金更新线程
        self.fundRefresher.start()

    def loadFavor(self):
        self.load_favor_btn.setEnabled(False)
        # 从json文档中加载已经保存的基金代码
        try:
            with open('favorite.json', 'r') as f:
                all_fvr_from_file = json.loads(f.read())
        except FileExistsError:
            with open('favorite.json', 'w'):
                return
        # 扔到线程下载器中启动详情下载
        self.startThreadSearch(all_fvr_from_file, favored=True)

    def displaySelectedFund(self, fund_item):
        pass

    def startClicked(self):
        self.start_btn.setEnabled(False)
        self.start_btn.setText('筛选中...')
        fs = gf_core.FundSelctor(self.history_combox.currentText(), self.rank_slider.value(),
                                 self.the_funds_should_in_the_table.keys(), self)
        fs.result_broadcast.connect(self.fundReceived)
        fs.send_to_display_info.connect(self.infoReceived)
        fs.send_to_display_info2.connect(self.infoReceived2)
        fs.start()

    def synClicked(self):
        if self.fundRefresher.currentState() == 1:
            self.fundRefresher.changeState(0)
            self.syn_btn.setText('自动更新')
        elif self.fundRefresher.currentState() == 0:
            self.fundRefresher.changeState(1)
            self.syn_btn.setText('更新中...')

    def fundReceived(self, funds):
        # 把线程下载器中接收的结果保存到基金显示池中
        for each in funds:
            self.the_funds_should_in_the_table[each[0]] = each
            # 判别如果收藏按钮没有启动, 并且接收结果中是收藏夹内容, 那么开启按钮
            if self.load_favor_btn.isEnabled() is False:
                try:
                    if '已收藏' in each[-1]:
                        self.load_favor_btn.setEnabled(True)
                except TypeError:
                    pass
        # 把显示池中的内容铺到表格中
        self.applyNewTable()
        self.resizeTable()
        self.start_btn.setEnabled(True)
        self.start_btn.setText('开始筛选')
        # 更改基金更新器的状态, 使其全部更新一次,
        # (1为自动判别交易时段, 非交易时段更新最新净值, 交易时段更新估算净值)
        # (2为全部更新)
        # (0为暂停更新)
        self.fundRefresher.changeState(2)

    def applyNewTable(self, order=None):
        # 清空当前表格, 重新铺垫
        self.display_table.clear()
        self.display_table.setColumnCount(17)
        self.display_table.setHorizontalHeaderLabels(['基金名称', '评分', '经理', '净值', '累计', '估算(%)',
                                                      '日涨', '周涨', '月涨', '季涨', '半年', '一年',
                                                      '两年', '三年', '规模', '收藏', ''])
        # 关闭排序功能, 以防铺垫错位
        self.display_table.setSortingEnabled(False)
        self.display_table.setRowCount(len(self.the_funds_should_in_the_table))
        try:
            # 判断是否需要按order来铺, 否则按显示池随意铺
            if order is None:
                for r, each in enumerate(self.the_funds_should_in_the_table.keys()):
                    self.placeItem(self.the_funds_should_in_the_table[each], r)
            else:
                for r, each in enumerate(order):
                    self.placeItem(self.the_funds_should_in_the_table[each], r)
        except KeyError as err:
            print(err)
        self.display_table.setSortingEnabled(True)

    def placeItem(self, each, r):
        # 单条基金信息, 按column位置铺
        name = QTableWidgetItem('{}  [{}]'.format(each[1], each[0]))
        name.setTextAlignment(Qt.AlignCenter)
        name.setToolTip(each[0])
        name.setData(1000, each[1])
        self.display_table.setItem(r, 0, name)

        score = mygfItem()
        _score = each[2]
        if None is not _score and '暂无数据' in _score:
            _score = ''
        score.setText(_score)
        score.setTextAlignment(Qt.AlignCenter)
        self.display_table.setItem(r, 1, score)

        manager = QTableWidgetItem()
        man_text_tooltip = ''
        _man_text_display = None
        for m in each[3]:
            if _man_text_display is None:
                _man_text_display = '{} {}'.format(m[1], m[2])
            man_text_tooltip += '{} {}\n'.format(m[1], m[2])
        _man_text_display = _man_text_display.replace('暂无数据', '-')
        if len(each[3]) > 1:
            _man_text_display += ' ...'
        manager.setText(_man_text_display)
        manager.setToolTip(man_text_tooltip[:-1])
        manager.setTextAlignment(Qt.AlignCenter)
        manager.setData(1000, each[3])
        self.display_table.setItem(r, 2, manager)

        for _n in range(4, 15):
            _inc = mygfItem()
            _sign = '%'
            if _n < 6:
                _sign = ''
            try:
                _val = each[_n]
                if '*' in _val:
                    _val = _val.replace('*', '')
                    _inc.setText('{}{} [new]'.format(round(float(_val), 2), _sign))
                else:
                    _inc.setText('{}{}'.format(round(float(_val), 2), _sign))
                _inc.setForeground(self.setValueColor(_val))
            except (ValueError, TypeError):
                pass
            _inc.setTextAlignment(Qt.AlignCenter)
            self.display_table.setItem(r, _n - 1, _inc)

        fund_scale = mygfItem()
        fund_scale.setText(str(each[15]) + '亿')
        fund_scale.setTextAlignment(Qt.AlignCenter)
        self.display_table.setItem(r, 14, fund_scale)

        favored = QTableWidgetItem()
        _is_favored = '收藏'
        try:
            _is_favored = each[16]
        except IndexError:
            pass
        if '已收藏' in _is_favored:
            name.setForeground(Qt.darkRed)
            favored.setForeground(Qt.gray)
        favored.setText(_is_favored)
        self.display_table.setItem(r, 15, favored)
        self.display_table.setItem(r, 16, QTableWidgetItem('删'))

    def reckonFeadback(self, rec):
        # 基金更新信息接收器
        # 如果收到Data为key的信息, 那么反馈当前表格中的所有基金代码给更新器(从基金显示池中提取)
        if 'Data' in rec.keys():
            self.fundRefresher.setFunds(tuple(self.the_funds_should_in_the_table.keys()))
            return
        for each in rec:
            # 接收器接收2种信息, 分别为str的估算净值, tuple的最新净值, 分别处理.
            if isinstance(rec[each], str):
                try:
                    self.the_funds_should_in_the_table[each][6] = rec[each]
                except KeyError:
                    print('{} removed?'.format(each))
                    return
            elif isinstance(rec[each], tuple):
                self.the_funds_should_in_the_table[each][4] = rec[each][0]
                self.the_funds_should_in_the_table[each][7] = '{}*'.format(rec[each][1])

        rows_order = self.wrapContent()
        self.applyNewTable(rows_order)

    def tableItemClicked(self, _item):
        # 当表格被点击时
        if _item.column() == 0:
            # 打开基金的详细信息链接 (本地打开, 开发中...)
            QDesktopServices().openUrl(QUrl('http://fund.eastmoney.com/{}.html'.format(_item.toolTip())))
        if _item.column() == 15:
            # 收藏功能
            if _item.text() == '已收藏':
                with open('favorite.json') as f:
                    favor = json.loads(f.read())
                tar_item = self.display_table.item(_item.row(), 0)
                fid = tar_item.toolTip()
                favor.pop(favor.index(fid))
                self.the_funds_should_in_the_table[fid].pop(-1)
                with open('favorite.json', 'w') as f:
                    f.write(json.dumps(favor))
                tar_item.setForeground(Qt.black)
                _item.setText('收藏')
                _item.setForeground(Qt.black)
            elif _item.text() == '收藏':
                with open('favorite.json') as f:
                    favor = json.loads(f.read())
                tar_item = self.display_table.item(_item.row(), 0)
                fid = tar_item.toolTip()
                favor.append(fid)
                self.the_funds_should_in_the_table[fid].append('已收藏')
                with open('favorite.json', 'w') as f:
                    f.write(json.dumps(favor))
                tar_item.setForeground(Qt.darkRed)
                _item.setText('已收藏')
                _item.setForeground(Qt.gray)

        if _item.column() == 16:
            # 从表格显示中删除当前被点击的基金(从显示池中删除, 然后保存当前显示序列, 然后按序列重新铺)
            reply = QMessageBox().question(self, '删除基金',
                                          '你确定要移除"{}"吗?'.format(self.display_table.item(_item.row(), 0).text()),
                                          QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                order = self.wrapContent()
                del_id = self.display_table.item(_item.row(), 0).toolTip()
                self.the_funds_should_in_the_table.pop(del_id)
                order.pop(order.index(del_id))
                self.applyNewTable(order)

    def wrapContent(self):
        # 将当前table里面的序列(基金代码)保存
        rows_order = []
        for row in range(self.display_table.rowCount()):
            rows_order.append(self.display_table.item(row, 0).toolTip())
        return rows_order

    def searchFund(self):
        # 搜索功能
        if re.match(r'\d{6}', self.search_line.text()) is None:
            # 判断是否为有效6位代码
            self.info_display.setText('[{}] 基金代码不正确, 请重新输入.'.format(datetime.now().strftime('%H%M%S')))
            return
        if self.search_line.text() in self.the_funds_should_in_the_table.keys():
            # 判断显示列表中有无这个基金
            self.info_display.setText('[{}] 基金已经在列表中'.format(datetime.now().strftime('%H%M%S')))
            return
        self.startThreadSearch([self.search_line.text()])

    def startThreadSearch(self, id_list, favored=False):
        # 打开一个新的线程开始查找某个基金, 给定favored参数, 会让下载线程增加一个"已收藏"的标签
        th = gf_core.FundsDownloader(id_list, favored=favored, parent=self)
        th.send_to_display_info.connect(self.infoReceived)
        th.send_to_display_info2.connect(self.infoReceived2)
        th.result_broadcast.connect(self.fundReceived)
        th.start()

    def setValueColor(self, val):
        # 给数据上色, 红或者绿
        try:
            if float(val) > 0:
                return Qt.red
            elif float(val) < 0:
                return Qt.darkGreen
        except ValueError:
            return Qt.black

    def resizeTable(self):
        for n in range(1, 17):
            self.display_table.horizontalHeader().setSectionResizeMode(n, QHeaderView.ResizeToContents)

    def infoReceived(self, info):
        self.info_display.setText(info)

    def infoReceived2(self, info):
        self.info_display2.setText('{}/{}'.format(info[0], info[1]))

    def stockReceived(self, stext):
        self.stockDisplay.setText(stext)

    def clearTable(self):
        self.the_funds_should_in_the_table.clear()
        self.applyNewTable()


class mygfItem(QTableWidgetItem):
    # 继承一个新的item类型, 用以将数据float化排序(父类是按str排序)
    def __lt__(self, other):
        if isinstance(other, QTableWidgetItem):
            try:
                my_value = float(re.search(r'([+|-]?\d+\.\d+|0)', self.text()).group(1))
                other_value = float(re.search(r'([+|-]?\d+\.\d+|0)', other.text()).group(1))
                return my_value < other_value
            except (AttributeError, TypeError):
                return super(mygfItem, self).__lt__(other)
