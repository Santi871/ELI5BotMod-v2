import praw
import os
import puni
import datetime
import urllib.parse
import psycopg2
import time
import nltk
import threading
from modules import filters


class CreateThread(threading.Thread):
    def __init__(self, thread_id, name, method, r):
        threading.Thread.__init__(self)
        self.threadID = thread_id
        self.name = name
        self.method = method
        self.r = r

    def run(self):
        print("Starting " + self.name)
        methodToRun = self.method(self.r)
        print("Exiting " + self.name)


class BotMod:

    """Main class for BotMod"""

    def __init__(self, s, devmode=False, use_database=False, use_commands=True, search_reposts=True):

        print("Initializing BotMod...")
        self.s = s
        self.devmode = devmode
        self.use_database = use_database
        self.listening = False
        self.channel = None
        self.subreddit = None
        self.refreshing = True
        self.already_done_reposts = []

        print("Connecting to reddit...")

        app_uri = 'https://127.0.0.1:65010/authorize_callback'
        self.r = praw.Reddit(user_agent='windows:ELI5Mod:v3 (by /u/santi871)')
        self.r.set_oauth_app_info(os.environ['REDDIT_APP_ID'], os.environ['REDDIT_APP_SECRET'], app_uri)
        self.r.refresh_access_information(os.environ['REDDIT_REFRESH_TOKEN'])
        self.r.config.api_request_delay = 1

        print("Connected to reddit.")

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
                            getattr(self.command_handler, command)(r, args_dict)
                    except Exception as e:
                        self.s.send_msg('Failed to run command. Exception: %s' % e, channel_name=channel)

    def scan_new_posts(self, r):

        for submission in praw.helpers.submission_stream(r, 'explainlikeimfive', limit=50, verbosity=0):

            self.filters.check_current_events(submission)
            self.filters.search_reposts(submission)

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












        
        

    


