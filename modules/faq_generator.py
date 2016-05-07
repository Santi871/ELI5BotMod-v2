class FaqGenerator:

    def __init__(self, r, subreddit):

        self.r = r
        self.subreddit = subreddit
        self.wiki_page = self.r.get_wiki_page(self.subreddit, "faq")
        self.wiki_page_content = self.wiki_page.content_md

    def wiki_append(self, string, newline=True):

        new_wiki = self.wiki_page_content
        if newline:
            new_wiki += '\n'
        new_wiki += string
        self.r.edit_wiki_page(self.subreddit, "faq", new_wiki)

    def add_entry(self, submission, search_results_list):

        new_search_results_list = []

        for item in search_results_list:

            if item.num_comments > 3:
                new_search_results_list.append(item)

        if len(new_search_results_list) > 3:

            self.wiki_append('---')
            self.wiki_append('**' + submission.title + '**')

            for item in new_search_results_list:

                item_str = "[%s](%s)" % (item.title, item.permalink) + ' **| Number of comments:** ' +\
                           str(item.num_comments) + ' **| Karma:** ' + str(item.score)

                self.wiki_append(item_str)

