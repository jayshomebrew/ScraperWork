import re
import requests
from six.moves.urllib_parse import parse_qs, urlencode

from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import scrape_sources
from resources.lib.modules import log_utils

DOM = client_utils.parseDOM

class source:
    def __init__(self):
        self.results = []
        self.domains = ['goojara.to', 'goojara.ch', 'supernova.to', 'goojara.is']
        self.base_link = 'https://goojara.to'
        self.search_link = '/?s=%s'
        self.php_entrypoint = '/xmre.php'
        self.notes = 'fixed session issue, using client.requests & replace cookie headers'
        self.headers = client.dnt_headers
        

    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        url = {'imdb': imdb, 'title': title, 'aliases': aliases, 'year': year}
        url = urlencode(url)
        return url


    def tvshow(self, imdb, tmdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        url = {'imdb': imdb, 'tvshowtitle': tvshowtitle, 'aliases': aliases, 'year': year}
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
            aliases = eval(data['aliases'])
            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            season, episode = (data['season'], data['episode']) if 'tvshowtitle' in data else ('0', '0')
            year = data['year']
            check_term = '%s - Season %s' % (title, season) if 'tvshowtitle' in data else title
            # check_title = cleantitle.get(check_term)
            
            if not self.base_link.startswith('https://ww1.'):
                self.base_link = 'https://ww1.' + self.base_link.split('://')[1]
        
            postdata = { 
                'x': '1',
                'q': title.lower(),
            }
    
            url = self.base_link + self.php_entrypoint
            
            self.cookie = client.request(self.base_link, headers=self.headers, output='cookie', timeout='10')
            cookie_dict = {cookie.split('=')[0]: cookie.split('=')[1] for cookie in self.cookie.split('; ')}
            r = client.request(url, headers=self.headers, post=postdata, cookie=self.cookie)
            r = DOM(r, 'ul')
            r = list(zip(DOM(r, 'a', ret='href'), DOM(r, 'div')))
            r = [(url, client_utils.remove_tags(html)) for url, html in r]
            r = [(url, re.sub(r'\(\d{4}\)', '', html), re.findall(r'\((\d{4})\)', html)[0]) for url, html in r]
            r = [(i[0], i[1], i[2]) for i in r if len(i[0]) > 0 and len(i[1]) > 0 and len(i[2]) > 0]
            # log_utils.log('r =' + repr(r), 1)
            
            # goojara tv show year are incorrect, sometimes.
            # this will match ALIAS and YEAR
            try:
                result_url = next(
                    i[0] for i in r if cleantitle.match_alias(i[1], aliases) and cleantitle.match_year(i[2], data.get('year')))

            except StopIteration:
                try:
                    year2 = data.get('year')
                    result_url = next(
                        i[0] for i in r if cleantitle.match_alias(i[1], aliases) and cleantitle.match_year(i[2], year2))

                except StopIteration:
                    result_url = next(i[0] for i in r if cleantitle.match_alias(i[1], aliases))

            if not result_url:
                return
            if not result_url.startswith(self.base_link):
                result_url = self.base_link + result_url
            
            r = client.request(result_url, headers=self.headers, cookie=self.cookie, verify=False)

            if 'tvshowtitle' in data:
                data_id = DOM(r, 'div', attrs={'id': 'seon'}, ret='data-id')[0]
                postdata = {'s': season, 't': data_id}
                r = client.request(url, headers=self.headers, post=postdata, cookie=self.cookie)
                r = list(zip(DOM(r, 'a', ret='href'), DOM(r, 'span', attrs={'class': 'sea'})))
                check_episode = episode.zfill(2)  # add leading zero
                found_url = [i[0] for i in r if check_episode == i[1]][0]
                if not found_url.startswith(self.base_link):
                    result_url = self.base_link + found_url
                # r = client.scrapePage(result_url).text

            resp1 = client.scrapePage(result_url, headers=self.headers, cookie=self.cookie)
            r = resp1.text

            r = [i for i in DOM(r, 'div', attrs={'class': 'lxbx'}) if 'Direct Links' in i][0]

            result_links = list(zip(DOM(r, 'a', ret='href'), 
                                    [re.sub(r'<span>.*?</span>', '', site).strip() for site in DOM(r, 'a')]))
            # log_utils.log('result_links =' + repr(result_links), 1)
            # log_utils.log('len(result_links) =' + repr(len(result_links)), 1)
            
            gg = cookie_dict
            response_content = resp1.content.decode(encoding='utf-8', errors='strict')
            match = re.findall(r"_3chk\(['\"](.+?)['\"],['\"](.+?)['\"]\)", response_content, re.DOTALL)
            ck, ck2 = match[0] if match else (None, None)

            gg[ck] = ck2
            cookie_dict[ck] = ck2

            # replace the Cookies in the header
            new_cookies = '; '.join([f"{k}={v}" for k, v in cookie_dict.items()])
            self.headers["Cookie"] = new_cookies

            for link, hoster in result_links:
                html = client.request(link, headers=self.headers)
                if not html:
                    # log_utils.log('FAILED link =' + repr(hoster) + repr(link), 1)
                    continue
                # log_utils.log('html =' + repr(hoster) + repr(html), 1)
                if any(msg in html.lower() for msg in ('file not found', 'no such file=', 'video you are looking for is not found')):
                    continue
                try:
                    link = DOM(html, 'iframe', ret='src')[0]
                except:
                    link = client.request(link, output='geturl')
                if link:
                    link = 'https:' + link if link.startswith('//') else link
                    # fix wootly links for resolveurl
                    # web.wootly.ch/e/some/text/123 -> www.wootly.ch/?v=123
                    link = re.sub(r"^(https?://)web\.wootly\.ch/e/.*/([^/]+)$",r"\1www.wootly.ch/?v=\2", link)
                try:
                    for source in scrape_sources.process(hostDict, link):
                        self.results.append(source)
                except:
                    #log_utils.log('sources', 1)
                    pass

            return self.results
        except:
            return self.results


    def resolve(self, url):
        # log_utils.log('url =' + repr(url), 1)
        return url

