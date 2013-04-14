import icloud.config
import getpass, os, os.path
from base64 import b64encode, b64decode
from test.config import SecureConfig

config = icloud.config.Config()

#Trying to obfuscate a bit here to prevent casual grepping.
k = config.get("k")
if config.get("k") is None:
    k = os.urandom(24)
    config.set("k", b64encode(k))
else:
    k = b64decode(k)

sc = SecureConfig(k, config)

def getUser():    
    username = sc.get("username")
    
    if username is None:
        print "Username:",
        username = raw_input()
        sc.set("username", username)
        sc.write()
    
    return username

def getPass():
    password = sc.get("password")
    
    if password is None:
        password = getpass.getpass()
        sc.set("password", password)
        sc.write()
    
    return password