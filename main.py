import sys
import eli5bot
import os
import time
import configparser
from slacksocket import SlackSocket


def main():
    s = SlackSocket(os.environ['SLACK_TOKEN'],translate=True)

    # config = configparser.ConfigParser()
    # config.read('config.ini')

    try:
        botmod = eli5bot.BotMod(s, use_database=True)
    except Exception as e:
        msg = s.send_msg('Failed to start bot.\n Exception: %s' % e, channel_name="eli5bot-dev")
        sys.exit()

    time.sleep(2)

    botmod.create_thread(botmod.repost_detector)
    botmod.create_thread(botmod.check_reports)

if __name__ == '__main__':
    main()
