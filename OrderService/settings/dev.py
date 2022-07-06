from .common import *

DEBUG = True

SECRET_KEY = 'c_-0n*cl_fk066!yj#mmph68fc4il%p!=c58qp6j()u870$a=1'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'OrderService',
        'USER': 'Test',
        'PASSWORD': 'test',
        'HOST': 'localhost',
    }
}