from time import sleep


class FaqGenerator:

    def __init__(self, r, subreddit):

        sleep(3)
        self.r = r
        self.subreddit = subreddit
        self.wiki_page = self.r.get_wiki_page(self.subreddit, "faq")

    def wiki_append(self, string, newline=True):

        new_wiki = self.wiki_page.content_md
        if newline:
            new_wiki += '\n\n'
        new_wiki += string
        self.r.edit_wiki_page(self.subreddit, "faq", new_wiki)

    def add_entry(self, submission, search_results_list):

        new_search_results_list = []

        for item in search_results_list:

            if item.num_comments > 3:
                new_search_results_list.append(item)

        item_str = ''

        item_str += '---' + '\n\n'
        item_str += '###' + submission.title + '\n\n'

        for index, item in enumerate(search_results_list):

            if index > 0:

                item_str += "[%s](%s)" % (item.title, item.permalink) + ' **| Number of comments:** ' +\
                           str(item.num_comments) + ' **| Karma:** ' + str(item.score) + '\n\n'

        self.wiki_append(item_str)

