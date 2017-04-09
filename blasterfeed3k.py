#!/usr/bin/python3

import argparse
import logging
import configparser
import os
import feedparser
from feedgen.feed import FeedGenerator
from newspaper import Article
from sqlitecache import SQliteCacheHandler
import threading
import dateutil
import datetime
import psutil
import sys


def parse_an_item(parsed_feed, fg, tzd, sq, feed_link):
    list_of_existing_items_links = list()

    # Now I need to parse all the items of the feed
    for item in parsed_feed.entries:
        fe = fg.add_entry()
        item_title = fe.title(item['title'])
        # element.encode('ascii', 'ignore') because I can get the error
        # UnicodeEncodeError: 'ascii' codec can't encode character u'\u2019' in position 69: ordinal not in range(128)
        logger.debug('Item title: {0}'.format(item_title.encode('ascii', 'ignore')))
        if 'author' in item:
            item_author = fe.author(name=item['author'])
            logger.debug('Item author: {0}'.format(item_author))
        if 'published' in item:
            # Same problem of the Feed pubDate
            if isinstance(item['published'], str):
                converted_item_pubdate = dateutil.parser.parse(item['published'], tzinfos=tzd)
                item_pubdate = fe.pubdate(converted_item_pubdate)
                logger.debug('Item pubDate with timestamp: {0}'.format(item_pubdate))
        item_link = fe.link(href=item['link'], rel='alternate')
        logger.debug('Item link: {0}'.format(item_link))
        # item_link[0].get('href') as we get an output in the format
        # [{'href': u'http://feedproxy.google.com/~r/Techcrunch/~3/JIfXiMdvFWM/', 'rel': 'alternate'}]
        list_of_existing_items_links.append(item_link[0].get('href'))

        if not cache_disabled:
            # First search if we have already stored this article in cache
            search_result = sq.search(item_link[0].get('href'))
            if search_result:
                logger.debug('Article found in SQLite, grabbing the content')
                content = search_result[4]

        # If cache is disabled or the previous search_result didn't return anything, retrieve the content
        if cache_disabled or (search_result is None):
            # Get the full article
            content = get_readable_content(logger, item_link[0].get('href'))

            # If content is None, remove the entry so it can be grabbed later
            if content is None:
                logger.debug('I\'m going to remove the entry for link {0} as the content is empty'.format(
                    item_link))
                fg.remove_entry(fe)

        # If cache is not disabled and search_result was empty and I have a content, store the content in SQLite
        if (not cache_disabled) and (search_result is None) and (content is not None):
            logger.debug('Storing the content in SQLite for: {0}'.format(item_link[0].get('href')))
            sq.insert(feed_link[0].get('href'), item_link[0].get('href'), datetime.datetime.now(), content)

        fe.content(content)

    return fg, list_of_existing_items_links


