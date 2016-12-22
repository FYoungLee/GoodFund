from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QComboBox, QSlider, QLabel, QTableWidget, \
    QTableWidgetItem, QPushButton, QHeaderView, QMessageBox, QLineEdit
from PyQt5.QtCore import Qt, QMutex, QUrl
from PyQt5.Qt import QDesktopServices
import gf_core
import json, re
from datetime import datetime


class GF_MainWindow(QWidget):
    def __init__(self, parent=None):
        super(GF_MainWindow, self).__init__(parent)
        self.setWindowTitle('好基基 by Fyoung')
        self.setFixedSize(1300, 650)
        self.fundRefresher = None
        self.stockRefresher = gf_core.StockRefresher()
        self.stockRefresher.stock_val_brodcast.connect(self.stockReceived)
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
        self.rank_slider.valueChanged.connect(self.rankSilderChanged)
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
        self.syn_btn = QPushButton('同步估算净值')
        self.syn_btn.setFixedWidth(200)
        self.syn_btn.clicked.connect(self.synClicked)
        self.syn_btn.setEnabled(False)
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
        self.display_table.setColumnCount(17)
        self.display_table.setHorizontalHeaderLabels(['基金名称', '评分', '经理', '净值', '累计', '估算(%)',
                                                      '日涨', '周涨', '月涨', '季涨', '半年', '一年',
                                                      '两年', '三年', '规模', '收藏', ''])
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
        self.stockRefresher.start()

    def rankSilderChanged(self, val):
        self.rank_label.setText(str(val))

    def displaySelectedFund(self, fund_item):
        pass

    def startClicked(self):
        self.start_btn.setEnabled(False)
        self.start_btn.setText('筛选中...')
        fs = gf_core.FundSelctor(self.history_combox.currentText(), self.rank_slider.value(), self)
        fs.result_broadcast.connect(self.fundReceived)
        fs.send_to_display_info.connect(self.infoReceived)
        fs.send_to_display_info2.connect(self.infoReceived2)
        fs.start()

    def synClicked(self):
        if '同步估算净值' in self.syn_btn.text():
            self.syn_btn.setText('同步估值中...')
            self.start_btn.setEnabled(False)
            args = []
            for r in range(self.display_table.rowCount()):
                arg = (self.display_table.item(r, 0).toolTip(), self.display_table.item(r, 0).text())
                args.append(arg)
            if self.fundRefresher is None:
                self.fundRefresher = gf_core.FundRefresher(args)
                self.fundRefresher.result_feedback.connect(self.reckonFeadback)
            else:
                self.fundRefresher.setFunds(args)
            self.fundRefresher.start()
        elif '同步估值中' in self.syn_btn.text():
            self.syn_btn.setText('同步估算净值')
            self.start_btn.setEnabled(True)

    def fundReceived(self, funds):
        self.start_btn.setEnabled(True)
        self.start_btn.setText('开始筛选')
        self.display_table.setRowCount(len(funds))
        for r, each in enumerate(funds):
            self.placeItem(each, r)

        self.resizeTable()
        self.syn_btn.setEnabled(True)
        self.syn_btn.click()

    def placeItem(self, each, r):
        name = QTableWidgetItem(each[1])
        name.setTextAlignment(Qt.AlignCenter)
        name.setToolTip(each[0])
        self.display_table.setItem(r, 0, name)

        score = QTableWidgetItem()
        _score = each[2]
        if None is not _score and '暂无数据' in _score:
            _score = ''
        score.setData(Qt.DisplayRole, _score)
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
            _inc = QTableWidgetItem()
            try:
                _inc.setData(Qt.DisplayRole, round(float(each[_n]), 2))
                _inc.setForeground(self.setValueColor(each[_n]))
            except (ValueError, TypeError):
                pass
            _inc.setTextAlignment(Qt.AlignCenter)
            self.display_table.setItem(r, _n - 1, _inc)

        fund_scale = QTableWidgetItem()
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

    def resizeTable(self):
        for n in range(1, 17):
            self.display_table.horizontalHeader().setSectionResizeMode(n, QHeaderView.ResizeToContents)

    def setValueColor(self, val):
        try:
            if float(val) > 0:
                return Qt.red
            elif float(val) < 0:
                return Qt.darkGreen
        except ValueError:
            return Qt.black

    def infoReceived(self, info):
        self.info_display.setText(info)

    def infoReceived2(self, info):
        self.info_display2.setText('{}/{}'.format(info[0], info[1]))

    def reckonFeadback(self, rec):
        if rec[0] is None:
            self.info_display.setText('[{}] 休市中...'.format(datetime.now().strftime('%H:%M:%S')))
            self.syn_btn.click()
            return
        locker = QMutex()
        locker.lock()
        r = self.display_table.findItems(rec[0], Qt.MatchExactly)[0].row()
        rec_item = QTableWidgetItem()
        rec_item.setData(Qt.DisplayRole, rec[1])
        rec_item.setTextAlignment(Qt.AlignCenter)
        try:
            rec_item.setForeground(self.setValueColor(rec[1]))
        except TypeError:
            pass
        self.display_table.setItem(r, 5, rec_item)
        self.display_table.item(r, 6).setText('{}% ({})'.format(rec[3], rec[2][6:-1]))
        self.display_table.item(r, 6).setForeground(self.setValueColor(rec[3]))
        locker.unlock()

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
            if reply == QMessageBox.No:
                return
            t_data = self.wrapContent()
            del_id = self.display_table.item(_item.row(), 0).toolTip()
            ret = tuple(filter(lambda x: del_id not in x[0], t_data))
            self.fundReceived(ret)

    def stockReceived(self, stext):
        self.stockDisplay.setText(stext)

    def wrapContent(self):
        wraped = []
        for r in range(self.display_table.rowCount()):
            t_list = [self.display_table.item(r, 0).toolTip(), self.display_table.item(r, 0).text(),
                      self.display_table.item(r, 1).data(Qt.DisplayRole), self.display_table.item(r, 2).data(1000)]
            for _c in range(3, 14):
                t_list.append(self.display_table.item(r, _c).data(Qt.DisplayRole))
            t_list.append(self.display_table.item(r, 14).text().replace('亿', ''))
            if self.display_table.item(r, 15).text() == '已收藏':
                t_list.append('已收藏')
            wraped.append(t_list)
        return wraped

    def searchFund(self):
        if re.match(r'\d{6}', self.search_line.text()) is None:
            self.info_display.setText('[{}] 基金代码不正确, 请重新输入.'.format(datetime.now().strftime('%H%M%S')))
            return
        for row in range(self.display_table.rowCount()):
            if self.search_line.text() in self.display_table.item(row, 0).toolTip():
                self.info_display.setText('[{}] 基金已经在列表中'.format(datetime.now().strftime('%H%M%S')))
                return
        th = gf_core.FundsDownloader([self.search_line.text()], self)
        th.send_to_display_info.connect(self.infoReceived)
        th.result_broadcast.connect(self.addNewItem)
        th.start()

    def addNewItem(self, sth):
        r = self.display_table.rowCount()
        self.display_table.setRowCount(r+1)
        self.placeItem(sth[0], r)
        self.resizeTable()
