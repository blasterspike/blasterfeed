#!/usr/bin/python3

import argparse
import logging
import os
import feedparser
from feedgen.feed import FeedGenerator
from newspaper import Article
from sqlitecache import SQliteCacheHandler
import dateutil
import datetime
import yaml
import my_timezones
import json
import sys


def json_serial(obj):
    """
    JSON serializer for objects not serializable by default json code
    """

    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError('Type {0} not serializable'.format(type(obj)))


def generate_new_feed(logger, website, feed, output_file):
    """
    Generate the new feed

    :param logger: custom logger
    :type logger: logger object
    :param website: name of the website provided in the config.yml
    :type website: string
    :param feed: feed URL provided in the config.yml
    :type feed: string
    :param output_file: full path where to save the generated RSS feed, provided in the config.yml
    :type output_file: string
    """
    new_feed_elements = parse_the_feed(logger, website, feed)
    fg = initialize_feed(logger, new_feed_elements)

    # Create a list with all the links of the entries present in the feed
    # It is going to be used to delete older records in the database
    list_of_all_entries_links = list()

    # Initialize class SQliteCacheHandler
    sq = SQliteCacheHandler(logger)

    # Parse all the entries of the feed
    for entry in new_feed_elements['feed_entries']:
        new_feed_entry = parse_an_entry(logger, entry)

        list_of_all_entries_links.append(new_feed_entry['entry_link'])

        # Get the full article for this entry
        content = get_full_content_from_entry_link(logger, cache_disabled, sq, new_feed_elements['feed_link'],
                                                   new_feed_entry['entry_link'])

        if content is not None:
            # As we have been able to get the full article, add the entry to the new feed that we are creating
            fg = add_entry_to_new_feed(logger, fg, new_feed_entry, content)
        else:
            logger.debug('The content for the entry link {0} is empty, not adding this entry to the new feed'.
                         format(new_feed_entry['entry_link']))

    # Generate the feed file
    fg.rss_file(output_file)
    logger.debug('New feed written to: {0}'.format(output_file))

    if not cache_disabled:
        # Clean the DB
        logger.debug('list_of_all_entries_links: {0}'.format(json.dumps(list_of_all_entries_links, indent=4)))
        sq.clean(new_feed_elements['feed_link'], list_of_all_entries_links)


def parse_the_feed(logger, website, feed):
    """
    Parse the retrieved feed and grab the elements needed to generate the new one

    :param logger: custom logger
    :type logger: logger object
    :param website: name of the website provided in the config file
    :type website: string
    :param feed: feed URL provided in the config file
    :type feed: string
    :return new_feed_elements: elements of the feed that we are going to generate
    :rtype new_feed_elements: dictionary
    """

    # Create a new dictionary where to save the elements of the feed that we are going to generate
    new_feed_elements = dict()
    # Create a list where to save the entries of the feed
    entries_list = list()

    # Parse the feed with feedparser
    parsed_feed = feedparser.parse(feed)

    # Set a feed title
    if hasattr(parsed_feed.feed, 'title'):
        new_feed_elements['feed_title'] = parsed_feed.feed.title
        logger.debug('feed_title: {0}'.format(new_feed_elements['feed_title']))
    else:
        new_feed_elements['feed_title'] = website
        logger.debug('Feed attribute title is not present, set it to website name from the config file: {0}'.format(
            new_feed_elements['feed_title']))

    # Set a feed link
    if hasattr(parsed_feed.feed, 'link'):
        new_feed_elements['feed_link'] = parsed_feed.feed.link
        logger.debug('feed_link: {0}'.format(new_feed_elements['feed_link']))
    else:
        new_feed_elements['feed_link'] = feed
        logger.debug('Feed attribute link is not present, set it to feed URL: {0}'.format(
            new_feed_elements['feed_link']))

    # Set a feed description
    # Not all feeds have all fields, 'description' field is mandatory by FeedGenerator
    if hasattr(parsed_feed.feed, 'description'):
        # 'description' field is mandatory by FeedGenerator
        if not parsed_feed.feed.description:
            new_feed_elements['feed_description'] = new_feed_elements['feed_title']
            logger.debug('Feed description is empty, set it to feed title: {0}'.format(
                new_feed_elements['feed_description']))
        else:
            new_feed_elements['feed_description'] = parsed_feed.feed.description
            logger.debug('feed_description: {0}'.format(new_feed_elements['feed_description']))
    else:
        new_feed_elements['feed_description'] = new_feed_elements['feed_title']
        logger.debug('Feed description is not present, set it to feed title: {0}'.format(
            new_feed_elements['feed_description'].encode('ascii', 'ignore')))

    # Set a feed publication date
    if hasattr(parsed_feed.feed, 'date'):
        # feedparser uses dateutil to parse pubDate if it's a string
        # Unfortunately dateutil doesn't support timezones and it fails with ValueError if pubDate doesn't have one
        # This way I provide date directly a datetime object with timestamp
        logger.debug('Feed publication date: {0}'.format(parsed_feed.feed.date))
        converted_feed_pubdate = dateutil.parser.parse(parsed_feed.feed.date, tzinfos=my_timezones.tzd)
        new_feed_elements['feed_pubdate'] = converted_feed_pubdate
        logger.debug('feed_pubdate: {0}'.format(new_feed_elements['feed_pubdate']))

    # Parse the entries in the feed
    for entry in parsed_feed.entries:
        entries_list.append(entry)
    new_feed_elements['feed_entries'] = entries_list

    return new_feed_elements


