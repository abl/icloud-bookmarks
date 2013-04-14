import httplib2
from xml.dom import minidom as dom
from urlparse import urljoin

CALDAV_SERVERS = ["p%02d-caldav.icloud.com" % x for x in xrange(1,10)]
BOOKMARK_SERVERS = ["p%02d-bookmarks.icloud.com" % x for x in xrange(1,10)]

## {{{ http://code.activestate.com/recipes/303061/ (r2)
def remove_whitespace_nodes(node, unlink=False):
    """Removes all of the whitespace-only text decendants of a DOM node.
    
    When creating a DOM from an XML source, XML parsers are required to
    consider several conditions when deciding whether to include
    whitespace-only text nodes. This function ignores all of those
    conditions and removes all whitespace-only text decendants of the
    specified node. If the unlink flag is specified, the removed text
    nodes are unlinked so that their storage can be reclaimed. If the
    specified node is a whitespace-only text node then it is left
    unmodified."""
    
    remove_list = []
    for child in node.childNodes:
        if child.nodeType == dom.Node.TEXT_NODE and \
           not child.data.strip():
            remove_list.append(child)
        elif child.hasChildNodes():
            remove_whitespace_nodes(child, unlink)
    for node in remove_list:
        node.parentNode.removeChild(node)
        if unlink:
            node.unlink()
## end of http://code.activestate.com/recipes/303061/ }}}

def parseXBELString(content, unlink=False):
    x = dom.parseString(content)
    remove_whitespace_nodes(x, unlink)
    
    return x


class Principal:
    CURRENT_USER_PRINCIPAL = '''<?xml version="1.0" encoding="UTF-8"?>
<A:propfind xmlns:A='DAV:'>
  <A:prop>
    <A:current-user-principal/>
  </A:prop>
</A:propfind>
'''

    CURRENT_BOOKMARKS = '''<?xml version="1.0" encoding="UTF-8"?>
<A:propfind xmlns:A="DAV:">
  <A:prop>
    <B:bookmark-home-set xmlns:B="urn:mobileme:bookmarks"/>
    <A:displayname/>
    <C:email-address-set xmlns:C="http://calendarserver.org/ns/"/>
    <A:principal-collection-set/>
    <A:principal-URL/>
    <A:resource-id/>
    <A:supported-report-set/>
  </A:prop>
</A:propfind>
'''
    @staticmethod
    def _extractLink(xml, key):
        return xml.getElementsByTagName(key)[0].getElementsByTagName("href")[0].lastChild.nodeValue

    def __init__(self, username, password, server=BOOKMARK_SERVERS[0], protocol="https"):
        self.username = username
        self.password = password
        self.server = server
        self.protocol = protocol
        self._cache = {}
        self._session = httplib2.Http()
        self._session.add_credentials(self.username, self.password)
        self._principal = None
    
    def __repr__(self):
        return "<icloud.webdav.Principal(%s, %s, %s, %s) = %s>" % (
            repr(self.username),
            repr("********"),
            repr(self.server),
            repr(self.protocol),
            ("<unauthenticated>" if self._principal is None else repr(self._principal))
        )
    
    def authenticate(self):
        resp, content = self._session.request("%s://%s" % (self.protocol, self.server), "PROPFIND", self.CURRENT_USER_PRINCIPAL,
            headers={'Depth':'1', 'Content-Type':"text/xml; charset='UTF-8'"})
        
        if resp['status'][0] == "2":
            xml = parseXBELString(content)
            self._principal = self._extractLink(xml, "current-user-principal")
            return True
        
        return False
    
    def getBookmarksURI(self):
        if "bookmark" in self._cache:
            return self._cache['bookmark']
        resp, content = self._session.request(self._principal, "PROPFIND", self.CURRENT_BOOKMARKS, headers={'Depth':'0', 'Brief':'t', 'Content-Type':'text/xml'})
        
        if resp['status'][0] == "2":
            xml = parseXBELString(content)
            bookmarks = self._extractLink(xml, "bookmark-home-set")
            
            self._cache['bookmark'] = bookmarks
            
            return bookmarks
        
        return None

