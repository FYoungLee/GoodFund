from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QComboBox, QSlider, QLabel, QTableWidget, \
    QTableWidgetItem, QPushButton, QHeaderView, QMessageBox, QLineEdit
from PyQt5.QtCore import Qt, QUrl
from PyQt5.Qt import QDesktopServices
import gf_core2
import json, re
from datetime import datetime


class GF_MainWindow(QWidget):
    def __init__(self, parent=None):
        super(GF_MainWindow, self).__init__(parent)
        self.setWindowTitle('好基基 by Fyoung')
        self.setMinimumSize(1440, 720)
        # 当前显示基金池
        self.favorites = []
        self.others = []

        # 开始GUI布局
        mlayout = QVBoxLayout()
        optionlayout = QHBoxLayout()
        optionlayout.addWidget(QLabel('历史排名'))
        self.history_combox = QComboBox()
        self.history_combox.addItem('三年涨幅')
        self.history_combox.addItem('两年涨幅')
        self.history_combox.addItem('一年涨幅')
        self.history_combox.addItem('今年涨幅')
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
        self.start_btn.setFixedWidth(100)
        self.start_btn.clicked.connect(self.startClicked)
        optionlayout.addWidget(self.start_btn)
        optionlayout.addStretch(1)

        midlayout = QHBoxLayout()
        self.syn_btn = QPushButton('更新中...')
        self.syn_btn.setFixedWidth(100)
        self.syn_btn.clicked.connect(self.synClicked)
        midlayout.addWidget(self.syn_btn)
        self.load_favor_btn = QPushButton('加载收藏')
        self.load_favor_btn.setFixedWidth(100)
        self.load_favor_btn.clicked.connect(self.loadFavor)
        midlayout.addWidget(self.load_favor_btn)
        self.clear_btn = QPushButton('清空')
        self.clear_btn.setFixedWidth(100)
        self.clear_btn.clicked.connect(self._clearTable)
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

        self.display_table = QTableWidget()

        self.display_table.itemClicked.connect(self.displaySelectedFund)
        self.display_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.display_table.setSortingEnabled(True)
        self.display_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.display_table.itemClicked.connect(self.tableItemClicked)
        self.display_table.setSelectionMode(QTableWidget.SingleSelection)
        self.display_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.display_table.setColumnCount(17)
        self.display_table.setHorizontalHeaderLabels(['基金名称', '评分', '经理', '净值', '累计', '估算(%)',
                                                      '日涨', '周涨', '月涨', '季涨', '半年', '今年', '一年',
                                                      '两年', '三年', '规模', '收藏'])
        mlayout.addLayout(optionlayout)
        mlayout.addLayout(midlayout)
        mlayout.addWidget(self.display_table)

        self.stockDisplay = QLabel()
        mlayout.addWidget(self.stockDisplay)

        self.setLayout(mlayout)
        # 载入收藏基金
        self.updater = gf_core2.FundsManager()
        self.updater.response_feedback.connect(self.infoReceived)

    def loadFavor(self):
        self.load_favor_btn.setEnabled(False)
        # 从json文档中加载已经保存的基金代码
        try:
            with open('favorite.json', 'r') as f:
                self.favorites = json.loads(f.read())
        except FileExistsError:
            with open('favorite.json', 'w'):
                return
        self.updater.funds_init_info(self.favorites + self.others)

    def displaySelectedFund(self, fund_item):
        pass

    def startClicked(self):
        self.start_btn.setEnabled(False)
        self.updater.get_filtered_list(self.history_combox.currentText(), self.rank_slider.value())

    def synClicked(self):
        if '更新中' in self.syn_btn.text():
            self.updater.timer_control(False)
            self.syn_btn.setText('更新停止')
        else:
            self.updater.timer_control(True)
            self.syn_btn.setText('更新中...')

    def infoReceived(self, feedback):
        if gf_core2.Tasks.FundsFull == feedback[0]:
            if feedback[1]:
                self.placeFunds(feedback[1])
            self.start_btn.setEnabled(True)
        elif gf_core2.Tasks.Stocks == feedback[0]:
            self.placeStocks(feedback[1])
        else:
            self.updateItem(feedback)
        self.updater.set_update_list(self.favorites+self.others)

    def placeFunds(self, funds):
        self.display_table.setSortingEnabled(False)
        startrow = self.display_table.rowCount()
        self.display_table.setRowCount(len(funds) + startrow)
        for _row, each in enumerate(funds):
            # 单条基金信息, 按column位置铺
            name = QTableWidgetItem('{}  [{}]'.format(each['fund_name'], each['fund_id']))
            name.setTextAlignment(Qt.AlignCenter)
            name.setToolTip(each['fund_id'])
            name.setData(1000, each['fund_name'])
            self.display_table.setItem(_row + startrow, 0, name)

            score = mygfItem()
            _score = each['fund_score']
            if None is not _score and '暂无数据' in _score:
                _score = ''
            score.setText(_score)
            score.setTextAlignment(Qt.AlignCenter)
            self.display_table.setItem(_row + startrow, 1, score)

            manager = QTableWidgetItem()
            man_text_tooltip = ''
            _man_text_display = None
            for m in each['managers']:
                if _man_text_display is None:
                    _man_text_display = '{} {}'.format(m[1], m[2])
                man_text_tooltip += '{} {}\n'.format(m[1], m[2])
            _man_text_display = _man_text_display.replace('暂无数据', '-')
            if len(each['managers']) > 1:
                _man_text_display += ' ...'
            manager.setText(_man_text_display)
            manager.setToolTip(man_text_tooltip[:-1])
            manager.setTextAlignment(Qt.AlignCenter)
            manager.setData(1000, each['managers'])
            self.display_table.setItem(_row + startrow, 2, manager)

            cur_val = mygfItem(each['current_val'])
            self.display_table.setItem(_row + startrow, 3, cur_val)

            tot_val = mygfItem(each['total_val'])
            self.display_table.setItem(_row + startrow, 4, tot_val)

            est_chg = mygfItem(each['est_change']+'%')
            est_chg.setForeground(self.setValueColor(each['est_change']))
            self.display_table.setItem(_row + startrow, 5, est_chg)

            latest_chg = mygfItem(each['latest_change'] + '%')
            color = self.setValueColor(each['latest_change'])
            latest_chg.setForeground(color)
            cur_val.setForeground(color)
            tot_val.setForeground(color)
            self.display_table.setItem(_row + startrow, 6, latest_chg)

            for _col, _each in enumerate(each['performance']):
                color = self.setValueColor(_each)
                if color == Qt.black:
                    continue
                pf = mygfItem(_each + ' %')
                pf.setForeground(self.setValueColor(_each))
                pf.setTextAlignment(Qt.AlignCenter)
                self.display_table.setItem(_row + startrow, _col + 7, pf)

            fund_scale = mygfItem(str(each['scales']) + '亿')
            fund_scale.setTextAlignment(Qt.AlignCenter)
            self.display_table.setItem(_row + startrow, 15, fund_scale)

            _is_favored = '收藏' if each['fund_id'] not in self.favorites else '已收藏'
            favored = QTableWidgetItem(_is_favored)
            if _is_favored == '已收藏':
                name.setForeground(Qt.darkRed)
                favored.setForeground(Qt.lightGray)
            self.display_table.setItem(_row + startrow, 16, favored)
            self.display_table.setItem(_row + startrow, 17, QTableWidgetItem('删'))
        self._resizeTable()
        self.display_table.setSortingEnabled(True)

    def updateItem(self, funds_pack):
        self.display_table.setSortingEnabled(False)
        funds_dict = {}
        for each in range(self.display_table.rowCount()):
            funds_dict[self.display_table.item(each, 0).toolTip()] = each
        if funds_pack[0] == gf_core2.Tasks.FundsEst:
            for each in funds_pack[1]:
                try:
                    color = self.setValueColor(each[1])
                    row = funds_dict[each[0]]
                    item = self.display_table.item(row, 5)
                    item.setText(each[1] + '%')
                    item.setForeground(color)
                    item.setTextAlignment(Qt.AlignCenter)
                except KeyError:
                    continue
        elif funds_pack[0] == gf_core2.Tasks.FundsVal:
            for each in funds_pack[1]:
                try:
                    color = self.setValueColor(each[2])
                    row = funds_dict[each[0]]
                    item = self.display_table.item(row, 6)
                    item.setText(each[2] + '%')
                    item.setForeground(color)
                    item.setTextAlignment(Qt.AlignCenter)
                    item = self.display_table.item(row, 3)
                    item.setText(each[1])
                    item.setForeground(color)
                    item.setTextAlignment(Qt.AlignCenter)
                except KeyError:
                    continue
        self.display_table.setSortingEnabled(True)

    def placeStocks(self, stocks):
        self.stockDisplay.setText(stocks)

    def tableItemClicked(self, _item):
        self.display_table.setSortingEnabled(False)
        # 当表格被点击时
        if _item.column() == 0:
            # 打开基金的详细信息链接 (本地打开, 开发中...)
            QDesktopServices().openUrl(QUrl('http://fund.eastmoney.com/{}.html'.format(_item.toolTip())))
        if _item.column() == 15:
            # 收藏功能
            if _item.text() == '已收藏':
                _item_0 = self.display_table.item(_item.row(), 0)
                self.favorites.remove(_item_0.toolTip())
                with open('favorite.json', 'w') as f:
                    f.write(json.dumps(self.favorites))
                _item_0.setForeground(Qt.black)
                _item.setText('收藏')
                _item.setForeground(Qt.black)
            elif _item.text() == '收藏':
                _item_0 = self.display_table.item(_item.row(), 0)
                self.favorites.append(_item_0.toolTip())
                with open('favorite.json', 'w') as f:
                    f.write(json.dumps(self.favorites))
                _item_0.setForeground(Qt.darkRed)
                _item.setText('已收藏')
                _item.setForeground(Qt.gray)
        if _item.column() == 16:
            # 从表格显示中删除当前被点击的基金(从显示池中删除, 然后保存当前显示序列, 然后按序列重新铺)
            reply = QMessageBox().question(self, '删除基金',
                                           '你确定要移除"{}"吗?'.format(self.display_table.item(_item.row(), 0).text()),
                                           QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                del_id = self.display_table.item(_item.row(), 0).toolTip()
                if '已收藏' in self.display_table.item(_item.row(), 15).text():
                    self.favorites.remove(del_id)
                else:
                    self.others.remove(del_id)
                self.display_table.removeRow(_item.row())
        self.display_table.setSortingEnabled(True)

    def searchFund(self):
        # 搜索功能
        if re.match(r'\d{6}', self.search_line.text()) is None:
            # 判断是否为有效6位代码
            self.info_display.setText('[{}] 基金代码不正确, 请重新输入.'.format(datetime.now().strftime('%H%M%S')))
            return
        if self.search_line.text() in self.favorites:
            # 判断显示列表中有无这个基金
            self.info_display.setText('[{}] 基金已经在列表中'.format(datetime.now().strftime('%H%M%S')))
            return

    @staticmethod
    def setValueColor(val):
        # 给数据上色, 红或者绿
        try:
            if float(val) > 0:
                return Qt.red
            elif float(val) < 0:
                return Qt.darkGreen
            else:
                return Qt.darkBlue
        except ValueError:
            return Qt.black

    def _resizeTable(self):
        for n in range(1, 17):
            self.display_table.horizontalHeader().setSectionResizeMode(n, QHeaderView.ResizeToContents)

    def _clearTable(self):
        self.display_table.clear()
        self.load_favor_btn.setEnabled(True)


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
