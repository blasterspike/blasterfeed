# blasterfeed

#### Table of Contents

1. [Description](#description)
2. [Installation](#Installation)
3. [Usage](#usage)
4. [Technical decisions](#technical-decisions)  
  4.1. [Python 3](#python-3)  
  4.2. [SQLite3](#sqlite3)
5. [The ini file](#the-ini-file)  
  5.1. [The structure](#the-structure)  
  5.2. [Example](#example)
6. [Caching](#caching)
7. [Threading](#threading)
8. [dateutil and timezone](#dateutil-and-timezone)
9. [Known issues](#known-issues)

## Description

Nowadays RSS feeds are providing just a brief summary instead of the full article.  
This python script creates a new RSS feed fetching the full article using the links present in the feed.

## Installation

blasterfeed is relying on some other python modules.
To install them

```bash
pip install -r requirements.txt
```

requests>=2.6.0
is to avoid the error

```
  File "/usr/local/lib/python2.7/dist-packages/requests/packages/urllib3/contrib/pyopenssl.py", line 70, in <module>
    ssl.PROTOCOL_SSLv3: OpenSSL.SSL.SSLv3_METHOD,
AttributeError: 'module' object has no attribute 'PROTOCOL_SSLv3'
```

Reference: [patch-pyopenssl-for-sslv3-issue](http://stackoverflow.com/questions/28987891/patch-pyopenssl-for-sslv3-issue)

## Usage

After setting the ini file (see paragragh below), just run

`python3 blasterfeed3k.py`

Available parameters

```
--debug <To enable debug mode>
--disable-cache <To not create a SQLite DB used for caching>
```

## Technical decisions

### Python 3

This is due to the compatibility offered by newspaper module.
As stated on their [README.md](https://github.com/codelucas/newspaper)

> Newspaper is a Python3 library! Or, view our deprecated and buggy Python2 branch

### SQLite3

Lightweight and sufficient for what this script has to do.
As we are initiating a connection per thread, there is no need to set the check_same_thread to False.

## The ini file

The ini file must be called settings.ini and must be place in the same directory where the script is.
For each feed you need to create a different section.
All the fields are mandatory.

### The structure

```
[feed_name]
url = <url_of_the_feed>
output_file = <full_path_of_the_output_file>
```

### Example

```
[AwesomeWebsite]
url = https://an-awesome-webiste.com/feed.xml
output_file = /var/www/rss/OriginalFeed.xml

[GreatWebsite]
url = https://great-webiste.com/feed.xml
output_file = /var/www/rss/GreatWebsite.xml
```

## Caching

To improve speed and reduce HTTP requests, for each item inside a feed, blasterfeed stores the HTML content of the 
full article inside a SQLite database.
The DB is called blasterfeed-cache.py and it is stored in the same directory of blasterfeed.py
At the end of each XML generation, a cleanup will run, deleting all the articles that are not present anymore in the 
feed.
The fields stored in the DB are:
- Link to the RSS feed
- Link to the item of the feed
- Date, for debug testing only
- Content

## Threading

For each section you have in settings.ini, blasterfeed will spawn a different thread.

## dateutil and timezone

feedparser uses dateutil to parse the feed pubDate if it is a string.
Unfortunately dateutil doesn't support timezones and it fails with ValueError if the feed pubDate doesn't have one.
To solve this issue, I have generated a dictionary with as much timezone as I can to use with dateutil, so I can provide to feedparser a datetime object with timestamp.
To generate this dictionary I have used the script *generate_timezone.py* which is not called anywhere.

## Known issues

If you get the following error fetching a full article

```
Traceback (most recent call last):
  File "/usr/local/lib/python2.7/dist-packages/newspaper/images.py", line 119, in fetch_url
    p.feed(new_data)
  File "/usr/local/lib/python2.7/dist-packages/PIL/ImageFile.py", line 392, in feed
    im.mode, d, a, im.decoderconfig
  File "/usr/local/lib/python2.7/dist-packages/PIL/Image.py", line 413, in _getdecoder
    raise IOError("decoder %s not available" % decoder_name)
IOError: decoder jpeg not available
```

follow the steps provided here: [PIL/Pillow IOError: decoder jpeg not available](https://coderwall.com/p/faqccw/pil-pillow-ioerror-decoder-jpeg-not-available)
