import os
import re

import jinja2
import webapp2

from google.appengine.ext import db

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
JINJA_ENV = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_DIR),
                               autoescape=False)

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
PASS_RE = re.compile(r"^.{3,20}$")
EMAIL_RE = re.compile(r"^[\S]+@[\S]+.[\S]+$")

def valid_username(username):
    return USER_RE.match(username)
def valid_password(password):
    return PASS_RE.match(password)
def valid_email(email):
    return EMAIL_RE.match(email)

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
    def blog_creation(self, subject="", content="", error=""):
        """ Renders blog post creation screen, preserving user input """


        self.render("newpost.html", subject=subject,
                    content=content, error=error)

    def post(self):
        """ Gathers blog post data and, if valid, writes to database """
        subject = self.request.get("subject")
        content = self.request.get("content")

        if subject and content:
            new_post = Post(subject=subject, content=content)
            new_post.put()

            self.redirect("/post/%s" % new_post.key().id())
        else:
            error = "Error: Subject and content are both required"
            self.blog_creation(subject, content, error)

    def get(self):
        self.blog_creation()

class BlogPost(Handler):
    """ Displays a single blog post at a permenant URL """

    def get(self, post_id):
        """ Queries database for post id and renders it """
        post_id = int(post_id)
        post = Post.get_by_id(post_id)

        self.render("post.html", post=post)

class UserSignUp(Handler):
    def write_form(self, form_data = ""):
        self.render('signup.html', form_data = form_data)

    def get(self):
        self.write_form()

    def post(self):
        form_data = {}

        form_data['user_username'] = self.request.get('username')
        form_data['user_password'] = self.request.get('password')
        form_data['user_verify'] = self.request.get('verify')
        form_data['user_email'] = self.request.get('email')

        username = valid_username(form_data['user_username'])
        password = valid_password(form_data['user_password'])
        verify = valid_password(form_data['user_verify'])
        email = valid_email(form_data['user_email'])

        if username and password and verify:
            error_flag = False
            #check email, if provided
            if form_data['user_email'] != "" and not email:
                form_data['email_error'] = "Trouble with your email"
                error_flag = True
            #check password, if provided
            if form_data['user_password'] != form_data['user_verify']:
                form_data['verify_error'] = "No matchy matchy"
                error_flag = True

            if error_flag is False:
                self.response.headers.add_header('Set-Cookie',
                                                 'username=%s' % str(form_data['user_username']))
                self.redirect('/welcome')
        else:
            if not username:
                form_data['username_error'] = "Bad username, bud"
            if not password or not verify:
                form_data['password_error'] = "Follow the password rules plz"
            if form_data['user_email'] != "" and not email:
                form_data['email_error'] = "Trouble with your email"

        self.write_form(form_data)

class Welcome(Handler):
    """Renders welcome screen after successful signup or login"""
    def get(self):
        message = ""
        usr_cookie = self.request.cookies.get('username')
        if usr_cookie:
            message = "Welcome, %s" % usr_cookie
        else:
            message = "Not logged in"

        self.render('welcome.html', message=message)




app = webapp2.WSGIApplication([('/', Blog),
                               ('/newpost', NewPost),
                               ('/post/(\d+)', BlogPost),
                               ('/signup', UserSignUp),
                               ('/welcome', Welcome)
                              ],
                              debug=True
                              )
