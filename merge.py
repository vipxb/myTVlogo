import xml.etree.ElementTree as ET
from collections import defaultdict
import aiohttp
import asyncio
from tqdm.asyncio import tqdm_asyncio  # 引入 tqdm 的异步支持
from datetime import datetime
import gzip
import shutil
from xml.dom import minidom
import re
from opencc import OpenCC
import os
from tqdm import tqdm  # 引入 tqdm 的同步支持

def transform2_zh_hans(string):
    cc = OpenCC("t2s")
    new_str = cc.convert(string)
    return new_str


def get_urls():
    urls = []
    with open('config.txt', 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith('#'):
                urls.append(line)
    return urls


async def process_channel(channel, urls, semaphore):
    if (os.exists(f'img/{channel}.png')):
        return
    flag = False
    async with semaphore:  # 使用信号量限制并发
        for url in urls:
            if flag:
                break
            now_url = url +"/"+ channel + '.png'
            async with aiohttp.ClientSession() as session:
                async with session.get(now_url) as response:
                    if response.status == 200:
                        content = await response.read()
                        with open(f'images/{channel}.png', 'wb') as f:
                            f.write(content)
                        flag = True

channels_url = "https://github.com/mytv-android/iptv-api/raw/refs/heads/master/config/demo.txt"
async def main():
    urls = get_urls()
    channels = []
    async with aiohttp.ClientSession() as session:
        async with session.get(channels_url) as response:
            if response.status == 200:
                content = await response.text()
                channels += [line for line in content.split(
                    '\n') if line and not line.startswith('#')]
    channels = list(set(channels))  # 去重
    semaphore = asyncio.Semaphore(10)  # 限制并发任务数量为 10

    tasks = []
    for channel in channels:
        tasks.append(process_channel(channel, urls, semaphore))
    with tqdm_asyncio(total=len(tasks), desc="Downloading channels") as pbar:
        for task in asyncio.as_completed(tasks):
            await task
            pbar.update(1)
    print("All channels Processed.")                        


if __name__ == '__main__':
    asyncio.run(main())
