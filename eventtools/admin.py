import datetime

import django
from django import forms
from django.conf.urls.defaults import patterns, url
from django.contrib import admin, messages
from django.core import validators
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import models
from django.http import QueryDict
from django.shortcuts import get_object_or_404, redirect
from mptt.forms import TreeNodeChoiceField
from mptt.admin import MPTTModelAdmin

from .diff import generate_diff
from .forms import ExceptionsWidget


def create_children(modeladmin, request, queryset):
    for event in queryset:
        e = type(event)._event_manager.create(parent=event)
create_children.short_description = "Create children of selected events"

def EventForm(EventModel):
    class _EventForm(forms.ModelForm):
        parent = TreeNodeChoiceField(queryset=EventModel._event_manager.all(), level_indicator=u"-", required=False)

        class Meta:
            model = EventModel

    return _EventForm

def EventAdmin(EventModel, SuperModel=MPTTModelAdmin): #pass in the name of your EventModel subclass to use this admin.
    class _EventAdmin(SuperModel):
        form = EventForm(EventModel)
        list_display = ('__unicode__', 'occurrence_link')
        change_form_template = 'admin/eventtools/event.html'
        save_on_top = True

        class Media:
            js = ('eventtools/js/ExceptionsWidget.js',)

        def __init__(self, *args, **kwargs):
            super(_EventAdmin, self).__init__(*args, **kwargs)
            self.occurrence_model = self.model.occurrences.related.model
        
        def occurrence_link(self, event):
            return '<a href="%s">View %s Occurrences</a>' % (
                reverse("%s:%s_%s_changelist_for_event" % (
                        self.admin_site.name,
                        self.occurrence_model._meta.app_label,
                        self.occurrence_model._meta.module_name),
                        args=(event.id,)),
                event.occurrence_count(),
                )
                
        occurrence_link.short_description = 'Occurrences'
        occurrence_link.allow_tags = True
        
        def get_urls(self):
            return patterns(
                '',
                url(r'(?P<parent_id>\d+)/create_child/',
                    self.admin_site.admin_view(self.create_child))
                ) + super(_EventAdmin, self).get_urls()

        def create_child(self, request, parent_id):
            parent = get_object_or_404(EventModel, id=parent_id)
            child = EventModel(parent=parent)

            # We don't want to save child yet, as it is potentially incomplete.
            # Instead, we'll get the parent and inheriting fields out of Event
            # and put them into a GET string for the new_event from.
            
            GET = QueryDict("parent=%s" % parent.id).copy()
            
            for field_name in EventModel._event_meta.fields_to_inherit:
                parent_attr = getattr(parent, field_name)
                if parent_attr:
                    if hasattr(parent_attr, 'all'): #for m2m. Sufficient?
                        GET[field_name] = u",".join([unicode(i.pk) for i in parent_attr.all()])
                    elif hasattr(parent_attr, 'pk'): #for fk. Sufficient?
                        GET[field_name] = parent_attr.pk
                    else:
                        GET[field_name] = parent_attr
        
            return redirect(
                reverse("%s:%s_%s_add" % (
                    self.admin_site.name, EventModel._meta.app_label,
                    EventModel._meta.module_name)
                )+"?%s" % GET.urlencode())
        
        def change_view(self, request, object_id, extra_context={}):
            obj = EventModel._event_manager.get(pk=object_id)

            if obj.parent:
                fields_diff = generate_diff(obj.parent, obj, include=EventModel._event_meta.fields_to_inherit)
            else:
                fields_diff = None
            extra_extra_context = {
                'fields_diff': fields_diff,
                'django_version': django.get_version()[:3],
                'object': obj,
                'occurrences_url':
                    reverse('%s:%s_%s_changelist_for_event' % (
                        self.admin_site.name,
                        self.occurrence_model._meta.app_label,
                        self.occurrence_model._meta.module_name),
                            args=(object_id,)),
                }
            extra_context.update(extra_extra_context)      
            return super(_EventAdmin, self).change_view(request, object_id, extra_context)
    return _EventAdmin

try:
    from feincms.admin.tree_editor import TreeEditor
except ImportError:
    pass
else:
    def FeinCMSEventAdmin(EventModel):
        class _FeinCMSEventAdmin(EventAdmin(EventModel), TreeEditor):
            pass
        return _FeinCMSEventAdmin


class TreeModelChoiceField(forms.ModelChoiceField):
    """ ModelChoiceField which displays depth of objects within MPTT tree. """
    def label_from_instance(self, obj):
        super_label = \
            super(TreeModelChoiceField, self).label_from_instance(obj)
        return u"%s%s" % ("-"*obj.level, super_label)


