

class SlackLogger:

    """This class pipes stdout a Slack channel"""

    def __init__(self, old_stdout, s, channel):
        self.s = s
        self.terminal = old_stdout
        self.channel = channel

    def write(self, message):
        self.terminal.write(message)
        print(message)
        self.s.send_msg(message, channel_name=self.channel)
