import sys
import eli5bot
import os
import time
from slacksocket import SlackSocket
from configparser import ConfigParser


def main():
    # Get the default Slack channel from config
    config = ConfigParser()
    config.read('config.ini')
    default_channel = config.get('slack', 'default_channel')

    # Create a SlackSocket instance with select filters
    event_filters = ['message']
    s = SlackSocket(os.environ['SLACK_TOKEN'], translate=True, event_filters=event_filters)

    # Try to create an instance of the bot
    try:
        botmod = eli5bot.BotMod(s)
    except Exception as e:
        msg = s.send_msg('Failed to start bot.\n Exception: %s' % e, channel_name=default_channel, confirm=False)

if __name__ == '__main__':
    main()
