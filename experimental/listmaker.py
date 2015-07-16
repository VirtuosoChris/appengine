#todo list
#prevent spam
#prevent duplicate submissions
#nonexistent lists, create list page
#karma buttons
#complete user pages
#user comments, suggestions on posts?
#search
#admin tools

#parent list item to "lists"
#parent content to particular list

#newlines in content

import webapp2
import cgi
import urllib
import os
import jinja2
import random
import shardcounter

from urlparse import urlparse
from markupsafe import Markup

from google.appengine.api import users
from google.appengine.ext import ndb




JINJA_ENVIRONMENT = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
                                       extensions=['jinja2.ext.autoescape'],
                                       autoescape=True)

DEFAULT_LIST_NAME = 'Reasons Why You Should Use ListMaker'
MAX_CONTENT_TEXT_LENGTH = 500
MAX_LIST_NAME_LENGTH = 140

def list_key(list_name=DEFAULT_LIST_NAME):
    return ndb.Key('ListMakerList', list_name)

def encode_list_name(sv):
    return urllib.quote(sv)

def decode_list_name(sv):
    return urllib.unquote(sv)

DEFAULT_LIST_NAME_ESCAPED = encode_list_name(DEFAULT_LIST_NAME)

def urlencode_filter(s):
    s = s.encode('utf8')
    s = encode_list_name(s)
    return Markup(s)

def list_upvote_counter_key(s):
    s = s.encode('utf8')
    s = ListMakerList.counter_key_prefix + "upvotes::" + encode_list_name(s)
    return Markup(s)

JINJA_ENVIRONMENT.filters['urlencode'] = urlencode_filter
JINJA_ENVIRONMENT.filters['upvote_key'] = list_upvote_counter_key

#def karma_delta(karma_delta, ndb_key):
#url_string = sandy_key.urlsafe()
#sandy_key.kind() == 'Account'

class ListMakerUser(ndb.Model): #todo aliases, different login mechanisms
    identity = ndb.UserProperty(indexed=True)

# shared data layout for a list, and list items
class ListMakerContent(ndb.Model):
    content = ndb.StringProperty(indexed=False);
    author  = ndb.UserProperty(indexed=True);
    date = ndb.DateTimeProperty(auto_now_add=True)

    def increment_upvote_counter():
        counter_name = counter_key_prefix + "upvotes::" + encode_list_name(content)
        shardcounter.increment_counter(counter_name)

    def increment_downvote_counter():
        counter_name = counter_key_prefix + "downvotes::" + encode_list_name(content)
        shardcounter.increment_counter(counter_name)

    def get_upvotes():
        counter_name = counter_key_prefix + "upvotes::" + encode_list_name(content)
        shardcounter.get_count(counter_name)

    def get_downvotes():
        counter_name = counter_key_prefix + "downvotes::" + encode_list_name(content)
        shardcounter.get_count(counter_name)

#todo tags, permissions
class ListMakerList(ListMakerContent):
    counter_key_prefix = "listcounter::"

class ListMakerListItem(ListMakerContent):
    counter_key_prefix = "listitemcounter::"

class MainPage(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'

        recent_lists = ListMakerList.query().order(-ListMakerList.date).fetch(limit=25)

        user = users.get_current_user()

        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        template_values = {
            'recent_lists' : recent_lists,
            'url' : url,
            'url_linktext' : url_linktext,
        }

        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))

class UserPage(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        self.response.write("Temp page, for user information, showing postings")


class CreateList(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        template = JINJA_ENVIRONMENT.get_template('create_list_page.html')

        user = users.get_current_user()

        user = users.get_current_user()

        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        template_values = {
            'url' : url,
            'url_linktext' : url_linktext,
        }

        self.response.write(template.render(template_values))

    def post(self):
        self.response.headers['Content-Type'] = 'text/html'

        list_name_unquoted = self.request.get('list_name')
        list_name = encode_list_name(list_name_unquoted)

        if len(list_name) > MAX_LIST_NAME_LENGTH:
            list_name = list_name[0:MAX_LIST_NAME_LENGTH]

        listKey = list_key(list_name)

        if listKey.get():
            self.response.write("ERROR : LIST ALREADY EXISTS")
            #self.redirect('/list/' + list_name) ###
        else:
            list = ListMakerList()
            list.key = listKey
            list.content = list_name_unquoted

            if users.get_current_user():
                list.author = users.get_current_user()

            list.put()

            self.redirect('/list/' + list_name)

class ListPage(webapp2.RequestHandler):
    def post(self):
        list_name = self.request.get('write_list', DEFAULT_LIST_NAME_ESCAPED)

        list_name = encode_list_name(list_name)

        content = self.request.get('content')

        if(len(content) > MAX_CONTENT_TEXT_LENGTH):
            content = content[0:MAX_CONTENT_TEXT_LENGTH];

        if len(content):
            listItem = ListMakerContent(parent=list_key(list_name))

            if users.get_current_user():
                listItem.author = users.get_current_user()

            listItem.content = content
            listItem.put()

        self.redirect('/list/'+ list_name)


    def get(self):
        self.response.headers['Content-Type'] = 'text/html'

        #some escape characters get expanded in self.request.url
        #Examples pluses are getting expanded to pluses instead of staying as %2B
        #Others don't, like spaces.
        #this is an ugly hack but i don't know why this isn't working
        list_name = decode_list_name(urlparse(self.request.uri)[2])
        list_name = encode_list_name(list_name)

        if list_name.startswith("/list/"):
            list_name = list_name[6:]

        listKey = list_key(list_name)

        if listKey.get():

            list_query = ListMakerContent.query(ancestor=listKey).order(-ListMakerContent.date)

            list_items = list_query.fetch(limit=None)

            user = users.get_current_user()

            if user:
                url = users.create_logout_url(self.request.uri)
                url_linktext = 'Logout'
            else:
                url = users.create_login_url(self.request.uri)
                url_linktext = 'Login'

            template_values = {
                'user' : user,
                'list' : list_items,
                'list_unquoted' : decode_list_name(list_name),
                'list_name' : list_name,
                'url' : url,
                'url_linktext' : url_linktext,
            }

            template = JINJA_ENVIRONMENT.get_template('list_page.html')
            self.response.write(template.render(template_values))

        else:
            self.response.write("List not found!")


class Karma(webapp2.RequestHandler):

    def post(self):
        self.response.headers['Content-Type'] = 'text/html'
        arg = self.request.get('arg', 'ERR')
        if(arg == 'ERR'):
            self.response.write('ERR')
        count = shardcounter.increment(arg)
        self.response.write(count)

    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        arg = self.request.get('arg', 'ERR')
        if(arg == 'ERR'):
            self.response.write('ERR')
        count = shardcounter.get_count(arg)
        self.response.write(count)

app = webapp2.WSGIApplication([
                               ('/', MainPage),
                               ('/newlist', CreateList),
                               (r'/list/.+',ListPage),
                               (r'/user/.+',UserPage),
                               ('/karma', Karma)
                               ], debug=True)
