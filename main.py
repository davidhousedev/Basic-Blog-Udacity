import os

import jinja2
import webapp2

from google.appengine.ext import db

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
JINJA_ENV = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_DIR),
                               autoescape=False)

class Handler(webapp2.RequestHandler):
    """ Renders html templates with Jinja2 variables """
    def write(self, *a, **kw):
        """ Writes HTML """
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        """ Finds specified template in '/template' of current dir """
        template = JINJA_ENV.get_template(template)
        return template.render(params)

    def render(self, template, **kw):
        """ Render a specific template (param0)
        with any number of vars (params1+) """
        self.write(self.render_str(template, **kw))

class Post(db.Model):
    """ Database entry for a blog post """
    subject = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)


class Blog(Handler):
    """ Default HTTP Request Handler """

    def display_posts(self):
        """ Display 10 most recent blog posts """
        posts = db.GqlQuery("SELECT * FROM Post "
                            "ORDER BY created DESC")
        self.render("blog.html", posts=posts)

    def get(self):
        """ Handle GET requests """
        self.display_posts()

class NewPost(Handler):
    """ Handler for creating a new blog post """
    def blog_creation(self, subject="", title="" error=""):
        """ Renders blog post creation screen, preserving user input """
        # subject = self.request.get("subject")
        # content = self.request.get("content")

        self.render("newpost.html", subject=subject,
                    content=content, error=error)


    def get(self):
        self.blog_creation()

app = webapp2.WSGIApplication([('/', Blog),
                               ('/newpost', NewPost)
                              ],
                              debug=True
                              )