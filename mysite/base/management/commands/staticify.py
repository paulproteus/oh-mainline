from optparse import make_option
import datetime
import logging
import os
import sys
import urllib

from django.core.management.base import BaseCommand
from django.core.urlresolvers import RegexURLPattern, RegexURLResolver
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
    '^__debug__/',
    # These URLs depend on templates which have been deleted.
    '^\\+landing/import$',
    '^\\+landing/opps$',
    '^\\+landing/projects$',
    # This URL is intended to crash.
    '^account/catch-me$',
    # This crashes when not logged in.
    '^profile/views/replace_icon_with_default$',
    # exrex can't generate a list of valid URLs for these tastypie resources.
    # Skip them, since they require login.
    '^(?P<resource_name>portfolio_entry)/set/(?P<pk_list>.*?)/$',
    '^(?P<resource_name>portfolio_entry)/(?P<pk>.*?)/$',
    '^(?P<resource_name>tracker_model)/set/(?P<pk_list>.*?)/$',
    '^(?P<resource_name>tracker_model)/(?P<pk>.*?)/$',
    # I think these come from django-admin and/or django.contrib.auth. I'm not sure; we don't need them, anyway.
    '^(.+)/$',
    '^(\\d+)/password/$',
    '^(.+)/history/$',
    '^(.+)/delete/$',
    '^disconnect/(?P<backend>[^/]+)/(?P<association_id>[^/]+)/$',
    '^complete/(?P<backend>[^/]+)/$',
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
        try:
            all_matches = list(exrex.generate(regex_pattern))
        except Exception:
            print 'exrex fail on', repr(regex_pattern)
            return
        longest_example = sorted(all_matches,
            key=lambda s: len(s))[-1]
        url = '/' + longest_example
        try:
            response = c.get(url)
        except Exception:
            print('Failed to get url=%s while looking at pattern=%s', url, regex_pattern)
        if response.get('location'):
            html = '<html><head><meta http-equiv="refresh" content="0; URL=\'%s\'" /></head></html>' % (urllib.quote(
                fix_wiki_url(response['location'].replace('http://testserver', '')), safe='/:'))
            save_html(url, html)
    else:
        print('too many', regex_pattern, num_possible)


class Command(BaseCommand):
    help = 'Generates a static HTML snapshot of the site'

    option_list = BaseCommand.option_list + (
        make_option('-d', '--dry-run', action='store_true',
                    dest='dry_run', default=False, help='Skip generating HTML for faster execution.'
        ),
        make_option('-m', '--max-work', type='int',
                    dest='max_work', default=float('inf'), help='Max # of URLs to process'
        ),
    )

    def add_arguments(self, parser):
        parser.add_argument('poll_id', nargs='+', type=int)

    def handle(self, *args, **options):
        import mysite.urls
        patterns = list(mysite.urls.urlpatterns)
        i = 0
        c = Client()
        while i < len(patterns):
            if i >= options.get('max_work'):
                return
            pattern = patterns[i]
            i += 1
            if isinstance(pattern, RegexURLPattern):
                regex_pattern = pattern.regex.pattern
                if regex_pattern in SKIPPABLE:
                    continue
                if not options.get('dry_run'):
                    save_regex_pattern(c, regex_pattern)
            elif isinstance(pattern, RegexURLResolver):
                try:
                    patterns.extend(pattern.url_patterns)
                except Exception:
                    print('whoa')
                    raise
            else:
                print('skipping', repr(pattern))
