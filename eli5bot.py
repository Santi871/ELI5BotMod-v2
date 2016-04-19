import praw
import sys
import os
import puni
import datetime
import urllib.parse
import psycopg2
import time
from imgurpython import ImgurClient
import matplotlib.pyplot as plt
import numpy as np
import math
import nltk


class BotMod:

    """Main class for BotMod"""

    def __init__(self, s, devmode=False):

        print("Initializing BotMod...")
        self.s = s
        self.devmode = devmode
        self.listening = False
        self.channel = None
        self.subreddit = None
        self.refreshing = True
        self.already_done_reposts = []
        self.usergroup_owner = ['santi871']
        self.usergroup_mod = ['santi871', 'akuthia', 'mason11987', 'mike_pants', 'mjcapples', 'securethruobscure',
                              'snewzie', 'teaearlgraycold', 'thom.willard', 'yarr']

        print("Connecting to reddit...")

        app_uri = 'https://127.0.0.1:65010/authorize_callback'
        self.r = praw.Reddit(user_agent='windows:ELI5Mod:v2 (by /u/santi871)')
        self.r.set_oauth_app_info(os.environ['REDDIT_APP_ID'], os.environ['REDDIT_APP_SECRET'], app_uri)
        self.r.refresh_access_information(os.environ['REDDIT_REFRESH_TOKEN'])

        print("Connected to reddit.")

        self.imgur = ImgurClient(os.environ['IMGUR_CLIENT_ID'], os.environ['IMGUR_CLIENT_SECRET'])

        print("Connecting to database...")

        urllib.parse.uses_netloc.append("postgres")
        self.url = urllib.parse.urlparse(os.environ['DATABASE_URL'])

        self.conn = psycopg2.connect(
                                database=self.url.path[1:],
                                user=self.url.username,
                                password=self.url.password,
                                host=self.url.hostname,
                                port=self.url.port
                                )

        self.cur = self.conn.cursor()

        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS RECENTPOSTS"
            "(ID SERIAL PRIMARY KEY,"
            "TITLE TEXT UNIQUE,"
            "DATE TEXT)")

        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS MODMAIL (ID SERIAL PRIMARY KEY, URL TEXT UNIQUE, AUTHOR TEXT, SUBJECT TEXT, BODY TEXT, DATE TEXT)")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS SHADOWBANS"
            "(ID SERIAL PRIMARY KEY,"
            "USERNAME TEXT UNIQUE,"
            "REASON TEXT, "
            "DATE TEXT, "
            "BY TEXT)")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS BANS (ID SERIAL PRIMARY KEY, USERNAME TEXT UNIQUE, LENGTH TEXT, REASON TEXT, AUTHOR TEXT, DATE TEXT)")

        self.conn.commit()


        print("Connected to database")

        self.startBot()

    def startBot(self):

        if self.devmode:
            #self.channel = "eli5bot-dev"
            self.subreddit = "santi871"
        else:
            #self.channel = "general"
            self.subreddit = "explainlikeimfive"

        self.subreddit2 = self.r.get_subreddit(self.subreddit)
        self.un = puni.UserNotes(self.r, self.subreddit2)

        msg = self.s.send_msg("Successfully connected.", channel_name="eli5bot-dev")
        print("Successfully connected.")

    def listenToChat(self):

        self.listening = True

        while self.listening:
            event = self.s.get_event()
            slack_event = event.event

            if slack_event.get('type') == 'message':

                content = slack_event.get('text')
                sender = slack_event.get('user')
                self.channel = slack_event.get('channel')

                try:
                    foundCommand = content.find("!")

                    if foundCommand == 0:

                        self.handleCommand(content, sender)
                except:
                    pass

        print("Stopped listening")

    def handleCommand(self, content, sender):

        splitContentTwice = content.split(' ', 2)
        splitContent = content.split()

        command = splitContent[0]

        try:
            self.command(command, splitContent, splitContentTwice, sender)
        except Exception as e:
            msg = self.s.send_msg('Failed to run command.\n Exception: %s' % e, channel_name=self.channel)


    def command(self, command, splitContent, splitContentTwice, sender):

        #COMMAND LIST STARTS HERE

        if command == "!shutdown":#SHUTDOWN

            if sender in self.usergroup_owner:
                self.shutdown()
            else:
                msg = self.s.send_msg('You are not authorized to run that command.', channel_name=self.channel)

        elif command == "!reboot":#REBOOT

            if sender in self.usergroup_owner:
                self.reboot()
            else:
                msg = self.s.send_msg('You are not authorized to run that command.', channel_name=self.channel)

        elif command == "!stoplistening": #STOP LISTENING

            if sender in self.usergroup_owner:
                msg = self.s.send_msg('Stopping to listen...', channel_name=self.channel)
                self.listening = False
            else:
                msg = self.s.send_msg('You are not authorized to run that command.', channel_name=self.channel)

        elif command =="!help":#HELP

            print(self.channel)
            msg = self.s.send_msg(#'!lock [submission_id] [reason_to_sticky]: Locks thread and stickies reason in it as a comment\n'
                                 '!shadowban [user] [reason]: Shadowbans user and adds usernote with reason - USERNAME IS CASE SENSITIVE!\n'
                                 '!load [thing] [limit]: Load entries of [thing] into database. [limit] defines how many entries to fetch from reddit. Default limit is None. Current things: modmail, bans.\n'
                                 '!summary [user]: generates a summary of [user]\n'
                                 '!shutdown: exit the bot script\n'
                                 '!reboot: reboot the bot script\n'
                                 '---Made by /u/Santi871 using SlackSocket + PRAW in Python 3.5', channel_name=self.channel)

        #elif splitContent[0]=="!lock": #LOCK THREADS

            #msg = self.s.send_msg('Locking thread id: %s with reason "%s"...' % (splitContentTwice[1], splitContentTwice[2]), channel_name=self.channel)

            #try:
                #submission = self.r.get_submission(submission_id=splitContentTwice[1])
                #comment = submission.add_comment(splitContentTwice[2])
                #comment.sticky()
                #submission.lock()
                #msg = self.s.send_msg('Thread locked successfully.', channel_name=self.channel)

            #except Exception as e:
                #msg = self.s.send_msg('Failed to lock thread.', channel_name=self.channel)
                #msg = self.s.send_msg('Exception: %s' % e, channel_name=self.channel)

        elif splitContent[0]=="!shadowban": #SHADOWBAN

            if sender in self.usergroup_mod:

                if len(splitContentTwice)==3:
                    wiki_page = self.r.get_wiki_page(self.subreddit, "config/automoderator")
                    wiki_page_content = wiki_page.content_md

                    begInd = wiki_page_content.find("shadowbans")
                    endInd = wiki_page_content.find("#end shadowbans", begInd)
                    username = splitContentTwice[1]
                    reason = splitContentTwice[2]
                    date = str(datetime.datetime.utcnow())

                    try:
                        self.cur.execute('''INSERT INTO SHADOWBANS(USERNAME, REASON, DATE, BY) VALUES(%s,%s,%s,%s)''', (username,reason, date, sender))
                        n = puni.Note(username,"Shadowbanned, reason: %s" % reason,sender,'','botban')
                        self.un.add_note(n)

                        replacement = ', "%s"]' % username

                        msg = self.s.send_msg('Shadowbanning user "%s" for reason "%s"...' % (splitContentTwice[1], splitContentTwice[2]), channel_name=self.channel)

                        newstr = wiki_page_content[:begInd] + wiki_page_content[begInd:endInd].replace("]", replacement) + wiki_page_content[endInd:]

                        self.r.edit_wiki_page(self.subreddit, "config/automoderator", newstr, reason='ELI5_ModBot shadowban user "/u/%s" executed by "/u/%s"' % (username, sender))

                        msg = self.s.send_msg('Shadowbanned user: ' + "https://www.reddit.com/user/" + username, channel_name=self.channel)

                    except Exception as e:
                        msg = self.s.send_msg('Failed to shadowban user.', channel_name=self.channel)
                        msg = self.s.send_msg('Exception: %s' % e, channel_name=self.channel)

                    self.conn.commit()

                else:
                    msg = self.s.send_msg('Usage: !shadowban [username] [reason]', channel_name=self.channel)

            else:
                msg = self.s.send_msg('You are not authorized to run that command.', channel_name=self.channel)

        elif splitContent[0]=="!load": #LOAD

            if splitContent[1]=="modmail": # LOAD MODMAIL

                if len(splitContent)==3:

                    limit = int(splitContent[2])

                else:

                    limit = None

                try:
                    self.loadModmail(limit)
                except Exception as e:
                    msg = self.s.send_msg('Failed to load modmail.', channel_name=self.channel)
                    msg = self.s.send_msg('Exception: %s' % e, channel_name=self.channel)

            if splitContent[1]=="bans": # LOAD BANS

                if len(splitContent)==3:

                    limit = int(splitContent[2])

                else:

                    limit = None

                try:
                    self.loadBans(limit)
                except Exception as e:
                    msg = self.s.send_msg('Failed to load bans.', channel_name=self.channel)
                    msg = self.s.send_msg('Exception: %s' % e, channel_name=self.channel)


        elif splitContent[0]=="!delete":#DELETE ROWS FROM TABLE

            if sender in self.usergroup_owner:

                try:
                    self.cur.execute('DELETE FROM %s' % splitContent[1])
                    self.conn.commit()
                    msg = self.s.send_msg('Successfully deleted all entries from %s' % splitContent[1], channel_name=self.channel)

                except Exception as e:
                    msg = self.s.send_msg('Failed to delete entries.', channel_name=self.channel)
                    msg = self.s.send_msg('Exception: %s' % e, channel_name=self.channel)

        elif splitContent[0]=="!summary":#SUMMARY


            try:
                msg = self.s.send_msg('Generating summary, please allow a few seconds...', channel_name=self.channel)
                self.summary(splitContent[1])


            except Exception as e:
                msg = self.s.send_msg('Failed to generate summary.', channel_name=self.channel)
                msg = self.s.send_msg('Exception: %s' % e, channel_name=self.channel)



        #END COMMAND LIST

        else:
            msg = self.s.send_msg('Command not recognized.', channel_name=self.channel)

    def shutdown(self):
        msg = self.s.send_msg('Shutting down...', channel_name=self.channel)
        self.conn.close()
        sys.exit()

    def reboot(self):
        msg = self.s.send_msg('Rebooting...', channel_name=self.channel)
        self.conn.close()
        self.listening = False

    def loadModmail(self, limit):

        entryCount = 0

        msg = self.s.send_msg('Loading modmail into database...', channel_name=self.channel)

        for modmail in self.r.get_mod_mail(self.subreddit, limit=limit):

            link = "https://www.reddit.com/message/messages/%s"  % modmail.id

            try:
                self.cur.execute('''INSERT INTO MODMAIL(URL, AUTHOR, SUBJECT, BODY,DATE) VALUES(%s,%s,%s,%s,%s)''', (link, modmail.author.name,modmail.subject, modmail.body, datetime.datetime.utcfromtimestamp(float(modmail.created_utc))))
                entryCount+=1

            except Exception:
                pass

            self.conn.commit()

            for reply in modmail.replies:

                link = "https://www.reddit.com/message/messages/%s"  % reply.id

                try:
                    self.cur.execute('''INSERT INTO MODMAIL(URL, AUTHOR, SUBJECT, BODY,DATE) VALUES(%s,%s,%s,%s,%s)''', (link, reply.author.name,reply.subject, reply.body, datetime.datetime.utcfromtimestamp(float(reply.created_utc))))
                    entryCount+=1

                except Exception:
                    pass

                self.conn.commit()

        msg = self.s.send_msg('Loaded %d modmail entries into database.' % entryCount, channel_name=self.channel)

    def loadBans(self, limit):

        msg = self.s.send_msg('Loading bans into database...', channel_name=self.channel)
        entryCount = 0

        for banned in self.r.get_mod_log(self.subreddit, action="banuser", limit=limit):

            try:
                self.cur.execute('''INSERT INTO BANS(USERNAME, LENGTH, REASON, AUTHOR, DATE) VALUES(%s,%s,%s,%s,%s)''', (banned.target_author,banned.details, banned.description, banned.mod, datetime.datetime.utcfromtimestamp(float(banned.created_utc))))
                entryCount+=1

            except Exception:
                pass

            self.conn.commit()

        msg = self.s.send_msg('Loaded %d ban entries into database.' % entryCount, channel_name=self.channel)

    def refreshModmail(self, limit=15):

        while self.refreshing:

            try:

                for modmail in self.r.get_mod_mail("explainlikeimfive", limit=limit):

                    link = "https://www.reddit.com/message/messages/%s"  % modmail.id

                    try:
                        self.cur.execute('''INSERT INTO MODMAIL(URL, AUTHOR, SUBJECT, BODY,DATE) VALUES(%s,%s,%s,%s,%s)''', (link, modmail.author.name,modmail.subject, modmail.body, datetime.datetime.utcfromtimestamp(float(modmail.created_utc))))

                    except Exception:
                        pass

                    self.conn.commit()

                    for reply in modmail.replies:

                        link = "https://www.reddit.com/message/messages/%s" % reply.id

                        try:
                            self.cur.execute('''INSERT INTO MODMAIL(URL, AUTHOR, SUBJECT, BODY,DATE) VALUES(%s,%s,%s,%s,%s)''', (link, reply.author.name,reply.subject, reply.body, datetime.datetime.utcfromtimestamp(float(reply.created_utc))))

                        except Exception:
                            pass

                        self.conn.commit()

            except:
                pass

            time.sleep(30)

    def refreshBans(self, limit=5):

        while self.refreshing:

            try:

                for banned in self.r.get_mod_log("explainlikeimfive", action="banuser", limit=limit):

                    try:
                        self.cur.execute('''INSERT INTO BANS(USERNAME, LENGTH, REASON, AUTHOR, DATE) VALUES(%s,%s,%s,%s,%s)''', (banned.target_author,banned.details, banned.description, banned.mod, datetime.datetime.utcfromtimestamp(float(banned.created_utc))))
                        n = puni.Note(banned.target_author, "Banned: %s" % banned.description,banned.mod,'','ban')
                        self.un.add_note(n)

                    except Exception:
                        pass

                    self.conn.commit()

            except:
                pass

            time.sleep(30)

    def logPosts(self, limit=20):

        while True:

            for submission in self.r.get_subreddit('explainlikeimfive').get_new(limit=20):

                try:
                    self.cur.execute('''INSERT INTO RECENTPOSTS(TITLE, DATE) VALUES(%s,%s)''', (submission.title, datetime.datetime.utcfromtimestamp(float(submission.created_utc))))

                except Exception:
                    pass

                self.conn.commit()

            time.sleep(30)

    def listFromDatabase(self, table):

        self.cur.execute('SELECT * FROM %s' % table)
        entryTuples = self.cur.fetchall()


    def summary(self, username):

        i=0
        totalComments = 0
        subredditNames = []
        subredditTotal = []
        orderedSubredditNames = []
        commentsInSubreddit = []
        orderedCommentsInSubreddit = []
        comment_lengths = []
        history = {}
        totalKarma = 0
        troll_index = 0
        troll_likelihood = "Low"
        blacklisted_subreddits = ('theredpill', 'rage', 'atheism', 'conspiracy', 'subredditdrama', 'subredditcancer',
                                  'SRSsucks', 'drama', 'undelete', 'blackout2015', 'oppression0', 'kotakuinaction',
                                  'tumblrinaction', 'offensivespeech')
        total_negative_karma = 0
        limit = 500
        user = self.r.get_redditor(username)
        totalKarma = 0
        x = []
        y = []
        s = []
        karma_accumulator = 0
        karma_accumulated = []
        karma_accumulated_total = []

        for comment in user.get_comments(limit=limit):

            displayname = comment.subreddit.display_name

            if displayname not in subredditNames:
                subredditNames.append(displayname)

            subredditTotal.append(displayname)

            totalKarma = totalKarma + comment.score

            x.append(datetime.datetime.utcfromtimestamp(float(comment.created_utc)))
            y.append(comment.score)
            comment_lengths.append(len(comment.body.split()))

            if comment.score < 0:
                total_negative_karma += comment.score

            if len(comment.body) < 200:
                troll_index += 0.1

            if displayname in blacklisted_subreddits:
                troll_index += 2.5

            i += 1

        totalCommentsRead = i

        troll_index *= limit/totalCommentsRead

        #comment_lengths_mean = np.mean(comment_lengths)

        average_karma = np.mean(y)

        if average_karma >= 5 and total_negative_karma > (-70 * (totalCommentsRead/limit)) and troll_index < 50:
            troll_likelihood = 'Low'

        if troll_index >= 40 or total_negative_karma < (-70 * (totalCommentsRead/limit)) or average_karma < 1:
            troll_likelihood = 'Moderate'

        if troll_index >= 60 or total_negative_karma < (-130 * (totalCommentsRead/limit)) or average_karma < -2:
            troll_likelihood = 'High'

        if troll_index >= 80 or total_negative_karma < (-180 * (totalCommentsRead / limit)) or average_karma < -5:
            troll_likelihood = 'Very high'

        if troll_index >= 100 or total_negative_karma < (-200 * (totalCommentsRead / limit)) or average_karma < -10:
            troll_likelihood = 'Extremely high'

        print(troll_index)
        print(total_negative_karma)

        for subreddit in subredditNames:

            i = subredditTotal.count(subreddit)
            commentsInSubreddit.append(i)
            totalComments += i

        i = 0

        for subreddit in subredditNames:

            if commentsInSubreddit[i] > (totalCommentsRead/(20*(limit/200))/(len(subredditNames)/30)):
                history[subreddit] = commentsInSubreddit[i]

            i+=1

        OldRange = (max(comment_lengths) - min(comment_lengths))
        NewRange = 2000 - 50

        for item in comment_lengths:
            n = (((item - min(comment_lengths)) * NewRange) / OldRange) + 50
            s.append(n)

        historyTuples = sorted(history.items(), key=lambda x: x[1])

        for each_tuple in historyTuples:

            orderedSubredditNames.append(each_tuple[0])
            orderedCommentsInSubreddit.append(each_tuple[1])

        user_karma_atstart = user.comment_karma - math.fabs((np.mean(y) * totalCommentsRead))

        for item in list(reversed(y)):
            karma_accumulator += item
            karma_accumulated.append(karma_accumulator)

        for item in karma_accumulated:
            karma_accumulated_total.append(user_karma_atstart + item)

        plt.style.use('ggplot')
        labels = orderedSubredditNames
        sizes = orderedCommentsInSubreddit
        colors = ['yellowgreen', 'gold', 'lightskyblue', 'lightcoral', 'teal', 'chocolate', 'olivedrab', 'tan']
        plt.subplot(3, 1, 1)
        plt.rcParams['font.size'] = 8
        plt.pie(sizes, labels=labels, colors=colors,
                autopct=None, startangle=90)
        plt.axis('equal')
        plt.title('User summary for /u/' + username, loc='center', y=1.2)

        ax1 = plt.subplot(3, 1, 2)
        x_inv = list(reversed(x))
        plt.rcParams['font.size'] = 10
        plt.scatter(x, y, c=y, vmin=-50, vmax=50, s=s, cmap='RdYlGn')
        ax1.set_xlim(x_inv[0], x_inv[totalCommentsRead-1])
        ax1.axhline(y=average_karma, xmin=0, xmax=1, c="lightskyblue", linewidth=2, zorder=4)
        plt.ylabel('Karma of comment')

        ax2 = plt.subplot(3, 1, 3)
        plt.plot_date(x, list(reversed(karma_accumulated_total)), '-r')
        plt.xlabel('Comment date')
        plt.ylabel('Total comment karma')

        filename = username + "_summary.png"

        figure = plt.gcf()
        figure.set_size_inches(11, 12)

        plt.savefig(filename)

        path = os.path.dirname(os.path.realpath(__file__)) + "/" + filename

        link = self.imgur.upload_from_path(path, config=None, anon=True)
        msg = self.s.send_msg("Showing summary for */u/" + username + "*. Total comments read: %d" % totalCommentsRead, channel_name=self.channel)
        msg = self.s.send_msg(link['link'], channel_name=self.channel)
        msg = self.s.send_msg("*Troll likelihood (experimental):* " + troll_likelihood, channel_name=self.channel)
        msg = self.s.send_msg('*User profile:* ' + "https://www.reddit.com/user/" + username, channel_name=self.channel)

        plt.clf()

    def repost_detector(self):

        self.already_done_reposts = []

        while True:

            try:
                submissions = self.r.get_subreddit('explainlikeimfive').get_new(limit=5)
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

    def check_reports(self):

        already_done_reports = []

        while True:

            try:
                reported_submissions = self.r.get_reports('explainlikeimfive')

                for submission in reported_submissions:

                    if submission.id not in already_done_reports:

                        author_submissions = self.r.get_redditor(submission.author).get_submitted(limit=500)
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












        
        

    


