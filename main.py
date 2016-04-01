import sys
import eli5bot
import os
import threading
import time
from slacksocket import SlackSocket

class myThread(threading.Thread):
    def __init__(self, threadID, name, botmod, method):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.botmod = botmod
        self.method = method
    def run(self):
        print("Starting " + self.name)
        methodToRun = self.method()
        print("Exiting " + self.name)
    

def main():
    s = SlackSocket(os.environ['SLACK_TOKEN'],translate=True)

    #Running = True

    #while Running:

    botmod = None

    try:
        msg = s.send_msg('Starting bot...', channel_name="eli5bot-dev")
        botmod = eli5bot.BotMod(s)
    except Exception as e:
        msg = s.send_msg('Failed to start bot.\n Exception: %s' % e, channel_name="eli5bot-dev")
        sys.exit()

    listenerThread = myThread(1, "Event listener", botmod, botmod.listenToChat)
    listenerThread.start()

    modmailThread = myThread(2, "Modmail logger", botmod, botmod.refreshModmail)
    modmailThread.start()

    bansThread = myThread(3, "Bans logger", botmod, botmod.refreshBans)
    bansThread.start()

if __name__ == '__main__':
    main()