class Bookmark:
    def __init__(self, principal, uri):
        self._principal = principal
        self._session = principal._session
        self._uri = uri
        self.guid = uri[-41:-5]
        self.href = None
        self.title = None
        self.position = None
    
    def __repr__(self):
        if self.href is not None:
            val = repr((self.title, self.href, self.position))
        else:
            val = "<unloaded>"
        return "<Bookmark %s = %s>" % (self.guid, val)
    
    def refresh(self):
        self.href = None
        self.title = None
        return self.get()
    
    @staticmethod
    def _traverse(xml):
        #Apple appears to randomly change the prefix on the tag and the presence/ordering of said prefix.
        #What seems to remain constant is the presence of a "bookmark" tag with an href and a child "title" tag
        #TODO: Add verification/handling for multiple return values.
        
        href = None
        title = None
        position = None
        
        
        assert len(xml.childNodes) == 1
        for root in xml.childNodes:
            assert root.nodeName.endswith("xbel")
            assert len(root.childNodes) == 1
            
            for bookmark in root.childNodes:
                assert bookmark.nodeName.endswith("bookmark")
                assert len(bookmark.childNodes) == 1
                
                for k,v in bookmark.attributes.items():
                    if k.startswith("xmlns"):
                        continue
                    
                    assert k.endswith("href") or k.endswith("position"), "Unexpected attribute '%s'" % k
                    if k.endswith("href"):
                        href = v
                    elif k.endswith("position"):
                        position = int(v)
                    
                for titleNode in bookmark.childNodes:
                    assert titleNode.nodeName.endswith("title")
                    assert len(titleNode.childNodes) == 1
                    
                    for textNode in titleNode.childNodes:
                        assert textNode.nodeType == dom.Node.TEXT_NODE
                        assert title is None
                        
                        title = textNode.nodeValue
                        
        
        return (href, title, position)
    
    def get(self):
        global xml
        
        if self.href is not None:
            return self
        
        resp, content = self._session.request(self._uri, "GET")
        xml = parseXBELString(content)
        
        (self.href, self.title, self.position) = Bookmark._traverse(xml)
        
        return self

class BookmarkFolder:
    def __repr__(self):
        if self._cache is not None:
            val = "<%d entries>" % (len(self._cache))
            name = repr(self._displayname)
        else:
            val = "<unloaded>"
            name = "<unloaded>"
        return "<BookmarkFolder %s %s = %s>" % (self.guid, name, val)
    
    def __init__(self, principal, uri, base_uri):
        self._principal = principal
        self._session = principal._session
        self._tail_uri = uri
        self.guid = uri[:36] if uri is not None else "00000000-0000-0000-0000-000000000000"
        self._base_uri = base_uri
        self._cache = None
        self._uri = urljoin(base_uri, uri) if uri is not None else base_uri

    def refresh(self):
        self._cache = None
        return self.get()

    def get(self):
        if self._cache is not None:
            return self._cache
        
        resp, content = self._session.request(self._uri, "PROPFIND", headers = {'Depth':'0', 'Content-Length':'0'})
        
        self._displayname = "<unnamed>"
        self._raw_properties = dom.parseString(content)
        
        for nameNode in self._raw_properties.getElementsByTagName("displayname"):
            for textNode in nameNode.childNodes:
                self._displayname = textNode.nodeValue
        
        resp, content = self._session.request(self._uri, "GET")
        if content is not None and len(content) > 0:
            self._cache = [BookmarkFactory.construct(self._principal, x, self._uri) for x in content.split(",")]
        else:
            self._cache = []
        return self._cache

class BookmarkFactory:
    @staticmethod
    def construct(principal, uri=None, base_uri=None):
        if base_uri is None:
            base_uri = principal.getBookmarksURI()
        
        if uri is None or uri[-1] == "/":
            return BookmarkFolder(principal, uri, base_uri)
        else:
            return Bookmark(principal, urljoin(base_uri, uri))
    