import datetime
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import numpy as np
import math
from imgurpython import ImgurClient
import puni
import os
import sys
import datetime
import traceback
from modules import utilities
from modules import filters


class CommandsHandler:

    """This class handles commands, you can define new commands here"""

    def __init__(self, obj, s, subreddit, log, db=None):

        self.obj = obj
        self.un = None
        self.s = s
        self.db = db
        self.subreddit = subreddit
        self.log = log
        self.un = None

        self.usergroup_owner = 'santi871'
        self.usergroup_mod = ('santi871', 'akuthia', 'mason11987', 'mike_pants', 'mjcapples', 'securethruobscure',
                              'snewzie', 'teaearlgraycold', 'thom.willard', 'yarr', 'cow_co', 'sterlingphoenix',
                              'hugepilchard', 'curmudgy', 'h2g2_researcher', 'jim777ps3', 'letstrythisagain_',
                              'mr_magnus', 'terrorpaw', 'kodack10')

        self.imgur = ImgurClient(os.environ['IMGUR_CLIENT_ID'], os.environ['IMGUR_CLIENT_SECRET'])

        self.docs = []

        for name, f in CommandsHandler.__dict__.items():
            if callable(f) and f.__doc__ is not None and name != 'monitor_chat':
                docstring = f.__doc__
                new_docstring = docstring.replace('\n', '')
                self.docs.append(new_docstring)

    def monitor_chat(self, r):

        self.un = puni.UserNotes(r, r.get_subreddit(self.subreddit))

        for eventobj in self.s.events():

            if eventobj.event.get('text') is not None and eventobj.event.get('user') != 'eli5-bot':

                channel = eventobj.event.get('channel')
                message = eventobj.event.get('text')
                split_message = message.split()
                command = split_message[0][1:]

                try:
                    if split_message[0][0] == "!":
                        getattr(self, command)(r, eventobj.event)
                        if self.db is not None:
                            self.db.insert_entry('command', slack_event=eventobj.event)
                except AttributeError:
                    self.s.send_msg('Command not found. Use !commands to see a list of available commands',
                                    channel_name=channel, confirm=False)
                    self.log.write(traceback.format_exc())
                    continue
                except Exception as e:
                    self.s.send_msg('Failed to run command. Exception: %s' % e, channel_name=channel,
                                    confirm=False)
                    self.log.write(traceback.format_exc())

    #  ----------- DEFINE COMMANDS HERE -----------

    def commands(self, *args):

        event_args = args[1]

        msg = '\n'.join(self.docs)

        self.s.send_msg(msg, channel_name=event_args['channel'], confirm=False)

    def shadowban(self, *args):

        """*!shadowban [user] [reason]:* Shadowbans [user] and adds usernote [reason] - USERNAME IS CASE SENSITIVE!"""

        r = args[0]
        event_args = args[1]
        split_event_args = event_args['text'].split()

        if event_args['user'] in self.usergroup_mod:

            if len(split_event_args) >= 3:

                self.s.send_msg('Shadowbanning user "%s" for reason "%s"...' % (split_event_args[1],
                                                                                ' '.join(split_event_args[2:])),
                                channel_name=event_args['channel'], confirm=False)

                wiki_page = r.get_wiki_page(self.subreddit, "config/automoderator")
                wiki_page_content = wiki_page.content_md

                beg_ind = wiki_page_content.find("shadowbans")
                end_ind = wiki_page_content.find("#end shadowbans", beg_ind)
                username = split_event_args[1]
                reason = ' '.join(split_event_args[2:])

                try:
                    n = puni.Note(username, "Shadowbanned, reason: %s" % reason, event_args['user'], '', 'botban')

                    replacement = ', "%s"]' % username

                    newstr = wiki_page_content[:beg_ind] + \
                             wiki_page_content[beg_ind:end_ind].replace("]", replacement) + \
                             wiki_page_content[end_ind:]

                    r.edit_wiki_page(self.subreddit, "config/automoderator", newstr,
                                     reason='ELI5_ModBot shadowban user "/u/%s" executed by "/u/%s"'
                                     % (username, event_args['user']))

                    if self.db is not None:
                        self.db.insert_entry("shadowban", user=username, reason=reason, author=event_args['user'])

                    self.un.add_note(n)
                    self.s.send_msg('Shadowbanned user: ' + "https://www.reddit.com/user/" + username,
                                    channel_name=event_args['channel'], confirm=False)

                except Exception as e:
                    self.s.send_msg('Failed to shadowban user.', channel_name=event_args['channel'], confirm=False)
                    self.s.send_msg('Exception: %s' % e, channel_name=event_args['channel'], confirm=False)
                    self.log.write(traceback.format_exc())

            else:
                self.s.send_msg('Usage: !shadowban [username] [reason]', channel_name=event_args['channel'],
                                confirm=False)

        else:
            self.s.send_msg('You are not authorized to run that command.', channel_name=event_args['channel'],
                            confirm=False)

    def summary(self, *args):

        """*!summary [user]:* generates a summary of [user]"""

        r = args[0]
        slack_args = args[1]
        split_text = slack_args['text'].split()

        msg = self.s.send_msg('Generating summary, please allow a few seconds...', channel_name=slack_args['channel'],
                              confirm=False)

        i = 0
        total_comments = 0
        subreddit_names = []
        subreddit_total = []
        ordered_subreddit_names = []
        comments_in_subreddit = []
        ordered_comments_in_subreddit = []
        comment_lengths = []
        history = {}
        total_karma = 0
        troll_index = 0
        troll_likelihood = "Low"
        blacklisted_subreddits = ('theredpill', 'rage', 'atheism', 'conspiracy', 'subredditdrama', 'subredditcancer',
                                  'SRSsucks', 'drama', 'undelete', 'blackout2015', 'oppression0', 'kotakuinaction',
                                  'tumblrinaction', 'offensivespeech', 'bixnood')
        total_negative_karma = 0
        limit = 500
        user = r.get_redditor(split_text[1])
        x = []
        y = []
        s = []

        karma_accumulator = 0
        karma_accumulated = []
        karma_accumulated_total = []

        for comment in user.get_comments(limit=limit):

            displayname = comment.subreddit.display_name

            if displayname not in subreddit_names:
                subreddit_names.append(displayname)

            subreddit_total.append(displayname)

            total_karma = total_karma + comment.score

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

        total_comments_read = i

        troll_index *= limit / total_comments_read

        average_karma = np.mean(y)

        if average_karma >= 5 and total_negative_karma > (-70 * (total_comments_read / limit)) and troll_index < 50:
            troll_likelihood = 'Low'

        if troll_index >= 40 or total_negative_karma < (-70 * (total_comments_read / limit)) or average_karma < 1:
            troll_likelihood = 'Moderate'

        if troll_index >= 60 or total_negative_karma < (-130 * (total_comments_read / limit)) or average_karma < -2:
            troll_likelihood = 'High'

        if troll_index >= 80 or total_negative_karma < (-180 * (total_comments_read / limit)) or average_karma < -5:
            troll_likelihood = 'Very high'

        if troll_index >= 100 or total_negative_karma < (-200 * (total_comments_read / limit)) or average_karma < -10:
            troll_likelihood = 'Extremely high'

        print(troll_index)
        print(total_negative_karma)

        for subreddit in subreddit_names:
            i = subreddit_total.count(subreddit)
            comments_in_subreddit.append(i)
            total_comments += i

        i = 0

        for subreddit in subreddit_names:

            if comments_in_subreddit[i] > (total_comments_read / (20 * (limit / 200)) / (len(subreddit_names) / 30)):
                history[subreddit] = comments_in_subreddit[i]

            i += 1

        old_range = 700 - 50
        new_range = 2000 - 50

        for item in comment_lengths:
            n = (((item - 50) * new_range) / old_range) + 50
            s.append(n)

        history_tuples = sorted(history.items(), key=lambda x: x[1])

        for each_tuple in history_tuples:
            ordered_subreddit_names.append(each_tuple[0])
            ordered_comments_in_subreddit.append(each_tuple[1])

        user_karma_atstart = user.comment_karma - math.fabs((np.mean(y) * total_comments_read))

        for item in list(reversed(y)):
            karma_accumulator += item
            karma_accumulated.append(karma_accumulator)

        for item in karma_accumulated:
            karma_accumulated_total.append(user_karma_atstart + item)

        plt.style.use('ggplot')
        labels = ordered_subreddit_names
        sizes = ordered_comments_in_subreddit
        colors = ['yellowgreen', 'gold', 'lightskyblue', 'lightcoral', 'teal', 'chocolate', 'olivedrab', 'tan']
        plt.subplot(3, 1, 1)
        plt.rcParams['font.size'] = 8
        plt.pie(sizes, labels=labels, colors=colors,
                autopct=None, startangle=90)
        plt.axis('equal')
        plt.title('User summary for /u/' + split_text[1], loc='center', y=1.2)

        ax1 = plt.subplot(3, 1, 2)
        x_inv = list(reversed(x))
        plt.rcParams['font.size'] = 10
        plt.scatter(x, y, c=y, vmin=-50, vmax=50, s=s, cmap='RdYlGn')
        ax1.set_xlim(x_inv[0], x_inv[total_comments_read - 1])
        ax1.axhline(y=average_karma, xmin=0, xmax=1, c="lightskyblue", linewidth=2, zorder=4)
        plt.ylabel('Karma of comment')

        ax2 = plt.subplot(3, 1, 3)
        plt.plot_date(x, list(reversed(karma_accumulated_total)), '-r')
        plt.xlabel('Comment date')
        plt.ylabel('Total comment karma')

        filename = split_text[1] + "_summary.png"

        figure = plt.gcf()
        figure.set_size_inches(11, 12)

        plt.savefig(filename)

        path = "/app/" + filename

        link = self.imgur.upload_from_path(path, config=None, anon=True)
        msg = self.s.send_msg("Showing summary for */u/" + split_text[1] +
                              "*. Total comments read: %d" % total_comments_read, channel_name=slack_args['channel'],
                              confirm=False)
        msg = self.s.send_msg(link['link'], channel_name=slack_args['channel'], confirm=False)
        msg = self.s.send_msg("*Troll likelihood (experimental):* " + troll_likelihood,
                              channel_name=slack_args['channel'], confirm=False)
        msg = self.s.send_msg('*User profile:* ' + "https://www.reddit.com/user/" + split_text[1],
                              channel_name=slack_args['channel'], confirm=False)

        plt.clf()

    def rules(self, *args):

        """*!rules [action] [args]:* Actions: add, list, remove. Args: in 'add': words to be filtered, in 'remove': rule
        id to remove, in 'list': none"""

        slack_args = args[1]
        split_text = slack_args['text'].split()

        if slack_args['user'] in self.usergroup_mod:

            if split_text[1] == 'add':

                self.s.send_msg("*This rule will filter submissions containing ALL of the following words:* " +
                                ' '.join(split_text[2:]), channel_name=slack_args['channel'], confirm=False)

                confirmed = utilities.prompt_command_confirm(self.s, slack_args['channel'])

                if confirmed:

                    self.db.insert_entry('recent_event', event_keywords=split_text[2:])

                    msg = self.s.send_msg('*Will now filter submissions containing:* ' + ' '.join(split_text[2:]),
                                          channel_name=slack_args['channel'], confirm=False)

            elif split_text[1] == 'list':

                rules_list = self.db.retrieve_entries('current_events', table_mode=True)

                self.s.send_msg('*List of currently active rules:*', channel_name=slack_args['channel'], confirm=False)

                msg = ''

                if not rules_list:
                    msg = 'There are no currently active rules.'
                else:
                    for rule in rules_list:
                        msg += '*ID:* ' + str(rule[0]) + ' *| Rule - submissions containing:* ' + rule[1] + '\n'

                self.s.send_msg(msg, channel_name=slack_args['channel'], confirm=False)

            elif split_text[1] == 'remove':

                self.s.send_msg('*Attempting to remove rule, ID %s...*' % split_text[2],
                                channel_name=slack_args['channel'], confirm=False)

                try:
                    self.db.delete_entry('current_events', split_text[2])
                    self.s.send_msg('*Successfully removed rule.*',
                                    channel_name=slack_args['channel'], confirm=False)
                except Exception as e:
                    self.s.send_msg('*Failed to remove rule.*\n*Exception:* ' + str(e),
                                    channel_name=slack_args['channel'], confirm=False)

        else:
            msg = self.s.send_msg('You are not allowed to do that.',
                                  channel_name=slack_args['channel'], confirm=False)

    def reboot(self, *args):

        """*!reboot:* restarts the bot"""

        slack_args = args[1]

        confirmed = utilities.prompt_command_confirm(self.s, slack_args['channel'])

        if confirmed:

            self.s.send_msg('Restarting bot...',
                            channel_name=slack_args['channel'], confirm=False)

            os.execl(sys.executable, sys.executable, *sys.argv)

    def repost(self, *args):

        """*!repost [id]:* flairs submission [id] as a repost and leaves sticky boilerplate comment"""

        r = args[0]
        slack_args = args[1]
        split_text = slack_args['text'].split()

        self.s.send_msg('Marking submission "%s" as a repost...' % split_text[1],
                        channel_name=slack_args['channel'], confirm=False)

        submisssion = r.get_submission(submission_id=split_text[1])

        filters.handle_repost(r, submisssion, search_query=None, flair_and_comment=True)

        self.s.send_msg('Done.',
                        channel_name=slack_args['channel'], confirm=False)

    def onlineusers(self, *args):

        """*!onlineusers:* generates a plot of online users over time"""

        slack_args = args[1]
        users = []
        date_strings = []
        dates = []

        self.s.send_msg('Generating plot...',
                        channel_name=slack_args['channel'], confirm=False)

        online_users_tuples = self.db.retrieve_entries('online_users')

        for each_tuple in online_users_tuples:

            users.append(each_tuple[0])
            date_strings.append(each_tuple[1])

        del date_strings[0]
        del users[0]

        for date in date_strings:
            dates.append(datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S"))

        plt.style.use('fivethirtyeight')
        plt.plot_date(dates, users, '-')

        formatter = DateFormatter('%Y-%m-%d %H:%M')
        plt.gcf().axes[0].xaxis.set_major_formatter(formatter)
        plt.title("Users online in ELI5")

        filename = 'onlineusers.png'

        figure = plt.gcf()
        figure.set_size_inches(20, 7)

        plt.savefig(filename)

        path = "/app/" + filename
        link = self.imgur.upload_from_path(path, config=None, anon=True)
        plt.clf()
        self.s.send_msg(link['link'], channel_name=slack_args['channel'], confirm=False)





