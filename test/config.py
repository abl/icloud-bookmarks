from base64 import b64encode, b64decode
from pyDes import triple_des, PAD_PKCS5

class SecureConfig:
    def __init__(self, des_key, config):
        self._des = triple_des(des_key)
        self._config = config
    
    def _clarify(self, value):
        return self._des.decrypt(b64decode(value), padmode=PAD_PKCS5)

    def _obfuscate(self, value):
        return b64encode(self._des.encrypt(value, padmode=PAD_PKCS5))

    def get(self, key):
        key = self._obfuscate(key)
        value = self._config.get(key)
        if value is None:
            return value
    
        return self._clarify(value)[len(key):]

    def set(self, key, value):
        key = self._obfuscate(key)
        value = self._obfuscate(key+value)
    
        self._config.set(key, value)
    
    def write(self):
        self._config.write()