def initialize_feed(logger, new_feed_elements):
    """
    Instanciate the FeedGenerator class with some data retrieved from the previous function

    :param logger: custom logger
    :type logger: logger object
    :param new_feed_elements: elements of the new feed that we are going to generate
    :type new_feed_elements: dictionary
    :return fg: FeedGenerator class
    :rtype fg: object
    """
    # Initialize feedgen
    fg = FeedGenerator()

    fg.title(new_feed_elements['feed_title'])
    fg.link(href=new_feed_elements['feed_link'], rel='alternate')
    fg.description(new_feed_elements['feed_description'])
    if 'feed_pubdate' in new_feed_elements:
        fg.pubDate(new_feed_elements['feed_pubdate'])
    logger.debug('Feed initialized for {0}'.format(new_feed_elements['feed_title']))

    return fg


def parse_an_entry(logger, entry):
    """
    Parse an entry of the retrieved feed

    :param logger: custom logger
    :type logger: logger object
    :param entry: feed entry of the existing feed
    :type entry: dictionary
    :return new_feed_entry: dictionary with some data extracted from the retrieved feed entry
    :rtype new_feed_entry: dictionary
    """

    # Create a dictionary to save all the elements of the existing feed, need to generate the new one
    new_feed_entry = dict()

    new_feed_entry['entry_title'] = entry['title']
    # element.encode('ascii', 'ignore') because I can get the error
    # UnicodeEncodeError: 'ascii' codec can't encode character u'\u2019' in position 69: ordinal not in range(128)
    logger.debug('entry_title: {0}'.format(entry['title'].encode('ascii', 'ignore')))

    if 'author' in entry:
        new_feed_entry['entry_author'] = entry['author']
        logger.debug('entry_author: {0}'.format(entry['author']))

    if 'published' in entry:
        # Same problem of the Feed pubDate
        converted_entry_pubdate = dateutil.parser.parse(entry['published'], tzinfos=my_timezones.tzd)
        new_feed_entry['entry_pubdate'] = converted_entry_pubdate
        logger.debug('entry_pubdate with timestamp: {0}'.format(converted_entry_pubdate))

    new_feed_entry['entry_link'] = entry['link']
    logger.debug('entry_link: {0}'.format(new_feed_entry['entry_link']))

    logger.debug('new_feed_entry: {0}'.format(json.dumps(new_feed_entry, indent=4, default=json_serial)))
    return new_feed_entry


