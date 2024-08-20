from lxml import etree

def run_lxml_parser(html_content: str):
    parser = etree.HTMLParser()
    tree = etree.fromstring(html_content, parser)
    title = tree.xpath('//title/text()')
    return title[0] if title else None
