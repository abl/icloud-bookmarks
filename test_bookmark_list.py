import icloud.webdav
from test_credential_cache import getUser, getPass

principal = icloud.webdav.Principal(getUser(), getPass())

if not principal.authenticate():
    print "[ERROR] Not authorized; check/clear settings."

print principal

bookmarks = icloud.webdav.BookmarkFactory.construct(principal)

b = bookmarks.get()

print b

print [x.get() for x in b]