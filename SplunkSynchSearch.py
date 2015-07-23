#! /usr/bin/python

import sys
import os
import urllib
import urllib2
import httplib2
from xml.dom import minidom
from time import sleep
from time import time


# External dependencies: httplib2
'''
To do:
- class documentation
- input validation for all the things, including server and query format
- better handling of invalid function calls
'''

class SplunkSynchSearch(object):
    '''
    Required parameters: server URL, username, password
    Optional parameters: query, search URI, login URI
    Query will be required later when submitting a search job
    Server should be checked to make sure we have protocol and port
    '''
    def __init__(self, server, username, password, search_uri='', login_uri='', query=''):
        self.server = server
        self.sUser = username
        self.sPass = password

        if query:
            self.searchQuery = self.checkSearchQuery(query)

        # Some sensible defaults
        self.sessionkey = ''

        if not search_uri:
            self.search_uri = 'servicesNS/admin/search/search/jobs/export'
        if not login_uri:
            self.login_uri =  'services/auth/login'


    def __setattr__(self, k, v):
        # Override setattr to make sure we validate the query is valid
        # anytime its value changes. Maybe it is better to do this at the
        # actual job submit time instead of overriding...
        if k in [ 'searchQuery' ]:
            checkQueryTerm = self.checkSearchQuery(v)
            super(SplunkSynchSearch, self).__setattr__(k, checkQueryTerm)
        else:
            super(SplunkSynchSearch, self).__setattr__(k, v)


    def checkSearchQuery(self, queryTerms):
        print('queryTerms is %s ' % queryTerms)
        if not queryTerms.startswith('search'):
            queryTerms = ''.join(['search ', queryTerms])

        return queryTerms


    def showSelf(self):
        from pprint import pprint
        pprint(vars(self))


    def get_session_token(self):
        myhttp = httplib2.Http(disable_ssl_certificate_validation=True)
        url = ''.join([self.server, '/', self.login_uri])
        body = urllib.urlencode({'username':self.sUser, 'password':self.sPass})
        response = myhttp.request(url, 'POST', headers={}, body=body)[1]
        sessionkey = minidom.parseString(response).getElementsByTagName \
            ('sessionKey')[0].childNodes[0].nodeValue
        self.sessionkey = sessionkey
        return(sessionkey)


    def submit_synch_search(self, outputmode):
        if not self.searchQuery:
            raise ValueException('Search object has no query')

        if not self.sessionkey:
            raise ValueException('Search object has no session token')


        myhttpSearch = httplib2.Http(disable_ssl_certificate_validation=True)
        url = ''.join([self.server, '/', self.search_uri])
        headers = {'Authorization': ''.join(['Splunk: ', self.sessionkey])}
        body = urllib.urlencode({'search': self.searchQuery})
        
        if outputmode == 'csv':
            body = ''.join([body, '&', urllib.urlencode({'output_mode': 'csv'})])
        elif outputmode == 'json':
            body = ''.join([body, '&', urllib.urlencode({'output_mode': 'json'})])
        elif outputmode == 'xml':
            body = ''.join([body, '&', urllib.urlencode({'output_mode': 'xml'})])
        else:
            return ValueException('Invalid output mode: {outputmode}'.format(outputmode=outputmode))
            
        response = myhttpSearch.request(url, 'POST', headers=headers, body=body)[1]
        return response



def main(argv):
    preamble = '''
    Thank you for choosing to run SplunkSynchSearch!  This is my
    implementation of the sample API code from Splunk, available at
    http://blogs.splunk.com/2011/08/02/splunk-rest-api-is-easy-to-use/

    When you are ready, just import SplunkSynchSearch.  You'll need to
    know your Splunk server, credentials, and search query.  If you are using
    the free version of Splunk, chances are your username is "admin" and your
    password is "changeme".  In the meantime, running this directly instead of
    importing will show you an example of how to instantiate a new search
    object and work with its methods.  The example will do a few things:

    (1) Create a new object
    (2) Generate a token
    (3) Submit a search, one for each output type
    (4) Write the search results to formats specific to the output mode
    (5) Call the showSelf method to print the object's attributes
    '''

    print(preamble)

    # Step one
    server = raw_input('Server name (eg. https://splunkserver:8089): ')
    searchQuery = '* earliest=-1h | stats count by sourcetype'
    print('We will use this search query: {query}'.format(query=searchQuery))
    sUser = raw_input('User name (eg. admin): ')
    sPass = raw_input('Password (eg. changeme): ')
    mySearch = SplunkSynchSearch(server=server, query=searchQuery, username=sUser, password=sPass)

    # Step two
    sessionToken = mySearch.get_session_token()
    print('Session token: {sessionToken}'.format(sessionToken = sessionToken))

    # This is a blocking search, so nothing happens until the above call for submitting the synchronous search finishes
    # Steps 3 and 4
    now = time()
    outputModes = ['csv', 'json', 'xml']
    for mode in outputModes:
        search_results = mySearch.submit_synch_search(mode)
        outfile = ''.join([str(now), '.', mode])
        print('Writing {outputmode} file: {outfile}'.format(outputmode=mode, outfile=outfile))
        with open(os.path.abspath(outfile), 'wb') as file:
            file.write(search_results)

    # Step 5
    mySearch.showSelf()

if __name__ == '__main__':
    main(sys.argv[1:])


