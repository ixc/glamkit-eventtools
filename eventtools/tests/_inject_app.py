import shlex
import subprocess
from random import randint

from django.db.models.loading import load_app
from django.conf import settings
from django.core.management import call_command
from django.template.loaders import app_directories
from django.template import loader
from django.test import TestCase

from _fixture import fixture

APP_NAME = 'eventtools.tests.eventtools_testapp'

class TestCaseWithApp(TestCase):

    """Make sure to call super(..).setUp and tearDown on subclasses"""
    
    def setUp(self):
        self.__class__.__module__ = self.__class__.__name__

        self.old_INSTALLED_APPS = settings.INSTALLED_APPS
        if isinstance(settings.INSTALLED_APPS, tuple):
            settings.INSTALLED_APPS += (APP_NAME,)
        else:
            settings.INSTALLED_APPS += [APP_NAME]
        self._old_root_urlconf = settings.ROOT_URLCONF
        settings.ROOT_URLCONF = '%s.urls' % APP_NAME
        load_app(APP_NAME)
        call_command('flush', verbosity=0, interactive=False)
        call_command('syncdb', verbosity=0, interactive=False)
        self.ae = self.assertEqual
        self._old_template_loaders = settings.TEMPLATE_LOADERS
        loaders = list(settings.TEMPLATE_LOADERS)
        try:
            loaders.remove('django.template.loaders.filesystem.Loader')
            settings.TEMPLATE_LOADERS = loaders
            self._refresh_cache()
        except ValueError:
                pass
        fixture(self)
        
    def tearDown(self):
        settings.INSTALLED_APPS = self.old_INSTALLED_APPS
        settings.ROOT_URLCONF = self._old_root_urlconf
        settings.TEMPLATE_LOADERS = self._old_template_loaders
        self._refresh_cache()
    
    def _refresh_cache(self):
        reload(app_directories)
        loader.template_source_loaders = None

    def open_string_in_browser(self, s):
        filename = "/tmp/%s.html" % randint(1, 100)
        f = open(filename, "w")
        f.write(s)
        f.close()
        subprocess.call(shlex.split("google-chrome %s" % filename))