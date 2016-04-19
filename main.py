import sys
import eli5bot
import os
import time
from slacksocket import SlackSocket


def main():
    s = SlackSocket(os.environ['SLACK_TOKEN'],translate=True)

    try:
        botmod = eli5bot.BotMod(s)
    except Exception as e:
        msg = s.send_msg('Failed to start bot.\n Exception: %s' % e, channel_name="eli5bot-dev")
        sys.exit()

    time.sleep(2)

    botmod.create_thread(botmod.listen_to_chat)
    botmod.create_thread(botmod.repost_detector)
    botmod.create_thread(botmod.check_reports())

if __name__ == '__main__':
    main()
