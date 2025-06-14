# -*- coding: utf-8 -*-

import re
from six.moves.urllib_parse import parse_qs, urlencode

from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import scrape_sources
from resources.lib.modules import log_utils

DOM = client_utils.parseDOM


class source:
    def __init__(self):
        try:
            self.results = []
            self.domains = ['projectfreetv.lol', 'projectfreetv.cyou', 'profreetv.stream']
            self.base_link = 'https://www.profreetv.stream'
            self.movie_link = '/movies/%s-%s/'
            self.tvshow_link = '/tv-series/%s-season-%s-episode-%s/'
            self.cookie = client.request(self.base_link, output='cookie', timeout='5')
            self.notes = 'sim/dupe site of projectfreetv_cyou and projectfreetv_lol.'
        except:
            #log_utils.log('__init__', 1)
            return


    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        url = {'imdb': imdb, 'title': title, 'year': year}
        url = urlencode(url)
        return url


    def tvshow(self, imdb, tmdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
        url = urlencode(url)
        return url


    def episode(self, url, imdb, tmdb, tvdb, title, premiered, season, episode):
        if not url:
            return
        url = parse_qs(url)
        url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
        url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
        url = urlencode(url)
        return url


    def sources(self, url, hostDict):
        try:
            if not url:
                return self.results
            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            season, episode = (data['season'], data['episode']) if 'tvshowtitle' in data else ('0', '0')
            year = data['premiered'] if 'tvshowtitle' in data else data['year']
            search_title = cleantitle.geturl(title)
            if 'tvshowtitle' in data:
                result_url = self.base_link + self.tvshow_link % (search_title, season, episode)
            else:
                result_url = self.base_link + self.movie_link % (search_title, year)
            html = client.request(result_url, cookie=self.cookie)
            try:
                ext_links = DOM(html, 'tr', attrs={'class': r'ext_link.+?'})
                links = [(DOM(i, 'a', ret='href'), DOM(i, 'a', ret='title')) for i in ext_links]
                links = [(i[0][0], i[1][0]) for i in links if len(i[0]) > 0 and len(i[1]) > 0]
                # log_utils.log('links =' + repr(links), 1)
                for link, host in links:
                    try:
                        link = self.base_link + link if not link.startswith('http') else link
                        if not link:
                            continue
                        
                        item = scrape_sources.make_item(hostDict, link, host=host, info=None, prep=True)
                        if item:
                            if scrape_sources.check_host_limit(item['source'], self.results):
                                continue
                            self.results.append(item)
                    except:
                        #log_utils.log('sources', 1)
                        pass
            except:
                #log_utils.log('sources', 1)
                pass
            return self.results
        except:
            #log_utils.log('sources', 1)
            return self.results


    def resolve(self, url):
        if any(x in url for x in self.domains):
            try:
                url = url.replace('/open/link/','/open/site/')
                html = client.request(url, cookie=self.cookie)
                if not html:
                    return
                try:
                    if 'redirecting...' in html.lower():  # fix for voe.sx
                        match = re.search(r"window\.location\.href\s*=\s*'([^']+)'", html)
                        link = match.group(1) if match else None
                        html = client.request(link, cookie=self.cookie)
                        if not html:
                            return
                    links = DOM(html, 'iframe', ret='src')
                    link = links[0] if links else None
                    if link:
                        link = link.replace('streamhls.to', 'savefiles.com') if 'streamhls.to' in link else link
                    if 'doodstream.com' in html.lower():  #fix for doodstream
                        hoster = DOM(html, 'link', attrs={'rel': 'preconnect'}, ret='href')[0]
                        hoster = 'https:' + hoster if hoster.startswith('//') else hoster
                        hoster = hoster.replace('i.doodcdn.io', 'dood.so')  ## hack fix for doodstream.com
                        link = hoster + link if not link.startswith('http') else link
                    if not link:
                        return
                    if link.startswith('/e/'):  #fix for mixdrop.co
                        html = DOM(html, 'div', attrs={'class': 'download-embed block'})
                        links = DOM(html, 'iframe', ret='src')
                        link = links[0] if links else None
                    if link == '/e/' or 'javascript' in link or link.endswith('/e/'):
                        link = None
                    if not link:
                        return
                except:
                    match = re.compile(r'"(/open/site/.+?)"', re.I|re.S).findall(html)[0]
                    link = self.base_link + match if not match.startswith('http') else match
                    link = client.request(link, output='geturl', timeout=10)
                return link
            except:
                #log_utils.log('resolve', 1)
                pass
        else:
            return url


