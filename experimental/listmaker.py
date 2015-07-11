from google.appengine.api import users
from google.appengine.ext import ndb
import webapp2
import cgi
import urllib
import os
import jinja2
from urlparse import urlparse

JINJA_ENVIRONMENT = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
                                       extensions=['jinja2.ext.autoescape'],
                                       autoescape=True)

DEFAULT_LIST_NAME = 'Reasons Why You Should Use ListMaker'
DEFAULT_LIST_NAME_ESCAPED = urllib.quote_plus(DEFAULT_LIST_NAME)
MAX_CONTENT_TEXT_LENGTH = 500

# We set a parent key on the 'Greetings' to ensure that they are all
# in the same entity group. Queries across the single entity group
# will be consistent.  However, the write rate should be limited to
# ~1/second.

def guestbook_key(guestbook_name=DEFAULT_LIST_NAME):
    """Constructs a Datastore key for a Guestbook entity.
        
        We use guestbook_name as the key.
        """
    return ndb.Key('Guestbook', guestbook_name)

class ListMakerUser(ndb.Model): #todo aliases, different login mechanisms
    identity = ndb.UserProperty(indexed=True)

# shared data layout for a list, and list items
class ListMakerContent(ndb.Model):
    content = ndb.StringProperty(indexed=False);
    author  = ndb.UserProperty(indexed=True);
    upvotes = ndb.IntegerProperty(indexed=False, default=1);
    downvotes = ndb.IntegerProperty(indexed=False, default=0);
    date = ndb.DateTimeProperty(auto_now_add=True)

class MainPage(webapp2.RequestHandler): #separate main page from list page and user page
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'

        self.response.write("Main Page")


class UserPage(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        self.response.write("Temp page, for user information, showing postings")


class ListPage(webapp2.RequestHandler): #separate main page from list page and user page
    
    def post(self):
        list_name = self.request.get('write_list', DEFAULT_LIST_NAME_ESCAPED)

        content = self.request.get('content')

        if(len(content) > MAX_CONTENT_TEXT_LENGTH):
            content = content[0:MAX_CONTENT_TEXT_LENGTH];

        if len(content):
            listItem = ListMakerContent(parent=guestbook_key(list_name))
        
            if users.get_current_user():
                listItem.author = users.get_current_user()
        
            listItem.content = content
            listItem.put()
        
        query_params = {'list_name': list_name}
        self.redirect('/list/'+list_name)


    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        
        list_name = urlparse(self.request.uri)[2]

        if list_name.startswith("/list/"):
            list_name = list_name[6:]
    
        list_query = ListMakerContent.query(ancestor=guestbook_key(list_name)).order(-ListMakerContent.date)
        
        list_items = list_query.fetch(10)
        
        user = users.get_current_user()
        
        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'
        
        template_values = {
            'user' : user,
            'greetings' : list_items,
            'guestbook_unquoted' : list_name,
            'guestbook_name' : urllib.quote_plus(list_name),
            'url' : url,
            'url_linktext' : url_linktext,
        }
        
        template = JINJA_ENVIRONMENT.get_template('list_page.html')
        self.response.write(template.render(template_values))

app = webapp2.WSGIApplication([
                               ('/', MainPage),
                               (r'/list/.+',ListPage),
                               (r'/user/.+',UserPage)
                               ], debug=True)