class DateAndMaybeTimeField(forms.SplitDateTimeField):
    """
    Allow blank time; default to 00:00:00:00 / 11:59:59:99999 (based on field label) 
    These times are time.min and time.max, by the way.
    """

    widget = admin.widgets.AdminSplitDateTime
    
    def clean(self, value):
        """ Override to make the TimeField not required. """
        try:
            return super(DateAndMaybeTimeField, self).clean(value)
        except ValidationError, error:
            if error.messages == [self.error_messages['required']]:
                if value[0] not in validators.EMPTY_VALUES:
                    out = self.compress([self.fields[0].clean(value[0]), None])
                    self.validate(out)
                    return out
            raise
                    
    def compress(self, data_list):
        if data_list:
            if data_list[0] in validators.EMPTY_VALUES:
                raise ValidationError(self.error_messages['invalid_date'])
            if data_list[1] in validators.EMPTY_VALUES:
                if self.label.lower().count('end'):
                    data_list[1] = datetime.time.max
                else:
                    data_list[1] = datetime.time.min
            return datetime.datetime.combine(*data_list)
        return None


def OccurrenceAdmin(OccurrenceModel):
    class _OccurrenceAdmin(admin.ModelAdmin):
        list_display = ['__unicode__','start','end','event',]
        list_editable = ['start','end','event',]
        # list_filter = ['event',]
        change_list_template = 'admin/eventtools/occurrence_list.html'
        
        def __init__(self, *args, **kwargs):
            super(_OccurrenceAdmin, self).__init__(*args, **kwargs)
            self.event_model = self.model.event.field.rel.to

        formfield_overrides = {
            models.DateTimeField: {'form_class':DateAndMaybeTimeField},
            }
            
        def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
            # override choices and form class for event field
            if db_field.name == 'event':
                # use TreeModelChoiceField in all views
                kwargs['form_class'] = TreeModelChoiceField
                if request and hasattr(request, '_event'):
                    # limit event choices in changelist
                    kwargs['queryset'] = request._event.get_descendants()
                return db_field.formfield(**kwargs)
            return super(_OccurrenceAdmin, self).formfield_for_foreignkey(
                db_field, request, **kwargs)

        def get_urls(self):
            return patterns(
                '',
                url(r'for_event/(?P<event_id>\d+)/$',
                    self.admin_site.admin_view(self.changelist_view),
                    name="%s_%s_changelist_for_event" % (
                        OccurrenceModel._meta.app_label,
                        OccurrenceModel._meta.module_name)),
                # workaround fix for "../" links in changelist breadcrumbs
                url(r'for_event/$',
                    self.admin_site.admin_view(self.changelist_view)),
                # and since relative URLs are used on changelist:
                url(r'for_event/(?P<event_id>\d+)/(?P<object_id>\d+)/$',
                    self.redirect_to_change_view),
                ) + super(_OccurrenceAdmin, self).get_urls()

        def redirect_to_change_view(self, request, event_id, object_id):
            return redirect('%s:%s_%s_change' % (
                    self.admin_site.name,
                    OccurrenceModel._meta.app_label,
                    OccurrenceModel._meta.module_name), object_id)

        def changelist_view(self, request, event_id=None, extra_context=None):
            if event_id:
                request._event = get_object_or_404(
                    self.event_model, id=event_id)
            else:
                messages.info(
                    request, "Occurrences can only be accessed via events.")
                return redirect("%s:%s_%s_changelist" % (
                        self.admin_site.name, self.event_model._meta.app_label,
                        self.event_model._meta.module_name))
            extra_context = extra_context or {}
            extra_context['root_event'] = request._event
            extra_context['root_event_change_url'] = reverse(
                '%s:%s_%s_change' % (
                    self.admin_site.name,
                    self.event_model._meta.app_label,
                    self.event_model._meta.module_name),
                args=(event_id,))
            return super(_OccurrenceAdmin, self).changelist_view(
                request, extra_context)

        def _get_event_ids(self, request):
            # includes a little bit of caching
            if hasattr(request, '_event'):
                if not hasattr(request, '_event_ids'):
                    descendants = request._event.get_descendants()
                    request._event_ids = \
                        descendants.values_list('id', flat=True)
                return request._event_ids
            return None

        def queryset(self, request):
            # limit to occurrences of descendents of request._event, if set
            queryset = super(_OccurrenceAdmin, self).queryset(request)
            if self._get_event_ids(request):
                queryset = queryset.filter(event__id__in=request._event_ids)
            return queryset

    return _OccurrenceAdmin


def GeneratorInline(GeneratorModel):
    class _GeneratorInline(admin.TabularInline):
        model = GeneratorModel
        extra = 1
        formfield_overrides = {
            models.DateTimeField: {'form_class': DateAndMaybeTimeField},
            }
        
        def formfield_for_dbfield(self, db_field, *args, **kwargs):
            formfield = super(_GeneratorInline, self).formfield_for_dbfield(
                db_field, *args, **kwargs)
            if db_field.name == 'exceptions':
                formfield.widget = ExceptionsWidget()
            return formfield
    return _GeneratorInline
