import datetime
import psycopg2
import matplotlib.pyplot as plt
import numpy as np
import math
import sys
import puni


def get_slack_event_args(slack_event):

    args = dict()

    args['channel'] = slack_event.get('channel')
    args['content'] = slack_event.get('text').split()
    args['author'] = slack_event.get('user')

    return args


class Commands:

    """Main class for commands, define new commands here"""

    def __init__(self, obj, s, db=None):

        self.obj = obj
        self.r = None
        self.s = s
        self.db = db

        self.usergroup_owner = 'santi871'
        self.usergroup_mod = ('santi871', 'akuthia', 'mason11987', 'mike_pants', 'mjcapples', 'securethruobscure',
                              'snewzie', 'teaearlgraycold', 'thom.willard', 'yarr')

        self.un = puni.UserNotes(self.r, 'explainlikeimfive')

    def assign_reddit_instance(self, r):
        self.r = r

    def handle_command(self, r, slack_event):

        self.r = r
        args = get_slack_event_args(slack_event)
        command = args['content'][0][1:]

        method = None
        try:
            method = getattr(self, command)(args)
        except AttributeError:
            self.s.send_msg('Command not recognized. Enter !commands for a list of commands',
                            channel_name=slack_event.get('channel'))

    #  ----------- DEFINE COMMANDS HERE -----------

    def commands(self, args):

        self.s.send_msg('!shadowban [user] [reason]: Shadowbans user and adds'
                        ' usernote with reason - USERNAME IS CASE SENSITIVE!\n'
                        '!summary [user]: generates a summary of [user]\n'
                        '!shutdown: exit the bot script\n'
                        '!reboot: reboot the bot script\n'
                        '---Made by /u/Santi871 using SlackSocket + PRAW in Python 3.5',
                        channel_name=args['channel'])

    def shadowban(self, args):

        if args['author'] in self.usergroup_mod:

            if len(args['content']) == 3:

                self.s.send_msg('Shadowbanning user "%s" for reason "%s"...' % (args['content'][1],
                                                                                args['content'][2:]),
                                channel_name=args['channel'])

                wiki_page = self.r.get_wiki_page('explainlikeimfive', "config/automoderator")
                wiki_page_content = wiki_page.content_md

                beg_ind = wiki_page_content.find("shadowbans")
                end_ind = wiki_page_content.find("#end shadowbans", beg_ind)
                username = args['content'][1]
                reason = args['content'][2:]

                try:
                    if self.db is not None:
                        self.db.insert_entry("shadowban", user=username, reason=reason, author=args['author'])

                    n = puni.Note(username, "Shadowbanned, reason: %s" % reason, args['author'], '', 'botban')
                    self.un.add_note(n)

                    replacement = ', "%s"]' % username

                    newstr = wiki_page_content[:beg_ind] + \
                             wiki_page_content[beg_ind:end_ind].replace("]", replacement) + \
                             wiki_page_content[end_ind:]

                    self.r.edit_wiki_page('explainlikeimfive', "config/automoderator", newstr,
                                          reason='ELI5_ModBot shadowban user "/u/%s" executed by "/u/%s"'
                                          % (username, args['author']))

                    self.s.send_msg('Shadowbanned user: ' + "https://www.reddit.com/user/" + username,
                                    channel_name=args['channel'])

                except Exception as e:
                    self.s.send_msg('Failed to shadowban user.', channel_name=args['channel'])
                    self.s.send_msg('Exception: %s' % e, channel_name=args['channel'])

            else:
                self.s.send_msg('Usage: !shadowban [username] [reason]', channel_name=args['channel'])

        else:
            self.s.send_msg('You are not authorized to run that command.', channel_name=args['channel'])


