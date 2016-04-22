import nltk
import datetime


class RepostDetector:

    def __init__(self, r, s):

        self.r = r
        self.s = s
        self.already_done_reposts = []

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
                tokens.remove("ELI5")
                tokens.remove(":")
                tokens.remove(";")
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
