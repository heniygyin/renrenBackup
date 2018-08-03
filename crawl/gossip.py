# coding: utf8

from datetime import datetime
import json
import re

from config import config
from models import Gossip

from .utils import get_image


crawler = config.crawler
normal_pattern = re.compile(r'<span style="color:#[0-9a-fA-F]*">(.*)</span>')


def load_gossip_page(page):
    param = {
        "id": crawler.uid,
        "page": page,
        "guest": crawler.uid,
    }
    r = crawler.get_json(config.GOSSIP_URL, params=param, method='POST')

    for c in r['array']:
        local_pic = get_image(c['tinyUrl'])

        gossip = {
            'id': c['id'],
            't': datetime.strptime(c['time'], "%Y-%m-%d %H:%M"),
            'guestId': c['guestId'],
            'guestName': c['guestName'],
            'headPic': local_pic,    # 居然保存的是当时的头像，这里不能往 User 表里塞了
            'attachSnap': get_image(c.get('headUrl', '')),
            'attachPic': get_image(c.get('largeUrl', '')),
            'whisper': c['whisper'] == 'true',
            'wap': c['wap'] == 'true',
            'gift': c['giftImg'] if c['gift'] == 'true' else '',
            'content': ''
        }

        # 内容出现在好几个地方，body, filterdBody, filterOriginBody
        # filterOriginBody 是连表情都没转义的
        # filterdBody 加了表情转义，但也加了那个坑爹的 <span style="color:#000000">
        #     还有手机发布的 <xiaonei_wap/>，和送礼物带的 <xiaonei_gift />

        body = c['filterdBody'].replace('\n', '<br>').replace('<xiaonei_wap/>', '')
        if gossip['gift']:
            body = re.sub(r'<xiaonei_gift img="http:[\.a-z0-9/]*"/>', '', body)
        patt = normal_pattern.findall(body)
        if not patt:
            print(f'ERROR on parsing gossip body:\n  {c["filterdBody"]}')
        else:
            gossip['content'] = patt[0]

        Gossip.insert(**gossip).on_conflict('replace').execute()

    print(f'  crawled {len(r["array"])} gossip on page {page}')
    return r['gossipCount']


def get_gossip():
    cur_page = 0
    total = config.ITEMS_PER_PAGE
    while cur_page*config.ITEMS_PER_PAGE < total:
        print(f'start crawl gossip page {cur_page}')
        total = load_gossip_page(cur_page)
        cur_page += 1

    return total
