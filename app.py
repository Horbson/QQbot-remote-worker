import os
from dotenv import load_dotenv

from mode import mode_manager
from client import MyClient

import botpy

load_dotenv()

bot_access_config = {"appid": os.getenv("qqbot_appid"), "secret": os.getenv("qqbot_appsecret")}

def main():
    intents = botpy.Intents(public_messages=True)
    client = MyClient(intents=intents, mode_manager=mode_manager)

    client.run(**bot_access_config)

if __name__ == "__main__":
    main()