def get_full_content_from_entry_link(logger, cache_disabled, sq, feed_link, entry_link):
    """
    Retrieve the full content of the website page using the link in the entry feed

    :param logger: custom logger
    :type logger: logger object
    :param cache_disabled: boolean if the cache is disabled
    :type cache_disabled: boolean
    :param sq: SQliteCacheHandler class
    :type sq: SQliteCacheHandler object
    :param feed_link: link of the retrieved feed. Used to store it into the SQLite database.
    :type feed_link: string
    :param entry_link: link of the entry feed
    :type entry_link: string
    :return content: content of the entire website page
    :rtype content: string
    """

    search_result = None
    content = None

    if not cache_disabled:
        # First search if we have already stored this article in cache
        search_result = sq.search(entry_link)
        if search_result:
            logger.debug('Article found in SQLite, grabbing the content from the database')
            content = search_result[4]

    # If cache is disabled or the previous search_result didn't return anything, retrieve the content
    if cache_disabled or (search_result is None):
        # Get the full article
        logger.debug('Article not found in SQLite, grabbing the content')
        content = get_readable_content(logger, entry_link)

    # If cache is not disabled and search_result was empty and I have a content, store the content in SQLite
    if (not cache_disabled) and (search_result is None) and (content is not None):
        logger.debug('Storing the content in SQLite for: {0}'.format(entry_link))
        sq.insert(feed_link, entry_link, datetime.datetime.now(), content)

    return content


def add_entry_to_new_feed(logger, fg, entry, content):
    """
    Add FeedEntry to FeedGenerator

    :param logger: custom logger
    :type logger: logger object
    :param fg: FeedGenerator class
    :type fg: FeedGenerator object
    :param entry: entry of the feed that we are going to generate
    :type entry: dictionary
    :param content: full content of the website page
    :type content: string
    :return fg: FeedGenerator class with the new entry
    :rtype fg: FeedGenerator object
    """
    fe = fg.add_entry()
    logger.debug('entry: {0}'.format(json.dumps(entry, indent=4, default=json_serial)))
    fe.title(entry['entry_title'])

    if 'author' in entry:
        fe.author(name=entry['entry_author'])

    if 'published' in entry:
        fe.pubdate(entry['entry_pubdate'])

    fe.link(href=entry['entry_link'], rel='alternate')

    fe.content(content)

    return fg


def get_readable_content(logger, link):
    """
    Retrieves the full content of a website page given the link in the entry feed

    :param logger: custom logger
    :type logger: logger object
    :param link: link in the entry feed
    :type link: string
    :return content: full content
    :rtype content: string
    """

    logger.debug('Fetching full article for {0}'.format(link))

    article_to_fetch = Article(
        url=link,
        keep_article_html=True,
        browser_user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:49.0) Gecko/20100101 Firefox/49.0',
        request_timeout=20)
    try:
        article_to_fetch.download()
    except Exception as e:
        logger.warning('Unable to download the article for link {0}, error: {1}'.format(link, e))
        return None
    else:
        if not article_to_fetch.html:
            logger.debug('HTML content is empty for link: {0}'.format(link))
            return None
        else:
            try:
                article_to_fetch.parse()
            except Exception as e:
                logger.warning('Unable to parse the article for link {0}, error: {1}'.format(link, e))
                return None
            else:
                return article_to_fetch.article_html


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', dest='debug_enabled', help='Enable debug mode', action='store_true')
    parser.add_argument('--disable-cache', dest='cache_disabled', help='Disable caching to SQLite', action='store_true')
    args = parser.parse_args()

    debug_enabled = args.debug_enabled
    cache_disabled = args.cache_disabled

    logger = logging.getLogger('Custom logger')
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s %(asctime)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    if debug_enabled:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)

    with open('{0}/config/config.yml'.format(os.path.dirname(__file__)), 'r') as config_file:
        try:
            config_data = yaml.load(config_file)
        except yaml.YAMLError as exc:
            logger.error('Unable to read configuration file: {0}'.format(exc))
            sys.exit(1)
    logger.debug('config_data: {0}'.format(config_data))

    for website in config_data.keys():
        logger.debug('Reading configuration for {0}'.format(website))
        feed = config_data[website]['feed']
        logger.debug('Feed to parse: {0}'.format(feed))
        output_file = config_data[website]['output_file']
        logger.debug('Output file: {0}'.format(output_file))

        generate_new_feed(logger, website, feed, output_file)
