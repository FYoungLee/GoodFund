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
        self.fundRefresher = gf_core.FundRefresher()
        self.fundRefresher.result_feedback.connect(self.reckonFeadback)
        self.stockRefresher = gf_core.StockRefresher()
        self.stockRefresher.stock_val_brodcast.connect(self.stockReceived)
        self.the_funds_should_in_the_table = {}
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

        optionlayout.addSpacing(100)
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

        midlayout = QHBoxLayout()
        self.start_btn = QPushButton('开始筛选')
        self.start_btn.setFixedWidth(200)
        self.start_btn.clicked.connect(self.startClicked)
        midlayout.addWidget(self.start_btn)
        self.syn_btn = QPushButton('开始更新')
        self.syn_btn.setFixedWidth(200)
        self.syn_btn.clicked.connect(self.synClicked)
        midlayout.addWidget(self.syn_btn)
        self.info_display = QLabel()
        self.info_display2 = QLabel()
        self.info_display2.setFixedWidth(50)
        midlayout.addWidget(self.info_display)
        midlayout.addWidget(self.info_display2)
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
        self.startThreadSearch(self.loadFavor(), favored=True)
        self.stockRefresher.start()
        self.fundRefresher.start()

    def loadFavor(self):
        try:
            with open('favorite.json', 'r') as f:
                all_fvr_from_file = json.loads(f.read())
        except FileExistsError:
            with open('favorite.json', 'w') as f:
                return
        return all_fvr_from_file

    # def rankSilderChanged(self, val):
    #     self.rank_label.setText(str(val))

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
        if '开始更新' in self.syn_btn.text() and self.fundRefresher.isRunning() is False:
            self.fundRefresher.start()

    def fundReceived(self, funds):
        for each in funds:
            self.the_funds_should_in_the_table[each[0]] = each
        self.applyNewTable()
        self.resizeTable()
        self.start_btn.setEnabled(True)
        self.start_btn.setText('开始筛选')
        self.syn_btn.click()

    def applyNewTable(self, order=None):
        self.display_table.clear()
        self.display_table.setColumnCount(17)
        self.display_table.setHorizontalHeaderLabels(['基金名称', '评分', '经理', '净值', '累计', '估算(%)',
                                                      '日涨', '周涨', '月涨', '季涨', '半年', '一年',
                                                      '两年', '三年', '规模', '收藏', ''])
        self.display_table.setSortingEnabled(False)
        self.display_table.setRowCount(len(self.the_funds_should_in_the_table))
        if order is None:
            for r, each in enumerate(self.the_funds_should_in_the_table.keys()):
                self.placeItem(self.the_funds_should_in_the_table[each], r)
        else:
            for r, each in enumerate(order):
                self.placeItem(self.the_funds_should_in_the_table[each], r)
        self.display_table.setSortingEnabled(True)

    def placeItem(self, each, r):
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
        self.infoReceived('[{}] 已更新'.format(datetime.now().strftime('%H:%M:%S')))
        self.syn_btn.setText('更新中...')
        if 'Data' in rec.keys():
            self.fundRefresher.setFunds(tuple(self.the_funds_should_in_the_table.keys()))
            return
        for each in rec:
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
        if _item.column() == 0:
            QDesktopServices().openUrl(QUrl('http://fund.eastmoney.com/{}.html'.format(_item.toolTip())))
        if _item.column() == 15:
            if _item.text() == '已收藏':
                with open('favorite.json') as f:
                    favor = json.loads(f.read())
                tar_item = self.display_table.item(_item.row(), 0)
                fid = tar_item.toolTip()
                favor.pop(favor.index(fid))
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
                with open('favorite.json', 'w') as f:
                    f.write(json.dumps(favor))
                tar_item.setForeground(Qt.darkRed)
                _item.setText('已收藏')
                _item.setForeground(Qt.gray)

        if _item.column() == 16:
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
        # 将当前table里面的所有数据打包
        rows_order = []
        for row in range(self.display_table.rowCount()):
            rows_order.append(self.display_table.item(row, 0).toolTip())
        return rows_order

    # def combineContent(self, pak1, pak2):
    #     # 比较两个list中的数据是否重复, 返回一个并集
    #     # y[0] 提出 pak2 中的基金id数据, 包装成一个新的id list, x从中对比.
    #     ret = pak2
    #     ret.extend([x for x in pak1 if x[0] not in [y[0] for y in pak2]])
    #     return ret

    def searchFund(self):
        if re.match(r'\d{6}', self.search_line.text()) is None:
            self.info_display.setText('[{}] 基金代码不正确, 请重新输入.'.format(datetime.now().strftime('%H%M%S')))
            return
        if self.search_line.text() in self.the_funds_should_in_the_table.keys():
            self.info_display.setText('[{}] 基金已经在列表中'.format(datetime.now().strftime('%H%M%S')))
            return
        self.startThreadSearch([self.search_line.text()])

    def startThreadSearch(self, id_list, favored=False):
        th = gf_core.FundsDownloader(id_list, favored=favored, parent=self)
        th.send_to_display_info.connect(self.infoReceived)
        th.result_broadcast.connect(self.fundReceived)
        th.start()

    def setValueColor(self, val):
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


class mygfItem(QTableWidgetItem):
    def __lt__(self, other):
        if isinstance(other, QTableWidgetItem):
            try:
                my_value = float(re.search(r'([+|-]?\d+\.\d+|0)', self.text()).group(1))
                other_value = float(re.search(r'([+|-]?\d+\.\d+|0)', other.text()).group(1))
                return my_value < other_value
            except (AttributeError, TypeError):
                return super(mygfItem, self).__lt__(other)
