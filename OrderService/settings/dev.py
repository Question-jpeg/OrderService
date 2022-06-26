from .common import *

DEBUG = True

SECRET_KEY = 'c_-0n*cl_fk066!yj#mmph68fc4il%p!=c58qp6j()u870$a=1'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}