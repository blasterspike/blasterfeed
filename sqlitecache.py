#!/usr/bin/env python

import sqlite3
import os


class SQliteCacheHandler:
    def __init__(self, logger):
        self.logger = logger
        self.conn = sqlite3.connect('{0}/config/blasterfeed-cache.sqlite3'.format(os.path.dirname(__file__)))
        self.logger.debug('SQLite3 connection object: {0}'.format(self.conn))
        self.c = self.conn.cursor()
        # Enable WAL journaling
        # https://www.sqlite.org/wal.html
        self.c.execute('PRAGMA journal_mode=wal')
        self.c.execute('''CREATE TABLE IF NOT EXISTS data (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                                                            feed_link TEXT,
                                                            item_link TEXT,
                                                            date TEXT,
                                                            content TEXT)
        ''')
        self.c.execute('''CREATE INDEX IF NOT EXISTS item_link_index ON data (item_link)''')
        self.conn.commit()

    def search(self, item_link):
        self.query = self.conn.execute('SELECT * FROM data WHERE item_link=?', (item_link,))
        self.result = self.query.fetchone()

        return self.result

    def insert(self, feed_link, item_link, date, content):
        self.query = self.conn.execute('INSERT INTO data VALUES (NULL, ?, ?, ?, ?)', (feed_link, item_link, date,
                                                                                      content))
        self.conn.commit()

    def clean(self, feed_link, list_of_items_links):
        # Unfortunately I can't pass python list to the execute, so I have to build the query first
        # http://stackoverflow.com/questions/5766230/select-from-sqlite-table-where-rowid-in-list-using-python-sqlite3-db-api-2-0
        sql = 'DELETE FROM data WHERE feed_link = \'{0}\' AND item_link NOT IN ({seq})'.format(
            feed_link,
            seq=', '.join(['?']*len(list_of_items_links))
        )

        self.query = self.conn.execute(sql, list_of_items_links)
        self.conn.commit()
        self.logger.debug('SQLite cleaned for: {0}'.format(feed_link))

    def __exit__(self):
        try:
            self.c.close()
        except sqlite3.ProgrammingError as error:
            self.logger.error('Error closing cursor to DB. Connection object: {conn}, '
                              'Error: {error}'.format(conn=self.conn, error=error))

        try:
            self.conn.close()
        except sqlite3.OperationalError as error:
            self.logger.error('Error closing connection to DB. Connection object: {conn}, '
                              'Error: {error}'.format(conn=self.conn, error=error))