def parse_the_feed(logger, section, feed, output_file, cache_disabled):
    tzd = {'Y': -43200,
           'NUT': -39600,
           'SST': -39600,
           'X': -39600,
           'CKT': -36000,
           'HAST': -36000,
           'HST': -36000,
           'TAHT': -36000,
           'TKT': -36000,
           'W': -36000,
           'MART': -34200,
           'MIT': -34200,
           'AKST': -32400,
           'GAMT': -32400,
           'GIT': -32400,
           'HADT': -32400,
           'HNY': -32400,
           'V': -32400,
           'AKDT': -28800,
           'CIST': -28800,
           'HAY': -28800,
           'HNP': -28800,
           'PST': -28800,
           'PT': -28800,
           'U': -28800,
           'HAP': -25200,
           'HNR': -25200,
           'MST': -25200,
           'PDT': -25200,
           'T': -25200,
           'CST': -21600,
           'EAST': -21600,
           'GALT': -21600,
           'HAR': -21600,
           'HNC': -21600,
           'MDT': -21600,
           'S': -21600,
           'CDT': -18000,
           'COT': -18000,
           'EASST': -18000,
           'ECT': -18000,
           'EST': -18000,
           'ET': -18000,
           'HAC': -18000,
           'HNE': -18000,
           'PET': -18000,
           'R': -18000,
           'HLV': -16200,
           'VET': -16200,
           'AST': -14400,
           'BOT': -14400,
           'CLT': -14400,
           'COST': -14400,
           'EDT': -14400,
           'FKT': -14400,
           'GYT': -14400,
           'HAE': -14400,
           'HNA': -14400,
           'PYT': -14400,
           'Q': -14400,
           'HNT': -12600,
           'NST': -12600,
           'NT': -12600,
           'ADT': -10800,
           'ART': -10800,
           'BRT': -10800,
           'CLST': -10800,
           'FKST': -10800,
           'GFT': -10800,
           'HAA': -10800,
           'P': -10800,
           'PMST': -10800,
           'PYST': -10800,
           'SRT': -10800,
           'UYT': -10800,
           'WGT': -10800,
           'HAT': -9000,
           'NDT': -9000,
           'BRST': -7200,
           'FNT': -7200,
           'O': -7200,
           'PMDT': -7200,
           'UYST': -7200,
           'WGST': -7200,
           'AZOT': -3600,
           'CVT': -3600,
           'EGT': -3600,
           'N': -3600,
           'EGST': 0,
           'GMT': 0,
           'UTC': 0,
           'WET': 0,
           'WT': 0,
           'Z': 0,
           'A': 3600,
           'CET': 3600,
           'DFT': 3600,
           'WAT': 3600,
           'WEDT': 3600,
           'WEST': 3600,
           'B': 7200,
           'CAT': 7200,
           'CEDT': 7200,
           'CEST': 7200,
           'EET': 7200,
           'SAST': 7200,
           'WAST': 7200,
           'C': 10800,
           'EAT': 10800,
           'EEDT': 10800,
           'EEST': 10800,
           'IDT': 10800,
           'MSK': 10800,
           'IRST': 12600,
           'AMT': 14400,
           'AZT': 14400,
           'D': 14400,
           'GET': 14400,
           'GST': 14400,
           'KUYT': 14400,
           'MSD': 14400,
           'MUT': 14400,
           'RET': 14400,
           'SAMT': 14400,
           'SCT': 14400,
           'AFT': 16200,
           'IRDT': 16200,
           'AMST': 18000,
           'AQTT': 18000,
           'AZST': 18000,
           'E': 18000,
           'HMT': 18000,
           'MAWT': 18000,
           'MVT': 18000,
           'PKT': 18000,
           'TFT': 18000,
           'TJT': 18000,
           'TMT': 18000,
           'UZT': 18000,
           'YEKT': 18000,
           'SLT': 19800,
           'NPT': 20700,
           'ALMT': 21600,
           'BIOT': 21600,
           'BTT': 21600,
           'F': 21600,
           'IOT': 21600,
           'KGT': 21600,
           'NOVT': 21600,
           'OMST': 21600,
           'YEKST': 21600,
           'CCT': 23400,
           'MMT': 23400,
           'CXT': 25200,
           'DAVT': 25200,
           'G': 25200,
           'HOVT': 25200,
           'ICT': 25200,
           'KRAT': 25200,
           'NOVST': 25200,
           'OMSST': 25200,
           'THA': 25200,
           'WIB': 25200,
           'ACT': 28800,
           'AWST': 28800,
           'BDT': 28800,
           'BNT': 28800,
           'CAST': 28800,
           'H': 28800,
           'HKT': 28800,
           'IRKT': 28800,
           'KRAST': 28800,
           'MYT': 28800,
           'PHT': 28800,
           'SGT': 28800,
           'ULAT': 28800,
           'WITA': 28800,
           'WST': 28800,
           'AWDT': 32400,
           'I': 32400,
           'IRKST': 32400,
           'JST': 32400,
           'KST': 32400,
           'PWT': 32400,
           'TLT': 32400,
           'WDT': 32400,
           'WIT': 32400,
           'YAKT': 32400,
           'ACST': 34200,
           'AEST': 36000,
           'ChST': 36000,
           'K': 36000,
           'PGT': 36000,
           'VLAT': 36000,
           'YAKST': 36000,
           'YAPT': 36000,
           'ACDT': 37800,
           'LHST': 37800,
           'AEDT': 39600,
           'L': 39600,
           'LHDT': 39600,
           'MAGT': 39600,
           'NCT': 39600,
           'PONT': 39600,
           'SBT': 39600,
           'VLAST': 39600,
           'VUT': 39600,
           'NFT': 41400,
           'ANAST': 43200,
           'ANAT': 43200,
           'FJT': 43200,
           'GILT': 43200,
           'M': 43200,
           'MAGST': 43200,
           'MHT': 43200,
           'NZST': 43200,
           'PETST': 43200,
           'PETT': 43200,
           'TVT': 43200,
           'WFT': 43200,
           'FJST': 46800,
           'NZDT': 46800 }

    # Parse the feed with feedparser
    parsed_feed = feedparser.parse(feed)
    # Initialize feedgen
    fg = FeedGenerator()
    if not cache_disabled:
        # Initialize class SQliteCacheHandler
        logger.debug('Thread ID: {0}'.format(threading.current_thread()))
        sq = SQliteCacheHandler(logger, threading.current_thread())

    if hasattr(parsed_feed.feed, 'title'):
        feed_title = fg.title(parsed_feed.feed.title)
        logger.debug('Feed title: {0}'.format(feed_title))
    else:
        feed_title = fg.title(section)
        logger.debug('Feed attribute title is not present, set it to section name from ini file: {0}'.format(section))
        logger.debug('feed_title: {0}'.format(feed_title))
    if hasattr(parsed_feed.feed, 'link'):
        feed_link = fg.link(href=parsed_feed.feed.link, rel='alternate')
        logger.debug('Feed link: {0}'.format(feed_link))
    else:
        feed_link = fg.link(href=feed, rel='alternate')
        logger.debug('Feed attribute link is not present, set it to feed URL: {0}'.format(feed))
    # Not all feeds have all fields
    if hasattr(parsed_feed.feed, 'description'):
        feed_description = fg.description(parsed_feed.feed.description)
        # 'description' field is mandatory by FeedGenerator
        if not feed_description:
            feed_description = fg.description(feed_title)
            logger.debug('Feed description is empty, set it to feed title: {0}'.format(feed_description))
        else:
            logger.debug('Feed description: {0}'.format(feed_description.encode('ascii', 'ignore')))
    else:
        # 'description' field is mandatory by FeedGenerator
        feed_description = fg.description(feed_title)
        logger.debug('Feed description not found, set it to feed title: {0}'.format(feed_description))
    if hasattr(parsed_feed.feed, 'date'):
        # feedparser uses dateutil to parse pubDate if it's a string
        # Unfortunately dateutil doesn't support timezones and it fails with ValueError if pubDate doesn't have one
        # This way I provide date directly a datetime object with timestamp
        logger.debug('Feed pubDate: {0}'.format(parsed_feed.feed.date))
        if isinstance(parsed_feed.feed.date, str):
            converted_feed_pubdate = dateutil.parser.parse(parsed_feed.feed.date, tzinfos=tzd)
            feed_pubdate = fg.pubDate(converted_feed_pubdate)
            logger.debug('Feed pubDate with timestamp: {0}'.format(feed_pubdate))

    fg, list_of_existing_items_links = parse_an_item(parsed_feed, fg, tzd, sq, feed_link)

    fg.rss_file(output_file)
    logger.debug('New feed written to: {0}'.format(output_file))

    if not cache_disabled:
        # Clean the DB
        sq.clean(feed_link[0].get('href'), list_of_existing_items_links)


