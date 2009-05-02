#!/usr/bin/env python

"""
(c) 2009 Kasper Souren

Affero GNU General Public Licence 3


A module to call Drupal Services, loosely based on several pieces of
code found elsewhere:

 * http://drupal.org/project/Python_Services
 * http://www.speakingx.com/blog/2008/11/21/testing-out-drupals-service-module-using-python
 * http://drupal.org/node/308629

Check /admin/build/services/settings on your Drupal install.

DrupalServices can be passed a configuration dict.  Based on that it
will instantiate the proper class.  Using Drupal Services with keys
but without a session is currently not supported.

"""


import xmlrpclib, time, random, string, hmac, hashlib, pprint

class BasicServices(xmlrpclib.Server):
    """Drupal Services without keys or sessions, not very secure."""
    def __init__(self, url):
        xmlrpclib.Server.__init__(self, url)
        self.connection = self.system.connect()
        self.sessid = self.connection['sessid']

    def _call(self, method_name, *args):
        to_eval = ('self.' + method_name + 
                   '(' + 
                   ', '.join(map(repr, args)) +  # Turn args into eval-uable string
                   ')')
        return eval(to_eval)


class ServicesSessid(BasicServices):
    """Drupal Services with sessid."""
    def __init__(self, url, username, password):
        BasicServices.__init__(self, url)
        self.session = self.user.login(self.sessid, username, password)

    def _call(self, method_name, *args):
        to_eval = ('self.' + method_name + 
                   '(' + ', '.join(map(repr, 
                                       [self.sessid] + 
                                       map(None, args))) # Python refuses to concatenate list and tuple
                   + ')')  
        return eval(to_eval)

class ServicesSessidKey(ServicesSessid):
    """Drupal Services with sessid and keys."""
    def __init__(self, url, username, password, domain, key):
        BasicServices.__init__(self, url)
        self.domain = domain
        self.key = key
        self._call('user.login', username, password)

    def _call(self, method_name, *args):
        hex, timestamp, nonce = self._token(method_name)
        to_eval = ('self.' + method_name + 
                   '(' + ', '.join(map(repr, 
                                       [hex,
                                        self.domain, timestamp,
                                        nonce, self.sessid] + 
                                       map(None, args))) # Python refuses to concatenate list and tuple
                   + ')')  
        try:  # TODO: refactor into self._eval
            return eval(to_eval)
        except xmlrpclib.Fault, err:
            print "Oh oh. An xmlrpc fault occurred."
            print "Fault code: %d" % err.faultCode
            print "Fault string: %s" % err.faultString


    def _token(self, api_function):
        timestamp = str(int(time.mktime(time.localtime())))
        nonce = "".join(random.sample(string.letters+string.digits, 10))
        return (hmac.new(self.key, "%s;%s;%s;%s" % 
                         (timestamp, self.domain, nonce, api_function), 
                         hashlib.sha256).hexdigest(),
                timestamp,
                nonce)


class DrupalServices: 
    """Drupal services class."""
    def __init__(self, config):
        self.config = config
        if (config.has_key('username') and config.has_key('key')):
            self.server = ServicesSessidKey(config['url'], 
                                            config['username'], config['password'], 
                                            config['domain'], config['key'])
        elif (config.has_key('username')):
            self.server = ServicesSessid(config['url'], config['username'], config['password'])
        else:
            self.server = BasicServices(config['url'])

    def listMethods(self):
        return self.server.system.listMethods()
    
    def getInfo(self, method_name):
        print method_name
        print self.server.system.methodHelp(fName)
        print self.server.system.methodSignature(fName)

    def call(self, method_name, *args):
        return self.server._call(method_name, *args)



if __name__ == "__main__":
    from config import config
    drupal = DrupalServices(config)

    new_node = { 'type': 'page',
                 'title': 'Just a little test',
                 'body': '''Ordenar bibliotecas es ejercer de un modo silencioso el arte de la crítica.
-- Jorge Luis Borges. (1899-1986) Escritor argentino.''',
                 }
    new_node_id = drupal.call('node.save', new_node)
    print 'New node id: %s' % new_node_id 
    print drupal.call('node.get', int(new_node_id), ['body'])
