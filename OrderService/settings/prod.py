from .common import *
import os

DEBUG = False

SECRET_KEY = os.environ['SECRET_KEY']

ALLOWED_HOSTS = [os.environ['ALLOWED_HOST1'], os.environ['ALLOWED_HOST2']]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ['DATABASE_NAME'],
        'USER': os.environ['DATABASE_LOGIN'],
        'PASSWORD': os.environ['DATABASE_PASSWORD'],
        'HOST': 'localhost',
    }
}

DEFAULT_FILE_STORAGE = 'storages.backends.ftp.FTPStorage'
FTP_STORAGE_LOCATION = os.environ['FTP_STORAGE_LOCATION']

SMSAERO_LOGIN = os.environ['SMSAERO_LOGIN']
SMSAERO_API_KEY = os.environ['SMSAERO_API_KEY']

