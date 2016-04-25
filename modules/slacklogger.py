

class SlackLogger:

    """This class pipes stdout a Slack channel"""

    def __init__(self, s, channel):
        self.s = s
        self.channel = channel

    def write(self, message):
        print("SlackLogger was called, msg: " + message)
        self.s.send_msg(message, channel_name=self.channel, confirm=False)
