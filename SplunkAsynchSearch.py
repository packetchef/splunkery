#!/usr/bin/env python

import sys
import os
import time
import urllib
import urllib2
import httplib2
from xml.dom import minidom
import re

# External dependencies: httplib2
'''
To do:
- class documentation
- input validation for all the things, including server and query format
- better handling of invalid function calls
- is there a better way of checking job status besides regex?
'''

class SplunkAsynchSearch(object):
    '''
    Required parameters: server URL, username, password
    Optional parameters: query, search jobs URI, login URI
    Query will be required later when submitting a search job
    Server should be checked to make sure we have protocol and port
    '''
    def __init__(self, server, username, password, search_jobs_uri='', login_uri='', query=''):
        self.server = server
        self.sUser = username
        self.sPass = password

        if query:
            self.searchQuery = self.checkSearchQuery(query)

        # Some sensible defaults
        self.sessionkey = ''
        self.jobsid = ''
        self.jobstatus = None

        if not search_jobs_uri:
            self.search_jobs_uri = 'services/search/jobs'
        if not login_uri:
            self.login_uri =  'services/auth/login'


    def __setattr__(self, k, v):
        # Override setattr to make sure we validate the query is valid
        # anytime its value changes. Maybe it is better to do this at the
        # actual job submit time instead of overriding...
        if k in [ 'searchQuery' ]:
            checkQueryTerm = self.checkSearchQuery(v)
            super(SplunkAsynchSearch, self).__setattr__(k, checkQueryTerm)
        else:
            super(SplunkAsynchSearch, self).__setattr__(k, v)


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


    def submit_asynch_search(self):
        # To do: we check that we have a token, need to also check it is valid
        # We are submitting a new search, so assume we don't have a job yet

        # A query is not required at initialization time, but if it is defined
        # at initialization, it gets run through a simple validator.  You can
        # define a query later, and this function will do a quick (basic)
        # check before trying to run the search.
        if not self.searchQuery:
            raise ValueException('Search object has no query')

        if not self.sessionkey:
            raise ValueException('Search object has no session token')

        self.jobstatus = None
        self.jobsid = None
        myhttp = httplib2.Http(disable_ssl_certificate_validation=True)
        url = ''.join([self.server, '/', self.search_jobs_uri])
        headers = {'Authorization': ''.join(['Splunk ', self.sessionkey])}
        body = urllib.urlencode({'search': self.searchQuery})
        response = myhttp.request(url, 'POST', headers=headers, body=body)[1]
        sid = minidom.parseString(response).getElementsByTagName('sid')[0].childNodes[0].nodeValue
        self.jobsid = sid
        return sid


    def get_job_status(self):
        # To do: make sure we have a token and sid, and they are valid
        # XML object will include an isDone key, with 1=done:
        # $ grep isDone stats.txt
        #  <s:key name="isDone">1</s:key>
        # The sample code pulls isDone and writes it as a string
        # So '0' for not done, '1' for done
        # Keep that in mind for any evaluations - use strings not ints!

        if not self.sessionkey:
            raise ValueException('Search object has no session token')

        if not self.jobstatus or self.jobstatus=='0':
            myhttp = httplib2.Http(disable_ssl_certificate_validation=True)
            url = ''.join([self.server, '/', self.search_jobs_uri, '/', self.jobsid])
            headers = {'Authorization': ''.join(['Splunk ', self.sessionkey])}
            statusXML = myhttp.request(url, 'GET', headers=headers)[1]
            status = re.compile('isDone">(0|1)')
            status = status.search(statusXML).groups()[0]
            self.jobstatus = status
        else:
            status = self.jobstatus
        return status


    def get_job_results(self, outputMode):
        # To do: make sure we have a token and sid, and they are valid
        # Also check the number of results, and maybe return an exception
        # or None if there are no results

        if not self.sessionkey:
            raise ValueException('Search object has no session token')

        if not self.jobsid:
            raise ValueException('Search object has no job SID')

        if self.jobstatus:
            myhttp = httplib2.Http(disable_ssl_certificate_validation=True)
            url = ''.join([self.server, '/', self.search_jobs_uri, '/', self.jobsid])
            headers = {'Authorization': ''.join(['Splunk ', self.sessionkey])}

            if outputMode == 'json':
                url = ''.join([url, '/results?output_mode=json&count=0'])
            elif outputMode == 'csv':
                url = ''.join([url, '/results?output_mode=csv&count=0'])
            else:
                url = ''.join([url, '/results?output_mode=xml&count=0'])

            results = myhttp.request(url, 'GET', headers=headers)[1]
        else:
            results = None
        
        return results
        

def main(argv):
    preamble = '''
    Thank you for choosing to run SplunkAsynchSearch!  This is my
    implementation of the sample API code from Splunk, available at
    http://blogs.splunk.com/2011/08/02/splunk-rest-api-is-easy-to-use/

    When you are ready, just import SplunkAsynchSearch.  You'll need to
    know your Splunk server, credentials, and search query.  If you are using
    the free version of Splunk, chances are your username is "admin" and your
    password is "changeme".  In the meantime, running this directly instead of
    importing will show you an example of how to instantiate a new search
    object and work with its methods.  The example will do a few things:

    (1) Create a new object
    (2) Generate a token
    (3) Submit the search
    (4) Call the showSelf method to print the object's attributes
    (5) Loop through a check of the job status until the job is done
    (6) When the job is done, write the search results to CSV and JSON files
    '''

    print(preamble)

    # Step one
    server = raw_input('Server name (eg. https://splunkserver:8089): ')
    searchQuery = '* earliest=-24h | stats count by sourcetype'
    print('We will use this search query: {query}'.format(query=searchQuery))
    sUser = raw_input('User name (eg. admin): ')
    sPass = raw_input('Password (eg. changeme): ')
    mySearch = SplunkAsynchSearch(server=server, query=searchQuery, username=sUser, password=sPass)

    # Step two
    sessionToken = mySearch.get_session_token()
    print('Session token: {sessionToken}'.format(sessionToken = sessionToken))

    # Step 3
    job_sid = mySearch.submit_asynch_search()
    print('Job sid: {job_sid}'.format(job_sid=job_sid))

    # Step 4
    mySearch.showSelf()

    # Step 5
    # Add a counter to the status check to prevent infinite searching
    # Also, what happens if we pass a bad sid?
    job_status = '0'
    while not job_status == '1':
        print('Checking status..')
        job_status = mySearch.get_job_status()
        time.sleep(0.5)
        # print('Job status: {job_status}'.format(job_status=job_status))
    print('Job {sid} is done'.format(sid=job_sid))

    # Step 6
    jsonResults = mySearch.get_job_results('json')
    csvResults = mySearch.get_job_results('csv')

    jsonFile = ''.join([job_sid, '.json'])
    csvFile = ''.join([job_sid, '.csv'])
    print('Writing JSON file: {json}'.format(json=jsonFile))
    with open(os.path.abspath(jsonFile), 'wb') as file:
        file.write(jsonResults)
    print('Writing CSV file: {csv}'.format(csv=csvFile))
    with open(os.path.abspath(csvFile), 'wb') as file:
        file.write(csvResults)

if __name__ == '__main__':
    main(sys.argv[1:])


