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

        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS CURRENT_EVENTS"
            "(ID SERIAL PRIMARY KEY,"
            "EVENT_KEYWORDS TEXT UNIQUE)")

        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS COMMANDS_LOG"
            "(ID SERIAL PRIMARY KEY,"
            "COMMAND TEXT,"
            "ARGS TEXT,"
            "AUTHOR TEXT,"
            "DATETIME TEXT)")

        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS USERS_ONLINE_LOG"
            "(ID SERIAL PRIMARY KEY,"
            "USERS_ONLINE INTEGER,"
            "DATETIME TEXT)")

        self.conn.commit()

    def insert_entry(self, entry_type, **kwargs):\

        if entry_type == "shadowban":

            name = kwargs['user']
            reason = kwargs['reason']
            date = str(datetime.datetime.utcnow())
            author = kwargs['author']

            try:
                self.cur.execute('''INSERT INTO SHADOWBANS(USERNAME, REASON, DATE, BY) VALUES(%s,%s,NOW(),%s)''',
                                 (name, reason, author))
            finally:
                self.conn.commit()

        if entry_type == 'recent_event':

            event_keywords = kwargs['event_keywords']
            event_keywords_string = ' '.join(event_keywords)

            try:
                self.cur.execute('''INSERT INTO CURRENT_EVENTS(EVENT_KEYWORDS) VALUES(%s)''', (event_keywords_string,))
            finally:
                self.conn.commit()

        if entry_type == 'command':

            slack_event = kwargs['slack_event']
            message = slack_event.get('text')
            split_message = message.split()
            command = split_message[0]
            command_args = ' '.join(split_message[1:])
            author = slack_event.get('user')
            date = str(datetime.datetime.utcnow())


            try:
                self.cur.execute('''INSERT INTO COMMANDS_LOG(COMMAND, ARGS, AUTHOR, DATETIME) VALUES(%s,%s,%s,NOW())''',
                                 (command, command_args, author))
            finally:
                self.conn.commit()

        if entry_type == 'users_online_log':

            online_users = kwargs['online_users']
            curtime = kwargs['curtime']

            try:
                self.cur.execute('''INSERT INTO USERS_ONLINE_LOG(USERS_ONLINE, DATETIME) VALUES(%s,%s)''',
                                 (online_users, curtime))
            finally:
                self.conn.commit()

    def retrieve_entries(self, entry_type, table_mode=False):

        if entry_type == 'current_events':

            if not table_mode:

                self.cur.execute('''SELECT EVENT_KEYWORDS FROM CURRENT_EVENTS''')
                all_events_list = self.cur.fetchall()

                for index, event in enumerate(all_events_list):
                    all_events_list[index] = event[0].split()

                return all_events_list

            if table_mode:
                self.cur.execute('''SELECT * FROM CURRENT_EVENTS''')
                all_events_list = self.cur.fetchall()

                return all_events_list

        if entry_type == 'online_users':

            self.cur.execute('''SELECT users_online, datetime FROM users_online_log''')
            ret = self.cur.fetchall()

            return ret

    def delete_entry(self, table, entry_id):

        if table == 'current_events':

            try:
                self.cur.execute('''DELETE FROM CURRENT_EVENTS WHERE id=%s''', (entry_id,))
            finally:
                self.conn.commit()







