from .common import *
import os
import dj_database_url

DEBUG = False

SECRET_KEY = os.environ['SECRET_KEY']

ALLOWED_HOSTS = ['krezer-orderservice.herokuapp.com']

DATABASES = {
    'default': dj_database_url.config() #reads the DATABASE_URL environment variable, parses the connection and returns dictionary
}

DEFAULT_FILE_STORAGE = 'api.storages.CustomS3Boto3Storage'

AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
AWS_STORAGE_BUCKET_NAME = os.environ['AWS_BUCKET_NAME']
AWS_DEFAULT_ACL = 'public-read'
AWS_QUERYSTRING_AUTH = True # Changed from "False"

SMSAERO_LOGIN = os.environ['SMSAERO_LOGIN']
SMSAERO_API_KEY = os.environ['SMSAERO_API_KEY']