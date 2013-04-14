import icloud.webdav
from test_credential_cache import getUser, getPass

if __name__ == "__main__":
    principal = icloud.webdav.Principal(getUser(), getPass())
    
    if principal.authenticate():
        print principal._principal