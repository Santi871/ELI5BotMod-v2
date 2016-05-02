import nltk
import datetime
import time
from configparser import ConfigParser


def intersect(titles):

    ret_set = set(titles[0])

    for index, element in enumerate(titles):
        if index > 0:
            ret_set = ret_set & set(element)

    return list(ret_set)


class Filters:

    """This class implements a set of filters through which submissions can be ran through"""

    def __init__(self, r, s, db, subreddit):

        # Parse config
        config = ConfigParser()
        config.read('modules_config.ini')

        self.tags = config.get('filters', 'tags').split(',')
        self.verbose = config.getboolean('filters', 'verbose')

        self.r = r
        self.s = s
        self.db = db
        self.already_done_reposts = []
        self.already_checked_cur_rules = []
        self.filters = []
        self.subreddit = subreddit

        for name, f in Filters.__dict__.items():
            if callable(f) and name[0] != "_" and name != "run_filters":
                self.filters.append(name)

    # -------------- DEFINE INTERNAL METHODS NEEDED BY THE FILTERS HERE --------------

    def _create_c_events_rule(self, search_results):

        list_of_tokenized_titles = []
        final_words_list = []

        for index, submission in enumerate(search_results):

            if index <= 3:

                tokenized_title = submission.title.lower().split()

                list_of_tokenized_titles.append(tokenized_title)

            # submission.remove()

        title_words_list = intersect(list_of_tokenized_titles)

        tokens = nltk.word_tokenize(' '.join(title_words_list))
        tagged = nltk.pos_tag(tokens)

        for word, tag in tagged:

            if tag in self.tags:
                final_words_list.append(word)

        try:
            final_words_list.remove('eli5')
        except ValueError:
            pass

        try:
            final_words_list.remove(':')
        except ValueError:
            pass

        try:
            final_words_list.remove(';')
        except ValueError:
            pass

        self.db.insert_entry('recent_event', event_keywords=final_words_list)

        self.s.send_msg("*Created current event rule, posts containing:* '%s'" % ' '.join(final_words_list),
                        channel_name="eli5bot-dev",
                        confirm=False)

    def _get_broken_cur_rule(self, title_words_list):

        broken_rule = None
        submission_title = ' '.join(title_words_list)

        current_rules = self.db.retrieve_entries('current_events')

        for rule in current_rules:

            if all(x in submission_title for x in rule):
                broken_rule = rule
                break

        if broken_rule is not None:
            ret = ' '.join(broken_rule)
        else:
            ret = None

        return ret

    def run_filters(self, submission):

        passed_list = []

        for filter_method in self.filters:

            passed = getattr(self, filter_method)(submission)
            passed_list.append(passed)

        if False in passed_list:
            return False
        else:
            return True

    # -------------- DEFINE FILTERS HERE --------------

    def check_current_rule(self, submission):

        if submission.id not in self.already_checked_cur_rules:
            title_words_list = nltk.word_tokenize(submission.title.lower())

            broken_rule = self._get_broken_cur_rule(title_words_list)
            self.already_checked_cur_rules.append(submission.id)

            if broken_rule is not None:
                # submission.remove()
                submission.report("Current rule: %s" % broken_rule)
                return False
            else:
                return True

    def search_reposts(self, submission):

        nltk.data.path.append('./nltk_data/')

        if submission.id not in self.already_done_reposts:

            words_list = []
            search_results_in_last_threehours = []
            search_result_list = []
            total_in_threehours = 0
            title = submission.title.lower()
            search_url = 'https://www.reddit.com/r/explainlikeimfive/search?q=title%3A%28'
            self.already_done_reposts.append(submission.id)

            tokens = nltk.word_tokenize(title)

            try:
                tokens.remove('eli5')
            except ValueError:
                pass

            try:
                tokens.remove(':')
            except ValueError:
                pass

            try:
                tokens.remove(';')
            except ValueError:
                pass

            tagged = nltk.pos_tag(tokens)

            for word, tag in tagged:

                if tag in self.tags:
                    words_list.append(word)
                    search_url += word + '+'
            search_url += '&restrict_sr=on&sort=relevance&t=all'

            search_query = ' '.join(words_list)
            full_search_query = "title:(" + search_query + ")"

            while True:

                try:
                    search_result = self.r.search(full_search_query, subreddit=self.subreddit, sort='new')
                    search_result_list = list(search_result)
                    break
                except AssertionError:
                    time.sleep(1)
                    continue

            if search_result_list:

                for item in search_result_list:

                    comment_time = datetime.datetime.fromtimestamp(item.created_utc)
                    d = datetime.datetime.now() - comment_time
                    delta_time = d.total_seconds()

                    if int(delta_time / 60) < 180:
                        total_in_threehours += 1
                        search_results_in_last_threehours.append(item)

                if len(search_result_list) >= 4:

                    if self.verbose:
                        msg_string = "---\n*Potential repost detected*\n" + \
                                     title + '\n' + "*POS tagger output:* " + str(tagged) + '\n' + \
                                     '*Link:* ' + submission.permalink + '\n' + "*Search query:* " +\
                                     full_search_query + '\n' + '*Search results:*\n'

                        for item in search_result_list:
                            msg_string += str(item) + '\n'

                        msg = self.s.send_msg(msg_string, channel_name="eli5bot-dev", confirm=False)

                    msg_mods_url = ("https://www.reddit.com/message/compose?to=%2Fr%2Fexplainlikeimfive&subject=I%20"
                                    "believe%20my%20post%20is%20not%20a%20repost&message=")

                    reddit_msg = """Hi!\n\nI've ran a search for you, and it seems this is commonly asked question. You
                                    can see the results of the search I've performed [here](""" +\
                                 search_url + ')' +\
                                 "\n\nIf you believe your submission is not a repost, feel free" \
                                 "to [message the moderators](" + msg_mods_url + ').'

                    reddit_msg_footer = "\n\n---\n\n*I am a bot, and this action was performed automatically.*"

                    submission.report("Potential repost")
                    return False

                if total_in_threehours >= 3:
                    msg_string = "---\n*Potential large influx of question*\n" + \
                                 title + '\n' + "*Search query:* " + full_search_query + '\n' + '*Link:* ' + \
                                 submission.permalink

                    msg = self.s.send_msg(msg_string, channel_name="eli5bot-dev", confirm=False)

                    return False

            return True
