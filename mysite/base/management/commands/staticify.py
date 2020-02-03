from optparse import make_option
import datetime
import logging
import os
import sys
import urllib

from django.core.management.base import BaseCommand
from django.core.urlresolvers import RegexURLPattern
from django.test.client import Client
import exrex

logger = logging.getLogger(__name__)


SKIPPABLE = [
    '^,$',
    r'^\)$',
    r'^blog/(?P<url>.*)',
    r'^bugs/?$',
    r'^bugs/(?P<number>\d+)$',
    r'^forum(?P<path>($|/.*))',
    r'^wiki$',
    r'^w(iki)?(?P<path>($|/.*))',
    '^\\+project_icon_poll/(?P<project_name>.+)',
    '^\\+unsubscribe/(?P<token_string>.+)',
    '^-profile.views.unsubscribe_do',
    '^\\+projedit/(?P<project__name>.+)',
    '^\\+do/project.views.wanna_help_do',
    '^\\+do/profile.views.set_expand_next_steps_do',
    '^\\+do/project.views.unlist_self_from_wanna_help_do',
    '^\\+answer/vote/(?P<object_id>\\d+)/(?P<direction>up|down|clear)vote/?$',
    '^missions/tar/downloadfile/(?P<name>.*)',
    '^missions/tar/ghello-0.4.tar.gz',
    '^customs/add/(?P<tracker_type>\\w*)$',
]

def save_html(url, html):
    path = 'output/' + url + '/'
    try:
        os.makedirs(path)
    except OSError, e:
        if e.errno == 17: # File exists
            pass
    filename = path + '/index.html'
    with open(filename, 'w') as fd:
        fd.write(html)

def fix_wiki_url(url):
    return url.replace('/wiki/', 'https://wiki.openhatch.org/wiki/')

def save_regex_pattern(c, regex_pattern):
    num_possible = exrex.count(regex_pattern)
    if num_possible <= 2:
        longest_example = sorted(
            exrex.generate(regex_pattern),
            key=lambda s: len(s))[-1]
        url = '/' + longest_example
        response = c.get(url)
        if response.get('location'):
            html = '<html><head><meta http-equiv="refresh" content="0; URL=\'%s\'" /></head></html>' % (urllib.quote(
                fix_wiki_url(response['location'].replace('http://testserver', '')), safe='/:'))
            save_html(url, html)
    else:
        print('too many', regex_pattern, num_possible)


class Command(BaseCommand):
    help = 'Generates a static HTML snapshot of the site'

    option_list = BaseCommand.option_list + (
    )

    def handle(self, *args, **options):
        import mysite.urls
        patterns = mysite.urls.urlpatterns
        num = 160 # len(patterns)
        c = Client()
        for pattern in patterns:
            if isinstance(pattern, RegexURLPattern):
                regex_pattern = pattern.regex.pattern
                if regex_pattern in SKIPPABLE:
                    continue
                save_regex_pattern(c, regex_pattern)
                num = num - 1
                if num == 0:
                    return
            else:
                print('skipping', pattern)
