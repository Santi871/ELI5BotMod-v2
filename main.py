import sys
import eli5bot
import os
from slacksocket import SlackSocket

def main():
    s = SlackSocket(os.environ['SLACK_TOKEN'],translate=True)

    Running = True

    while Running:

        botmod = None

        try:
            msg = s.send_msg('Starting bot...', channel_name="eli5bot-dev")
            botmod = eli5bot.BotMod(s)
        except Exception as e:
            msg = s.send_msg('Failed to start bot.\n Exception: %s' % e, channel_name="eli5bot-dev")
            sys.exit()

        botmod.listenToChat()



if __name__ == '__main__':
    main()
