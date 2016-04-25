import praw
import os
import puni
import time
import sys
import threading
from modules import slacklogger
import traceback


class CreateThread(threading.Thread):
    def __init__(self, thread_id, name, method, r):
        threading.Thread.__init__(self)
        self.threadID = thread_id
        self.name = name
        self.method = method
        self.r = r

    def run(self):

        while True:
            try:
                print("Starting " + self.name)
                methodToRun = self.method(self.r)
                print("Exiting " + self.name)
            except Exception as e:
                print("Failure in thread '%s', exception: %s" % (self.name, e))
                time.sleep(1)


class BotMod:

    """Main class for BotMod"""

    def __init__(self, s, devmode=False, use_database=False, use_commands=True, use_filters=True):

        self.slack_log = slacklogger.SlackLogger(s, 'eli5bot-log')

        print("Initializing BotMod...", file=self.slack_log)
        self.s = s
        self.devmode = devmode
        self.use_database = use_database
        self.listening = False
        self.channel = None
        self.subreddit = None
        self.refreshing = True
        self.already_done_reposts = []

        print("Connecting to reddit...", file=self.slack_log)

        app_uri = 'https://127.0.0.1:65010/authorize_callback'
        self.r = praw.Reddit(user_agent='windows:ELI5Mod:v3 (by /u/santi871)')
        self.r.set_oauth_app_info(os.environ['REDDIT_APP_ID'], os.environ['REDDIT_APP_SECRET'], app_uri)
        self.r.refresh_access_information(os.environ['REDDIT_REFRESH_TOKEN'])
        self.r.config.api_request_delay = 1

        print("Connected to reddit.", file=self.slack_log)

        if use_database:

            from modules import database
            print("Connecting to database...")
            self.db = database.Database()
            print("Connected to database.")

        if use_commands:

            from modules import commands as commands_module
            self.commands_module = commands_module
            self.command_handler = self.commands_module.CommandsHandler(self, self.s, self.db)
            self.create_thread(self.listen_to_chat)

        if use_filters:
            from modules import filters
            self.filters = filters.Filters(self.r, self.s, self.db)
            self.create_thread(self.scan_new_posts)

        if self.devmode:
            self.subreddit = "santi871"
        else:
            self.subreddit = "explainlikeimfive"

        self.subreddit2 = self.r.get_subreddit(self.subreddit)
        self.un = puni.UserNotes(self.r, self.subreddit2)

        print("Done initializing.")

    @staticmethod
    def create_thread(method):

        app_uri = 'https://127.0.0.1:65010/authorize_callback'
        thread_r = praw.Reddit(user_agent='windows:ELI5Mod:v3 (by /u/santi871)')
        thread_r.set_oauth_app_info(os.environ['REDDIT_APP_ID'], os.environ['REDDIT_APP_SECRET'], app_uri)
        thread_r.refresh_access_information(os.environ['REDDIT_REFRESH_TOKEN'])
        thread_r.config.api_request_delay = 1

        thread = CreateThread(1, str(method) + " thread", method, thread_r)
        thread.start()

    def listen_to_chat(self, r):

        self.listening = True

        while self.listening:
            event = self.s.get_event()
            slack_event = event.event

            if slack_event.get('type') == 'message':

                if slack_event.get('text') is not None:
                    args = slack_event.get('text').split()

                    channel = slack_event.get('channel')
                    command = args[0][1:]
                    args_dict = self.commands_module.get_slack_event_args(slack_event)

                    try:
                        if args[0][0] == "!":
                            getattr(self.command_handler, "sadsdadd")(r, args_dict)
                    except Exception as e:
                        self.s.send_msg('Failed to run command. Exception: %s' % e, channel_name=channel)
                        self.slack_log.write(traceback.format_exc())

    def scan_new_posts(self, r):

        while True:

            try:
                for submission in praw.helpers.submission_stream(r, 'explainlikeimfive', limit=50, verbosity=0):
                    self.filters.run_filters(submission)
            except TypeError:
                time.sleep(1)
                continue

    def check_reports(self, r):

        already_done_reports = []

        while True:

            try:
                reported_submissions = r.get_reports('explainlikeimfive')

                for submission in reported_submissions:

                    if submission.id not in already_done_reports:

                        author_submissions = r.get_redditor(submission.author).get_submitted(limit=500)
                        removed_submissions = 0

                        for item in author_submissions:

                            if item.banned_by is not None:

                                removed_submissions += 1

                        if removed_submissions > 2:

                            n = puni.Note(submission.author,
                                          "Multiple removed submissions. Verify user history.",
                                          "ELI5_BotMod", submission.permalink, 'spamwatch')
                            self.un.add_note(n)

                            submission.report(reason="Warning: this user has had multiple submissions removed"
                                                     " in the past")

                        already_done_reports.append(submission.id)

            except:
                time.sleep(5)
                continue

            time.sleep(10)












        
        

    


