import nltk
import datetime


def intersect(titles):

    ret_set = set(titles[0])

    for index, element in enumerate(titles):
        if index > 0:
            ret_set = ret_set & set(element)

    return list(ret_set)


class Filters:

    """This module implements a set of filters through which submissions can be ran through"""

    current_events = []

    def __init__(self, r, s):

        self.r = r
        self.s = s
        self.already_done = []
        self.already_checked_cur_events = []
        self.tags = ('NN', 'NNP', 'NNPS', 'JJ', 'NNS', 'VBG', 'VB', 'VBN', 'CD', 'RB', 'VBD')

    def _create_c_events_rule(self, search_results):

        list_of_tokenized_titles = []
        final_words_list = []

        for index, submission in enumerate(search_results):

            if index <= 3:

                tokenized_title = submission.title.lower().split()

                list_of_tokenized_titles.append(tokenized_title)

            submission.remove()

        title_words_list = intersect(list_of_tokenized_titles)

        tokens = nltk.word_tokenize(' '.join(title_words_list))
        tagged = nltk.pos_tag(tokens)

        for word, tag in tagged:

            if tag in self.tags:
                final_words_list.append(word)

        final_words_list.remove('eli5')

        try:
            final_words_list.remove(':')
        except ValueError:
            pass

        try:
            final_words_list.remove(';')
        except ValueError:
            pass

        self.current_events.append(final_words_list)

        self.s.send_msg("*Created current event rule, posts containing:* %s" % ' '.join(final_words_list),
                        channel_name="eli5bot-dev",
                        confirm=False)

    def _get_broken_cur_event(self, title_words_list):

        broken_event = None
        submission_title = ' '.join(title_words_list)
        for event in self.current_events:

            broken_event = event

            if all(x in submission_title for x in event):
                break

        if broken_event is not None:
            ret = ' '.join(broken_event)
        else:
            ret = None

        return ret

    def check_current_events(self, submissions):

        for submission in submissions:

            if submission.id not in self.already_checked_cur_events:
                title_words_list = nltk.word_tokenize(submission.title.lower())

                broken_event = self._get_broken_cur_event(title_words_list)

                if broken_event is not None:
                    submission.remove()

                self.already_checked_cur_events.append(submission.id)

    def search_reposts(self, submissions):

        nltk.data.path.append('./nltk_data/')

        for submission in submissions:

            if submission.id not in self.already_done:

                words_list = []
                search_results_in_last_threehours = []
                total_in_threehours = 0
                title = submission.title.lower()
                self.already_done.append(submission.id)

                tokens = nltk.word_tokenize(title)
                tokens.remove('eli5')

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

                search_query = ' '.join(words_list)
                full_search_query = "title:(" + search_query + ")"

                search_result = self.r.search(full_search_query, subreddit="santi871", sort='new')
                search_result_list = list(search_result)

                for item in search_result_list:

                    comment_time = datetime.datetime.fromtimestamp(item.created_utc)
                    d = datetime.datetime.now() - comment_time
                    delta_time = d.total_seconds()

                    if int(delta_time / 60) < 180:
                        total_in_threehours += 1
                        search_results_in_last_threehours.append(item)

                if len(search_result_list) >= 4:

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

                    self._create_c_events_rule(search_results_in_last_threehours)
