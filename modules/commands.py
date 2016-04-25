import datetime
import matplotlib.pyplot as plt
import numpy as np
import math
from imgurpython import ImgurClient
import puni
import os
import sys


class CommandsHandler:

    """This class handles commands, you can define new commands here"""

    def __init__(self, obj, s, subreddit, db=None):

        self.obj = obj
        self.un = None
        self.s = s
        self.db = db
        self.subreddit = subreddit

        self.usergroup_owner = 'santi871'
        self.usergroup_mod = ('santi871', 'akuthia', 'mason11987', 'mike_pants', 'mjcapples', 'securethruobscure',
                              'snewzie', 'teaearlgraycold', 'thom.willard', 'yarr')

        self.imgur = ImgurClient(os.environ['IMGUR_CLIENT_ID'], os.environ['IMGUR_CLIENT_SECRET'])

        self.docs = []

        for name, f in CommandsHandler.__dict__.items():
            if callable(f) and f.__doc__ is not None:
                self.docs.append(f.__doc__)

    #  ----------- DEFINE COMMANDS HERE -----------

    def commands(self, *args):

        event_args = args[1]

        msg = '\n'.join(self.docs)

        self.s.send_msg(msg, channel_name=event_args['channel'], confirm=False)

    def shadowban(self, *args):

        """!shadowban [user] [reason]: Shadowbans [user] and adds usernote [reason] - USERNAME IS CASE SENSITIVE!"""

        r = args[0]
        event_args = args[1]

        un = puni.UserNotes(r, r.get_subreddit(self.subreddit))

        if event_args['user'] in self.usergroup_mod:

            if len(event_args['text']) >= 3:

                self.s.send_msg('Shadowbanning user "%s" for reason "%s"...' % (event_args['text'][1],
                                                                                ' '.join(event_args['text'][2:])),
                                channel_name=event_args['channel'], confirm=False)

                wiki_page = r.get_wiki_page(self.subreddit, "config/automoderator")
                wiki_page_content = wiki_page.content_md

                beg_ind = wiki_page_content.find("shadowbans")
                end_ind = wiki_page_content.find("#end shadowbans", beg_ind)
                username = event_args['text'][1]
                reason = event_args['text'][2:]

                try:
                    if self.db is not None:
                        self.db.insert_entry("shadowban", user=username, reason=reason, author=event_args['user'])

                    n = puni.Note(username, "Shadowbanned, reason: %s" % reason, event_args['user'], '', 'botban')
                    un.add_note(n)

                    replacement = ', "%s"]' % username

                    newstr = wiki_page_content[:beg_ind] + \
                             wiki_page_content[beg_ind:end_ind].replace("]", replacement) + \
                             wiki_page_content[end_ind:]

                    r.edit_wiki_page(self.subreddit, "config/automoderator", newstr,
                                     reason='ELI5_ModBot shadowban user "/u/%s" executed by "/u/%s"'
                                     % (username, event_args['user']))

                    self.s.send_msg('Shadowbanned user: ' + "https://www.reddit.com/user/" + username,
                                    channel_name=event_args['channel'], confirm=False)

                except Exception as e:
                    self.s.send_msg('Failed to shadowban user.', channel_name=event_args['channel'], confirm=False)
                    self.s.send_msg('Exception: %s' % e, channel_name=event_args['channel'], confirm=False)

            else:
                self.s.send_msg('Usage: !shadowban [username] [reason]', channel_name=event_args['channel'],
                                confirm=False)

        else:
            self.s.send_msg('You are not authorized to run that command.', channel_name=event_args['channel'],
                            confirm=False)

    def summary(self, *args):

        """!summary [user]: generates a summary of [user]"""

        r = args[0]
        slack_args = args[1]

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
        user = r.get_redditor(slack_args['text'][1])
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
        plt.title('User summary for /u/' + slack_args['text'][1], loc='center', y=1.2)

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

        filename = slack_args['text'][1] + "_summary.png"

        figure = plt.gcf()
        figure.set_size_inches(11, 12)

        plt.savefig(filename)

        path = "/app/" + filename

        link = self.imgur.upload_from_path(path, config=None, anon=True)
        msg = self.s.send_msg("Showing summary for */u/" + slack_args['text'][1] +
                              "*. Total comments read: %d" % total_comments_read, channel_name=slack_args['channel'])
        msg = self.s.send_msg(link['link'], channel_name=slack_args['channel'], confirm=False)
        msg = self.s.send_msg("*Troll likelihood (experimental):* " + troll_likelihood,
                              channel_name=slack_args['channel'], confirm=False)
        msg = self.s.send_msg('*User profile:* ' + "https://www.reddit.com/user/" + slack_args['text'][1],
                              channel_name=slack_args['channel'], confirm=False)

        plt.clf()

    def addrule(self, *args):

        """!addrule [words to be filtered]: Creates a rule to filter new questions that contain ALL the words passed"""

        slack_args = args[1]

        self.db.insert_entry('recent_event', event_keywords=slack_args['text'][1:])

        msg = self.s.send_msg('*Will now filter submissions containing:* ' + ' '.join(slack_args['text'][1:]),
                              channel_name=slack_args['channel'], confirm=False)

    def reboot(self, *args):

        """!reboot: restarts the bot"""

        slack_args = args[1]

        self.s.send_msg('Restarting bot...',
                        channel_name=slack_args['channel'], confirm=False)

        os.execl(sys.executable, sys.executable, *sys.argv)



