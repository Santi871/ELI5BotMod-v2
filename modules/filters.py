import nltk
import datetime


def intersect(a, b, c):
    return list(set(a) & set(b) & set(c))


class Filters:

    """This module implements a set of filters through which submissions can be ran through"""

    def __init__(self, r, s):

        self.r = r
        self.s = s
        self.already_done = []
        self.tags = ('NN', 'NNP', 'NNPS', 'JJ', 'NNS', 'VBG', 'VB', 'VBN', 'CD', 'VBP', 'RB', 'VBD')
        self.current_events = []

    def _create_c_events_rule(self, search_results):

        list_of_words_lists = []

        print(str(search_results))

        for index, submission in enumerate(search_results):

            if index <= 3:

                words_list = []

                tokens = nltk.word_tokenize(submission.title)
                tagged = nltk.pos_tag(tokens[1:])

                for word, tag in tagged:

                    if tag in self.tags:
                        words_list.append(word)

                list_of_words_lists.append(words_list)

                submission.remove()

        title_keywords_list = intersect(list_of_words_lists[0], list_of_words_lists[1], list_of_words_lists[2])

        self.current_events.append(title_keywords_list)

        self.s.send_msg("Created cur event rule: %s" % ' '.join(title_keywords_list), channel_name="eli5bot-dev")

    def _get_broken_cur_event(self, title_words_list):

        broken_event = None

        for title in self.current_events:

            broken_event = title

            print(str(title))
            print(str(title_words_list))
            print(str(self.current_events))

            got_intersection = set(title) & set(title_words_list)

            if got_intersection:
                break

        return ' '.join(broken_event)

    def check_current_events(self, submissions):

        already_checked = []

        for submission in submissions:

            if submission.id not in already_checked:
                title_words_list = nltk.word_tokenize(submission.title)

                print(submission.id)
                print(str(title_words_list))

                broken_event = self._get_broken_cur_event(title_words_list)

                if broken_event:
                    submission.report("Broken event: %s" % broken_event)
                    self.s.send_msg("Broken event: %s" % broken_event, channel_name="eli5bot-dev")

                already_checked.append(submission.id)

    def search_reposts(self, submissions):

        nltk.data.path.append('./nltk_data/')

        for submission in submissions:

            if submission.id not in self.already_done:

                words_list = []
                total_in_threehours = 0
                title = submission.title
                self.already_done.append(submission.id)

                tokens = nltk.word_tokenize(title)
                tagged = nltk.pos_tag(tokens[1:])

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

                    self._create_c_events_rule(search_result_list)
