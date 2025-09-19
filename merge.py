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

retry = 3  # 重试次数
sleep_time = 5  # 重试间隔时间（秒）
max_tasks = 10  # 最大并发任务数

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
    if (os.path.exists(f'./img/{channel}.png')):
        return
    flag = False
    async with semaphore:  # 使用信号量限制并发
        for url in urls:
            if flag:
                break
            now_url = url +"/"+ channel + '.png'
            retry_count = 0
            while retry_count < retry and not flag:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(now_url) as response:
                            if response.status == 200:
                                content = await response.read()
                                with open(f'./img/{channel}.png', 'wb') as f:
                                    f.write(content)
                                flag = True
                            retry_count = retry
                except Exception as e:
                    retry_count += 1
                    print(f"Error fetching {now_url}: {e}")
                    await asyncio.sleep(sleep_time)  # 等待一段时间后重试

channels_url = [
    "https://github.com/mytv-android/iptv-api/raw/refs/heads/master/config/demo.txt", 
    "https://github.com/mytv-android/myTVlogo/raw/refs/heads/main/channel.txt",
    "https://github.com/ldm0206/iptv-api/raw/refs/heads/master/config/demo.txt"
]
async def main():
    urls = get_urls()
    channels = []
    for channel_url in channels_url:
        async with aiohttp.ClientSession() as session:
            async with session.get(channel_url) as response:
                if response.status == 200:
                    content = await response.text()
                    channels += [line for line in content.split(
                        '\n') if line and not line.startswith('#')]
    channels = list(set(channels))  # 去重
    semaphore = asyncio.Semaphore(max_tasks)  # 限制并发任务数量为 10

    tasks = []
    for channel in channels:
        tasks.append(process_channel(channel, urls, semaphore))
    with tqdm_asyncio(total=len(tasks), desc="Downloading channels") as pbar:
        for task in asyncio.as_completed(tasks):
            await task
            pbar.update(1)
    print("All channels Processed.")                        


def generate_img_file_list():
    """
    根据./img中的所有文件生成一份文件列表，去掉文件的扩展名
    """
    img_dir = './img'
    file_list = []

    if os.path.exists(img_dir):
        for filename in os.listdir(img_dir):
            if os.path.isfile(os.path.join(img_dir, filename)):
                # 去掉文件扩展名
                name_without_ext = os.path.splitext(filename)[0]
                # 去掉前缀下划线（如果存在）
                # if name_without_ext.startswith('_'):
                #     name_without_ext = name_without_ext[1:]
                file_list.append(name_without_ext)

    # 排序文件列表
    file_list.sort()

    # 将结果写入文件
    txt_path = 'logo_list.txt'
    with open(txt_path, 'w', encoding='utf-8') as f:
        for filename in file_list:
            f.write(filename + '\n')

    gz_path = 'logo_list.gz'
    with open(txt_path, 'rb') as f_in, gzip.open(gz_path, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)

    print(f"已生成压缩文件：{gz_path}")
    print(f"生成了包含 {len(file_list)} 个文件的列表： {txt_path}")

if __name__ == '__main__':
    os.makedirs('img', exist_ok=True)
    asyncio.run(main())
    generate_img_file_list()
