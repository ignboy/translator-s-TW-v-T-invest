from flask import Flask, request, jsonify
import requests
import logging
import os

app = Flask(__name__)

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='bot.log'
)
logger = logging.getLogger(__name__)

# Конфигурация (лучше вынести в отдельный файл или переменные окружения)
CONFIG = {
    "t.d59epU-Tw4F8VSdeKDndtvL41FGdU7UenZ4pVCgb9QlJZJidfsvX4cYeLDYAt2rk152_4Z8bC_I03JPjqDWgVQ": os.getenv("TINKOFF_TOKEN", "your_tinkoff_token"),
    "7599474107:AAFyWhxpcyvE7Bl414flIcAuEVHMmgvI0Vc": os.getenv("TELEGRAM_TOKEN", "your_telegram_token"),
    "2056726947": os.getenv("TELEGRAM_CHAT_ID", "your_chat_id"),
}


class TinkoffAPI:
    BASE_URL = "https://api-invest.tinkoff.ru/openapi"

    def __init__(self, token):
        self.token = token
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def get_figi(self, ticker):
        url = f"{self.BASE_URL}/market/search/by-ticker?ticker={ticker}"
        response = requests.get(url, headers=self.headers)
        data = response.json()
        return data["payload"]["instruments"][0]["figi"]

    def place_order(self, figi, operation, price, lots=1):
        url = f"{self.BASE_URL}/orders/limit-order"
        payload = {
            "figi": figi,
            "lots": lots,
            "operation": operation,
            "price": float(price)
        }
        response = requests.post(url, headers=self.headers, json=payload)
        return response.json()


def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{CONFIG['TELEGRAM_TOKEN']}/sendMessage"
    params = {"chat_id": CONFIG["TELEGRAM_CHAT_ID"], "text": message}
    requests.post(url, json=params)


@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        logger.info(f"Received webhook: {data}")

        # Пример формата сигнала:
        # {
        #   "action": "BUY|SELL",
        #   "ticker": "AAPL",
        #   "price": 150.0,
        #   "lots": 1
        # }

        tinkoff = TinkoffAPI(CONFIG["TINKOFF_TOKEN"])
        figi = tinkoff.get_figi(data["ticker"])

        if data["action"].upper() in ["BUY", "SELL"]:
            result = tinkoff.place_order(
                figi=figi,
                operation=data["action"].upper(),
                price=data["price"],
                lots=data.get("lots", 1)
            )

            message = (f"🛎️ New order executed:\n"
                       f"Ticker: {data['ticker']}\n"
                       f"Action: {data['action']}\n"
                       f"Price: {data['price']}\n"
                       f"Lots: {data.get('lots', 1)}\n"
                       f"Result: {result}")

            send_telegram_message(message)
            logger.info(message)

            return jsonify({"status": "success", "data": result})

        return jsonify({"status": "error", "message": "Invalid action"}), 400

    except Exception as e:
        error_msg = f"Error processing webhook: {str(e)}"
        logger.error(error_msg)
        send_telegram_message(f"❌ Error: {error_msg}")
        return jsonify({"status": "error", "message": error_msg}), 500


@app.route('/')
def index():
    return "TradingView to Tinkoff Bot is running!"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)