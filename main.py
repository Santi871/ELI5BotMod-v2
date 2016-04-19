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
        botmod = eli5bot.BotMod(s)
    except Exception as e:
        msg = s.send_msg('Failed to start bot.\n Exception: %s' % e, channel_name="eli5bot-dev")
        sys.exit()

    time.sleep(2)

    botmod.create_thread(botmod.listen_to_chat)

    time.sleep(2)

    repostThread = myThread(4, "Repost detector", botmod, botmod.repost_detector)
    repostThread.start()

    time.sleep(2)

    reportsThread = myThread(5, "Report checker", botmod, botmod.check_reports)
    reportsThread.start()

if __name__ == '__main__':
    main()