'''
    def command(self, args, sender, r):

        command = args[0]

        # COMMAND LIST STARTS HERE

        if command == "!shutdown":  # SHUTDOWN

            if sender in self.usergroup_owner:
                self.shutdown()
            else:
                msg = self.s.send_msg('You are not authorized to run that command.', channel_name=self.channel)

        elif command == "!reboot":  # REBOOT

            if sender in self.usergroup_owner:
                self.reboot()
            else:
                msg = self.s.send_msg('You are not authorized to run that command.', channel_name=self.channel)

        elif command == "!stoplistening":  # STOP LISTENING

            if sender in self.usergroup_owner:
                msg = self.s.send_msg('Stopping to listen...', channel_name=self.channel)
                self.listening = False
            else:
                msg = self.s.send_msg('You are not authorized to run that command.', channel_name=self.channel)

        elif command == "!help":  # HELP

            print(self.channel)
            msg = self.s.send_msg('!shadowban [user] [reason]: Shadowbans user and adds'
                                  ' usernote with reason - USERNAME IS CASE SENSITIVE!\n'
                                  '!summary [user]: generates a summary of [user]\n'
                                  '!shutdown: exit the bot script\n'
                                  '!reboot: reboot the bot script\n'
                                  '---Made by /u/Santi871 using SlackSocket + PRAW in Python 3.5',
                                  channel_name=self.channel)

        elif command == "!shadowban":  # SHADOWBAN

            if sender in self.usergroup_mod:

                if len(args) == 3:
                    wiki_page = r.get_wiki_page(self.subreddit, "config/automoderator")
                    wiki_page_content = wiki_page.content_md

                    beg_ind = wiki_page_content.find("shadowbans")
                    end_ind = wiki_page_content.find("#end shadowbans", beg_ind)
                    username = args[1]
                    reason = args[2:]
                    date = str(datetime.datetime.utcnow())

                    try:
                        if self.use_database:
                            self.db.insert_entry("shadowban", user=username, reason=reason, author=sender)

                        n = puni.Note(username, "Shadowbanned, reason: %s" % reason, sender, '', 'botban')
                        self.un.add_note(n)

                        replacement = ', "%s"]' % username

                        msg = self.s.send_msg('Shadowbanning user "%s" for reason "%s"...' % (split_content_twice[1],
                                                                                              split_content_twice[2]),
                                              channel_name=self.channel)

                        newstr = wiki_page_content[:beg_ind] + \
                                 wiki_page_content[beg_ind:end_ind].replace("]", replacement) + \
                                 wiki_page_content[end_ind:]

                        r.edit_wiki_page(self.subreddit, "config/automoderator", newstr,
                                         reason='ELI5_ModBot shadowban user "/u/%s" executed by "/u/%s"'
                                         % (username, sender))

                        msg = self.s.send_msg('Shadowbanned user: ' + "https://www.reddit.com/user/" + username,
                                              channel_name=self.channel)

                    except Exception as e:
                        msg = self.s.send_msg('Failed to shadowban user.', channel_name=self.channel)
                        msg = self.s.send_msg('Exception: %s' % e, channel_name=self.channel)

                else:
                    msg = self.s.send_msg('Usage: !shadowban [username] [reason]', channel_name=self.channel)

            else:
                msg = self.s.send_msg('You are not authorized to run that command.', channel_name=self.channel)

        elif command == "!summary":  # SUMMARY


            try:
                msg = self.s.send_msg('Generating summary, please allow a few seconds...', channel_name=self.channel)
                self.summary(args[1], r)

            except Exception as e:
                msg = self.s.send_msg('Failed to generate summary.', channel_name=self.channel)
                msg = self.s.send_msg('Exception: %s' % e, channel_name=self.channel)

        # END COMMAND LIST

        else:
            msg = self.s.send_msg('Command not recognized.', channel_name=self.channel)

    def shutdown(self):
        msg = self.s.send_msg('Shutting down...', channel_name=self.channel)
        sys.exit()

    def reboot(self):
        msg = self.s.send_msg('Rebooting...', channel_name=self.channel)
        self.listening = False

    def summary(self, username, r):

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
                                  'tumblrinaction', 'offensivespeech')
        total_negative_karma = 0
        limit = 500
        user = r.get_redditor(username)
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

        if average_karma >= 5 and total_negative_karma > (-70 * (total_comments_read/limit)) and troll_index < 50:
            troll_likelihood = 'Low'

        if troll_index >= 40 or total_negative_karma < (-70 * (total_comments_read/limit)) or average_karma < 1:
            troll_likelihood = 'Moderate'

        if troll_index >= 60 or total_negative_karma < (-130 * (total_comments_read/limit)) or average_karma < -2:
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

            if comments_in_subreddit[i] > (total_comments_read/(20*(limit/200))/(len(subreddit_names)/30)):
                history[subreddit] = comments_in_subreddit[i]

            i+=1

        old_range = (max(comment_lengths) - min(comment_lengths))
        new_range = 2000 - 50

        for item in comment_lengths:
            n = (((item - min(comment_lengths)) * new_range) / old_range) + 50
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
        plt.title('User summary for /u/' + username, loc='center', y=1.2)

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

        filename = username + "_summary.png"

        figure = plt.gcf()
        figure.set_size_inches(11, 12)

        plt.savefig(filename)

        path = os.path.dirname(os.path.realpath(__file__)) + "/" + filename

        link = self.imgur.upload_from_path(path, config=None, anon=True)
        msg = self.s.send_msg("Showing summary for */u/" + username +
                              "*. Total comments read: %d" % total_comments_read, channel_name=self.channel)
        msg = self.s.send_msg(link['link'], channel_name=self.channel)
        msg = self.s.send_msg("*Troll likelihood (experimental):* " + troll_likelihood, channel_name=self.channel)
        msg = self.s.send_msg('*User profile:* ' + "https://www.reddit.com/user/" + username, channel_name=self.channel)

        plt.clf()
'''





