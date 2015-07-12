#todo list
#prevent spam
#prevent duplicate submissions
#nonexistent lists, create list page
#karma buttons
#complete homepage
#complete user pages

#parent list item to "lists"
#parent content to particular list

import webapp2
import cgi
import urllib
import os
import jinja2
from urlparse import urlparse

from google.appengine.api import users
from google.appengine.ext import ndb


JINJA_ENVIRONMENT = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
                                       extensions=['jinja2.ext.autoescape'],
                                       autoescape=True)

DEFAULT_LIST_NAME = 'Reasons Why You Should Use ListMaker'
DEFAULT_LIST_NAME_ESCAPED = urllib.quote_plus(DEFAULT_LIST_NAME)
MAX_CONTENT_TEXT_LENGTH = 500
MAX_LIST_NAME_LENGTH = 140

# We set a parent key on the 'Greetings' to ensure that they are all
# in the same entity group. Queries across the single entity group
# will be consistent.  However, the write rate should be limited to
# ~1/second.

def list_key(list_name=DEFAULT_LIST_NAME):
    return ndb.Key('ListMakerList', list_name)

#def karma_delta(karma_delta, ndb_key):
#url_string = sandy_key.urlsafe()
#sandy_key.kind() == 'Account'

class ListMakerUser(ndb.Model): #todo aliases, different login mechanisms
    identity = ndb.UserProperty(indexed=True)

# shared data layout for a list, and list items
class ListMakerContent(ndb.Model):
    content = ndb.StringProperty(indexed=False);
    author  = ndb.UserProperty(indexed=True);
    upvotes = ndb.IntegerProperty(indexed=False, default=1);
    downvotes = ndb.IntegerProperty(indexed=False, default=0);
    date = ndb.DateTimeProperty(auto_now_add=True)

class ListMakerList(ListMakerContent):
    pass

class ListMakerListItem(ListMakerContent):
    pass

class MainPage(webapp2.RequestHandler): #separate main page from list page and user page
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'

        self.response.write("Main Page")


class UserPage(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        self.response.write("Temp page, for user information, showing postings")


class CreateList(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        template = JINJA_ENVIRONMENT.get_template('create_list_page.html')
        self.response.write(template.render())
    
    def post(self):
        self.response.headers['Content-Type'] = 'text/html'

        list_name = urllib.quote_plus(self.request.get('list_name'))
        
        if len(list_name) > MAX_LIST_NAME_LENGTH:
            list_name = list_name[0:MAX_LIST_NAME_LENGTH]
        
        listKey = list_key(list_name)
    
        if listKey.get():
            self.response.write("ERROR : LIST ALREADY EXISTS")
            #self.redirect('/list/' + list_name) ###
        else:
            list = ListMakerList()
            list.key = listKey
            list.content = list_name
        
            if users.get_current_user():
                list.author = users.get_current_user()
            
            list.put()
            
            self.redirect('/list/' + urllib.quote_plus(list_name))


class ListPage(webapp2.RequestHandler):
    def post(self):
        list_name = self.request.get('write_list', DEFAULT_LIST_NAME_ESCAPED)
        list_name = urllib.quote_plus(list_name)

        content = self.request.get('content')

        if(len(content) > MAX_CONTENT_TEXT_LENGTH):
            content = content[0:MAX_CONTENT_TEXT_LENGTH];

        if len(content):
            listItem = ListMakerContent(parent=list_key(list_name))
        
            if users.get_current_user():
                listItem.author = users.get_current_user()
        
            listItem.content = content
            listItem.put()
        
        #self.response.write(urllib.quote_plus(list_name))
        self.redirect('/list/'+list_name)


    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        
        list_name = urlparse(self.request.uri)[2]

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
                'list_unquoted' : urllib.unquote_plus(list_name),
                'list_name' : list_name,
                'url' : url,
                'url_linktext' : url_linktext,
            }
        
            template = JINJA_ENVIRONMENT.get_template('list_page.html')
            self.response.write(template.render(template_values))

        else:
            self.response.write("List not found!")


app = webapp2.WSGIApplication([
                               ('/', MainPage),
                               ('/newlist', CreateList),
                               (r'/list/.+',ListPage),
                               (r'/user/.+',UserPage)
                               ], debug=True)

