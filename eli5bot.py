import praw
import OAuth2Util
import sys
import os
import puni
import datetime
import urllib.parse
import psycopg2
import time
from imgurpython import ImgurClient
import matplotlib.pyplot as plt


class BotMod:


    'Main class for BotMod'

    def __init__(self, s, devmode=False):

        print("Initializing BotMod...")
        self.s = s
        self.devmode = devmode
        self.listening = False
        self.channel = None
        self.subreddit = None
        self.refreshing = True
        self.usergroup_owner = ['santi871']
        self.usergroup_mod = ['santi871', 'akuthia', 'mason11987', 'mike_pants', 'mjcapples', 'securethruobscure', 'snewzie', 'teaearlgraycold', 'thom.willard']

        print("Connecting to reddit...")

        self.r = praw.Reddit(user_agent='windows:ELI5Mod:v2 (by /u/santi871)')
        self.o = OAuth2Util.OAuth2Util(self.r)
        self.o.refresh(force=True)

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
            "CREATE TABLE IF NOT EXISTS MODMAIL (ID SERIAL PRIMARY KEY, URL TEXT UNIQUE, AUTHOR TEXT, SUBJECT TEXT, BODY TEXT, DATE TEXT)")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS SHADOWBANS "
            "(ID SERIAL PRIMARY KEY,"
            "USERNAME TEXT UNIQUE,"
            "REASON TEXT, "
            "DATE TEXT, "
            "BY TEXT)")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS BANS (ID SERIAL PRIMARY KEY, USERNAME TEXT UNIQUE, LENGTH TEXT, REASON TEXT, AUTHOR TEXT, DATE TEXT)")

        print("Connected to database")

        self.startBot()

    def startBot(self):

        if self.devmode:
            self.channel = "eli5bot-dev"
            self.subreddit = "santi871"
        else:
            self.channel = "general"
            self.subreddit = "explainlikeimfive"

        self.subreddit2 = self.r.get_subreddit(self.subreddit)
        self.un = puni.UserNotes(self.r, self.subreddit2)

        msg = self.s.send_msg("Ready.", channel_name=self.channel)
        print("Ready")

    def listenToChat(self):

        self.listening = True

        while self.listening:
            event = self.s.get_event()
            slack_event = event.event

            if slack_event.get('type') == 'message':

                content = slack_event.get('text')
                sender = slack_event.get('user')

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
            msg = self.s.send_msg('Failed to run command.\n Exception: %s' % e, channel_name=self.subreddit)    


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

                        link = "https://www.reddit.com/message/messages/%s"  % reply.id

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
        history = {}
        totalKarma = 0
        limit = 500
        user = self.r.get_redditor(username)
        totalKarma = 0
        x = []
        y = []

        for comment in user.get_comments(limit=limit):

            displayname = comment.subreddit.display_name

            if displayname not in subredditNames:
                subredditNames.append(displayname)

            subredditTotal.append(displayname)

            totalKarma = totalKarma + int(comment.score)

            x.append(datetime.datetime.utcfromtimestamp(float(comment.created_utc)))
            y.append(comment.score)
            
            i+=1

        totalCommentsRead = i

        for subreddit in subredditNames:

            i = subredditTotal.count(subreddit)
            commentsInSubreddit.append(i)
            totalComments = totalComments + i

        i = 0

        for subreddit in subredditNames:
            
            if commentsInSubreddit[i] > (totalCommentsRead/(20*(limit/200))/(len(subredditNames)/30)):
                history[subreddit] = commentsInSubreddit[i]

            i+=1


        historyTuples = sorted(history.items(), key=lambda x: x[1])

        for each_tuple in historyTuples:

            orderedSubredditNames.append(each_tuple[0])
            orderedCommentsInSubreddit.append(each_tuple[1])

        labels = orderedSubredditNames
        sizes = orderedCommentsInSubreddit
        colors = ['yellowgreen', 'gold', 'lightskyblue', 'lightcoral', 'teal', 'chocolate', 'olivedrab', 'tan']
        plt.subplot(211)
        plt.rcParams['font.size'] = 8
        plt.pie(sizes, labels=labels, colors=colors,
                autopct=None, shadow=True, startangle=90)
        plt.axis('equal')
        plt.subplot(212)
        plt.rcParams['font.size'] = 10
        plt.plot_date(x, y)
        plt.grid()
        plt.xlabel('Comment date')
        plt.ylabel('Karma of comment')

        filename = username + "_summary.png"

        plt.savefig(filename)

        path = os.path.dirname(os.path.realpath(__file__)) + "/" + filename
        
        link = self.imgur.upload_from_path(path, config=None, anon=True)
        msg = self.s.send_msg("Showing summary for /u/" + username + ". Total comments read: %d" % totalCommentsRead, channel_name=self.channel)
        msg = self.s.send_msg(link['link'], channel_name=self.channel)
        msg = self.s.send_msg("Average karma: %d" % (totalKarma/totalCommentsRead), channel_name=self.channel)
        msg = self.s.send_msg('User profile: ' + "https://www.reddit.com/user/" + username, channel_name=self.channel)
                
        plt.clf()
        

        
        

    


