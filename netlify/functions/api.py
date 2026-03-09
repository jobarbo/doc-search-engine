from serverless_wsgi import handle_request
import sys
import os

# Add the project root to the Python path so it can import the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import app

def handler(event, context):
    """
    AWS Lambda handler for Netlify Functions using serverless-wsgi.
    """
    return handle_request(app, event, context)
