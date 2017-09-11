import requests
import json
import time
import re
from datetime import datetime
import asyncio
import aiohttp

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


def download_finatial_reports(scodes, timeout=1, limits=10):
    # url = 'http://datainterface.eastmoney.com/EM_DataCenter/JS.aspx?type=SR&sty=YJBB&code={}'
    # try:
    #     page = requests.get(url.format(scode))
    #     if page.ok:
    #         jsontext = page.text[1:-1]
    #         if 'stats:false' in jsontext:
    #             return
    #         data = json.loads(jsontext)
    #         data = [x.split(',') for x in data]
    #         _ret = {}
    #         for each in data:
    #             yy, mm, dd = each[-2].split('-')
    #             date_ts = datetime(int(yy), int(mm), int(dd)).timestamp()
    #             _ret[date_ts] = float(each[2])
    #         return _ret
    #     else:
    #         raise requests.exceptions.RequestException
    # except requests.exceptions.RequestException:
    #     time.sleep(timeout)
    #     download_finatial_reports(scode, timeout=timeout+1)

    url = 'http://datainterface.eastmoney.com/EM_DataCenter/JS.aspx?type=SR&sty=YJBB&code={}'
    ret = {}
    done = [0]

    async def fetch(session, s_url, scode, timeout=timeout):
        try:
            async with session.get(s_url) as resp:
                pbytes = await resp.read()
                page_content = pbytes.decode()
                if 'stats:false' not in page_content:
                    data = json.loads(page_content[1:-1])
                    data = [x.split(',') for x in data]
                    _ret = {}
                    for each in data:
                        yy, mm, dd = each[-2].split('-')
                        date_ts = datetime(int(yy), int(mm), int(dd)).timestamp()
                        _ret[date_ts] = float(each[2])
                    ret[scode] = _ret
                    done[0] += 1
                    print('{} Done ({}/{})'.format(scode, done[0], len(scodes)))
        except Exception as err:
            print('{} fetching err: {}; link: {}'.format(scode, err, s_url))
            await asyncio.sleep(timeout)
            await fetch(session, s_url, scode, timeout=timeout+1)

    async def loader(sem, session, scode):
        s_url = url.format(scode[-6:])
        async with sem:
            await fetch(session, s_url, scode)

    async def run():
        tasks = []
        sem = asyncio.Semaphore(limits)
        async with aiohttp.ClientSession() as session:
            for each in scodes:
                task = asyncio.ensure_future(loader(sem, session, each))
                tasks.append(task)
            await asyncio.gather(*tasks)

    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(run())
    loop.run_until_complete(future)

    return ret


def download_all_shares_id(timeout=1):
    url = 'http://quote.eastmoney.com/stock_list.html'
    try:
        resp = requests.get(url)
        return re.findall(r'<li><a.*>(.*)\(((60|90|00|30)\d{4})\)</a></li>', resp.content.decode('gbk'))
    except requests.exceptions.RequestException:
        time.sleep(timeout)
        download_all_shares_id(timeout+1)

def update_finatial_reports():
    all_shares = download_all_shares_id()
    f_shares = download_finatial_reports([x[1] for x in all_shares])
    data = {'update_ts': datetime.today().timestamp(), 'datas': f_shares}
    with open('Stock_Finatial_Reports.json', 'w') as f:
        f.write(json.dumps(data))

def get_managers():
    req = requests.get('http://fund.eastmoney.com/Data/FundDataPortfolio_Interface.aspx?dt=14&pn=5000')
    m_str = re.search(r'data:(\[.*\]),', req.text).groups()[0]
    managers = json.loads(m_str)
    man_id = [x[0] for x in managers]
    ret_man = {}

    async def getm(session, url, mid):
        async with session.get(url) as resp:
            text = await resp.text()
            ret_man[mid] = json.loads(text)
            print(mid, 'Done')

    async def apply(mid):
        tasks = []
        async with aiohttp.ClientSession() as session:
            for each in mid:
                url = "http://fundmobapi.eastmoney.com/FundMApi/FundMangerBase.ashx?deviceid=fundmanager2016&version=4.3.0&product=EFund&plat=Iphone&MGRID={}".format(each)
                tasks.append(asyncio.ensure_future(getm(session, url, each)))
            await asyncio.gather(*tasks)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(apply(man_id))

    # for each in man_id:
    #     while True:
    #         try:
    #             url = "https://fundmobapi.eastmoney.com/FundMApi/FundMangerBase.ashx?deviceid=fundmanager2016&version=4.3.0&product=EFund&plat=Iphone&MGRID={}".format(each)
    #             print('[{}] {}'.format(time.ctime(), url))
    #             r = requests.get(url, 5)
    #             ret_man.append(json.loads(r.text))
    #             break
    #         except requests.exceptions.RequestException:
    #             pass
    return ret_man


