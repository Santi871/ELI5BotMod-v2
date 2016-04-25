

class SlackLogger:

    """This class pipes stdout a Slack channel"""

    def __init__(self, stdout, s, channel):
        self.s = s
        self.terminal = stdout
        self.channel = channel

    def write(self, message):
        self.terminal.write(message)
        self.s.send_msg(message, channel_name=self.channel)
