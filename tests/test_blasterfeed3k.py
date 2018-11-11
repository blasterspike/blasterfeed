import unittest2
import logging
import datetime
import dateutil
import my_timezones
from feedgen.feed import FeedGenerator
from blasterfeed3k import *


class Test001SvcTests(unittest2.TestCase):
    def setUp(self):
        self.logger = logging.getLogger('Custom logger')

    def test_001_parse_the_feed(self):
        website = 'example.com'
        feed = 'tests/sample_feed.rss'

        new_feed_elements = parse_the_feed(self.logger, website, feed)

        with open('tests/parse_the_feed_expected_output.txt', 'r') as f:
            expected_dictionary = json.loads(f.read())

        published = dateutil.parser.parse('Sun, 04 Nov 2018 16:00:06 +0000', tzinfos=my_timezones.tzd)
        expected_dictionary.update({'feed_pubdate': published})

        self.maxDiff = None
        self.assertEqual(new_feed_elements, expected_dictionary)

    def test_002_parse_the_feed_with_empty_description(self):
        website = 'example.com'
        feed = 'tests/sample_feed_empty_description.rss'

        new_feed_elements = parse_the_feed(self.logger, website, feed)

        published = dateutil.parser.parse('Sun, 04 Nov 2018 16:00:06 +0000', tzinfos=my_timezones.tzd)
        expected_dictionary = {
            "feed_title": "Feed title",
            "feed_link": "https://example.com/",
            "feed_description": "Feed title",
            "feed_pubdate": published,
            "feed_entries": []
        }

        self.assertEqual(new_feed_elements, expected_dictionary)

    def test_003_initialize_feed(self):
        new_feed_elements = {
            'feed_title': 'Test title',
            'feed_link': 'https://example.com/',
            'feed_description': 'Test description',
            'feed_pubdate': 'Sun, 04 Nov 2018 16:00:06 +0000'
        }

        fg = initialize_feed(self.logger, new_feed_elements)

        self.assertEqual(fg.title(), new_feed_elements['feed_title'])
        self.assertEqual(fg.link(), [{'href': new_feed_elements['feed_link'], 'rel': 'alternate'}])
        self.assertEqual(fg.description(), new_feed_elements['feed_description'])
        self.assertEqual(fg.pubDate(), datetime.datetime(2018, 11, 4, 16, 0, 6, tzinfo=dateutil.tz.tzutc()))

    def test_004_parse_an_entry(self):
        entry = {
            'title': 'Entry title',
            'author': 'Entry author',
            'published': 'Sun, 04 Nov 2018 15:00:24 +0000',
            'link': 'https://example.com'
        }

        new_feed_entry = parse_an_entry(self.logger, entry)

        published = dateutil.parser.parse(entry['published'], tzinfos=my_timezones.tzd)
        expected_dictionary = {
            'entry_title': 'Entry title',
            'entry_author': 'Entry author',
            'entry_pubdate': published,
            'entry_link': 'https://example.com'
        }

        self.assertEqual(new_feed_entry, expected_dictionary)

    def test_005_add_entry_to_new_feed(self):
        expected_fg = FeedGenerator()
        expected_fg.title('Test title')
        expected_fg.link(href='https://example.com/', rel='alternate')
        expected_fg.description('Test description')
        expected_fe = expected_fg.add_entry()
        expected_fe.title('Entry title')
        expected_fe.author(name='Entry author')
        expected_fe.link(href='https://example.com/', rel='alternate')
        expected_fe.content('...')

        # Create a simple FeedGenerator to pass it to the method
        # These 3 elements are required
        fg = FeedGenerator()
        fg.title('Test title')
        fg.link(href='https://example.com/', rel='alternate')
        fg.description('Test description')

        entry = {
            'entry_title': 'Entry title',
            'entry_author': 'Entry author',
            'entry_link': 'https://example.com/'
        }
        content = '...'
        result_fg = add_entry_to_new_feed(self.logger, fg, entry, content)

        self.assertItemsEqual(result_fg.rss_str(), expected_fg.rss_str())


if __name__ == '__main__':
    unittest2.main()