def recalc_bonus():
    with open('S_Bonus.json') as f:
        sbonus = json.loads(f.read())

    n_bonus = {}
    for key in sbonus:
        datas = sbonus[key]
        if len(datas) == 1:
            continue
        d = [(datas[0][x], datas[1][x]) for x in range(len(datas[0]))][::-1][:-1]
        ret = {}

        def cc(mm, p, r):
            def ff(p):
                p1 = 0
                for n, e in enumerate(p):
                    if '12-31' in e[0] and n != 0:
                        p1 = float(e[1])
                        for _e in p[:-1]:
                            if mm in _e[0] and '--' not in _e[1]:
                                return p1, float(_e[1]), 1
                if p1:
                    if mm == '03':
                        return p1, p1 / 4, 1
                    elif mm == '06':
                        return p1, p1 / 2, 1
                    elif mm == '09':
                        return p1, p1 * 3 / 4, 1
                elif mm == '09':
                    return 1, 1, 0.75
                for e in p:
                    if '09-30' in e[0]:
                        p1 = float(e[1])
                        for _e in p[:-1]:
                            if mm in _e[0] and '--' not in _e[1]:
                                return p1, float(_e[1]), 0.75
                if p1:
                    if mm == '03':
                        return p1, p1 / 3, 0.75
                    elif mm == '06':
                        return p1, p1 * 2 / 3, 0.75
                return 0, 0, 0

            try:
                pos_1, pos_2, ratio = ff(p)
                if pos_1:
                    return round((float(p[-1][1]) + pos_1 - pos_2) / ratio, 2)
                else:
                    raise IndexError
            except (ValueError, IndexError):
                return round(float(p[-1][1]) / r, 2)

        for n, each in enumerate(d):
            try:
                yy, mm, dd = each[0].split('-')
                if '--' not in each[1]:
                    if mm == '12':
                        ret[each[0]] = float(each[1])
                    else:
                        r = 0.75
                        if mm == '06':
                            r = 0.5
                        elif mm == '03':
                            r = 0.25
                        if n >= 5:
                            ret[each[0]] = cc(mm, d[n - 4:n + 1], r)
                        else:
                            ret[each[0]] = round(float(each[1]) / r, 2)
            except ValueError:
                continue
        if len(datas) == 1:
            continue
        if ret:
            n_bonus[key] = ret
    return n_bonus


def get_all_reports_from163():
    ret = {}
    async def apply_tasks(sids):
        tasks = []
        sem = asyncio.Semaphore(10)
        async with aiohttp.ClientSession() as session:
            for sid in sids:
                tasks.append(asyncio.ensure_future(do_job(sem, session, sid)))
            await asyncio.gather(*tasks)

    async def do_job(sem, session, sid):
        url = 'http://quotes.money.163.com/service/zycwzb_{}.html?type=report'.format(sid)
        try:
            async with sem:
                async with session.get(url, timeout=10) as resp:
                    raw_data = await resp.read()
                    clean_datas(sid, raw_data)
        except (asyncio.TimeoutError, aiohttp.client_exceptions.ClientError) as err:
            print(sid, err, 'Error, try again.')
            await do_job(sem, session, sid)

    def clean_datas(sid, raw_data):
        raw_text = raw_data.decode(encoding='GBK')
        data_matrix = [y.strip().split(',') for y in [x for x in raw_text.split('\r\n') if x]]
        ret[sid] = [[y for y in x if y] for x in data_matrix if len(x) == len(data_matrix[0])]
        print(sid, 'Done!')

    while True:
        try:
            resp = requests.get('http://quote.eastmoney.com/stock_list.html')
            rst = re.findall(r'<li><a.*>(.*)\(((60|90|00|30)\d{4})\)</a></li>', resp.content.decode('gbk'))
            sids = [x[1] for x in rst]
            break
        except requests.exceptions.RequestException:
            time.sleep(3)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.ensure_future(apply_tasks(sids)))
    return ret


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
    #
    # m = ManFilter()
    # m.start()

    choice = input('1. Update Stocks Finatial Reports.\n'
                   '2. Update Managers Details.\n'
                   '>> ')
    if choice == '1':
        data = get_all_reports_from163()
        with open('S_Bonus.json', 'w') as f:
            f.write(json.dumps(data))
    elif choice == '2':
        m = get_managers()
        with open('Managers.json', 'w') as f:
            f.write(json.dumps(m))