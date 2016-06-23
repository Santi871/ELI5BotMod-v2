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
        response = [{
            "text": "Choose a game to play",
            "fallback": "You are unable to choose a game",
            "callback_id": "wopr_game",
            "color": "#3AA3E3",
            "attachment_type": "default",
            "actions": [
                {
                    "name": "chess",
                    "text": "Chess",
                    "type": "button",
                    "value": "chess"
                },
                {
                    "name": "maze",
                    "text": "Falken's Maze",
                    "type": "button",
                    "value": "maze"
                },
                {
                    "name": "war",
                    "text": "Thermonuclear War",
                    "style": "danger",
                    "type": "button",
                    "value": "war",
                    "confirm": {
                        "title": "Are you sure?",
                        "text": "Wouldn't you prefer a good game of chess?",
                        "ok_text": "Yes",
                        "dismiss_text": "No"
                    }
                }
            ]
        }]

        return Response(response=json.dumps(response), status=200, mimetype='application/json')

    else:
        return Response(), 200


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
