def prompt_command_confirm(s, channel, verbose=True):

    if verbose:
        s.send_msg("Are you sure you want to run this command? '!confirm' for yes, '!reject' for no",
                   channel_name=channel, confirm=False)

    for eventobj in s.events():

        if eventobj.event.get('text') is not None and eventobj.event.get('user') != 'eli5-bot':

            channel = eventobj.event.get('channel')
            message = eventobj.event.get('text')
            split_message = message.split()
            command = split_message[0]

            if command[0][0] == '!':
                if command == "!confirm":
                    return True
                if command == "!reject":
                    s.send_msg("Command rejected.", channel_name=channel, confirm=False)
                    return False
                else:
                    s.send_msg("A command is pending confirmation: '!confirm' for yes, '!reject' for no",
                               channel_name=channel, confirm=False)


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

