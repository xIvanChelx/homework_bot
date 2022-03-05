import logging
import os
import sys
import time
from http import HTTPStatus
from logging import StreamHandler

import requests
import telegram
from dotenv import load_dotenv

import exceptions

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 20
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f"OAuth {PRACTICUM_TOKEN}"}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}


def send_message(bot, message):
    """Бот отправляет сообщение."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logger.error(f'Сообщение в Telegram не отправлено. Ошибка {error}.')
    else:
        logger.info('Сообщение отправлено')


def get_api_answer(current_timestamp):
    """Получаем ответ от API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != HTTPStatus.OK:
        message = 'Ошибка. Эндпоинт недоступен.'
        logger.error(message)
        raise exceptions.EndPointNotAvaliable(message)
    else:
        return response.json()


def check_response(response):
    """Проверяем ответ от API."""
    print(response)
    if not isinstance(response, dict):
        message = 'Ошибка. Ответ от API не словарь.'
        logger.error(message)
        raise TypeError(message)
    if len(response.get("homeworks")) == 0:
        message = 'Обновления статусов в ответе API отсутствуют'
        logger.debug(message)
        raise IndexError(message)
    if type(response['homeworks']) is not list:
        message = 'Ошибка. Домашние работы не в виде списка.'
        logger.error(message)
        raise TypeError(message)
    response = response.get('homeworks')
    return response


def parse_status(homework):
    """Проверяем статус работы."""
    try:
        homework.get('homework_name')
    except KeyError as error:
        message = f'Ошибка {error}. Отсутствует ключ "homework_name".'
        logger.error(message)
    else:
        homework_name = homework.get('homework_name')
    try:
        homework.get('status')
    except KeyError as error:
        message = f'Ошибка {error}. Отсутствует ключ "status".'
        logger.error(message)
    else:
        homework_status = homework.get('status')
    try:
        homework_status in HOMEWORK_STATUSES
    except Exception as error:
        message = f'Ошибка {error}. Недокументированный статус.'
        logger.error(message)
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем доступность токенов в переменных окружения."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    else:
        return False


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    check_tokens_result = check_tokens()
    error_message_bot = 0
    if check_tokens_result is False:
        message = 'Отсутствуют обязятельные переменные окружения'
        logger.critical(message)
        raise SystemExit(message)

    while True:
        try:
            response = get_api_answer(current_timestamp)
            checked_response = check_response(response)
            message = parse_status(checked_response[0])
            send_message(bot, message)
            current_timestamp = response.get('current_date')
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != error_message_bot:
                send_message(bot, message)
                error_message_bot = message
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
