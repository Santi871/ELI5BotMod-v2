import sys
import eli5bot
import os
import time
from slacksocket import SlackSocket
from configparser import ConfigParser
from flask import Flask, request, Response
import json


app = Flask(__name__)

SLACK_WEBHOOK_SECRET = os.environ.get('SLACK_WEBHOOK_SECRET')
SLACK_SLASHCMDS_SECRET = os.environ.get('SLACK_SLASHCMDS_SECRET')


@app.route('/slack', methods=['POST'])
def inbound():
    print(str(request.form))
    if request.form.get('token') == SLACK_WEBHOOK_SECRET:
        channel = request.form.get('channel_name')
        username = request.form.get('user_name')
        text = request.form.get('text')
        inbound_message = username + " in " + channel + " says: " + text
        print(inbound_message)
    return Response(), 200


@app.route('/', methods=['GET'])
def test():
    return Response('It works!')


@app.route('/slackcommands', methods=['POST'])
def command():
    print(str(request.form))
    if request.form.get('token') == SLACK_SLASHCMDS_SECRET:
        response = {"text": "Thank you for the question. An expert will reply soon!"}
        return json.dumps(response)
    else:
        return None


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
    app.run(threaded=True)
