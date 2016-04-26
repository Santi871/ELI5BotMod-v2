

class SlackLogger:

    """
    This class sends messages you wish to log to a log channel
    Eg prints, tracebacks, etc.
    """

    def __init__(self, s, channel):
        self.s = s
        self.channel = channel

    def write(self, message):
        self.s.send_msg(message, channel_name=self.channel, confirm=False)
