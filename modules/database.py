import psycopg2
import urllib.parse
import os
import datetime


class Database:

    """Database module for BotMod"""

    def __init__(self, create_tables=True):

        urllib.parse.uses_netloc.append("postgres")
        self.url = urllib.parse.urlparse(os.environ['DATABASE_URL'])

        self.conn = psycopg2.connect(
            database=self.url.path[1:],
            user=self.url.username,
            password=self.url.password,
            host=self.url.hostname,
            port=self.url.port
        )

        self.cur = self.conn.cursor()

        if create_tables:
            self.create_required_tables()

    def create_required_tables(self):

        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS RECENTPOSTS"
            "(ID SERIAL PRIMARY KEY,"
            "TITLE TEXT UNIQUE,"
            "DATE TEXT)")

        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS MODMAIL (ID SERIAL PRIMARY KEY, URL TEXT UNIQUE, AUTHOR TEXT,"
            " SUBJECT TEXT, BODY TEXT, DATE TEXT)")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS SHADOWBANS"
            "(ID SERIAL PRIMARY KEY,"
            "USERNAME TEXT UNIQUE,"
            "REASON TEXT, "
            "DATE TEXT, "
            "BY TEXT)")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS BANS (ID SERIAL PRIMARY KEY, USERNAME TEXT UNIQUE, LENGTH TEXT,"
            " REASON TEXT, AUTHOR TEXT, DATE TEXT)")

        self.conn.commit()

    def insert_entry(self, type, **kwargs):\

        if type == "shadowban":

            name = kwargs['user']
            reason = kwargs['reason']
            date = str(datetime.datetime.utcnow())
            author = kwargs['author']

            self.cur.execute('''INSERT INTO SHADOWBANS(USERNAME, REASON, DATE, BY) VALUES(%s,%s,%s,%s)''',
                             (name, reason, date, author))

            self.conn.commit()
