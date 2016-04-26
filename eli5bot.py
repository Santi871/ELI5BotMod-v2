import praw
import os
import puni
import time
import threading
import traceback
import configparser
from modules import slacklogger


class CreateThread(threading.Thread):
    def __init__(self, thread_id, name, method, r, slacklog):
        threading.Thread.__init__(self)
        self.threadID = thread_id
        self.name = name
        self.method = method
        self.r = r
        self.slack_log = slacklog

    def run(self):

        # This loop will run when the thread raises an exception
        while True:
            try:
                print("Starting " + self.name, file=self.slack_log)
                methodToRun = self.method(self.r)
                print("Exiting " + self.name, file=self.slack_log)
            except:
                print("*Unhandled exception"
                      " in thread* '%s'. Attempting to restart thread..." % self.name, file=self.slack_log)
                self.slack_log.write(traceback.format_exc())
                time.sleep(1)


class BotMod:

    """Main class for BotMod"""

    def __init__(self, s):

        # Parse config
        config = configparser.ConfigParser()
        config.read('config.ini')

        self.devmode = config.getboolean('bot', 'test_mode')
        self.use_database = config.getboolean('modules', 'database')
        self.subreddit = config.get('bot', 'subreddit')
        use_filters = config.getboolean('modules', 'filters')
        use_commands = config.getboolean('modules', 'commands')
        slack_log_channel = config.get('slack', 'log_channel')

        # Get an instance of SlackLogger to print to Slack log channel
        self.slack_log = slacklogger.SlackLogger(s, slack_log_channel)

        # Initialize some variables and constants
        print("----------------------", file=self.slack_log)
        print("Initializing BotMod...", file=self.slack_log)
        self.s = s

        # Authenticate with reddit via OAuth2
        print("Connecting to reddit...", file=self.slack_log)
        app_uri = 'https://127.0.0.1:65010/authorize_callback'
        self.r = praw.Reddit(user_agent='windows:ELI5Mod:v3 (by /u/santi871)')
        self.r.set_oauth_app_info(os.environ['REDDIT_APP_ID'], os.environ['REDDIT_APP_SECRET'], app_uri)
        self.r.refresh_access_information(os.environ['REDDIT_REFRESH_TOKEN'])
        self.r.config.api_request_delay = 1
        print("Connected to reddit.", file=self.slack_log)

        # If we are using the database module
        if self.use_database:
            from modules import database
            print("Connecting to database...", file=self.slack_log)
            self.db = database.Database()  # Create a database object
            print("Connected to database.", file=self.slack_log)
        else:
            self.db = None

        # If we are using the commands module
        if use_commands:
            from modules import commands as commands_module
            self.command_handler = commands_module.CommandsHandler(self, self.s, self.subreddit, self.db)
            self.create_thread(self.listen_to_chat)  # Start a thread to watch Slack chat

        # If we are using the filters module
        if use_filters:
            from modules import filters
            self.filters = filters.Filters(self.r, self.s, self.db, self.subreddit)  # Create an instance of Filters
            self.create_thread(self.scan_new_posts)  # Start a thread to scan incoming submissions

        # Get an instance of UserNotes
        self.un = puni.UserNotes(self.r, self.r.get_subreddit(self.subreddit))

        print("Done initializing.", file=self.slack_log)

    def create_thread(self, method):

        # Threads need their own authenticated reddit instance, so we make one
        app_uri = 'https://127.0.0.1:65010/authorize_callback'
        thread_r = praw.Reddit(user_agent='windows:ELI5Mod:v3 (by /u/santi871)')
        thread_r.set_oauth_app_info(os.environ['REDDIT_APP_ID'], os.environ['REDDIT_APP_SECRET'], app_uri)
        thread_r.refresh_access_information(os.environ['REDDIT_REFRESH_TOKEN'])
        thread_r.config.api_request_delay = 1

        # Create a thread with the method and reddit instance we called
        thread = CreateThread(1, str(method) + " thread", method, thread_r, self.slack_log)
        thread.start()

    def listen_to_chat(self, r):

        # Listen for Slack events
        for eventobj in self.s.events():

            if eventobj.event.get('text') is not None and eventobj.event.get('user') != 'eli5-bot':

                channel = eventobj.event.get('channel')
                message = eventobj.event.get('text')
                split_message = message.split()
                command = split_message[0][1:]

                try:
                    if split_message[0][0] == "!":
                        getattr(self.command_handler, command)(r, eventobj.event)
                        if self.db is not None:
                            self.db.insert_entry('command', slack_event=eventobj.event)
                except AttributeError:
                    self.s.send_msg('Command not found. Use !commands to see a list of available commands',
                                    channel_name=channel, confirm=False)
                    self.slack_log.write(traceback.format_exc())
                    continue
                except Exception as e:
                    self.s.send_msg('Failed to run command. Exception: %s' % e, channel_name=channel,
                                    confirm=False)
                    self.slack_log.write(traceback.format_exc())

    def scan_new_posts(self, r):

        while True:

            try:
                for submission in praw.helpers.submission_stream(r, self.subreddit, limit=10, verbosity=0):
                    self.filters.run_filters(submission)
            except TypeError:
                time.sleep(1)
                continue
            except:
                self.slack_log.write(traceback.format_exc())

'''

    def check_reports(self, r):

        already_done_reports = []

        while True:

            try:
                reported_submissions = r.get_reports(self.subreddit)

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

'''











        
        

    


