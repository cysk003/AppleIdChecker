import webview
import requests
import threading
import queue
import concurrent.futures
import logging
from apple_id_checker import AppleIDChecker
from threading import Lock, Event
from concurrent.futures import ThreadPoolExecutor
# 配置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 常量
PROXY_API_URL = 'https://api.hailiangip.com:8522/api/getIp?type=1&num=200&pid=-1&unbindTime=180&cid=-1&orderId=O23110722352356692123&time=1699738697&sign=4bc1e1ba75c91b0da7d6328552104498&noDuplicate=1&dataType=1&lineSeparator=0'  # 请替换成您的代理获取API的URL
NUM_PROXIES_TO_FETCH = 200  # 每次API调用最多获取的代理数

# 代理队列全局变量
proxy_queue = queue.Queue()
proxy_queue_lock = Lock()  # A lock to ensure thread-safe operations on the proxy queue
stop_event = Event()  # An event to signal the threads to stop


def fetch_and_replenish_proxy_queue_thread_safe(num_proxies):
    with proxy_queue_lock:  # Ensure that only one thread can replenish the queue at a time
        fetch_and_replenish_proxy_queue(num_proxies)

# 获取代理IP并填充队列的函数


def fetch_and_replenish_proxy_queue(num_proxies):
    # 获取代理列表，并且填充到队列中
        response = requests.get(PROXY_API_URL)
        proxies = response.text.strip().split('\n')
        for proxy in proxies:
            proxy_queue.put(proxy)


# 使用提供的代理检查Apple ID的函数
def check_apple_id(apple_id, password):
    # Assuming the AppleIDChecker class and its try_login method are correctly defined
    checker = AppleIDChecker()
    proxy = None
    while not stop_event.is_set():  # Check if the event is set before each operation
        try:
            if proxy_queue.empty():  # If the queue is empty, fetch new proxies
                logger.info("Queue is empty, fetching new proxies...")
                fetch_and_replenish_proxy_queue_thread_safe(
                    NUM_PROXIES_TO_FETCH)

            proxy = proxy_queue.get(timeout=5)  # Get a proxy with a timeout
            result = checker.try_login(apple_id, password, proxy)
            return result  # This will exit only the current thread
        except queue.Empty:
            logger.error(
                "Queue is empty, no available proxy IPs, stopping check.")
            break
        except Exception as e:
            logger.error(f"Error for {apple_id}: {e}")
            # Consider if you want to re-raise the exception or handle it differently

    logger.info(
        f"Thread {threading.current_thread().name} received stop signal for {apple_id}")


# Define a global variable to hold the window reference
global_window = None

# 对外暴露给webview的API类
# 对外暴露的API类


class Api:
    def __init__(self):
        self.checker = AppleIDChecker()
        self.is_checking = False  # 标记当前是否正在检查

    # 设置代理API地址的方法
    def set_proxy_api(self, proxy_api_url):
        global PROXY_API_URL  # 使用global关键字来更新全局变量
        PROXY_API_URL = proxy_api_url

    # 使用新的代理API地址获取代理的方法
    def fetch_proxies(self, num_proxies):
        if not PROXY_API_URL:
            logger.error("代理API地址未设置。")
            return []

        response = requests.get(PROXY_API_URL, params={
                                'type': '1', 'num': num_proxies})  # 使用新的API地址来获取代理
        if response.ok:
            # 根据实际响应格式拆分代理字符串
            return response.text.strip().split('\n')
        else:
            logger.error("Failed to retrieve proxies: %s",
                         response.status_code)
            return []

    # 初始化代理队列的函数
    def initialize_proxy_queue(self, num_proxies):
        proxies = self.fetch_proxies(num_proxies)
        for proxy in proxies:
            proxy_queue.put(proxy)

    # 开始检查Apple IDs的对外暴露方法
    def check_apple_ids(self, file_content, num_threads):
        if self.is_checking:  # 如果当前正在检查，则返回
            return

        self.is_checking = True
        self.initialize_proxy_queue(min(num_threads, NUM_PROXIES_TO_FETCH))

        # 将文件内容拆分为Apple ID和密码对
        apple_ids = [line.split(
            '----') for line in file_content.strip().split('\n') if '----' in line]

        # 使用线程池执行并发检查
        results = {"correct": 0, "incorrect": 0, "locked": 0, "exception": 0,
                   "total": len(apple_ids), "detected": 0, "undetected": 0}
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures_to_apple_id = {executor.submit(
                check_apple_id, apple_id, password): apple_id for apple_id, password in apple_ids}

            # 处理完成的任务并更新UI
            for future in concurrent.futures.as_completed(futures_to_apple_id):
                apple_id = futures_to_apple_id[future]
                try:
                    result = future.result()
                    # 根据结果更新计数器
                    if result["status"] == "密码正确":
                        results["correct"] += 1
                        results["detected"] += 1
                    elif result["status"] == "密码错误":
                        results["incorrect"] += 1
                        results["detected"] += 1
                    elif result["status"] == "帐号被锁":
                        results["locked"] += 1
                        results["detected"] += 1
                    else:
                        results["exception"] += 1
                        results["detected"] += 1

                    results["undetected"] = results["total"] - \
                        results["detected"]

                    # 使用线程安全的方式更新UI
                    update_ui_with_results(results)
                except Exception as exc:
                    logger.error(
                        f'Apple ID check for {apple_id} generated an exception: {exc}')

        self.is_checking = False  # 重置检查标志

# 安全地在主线程中更新UI的函数


def stop_checking():
    stop_event.set()  # Signal all threads to stop

# 安全地在主线程中更新UI的函数


def update_ui_with_results(results):
    # 构造更新UI的JavaScript代码
    update_ui_script = f"""
        document.getElementById('correct-count').innerText = '{results['correct']}';
        document.getElementById('incorrect-count').innerText = '{results['incorrect']}';
        document.getElementById('locked-count').innerText = '{results['locked']}';
        document.getElementById('exception-count').innerText = '{results['exception']}';
        document.getElementById('total-count').innerText = '{results['total']}';
        document.getElementById('detected-count').innerText = '{results['detected']}';
        document.getElementById('undetected-count').innerText = '{results['undetected']}';
    """
    # 在主线程中执行JavaScript代码更新UI
    global_window.evaluate_js(update_ui_script)

# 创建webview窗口并启动


def create_webview_window():
    global global_window  # Use the global keyword to modify the global variable
    api = Api()
    global_window = webview.create_window(
        'Apple ID Checker', 'index.html', js_api=api)
    webview.start()


if __name__ == '__main__':
    create_webview_window()
