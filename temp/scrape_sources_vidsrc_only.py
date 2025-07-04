# -*- coding: utf-8 -*-


vidsrc_domains = ['v2.vidsrc.me', 'vidsrc.me', 'vidsrc.to', 'cloudnestra.com']


def vidsrc(link, hostDict, info=None):
    sources = []
    search = set(hostDict) # include domains in hostDict, so we can use make_item
    hostDict.extend(i for i in vidsrc_domains if i not in search and not search.add(i))
    try:
        if scrape_vidsrc == 'false':
            return sources
        domain = re.findall(r'(?://|\.)(v2\.vidsrc\.me|vidsrc\.me|vidsrc\.to|cloudnestra\.com)/', link)[0]
        headers = {'User-Agent': client.UserAgent, 'Referer': f'https://{domain}/'}
        redirectlink = client.request(link, redirect=True, verify=False, headers=headers, output='geturl')
        html = client.request(redirectlink, redirect=True, verify=False, headers=headers, output='')
        items = client_utils.parseDOM(html, 'script')
        for item in items:
            if 'player_iframe' not in item:
                continue
            try:
                item_base = f'https://{domain}'
                item_html = item.replace("\'", '"')
                item_src = re.findall(r'src: "(.*?)"', item_html, re.DOTALL)[0]
                item_src = item_base + item_src if item_src.startswith('/') else item_src
                item_html = client.request(item_src, headers=headers, output='')
                scripts = client_utils.parseDOM(item_html, 'script')
                for script in scripts:
                    if 'new playerjs' not in script.lower():
                        continue
                    script_html = script.replace("\'", '"')
                    m3u8_link = re.findall(r'file: "(https[^"]*)"', script_html, re.DOTALL)[0]
                    url = prepare_link(m3u8_link)
                    # log_utils.log('url =' + repr(url), 1)
                    if not url:
                        continue
                    # source = {'source': 'v2.vidsrc.me', 'quality': 'SD', 'info': None, 'url': url, 'direct': False }
                    source = make_item(hostDict, url, host='v2.vidsrc.me', info=info, prep=False)
                    # log_utils.log('source =' + repr(source), 1)
                    if source:
                        sources.append(source)
            except:
                # log_utils.log('vidsrc', 1)
                pass
        # log_utils.log('source =' + repr(source), 1)
        return sources
    except Exception:
        log_utils.log('vidsrc', 1)
        return sources



