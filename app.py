import os
from dotenv import load_dotenv

from mode import mode_manager
from client import MyClient
from utils.logging_config import setup_logging

import botpy

load_dotenv()

_log = botpy.logging.get_logger()

bot_access_config = {"appid": os.getenv("qqbot_appid"), "secret": os.getenv("qqbot_appsecret")}

def main():
    setup_logging()
    intents = botpy.Intents(public_messages=True)
    _log.info("应用启动")
    client = MyClient(intents=intents, mode_manager=mode_manager)

    client.run(**bot_access_config)

if __name__ == "__main__":
    main()
