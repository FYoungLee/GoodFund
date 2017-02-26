from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QComboBox, QSlider, QLabel, QTableWidget, \
    QTableWidgetItem, QPushButton, QHeaderView, QLineEdit
from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.Qt import QDesktopServices
import gf_core3
import json, re
from datetime import datetime


class GF_MainWindow(QWidget):
    def __init__(self, parent=None):
        super(GF_MainWindow, self).__init__(parent)
        self.setWindowTitle('搞个好基基 作者：肥羊')
        self.setMinimumSize(1440, 720)
        # 当前显示基金池
        self.favorites = []

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
        self.display_table.setColumnCount(19)
        self.display_table.setHorizontalHeaderLabels(['基金名称', '评分', '经理', '净值', '累计', '估算',
                                                      '日涨', '周涨', '月涨', '季涨', '半年', '今年', '一年',
                                                      '两年', '三年', '规模', '市盈', '市净', '收藏'])

        mlayout.addLayout(optionlayout)
        mlayout.addLayout(midlayout)
        mlayout.addWidget(self.display_table)

        self.marketsDisplay = QLabel()
        mlayout.addWidget(self.marketsDisplay)

        self.setLayout(mlayout)
        # 载入收藏基金
        self.updater = gf_core3.Updater()
        self.updater.fund_sender.connect(self.placeFunds)
        self.updater.market_sender.connect(lambda x: self.marketsDisplay.setText(x))
        self.updater.start()

    def loadFavor(self):
        self.load_favor_btn.setEnabled(False)
        # 从json文档中加载已经保存的基金代码
        try:
            with open('favorite.json', 'r') as f:
                favors = json.loads(f.read())
                for each in favors:
                    if each not in self.favorites:
                        self.favorites.append(each)
        except FileExistsError:
            with open('favorite.json', 'w'):
                return
        for fid in self.favorites:
            self.updater.add_fund_to_update(fid)

    def displaySelectedFund(self, fund_item):
        # TODO display fund information locally
        pass

    def startClicked(self):
        self.start_btn.setEnabled(False)
        self.updater.get_filtered_list(self.history_combox.currentText(), self.rank_slider.value())

    def synClicked(self):
        if '更新中' in self.syn_btn.text():
            self.syn_btn.setText('更新停止')
            self.updater.stopTimer()
        else:
            self.syn_btn.setText('更新中...')
            self.updater.startUpdateTimer()

    def placeFunds(self, funds):
        start = datetime.now().timestamp()
        self.start_btn.setEnabled(True)
        self.load_favor_btn.setEnabled(True)
        self.display_table.setSortingEnabled(False)
        starting_row = self.display_table.rowCount()
        for fund in funds:
            row = self.isFundInTable(fund)
            if row != -1:
                self.updateFundItem(row, fund)
            else:
                starting_row += 1
                self.display_table.setRowCount(starting_row)
                self.placeNewFund(starting_row - 1, fund)
        self._resizeTable()
        self.display_table.setSortingEnabled(True)
        print('[{}]Placing item time cost: {}'.format(datetime.now().ctime(), datetime.now().timestamp() - start))

    def isFundInTable(self, fund):
        rows = self.display_table.rowCount()
        for row in range(rows):
            if fund.id == self.display_table.item(row, 0).toolTip():
                return row
        return -1

    def updateFundItem(self, row, fund):
        fund.calculate_averages()
        self.display_table.item(row, 5).setText(fund.estimate)
        color = self.setValueColor(fund.estimate)
        self.display_table.item(row, 5).setForeground(color)
        is_new = 'NEW' if fund.fresh else ''
        self.display_table.item(row, 6).setText(fund.latest_change + '%' + is_new)
        color = self.setValueColor(fund.latest_change)
        self.display_table.item(row, 6).setForeground(color)
        self.display_table.item(row, 3).setText(fund.current_value)
        self.display_table.item(row, 3).setForeground(color)
        self.display_table.item(row, 4).setText(fund.total_value)
        self.display_table.item(row, 4).setForeground(color)
        self.display_table.item(row, 16).setText(str(round(fund.avg_PE, 2)))
        self.display_table.item(row, 17).setText(str(round(fund.avg_PB, 2)))
        stocks_tooltip = ''
        for stock in fund.stocks:
            stocks_tooltip += '({})[{}] {} 价格:{}\t市盈率:{}\t市净率:{}\t量比:{}\n'\
                .format(stock.ratio, stock.id, stock.name, stock.price, stock.PE, stock.PB, stock.QR)
        self.display_table.item(row, 16).setToolTip(stocks_tooltip)
        self.display_table.item(row, 17).setToolTip(stocks_tooltip)

    def placeNewFund(self, row, fund):
        # 单条基金信息, 按column位置铺
        name = QTableWidgetItem('{}  [{}]'.format(fund.name, fund.id))
        name.setTextAlignment(Qt.AlignCenter)
        name.setToolTip(fund.id)
        name.setData(1000, fund.name)
        self.display_table.setItem(row, 0, name)

        score = MyTableItem()
        score.setText(fund.score)
        score.setTextAlignment(Qt.AlignCenter)
        self.display_table.setItem(row, 1, score)

        manager = QTableWidgetItem()
        man_text_tooltip = ''
        best = None
        for mid in fund.managers:
            man_text_tooltip += '[{}]{} {}\n'.format(mid, fund.managers[mid]['name'], fund.managers[mid]['score'])
            if best is None or fund.managers[mid]['score'] > best['score']:
                best = fund.managers[mid]
        man_text_display = '{} {}'.format(best['name'], best['score']) if best is not None else ''
        if len(fund.managers) > 1:
            man_text_display += ' ...'
        manager.setText(man_text_display)
        manager.setToolTip(man_text_tooltip[:-1])
        manager.setTextAlignment(Qt.AlignCenter)
        manager.setData(1000, fund.managers)
        self.display_table.setItem(row, 2, manager)

        cur_val = MyTableItem(fund.current_value)
        self.display_table.setItem(row, 3, cur_val)

        tot_val = MyTableItem(fund.total_value)
        self.display_table.setItem(row, 4, tot_val)

        est_chg = MyTableItem(fund.estimate + '%')
        est_chg.setForeground(self.setValueColor(fund.estimate))
        self.display_table.setItem(row, 5, est_chg)

        is_new = 'NEW' if fund.fresh else ''
        latest_chg = MyTableItem(fund.latest_change + '%' + is_new)
        color = self.setValueColor(fund.latest_change)
        latest_chg.setForeground(color)
        cur_val.setForeground(color)
        tot_val.setForeground(color)
        self.display_table.setItem(row, 6, latest_chg)

        for _col, _each in enumerate(fund.perform):
            color = self.setValueColor(_each)
            if color == Qt.black:
                continue
            pf = MyTableItem(_each + ' %')
            pf.setForeground(self.setValueColor(_each))
            pf.setTextAlignment(Qt.AlignCenter)
            self.display_table.setItem(row, _col + 7, pf)

        fund_scale = MyTableItem(str(fund.scales) + '亿')
        fund_scale.setTextAlignment(Qt.AlignCenter)
        self.display_table.setItem(row, 15, fund_scale)

        fund_pe = MyTableItem(str(fund.avg_PE))
        fund_pe.setTextAlignment(Qt.AlignCenter)
        self.display_table.setItem(row, 16, fund_pe)

        fund_pb = MyTableItem(str(fund.avg_PB))
        fund_pb.setTextAlignment(Qt.AlignCenter)
        self.display_table.setItem(row, 17, fund_pb)

        is_favored = '收藏' if fund.id not in self.favorites else '已收藏'
        favored = QTableWidgetItem(is_favored)
        if is_favored == '已收藏':
            name.setForeground(Qt.darkRed)
            favored.setForeground(Qt.lightGray)
        self.display_table.setItem(row, 18, favored)

    def tableItemClicked(self, _item):
        self.display_table.setSortingEnabled(False)
        # 当表格被点击时
        if isinstance(_item, int):
            row = _item
            del_id = self.display_table.item(row, 0).toolTip()
            if '已收藏' in self.display_table.item(row, 15).text():
                self.favorites.remove(del_id)
            self.display_table.removeRow(row)
            self.updater.remove(del_id)
        elif isinstance(_item, QTableWidgetItem):
            if _item.column() == 0:
                # 打开基金的详细信息链接 (本地打开, 开发中...)
                QDesktopServices().openUrl(QUrl('http://fund.eastmoney.com/{}.html'.format(_item.toolTip())))
            if _item.column() == 18:
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
        self.display_table.setSortingEnabled(True)

    def searchFund(self):
        # 搜索功能
        fid = self.search_line.text()
        if re.match(r'\d{6}', fid) is None:
            # 判断是否为有效6位代码
            self.info_display.setText('[{}] 基金代码不正确, 请重新输入.'.format(datetime.now().strftime('%H%M%S')))
            return
        if fid in self.favorites:
            # 判断显示列表中有无这个基金
            self.info_display.setText('[{}] 基金已经在列表中'.format(datetime.now().strftime('%H%M%S')))
            return
        self.updater.add_fund_to_update(fid)

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
        for n in range(1, self.display_table.columnCount()):
            self.display_table.horizontalHeader().setSectionResizeMode(n, QHeaderView.ResizeToContents)

    def clearAll(self):
        self.display_table.clear()
        self.updater.funds.clear()


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

