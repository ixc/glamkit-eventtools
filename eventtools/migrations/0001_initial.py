# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Rule'
        db.create_table('eventtools_rule', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('common', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('frequency', self.gf('django.db.models.fields.CharField')(max_length=10, blank=True)),
            ('params', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('complex_rule', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('eventtools', ['Rule'])

    def backwards(self, orm):
        # Deleting model 'Rule'
        db.delete_table('eventtools_rule')

    models = {
        'eventtools.rule': {
            'Meta': {'ordering': "('-common', 'name')", 'object_name': 'Rule'},
            'common': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'complex_rule': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'frequency': ('django.db.models.fields.CharField', [], {'max_length': '10', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'params': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        }
    }

    complete_apps = ['eventtools']