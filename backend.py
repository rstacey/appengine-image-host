"""
Provides a protected administrative area for uploading and deleteing images
"""

import os
import datetime
import json

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import images
from google.appengine.ext.webapp import template
from google.appengine.api import users

from models import Image

def handle_response(self, success, id):
    if self.request.get("output") == "json":
        self.response.headers['Content-Type'] = "application/json"
        obj = {
            'success': success, 
            'id': id,
          } 
        self.response.out.write(json.dumps(obj))
    else:
        self.redirect('/')

class Index(webapp.RequestHandler):
    """
    Main view for the application.
    Protected to logged in users only.
    """
    def get(self):
        "Responds to GET requets with the admin interface"
        # query the datastore for images.
        images = Image.all()
        images.order("-date")

        # we need the logout url for the frontend
        logout = users.create_logout_url("/")

        # prepare the context for the template
        context = {
            "images": images,
            "logout": logout,
        }
        # calculate the template path
        path = os.path.join(os.path.dirname(__file__), 'templates',
            'index.html')
        # render the template with the provided context
        self.response.out.write(template.render(path, context))

class List(webapp.RequestHandler):
    "Returns a list of images"
    def get(self):
        # query the datastore for images.
        images_query = Image.all().order("-date")
        offset = self.request.get("start")
        if offset:
            offset = int(offset)
        else:
	        offset = 0

        # prepare the context for the template
        results = []
        for image in images_query.run(offset=offset, limit=10):
            image_json = {
               'id': str(image.key())
            }
            results.append(image_json)

        # render the template with the provided context
        self.response.headers['Content-Type'] = "application/json"
        self.response.out.write(json.dumps(results))

class Deleter(webapp.RequestHandler):
    "Deals with deleting images"
    def post(self):
        "Delete a given image"
        # we get the user as you can only delete your own images
        user = users.get_current_user()
        key = self.request.get("key")
        success = False
        if key:
            image = db.get(key)
            # check that we own this image
            image.delete()
            success = True
        handle_response(self, success, key)
       
class Uploader(webapp.RequestHandler):
    "Deals with uploading new images to the datastore"
    def post(self):
        "Upload via a multitype POST message"
        
        img = self.request.get("img")

        # if we don't have image data we'll quit now
        if not img:
            handle_response(self, False, "")
            return 
            
        # we have image data
        try:
            # check we have numerical width and height values
            width = int(self.request.get("width"))
            height = int(self.request.get("height"))
        except ValueError:
            # if we don't have valid width and height values
            # then just use the original image
            image_content = img
        else:
            # if we have valid width and height values
            # then resize according to those values
            image_content = images.resize(img, width, height)
        
        # get the image data from the form
        original_content = img
        # always generate a thumbnail for use on the admin page
        thumb_content = images.resize(img, 100, 100)
        
        # create the image object
        image = Image()
        # and set the properties to the relevant values
        image.image = db.Blob(image_content)
        # we always store the original here in case of errors
        # although it's currently not exposed via the frontend
        image.original = db.Blob(original_content)
        image.thumb = db.Blob(thumb_content)
        image.user = users.get_current_user()
                
        # store the image in the datasore
        image.put()

        handle_response(self, True, str(image.key()))
                
# wire up the views
application = webapp.WSGIApplication([
    ('/', Index),
    ('/list', List),
    ('/upload', Uploader),
    ('/delete', Deleter)
], debug=True)

def main():
    "Run the application"
    run_wsgi_app(application)

if __name__ == '__main__':
    main()