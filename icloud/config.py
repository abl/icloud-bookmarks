import os, os.path

try:
    import ujson as json
except ImportError:
    import json


class Config:
    def __init__(self, dct={}):
        cfgdir = os.path.expanduser("~/.python-icloud")
        if not os.path.exists(cfgdir):
            os.mkdir(cfgdir)
        
        self._properties = dct
        
        self._filename  = os.path.expanduser("~/.python-icloud/config.json")
        if os.path.exists(self._filename):
            props = {}
            with open(self._filename) as f:
                props = json.load(f)
            
            for k,v in props.items():
                self._properties[k] = v
        
    def get(self, key):
        if key in self._properties:
            return self._properties[key]
        return None
    
    def set(self, key, value):
        self._properties[key] = value
    
    def write(self):
        with open(self._filename, 'w') as f:
            json.dump(self._properties, f)