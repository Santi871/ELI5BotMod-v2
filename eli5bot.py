import praw
import os
import puni
import time
import threading
import traceback
import configparser
import datetime
from modules import utilities
import requests.exceptions
import copy


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
        self.slack_log = utilities.SlackLogger(s, slack_log_channel)

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
            self.command_handler = commands_module.CommandsHandler(self, self.s, self.subreddit, self.slack_log,
                                                                   self.db)
            self.create_thread(self.listen_to_chat)  # Start a thread to watch Slack chat

        # If we are using the filters module
        if use_filters:
            from modules import filters
            self.filters = filters.Filters(self.r, self.s, self.db, self.subreddit)  # Create an instance of Filters
            self.create_thread(self.scan_new_posts)  # Start a thread to scan incoming submissions

        # Get an instance of UserNotes
        self.un = puni.UserNotes(self.r, self.r.get_subreddit(self.subreddit))

        self.create_thread(self.log_online_users)
        self.create_thread(self.handle_unflaired)

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

        self.command_handler.monitor_chat(r)

    def scan_new_posts(self, r):

        while True:

            try:
                for submission in praw.helpers.submission_stream(r, self.subreddit, limit=10, verbosity=0):
                    self.filters.run_filters(submission)
            except TypeError:
                time.sleep(1)
                continue
            except (praw.errors.HTTPException, requests.exceptions.ReadTimeout):
                time.sleep(1)
                continue
            except:
                self.slack_log.write(traceback.format_exc())

    def log_online_users(self, r):

        online_users_logger = utilities.OnlineUsersLogger(r, self.db, self.subreddit)
        online_users_logger.log_to_database(3600)

    def handle_unflaired(self, r):

        unflaired_submissions_ids = []
        unflaired_submissions = []

        while True:

            lowest_timestamp = datetime.datetime.now() - datetime.timedelta(minutes=30)
            highest_timestamp = datetime.datetime.now() - datetime.timedelta(minutes=2)

            try:
                submissions = praw.helpers.submissions_between(r, 'explainlikeimfive',
                                                               lowest_timestamp=lowest_timestamp.timestamp(),
                                                               highest_timestamp=highest_timestamp.timestamp())

                for submission in submissions:
                    if submission.id not in unflaired_submissions_ids and submission.link_flair_text is None:

                        print(submission.id, file=self.slack_log)
                        submission.report("Unassigned flair")
                        submission.remove()

                        s1 = submission.author
                        s2 = 'https://www.reddit.com/message/compose/?to=/r/explainlikeimfive'
                        comment = ("""Hi /u/%s,

It looks like you haven't assigned a category flair to your question, so it has been automatically removed.
You can assign a category flair to your question by clicking the *flair* button under it.

Shortly after you have assigned a category flair to your question, it will be automatically re-approved and this message
will be deleted.

---

*I am a bot, and this action was performed automatically.
Please [contact the moderators](%s) if you have any questions or concerns*
""") % (s1, s2)
                        comment_obj = submission.add_comment(comment)
                        comment_obj.distinguish(sticky=True)
                        unflaired_submissions_ids.append(submission.id)
                        unflaired_submissions.append((submission.id, comment_obj.fullname))

                unflaired_submissions_duplicate = copy.deepcopy(unflaired_submissions)

                for submission_tuple in unflaired_submissions_duplicate:

                    refreshed_submission = r.get_submission(submission_id=submission_tuple[0])

                    comment_obj = r.get_info(thing_id=submission_tuple[1])

                    if refreshed_submission.link_flair_text is not None:
                        refreshed_submission.approve()

                        comment_obj.remove()

                        unflaired_submissions.remove(submission_tuple)
                        unflaired_submissions_ids.remove(submission_tuple[0])

                    else:

                        submission_time = datetime.datetime.fromtimestamp(refreshed_submission.created_utc)
                        d = datetime.datetime.now() - submission_time
                        delta_time = d.total_seconds()

                        if delta_time >= 10800:

                            unflaired_submissions.remove(submission_tuple)
                            unflaired_submissions_ids.remove(submission_tuple[0])
                            comment_obj.remove()

            except:
                self.slack_log.write(traceback.format_exc())
                continue

            time.sleep(60)

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











        
        

    


