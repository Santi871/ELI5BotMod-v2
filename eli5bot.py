import praw
import os
import puni
import datetime
import urllib.parse
import psycopg2
import time
import nltk
import threading
import modules.commands as commands_module


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

    def __init__(self, s, devmode=False, use_database=False, use_commands=True):

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

                args = slack_event.get('text')
                channel = slack_event.get('channel')

                args_dict = commands_module.get_slack_event_args(slack_event)

                print(args[0])
                print(args[0][1:])

                try:
                    if args[0] == "!":
                        commands_module.Command.commands_dict[args[0][1:]](self, args_dict)
                except Exception as e:
                    self.s.send_msg('Failed to run command. Exception: %s' % e, channel_name=channel)

    def repost_detector(self, r):

        self.already_done_reposts = []

        while True:

            try:
                submissions = r.get_subreddit('explainlikeimfive').get_new(limit=5)
                submissions_list = list(submissions)
                self.search_reposts(submissions_list)
                time.sleep(10)

            except Exception:
                time.sleep(2)

    def search_reposts(self, submissions):

        tags = ('NN', 'NNP', 'NNPS', 'JJ', 'NNS', 'VBG', 'VB', 'VBN', 'CD', 'VBP', 'RB', 'VBD')

        nltk.data.path.append('./nltk_data/')

        for submission in submissions:

            if submission.id not in self.already_done_reposts:

                words_list = []
                total_in_threehours = 0
                title = submission.title
                self.already_done_reposts.append(submission.id)

                tokens = nltk.word_tokenize(title)
                tagged = nltk.pos_tag(tokens)

                for word, tag in tagged:

                    if tag in tags:
                        words_list.append(word)

                search_query = ' '.join(words_list)
                full_search_query = "title:(" + search_query + ")"

                search_result = self.r.search(full_search_query, subreddit="explainlikeimfive", sort='new')
                search_result_list = list(search_result)

                for item in search_result_list:

                    comment_time = datetime.datetime.fromtimestamp(item.created_utc)
                    d = datetime.datetime.now() - comment_time
                    delta_time = d.total_seconds()

                    if int(delta_time / 60) < 180:
                        total_in_threehours += 1

                if len(search_result_list) >= 3:

                    msg_string = "---\n*Potential repost detected*\n" + \
                                 title + '\n' + "*POS tagger output:* " + str(tagged) + '\n' + \
                                 '*Link:* ' + submission.permalink + '\n' + "*Search query:* " + full_search_query + \
                                 '\n' + '*Search results:*\n'

                    for item in search_result_list:
                        msg_string += str(item) + '\n'

                    msg = self.s.send_msg(msg_string, channel_name="eli5bot-dev", confirm=False)

                    submission.report("Potential repost")

                if total_in_threehours >= 3:

                    msg_string = "---\n*Potential large influx of question*\n" + \
                                 title + '\n' + "*Search query:* " + full_search_query + '\n' + '*Link:* ' + \
                                 submission.permalink

                    msg = self.s.send_msg(msg_string, channel_name="eli5bot-dev", confirm=False)

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












        
        

    


