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

    def add_entry(self, submission, search_query):

        search_url = 'https://www.reddit.com/r/explainlikeimfive/search?q=title%3A%28'

        for word in search_query.split():
            search_url += word + '+'

        search_url += '%29&restrict_sr=on&sort=relevance&t=all'

        item_str = '---' + '\n\n'
        item_str += '###[' + submission.title + '](' + search_url + ')\n\n'

        self.wiki_append(item_str)

