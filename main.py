import os
import re

import jinja2
import webapp2
import hmac
import hashlib
import random
import string

from google.appengine.ext import db

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
JINJA_ENV = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_DIR),
                               autoescape=False)

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
PASS_RE = re.compile(r"^.{3,20}$")
EMAIL_RE = re.compile(r"^[\S]+@[\S]+.[\S]+$")

# User signup validation
def valid_username(username):
    return USER_RE.match(username)
def valid_password(password):
    return PASS_RE.match(password)
def valid_email(email):
    return EMAIL_RE.match(email)

SECRET = "turtles"

# Hash signin cookie
def hash_str(s):
    """ Returns HMAC hashed string with SECRET of param
            Returns str"""
    return hmac.new(SECRET, s).hexdigest()
def make_secure_val(s):
    """ Hashes param value and returns string containing cookie val and hashed val
            Returns 'val|hashed_val'"""
    return str("%s|%s" % (s, hash_str(s)))
def check_secure_val(h):
    """ Verifies that param cookie has been hashed with SECRET
            Returns value of cookie or None """
    val = h.split('|')[0]
    if h == make_secure_val(val):
        return val

# Password hashing
def make_salt():
    return ''.join(random.choice(string.letters) for x in xrange(5))

def make_pw_hash(name, pw, salt=""):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s,%s' % (h, salt)

def valid_pw(name, pw, h):
    db_salt = h.split(',')[1]

    if h == make_pw_hash(name, pw, db_salt):
        return True



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

class User(db.Model):
    """ Database entry for a user """
    username = db.StringProperty(required=True)
    password = db.StringProperty(required=True)
    email = db.StringProperty()
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

            #check if user already exists
            users = db.GqlQuery("SELECT * FROM User WHERE username='%s'" % form_data['user_username'])
            for user in users:
                if user.username == form_data['user_username']:
                    form_data['username_error'] = "User already exists"
                    form_data['user_username'] = ""
                    error_flag = True

            if error_flag is False:
                hash_pass = make_pw_hash(form_data['user_username'],
                                         form_data['user_password'])

                user = User(username=form_data['user_username'],
                            password=hash_pass,
                            email=form_data['user_email'])
                user.put()
                user_db_id = str(user.key().id())
                print "put user, id=%s" % user.key().id()
                self.response.headers.add_header('Set-Cookie',
                                                 'user_id=%s' % make_secure_val(user_db_id))
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
        usr_cookie = self.request.cookies.get('user_id')
        if usr_cookie:
            if check_secure_val(usr_cookie):
                key = db.Key.from_path('User', int(usr_cookie.split('|')[0]))
                user = db.get(key)
                print "user username is: %s" % user.username

                if not user:
                    self.error(404)
                    return

                message = "Welcome, %s" % str(user.username)
                self.render('welcome.html', message=message)

                return


        self.redirect('/signup')




app = webapp2.WSGIApplication([('/', Blog),
                               ('/newpost', NewPost),
                               (r'/post/(\d+)', BlogPost),
                               ('/signup', UserSignUp),
                               ('/welcome', Welcome)
                              ],
                              debug=True
                             )