def get_readable_content(logger, link):
    logger.debug('Fetching full article for {0}'.format(link))

    article_to_fetch = Article(
        url=link,
        keep_article_html=True,
        browser_user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:49.0) Gecko/20100101 Firefox/49.0',
        request_timeout=20)
    try:
        article_to_fetch.download()
    except:
        logger.warning('Unable to download the article for link: {0}'.format(link))
        return None
    else:
        if not article_to_fetch.html:
            logger.debug('HTML content is empty for link: {0}'.format(link))
            return None
        else:
            try:
                article_to_fetch.parse()
            except:
                logger.warning('Unable to parse the article for link: {0}'.format(link))
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
    formatter = logging.Formatter('%(levelname)s %(asctime)s %(threadName)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    if debug_enabled:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)

    running = False
    if not cache_disabled:
        # Check if another process is running. If so, quit because we don't want undesired accesses to the SQLite
        for p in psutil.process_iter():
            if os.path.basename(__file__) in p.name():
                running = True

        if running:
            logger.warning('Another process is running. Quit.')
            sys.exit(0)

    config = configparser.RawConfigParser(allow_no_value=True)
    ini_file = os.path.dirname(os.path.realpath(__file__)) + '/settings.ini'
    logger.debug('ini file path: {0}'.format(ini_file))
    config.read(ini_file)

    threads = []
    for section in config.sections():
        logger.debug('Reading configuration for {0}'.format(section))
        feed = config.get(section, 'feed')
        logger.debug('Feed to parse: {0}'.format(feed))
        output_file = config.get(section, 'output_file')
        logger.debug('Output file: {0}'.format(output_file))

        # Start thread
        t = threading.Thread(target=parse_the_feed, args=(logger, section, feed, output_file, cache_disabled))
        threads.append(t)
        t.start()
