# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Rule.normalized'
        db.add_column('eventtools_rule', 'normalized',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Rule.normalized'
        db.delete_column('eventtools_rule', 'normalized')

    models = {
        'eventtools.rule': {
            'Meta': {'ordering': "('-common', 'name')", 'object_name': 'Rule'},
            'common': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'complex_rule': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'frequency': ('django.db.models.fields.CharField', [], {'max_length': '10', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'normalized': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'params': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        }
    }

    complete_apps = ['eventtools']