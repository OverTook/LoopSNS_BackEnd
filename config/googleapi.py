from config import *
import os

# Firebase Configurations
CREDENTIAL_PATH = os.getenv('CREDENTIAL_PATH', '/default/path')
GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '/default/path')
STORAGE_BUCKET = os.getenv('STORAGE_BUCKET', "default.bucket.com")
PROJECT_ID = os.getenv('PROJECT_ID', 'default-project-id')

# Googlemaps 
GOOGLEMAPS_KEY = os.getenv('GOOGLEMAPS_KEY', 'default-key')
