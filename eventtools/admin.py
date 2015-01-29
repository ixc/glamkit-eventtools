import django
from django import forms
from eventtools.conf import settings
from django.conf.urls import patterns, url
from django.contrib import admin, messages
from django.core.urlresolvers import reverse
from django.http import QueryDict
from django.shortcuts import get_object_or_404, redirect
from django.forms.models import BaseInlineFormSet
from mptt.forms import TreeNodeChoiceField
from mptt.admin import MPTTModelAdmin
from django.utils.translation import ugettext_lazy as _

from utils.diff import generate_diff

from .models import Rule
from .filters import IsGeneratedListFilter
    
MPTT_ADMIN_LEVEL_INDENT = getattr(settings, 'MPTT_ADMIN_LEVEL_INDENT', 10)


class TreeModelChoiceField(forms.ModelChoiceField):
    """ ModelChoiceField which displays depth of objects within MPTT tree. """
    def label_from_instance(self, obj):
        super_label = \
            super(TreeModelChoiceField, self).label_from_instance(obj)
        return u"%s%s" % ("-"*obj.level, super_label)


# ADMIN ACTIONS
def _remove_occurrences(modeladmin, request, queryset):
    for m in queryset:
        # if the occurrence was generated, then add it as an exclusion.
        if m.generated_by is not None:
            m.event.exclusions.get_or_create(start=m.start)
        m.delete()
_remove_occurrences.short_description = _("Delete occurrences (and prevent recreation by a repeating occurrence)")

def _wipe_occurrences(modeladmin, request, queryset):
    queryset.delete()
_wipe_occurrences.short_description = _("Delete occurrences (but allow recreation by a repeating occurrence)")

def _convert_to_oneoff(modeladmin, request, queryset):
    for m in queryset:
        # if the occurrence was generated, then add it as an exclusion.
        if m.generated_by is not None:
            m.event.exclusions.get_or_create(start=m.start)
    queryset.update(generated_by=None)
_convert_to_oneoff.short_description = _("Make occurrences one-off (and prevent recreation by a repeating occurrence)")

def _cancel(modeladmin, request, queryset):
    queryset.update(status=settings.OCCURRENCE_STATUS_CANCELLED[0])
_cancel.short_description = _("Make occurrences cancelled")

def _fully_booked(modeladmin, request, queryset):
    queryset.update(status=settings.OCCURRENCE_STATUS_FULLY_BOOKED[0])
_fully_booked.short_description = _("Make occurrences fully booked")

def _clear_status(modeladmin, request, queryset):
    queryset.update(status="")
_clear_status.short_description = _("Clear booked/cancelled status")

class OccurrenceAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(OccurrenceAdminForm, self).__init__(*args, **kwargs)
        EventModel = self.instance.EventModel()
        self.fields['event'] = TreeModelChoiceField(EventModel.objects)

        event = self.instance.event
        if event:
            if self.instance.generated_by:
                #generated_by events are limited to children of the generator event
                #(otherwise syncing breaks). TODO: make syncing look at ancestors as well?
                self.fields['event'].queryset = self.instance.generated_by.event.get_descendants(include_self=True)
            else:
                self.fields['event'].queryset = \
                    event.get_descendants(include_self = True) | \
                    event.get_ancestors() | \
                    event.get_siblings()



def OccurrenceAdmin(OccurrenceModel):
    class _OccurrenceAdmin(admin.ModelAdmin):
        form = OccurrenceAdminForm
        list_display = ['start', '_duration', 'event', 'from_a_repeating_occurrence', 'edit_link', 'status']
        list_display_links = ['start'] # this is turned off in __init__
        list_editable = ['event', 'status']
        list_filter = [IsGeneratedListFilter,]
        change_list_template = 'admin/eventtools/occurrence_list.html'
        fields = ("event" , "start", "_duration", "generated_by", 'status')
        readonly_fields = ('generated_by', )
        actions = [_cancel, _fully_booked, _clear_status, _convert_to_oneoff, _remove_occurrences, _wipe_occurrences]
        date_hierarchy = 'start'
        
        def __init__(self, *args, **kwargs):
            super(_OccurrenceAdmin, self).__init__(*args, **kwargs)
            self.event_model = self.model.EventModel()
            self.list_display_links = (None,) #have to specify it here to avoid Django complaining
  
        def edit_link(self, occurrence):
            if occurrence.generated_by is not None:
                change_url = reverse(
                    '%s:%s_%s_change' % (
                        self.admin_site.name,
                        self.event_model._meta.app_label,
                        self.event_model._meta.module_name),
                    args=(occurrence.generated_by.event.id,)
                )
                return "via a repeating occurrence in <a href='%s'>%s</a>" % (
                    change_url,
                    occurrence.generated_by.event,
                )
            else:
                change_url = reverse(
                    '%s:%s_%s_change' % (
                        self.admin_site.name,
                        type(occurrence)._meta.app_label,
                        type(occurrence)._meta.module_name),
                    args=(occurrence.id,)
                )
                return "<a href='%s'>Edit</a>" % (
                    change_url,
                )
        edit_link.short_description = "edit"
        edit_link.allow_tags = True

        def get_changelist_form(self, request, **kwargs):
            kwargs.setdefault('form', OccurrenceAdminForm)
            return super(_OccurrenceAdmin, self).get_changelist_form(request, **kwargs)

        def event_edit_url(self, event):
            return reverse(
                '%s:%s_%s_change' % (
                    self.admin_site.name,
                    self.event_model._meta.app_label,
                    self.event_model._meta.module_name),
                args=(event.id,)
            )

        def from_a_repeating_occurrence(self, occurrence):
            return occurrence.generated_by is not None
        from_a_repeating_occurrence.boolean = True
  
        def get_urls(self):
            """
            Add the event-specific occurrence list.
            """
            return patterns('',
                # causes redirect to events list, because we don't want to see all occurrences.
                url(r'^$',
                    self.admin_site.admin_view(self.changelist_view_for_event)),
                url(r'for_event/(?P<event_id>\d+)/$',
                    self.admin_site.admin_view(self.changelist_view_for_event),
                    name="%s_%s_changelist_for_event" % (
                        OccurrenceModel._meta.app_label,
                        OccurrenceModel._meta.module_name)),
                # workaround fix for "../" links in changelist breadcrumbs
                # causes redirect to events changelist
                url(r'for_event/$',
                    self.admin_site.admin_view(self.changelist_view_for_event)),
                url(r'for_event/(?P<event_id>\d+)/(?P<object_id>\d+)/$',
                    self.redirect_to_change_view),
            ) + super(_OccurrenceAdmin, self).get_urls()
      
        def changelist_view_for_event(self, request, event_id=None, extra_context=None):
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
     
        def redirect_to_change_view(self, request, event_id, object_id):
            return redirect('%s:%s_%s_change' % (
                    self.admin_site.name,
                    OccurrenceModel._meta.app_label,
                    OccurrenceModel._meta.module_name), object_id)
     
        def queryset(self, request):
            if hasattr(request, '_event'):
                return request._event.occurrences_in_listing()
            else:
                qs = super(_OccurrenceAdmin, self).queryset(request)
            return qs
     
        def get_actions(self, request):
            # remove 'delete' action
            actions = super(_OccurrenceAdmin, self).get_actions(request)
            if 'delete_selected' in actions:
                del actions['delete_selected']
            return actions
    return _OccurrenceAdmin

def EventForm(EventModel):
    class _EventForm(forms.ModelForm):
        parent = TreeNodeChoiceField(queryset=EventModel._event_manager.all(), level_indicator=u"-", required=False)

        class Meta:
            model = EventModel
    return _EventForm

def EventAdmin(EventModel, SuperModel=MPTTModelAdmin, show_exclusions=False, show_generator=True, *args, **kwargs):
    """ pass in the name of your EventModel subclass to use this admin. """
    
    class _EventAdmin(SuperModel):
        form = EventForm(EventModel)
        occurrence_inline = OccurrenceInline(EventModel.OccurrenceModel())
        list_display = ['unicode_bold_if_listed', 'occurrence_link', 'season', 'status'] # leave as list to allow extension
        change_form_template = kwargs['change_form_template'] if 'change_form_template' in kwargs else 'admin/eventtools/event.html'
        save_on_top = kwargs['save_on_top'] if 'save_on_top' in kwargs else True
        prepopulated_fields = {'slug': ('title', )}
        search_fields = ('title',)

#        def queryset(self, request):
#             return EventModel.objects.annotate(occurrence_count=Count('occurrences'))

        def append_eventtools_inlines(self, inline_instances):
            eventtools_inlines = [
                self.occurrence_inline,
            ]
            if show_generator:
                eventtools_inlines.append(GeneratorInline(EventModel.GeneratorModel()))

            if show_exclusions:
                eventtools_inlines.append(ExclusionInline(EventModel.ExclusionModel()))
            
            for inline_class in eventtools_inlines:
                inline_instance = inline_class(self.model, self.admin_site)
                inline_instances.append( inline_instance )


        def get_inline_instances(self, request, *args, **kwargs):
            """
            This overrides the regular ModelAdmin.get_inline_instances(self, request)
            """
            # Get any regular Django inlines the user may have defined.
            inline_instances = super(_EventAdmin, self).get_inline_instances(
                request, *args, **kwargs)
            # Append our eventtools inlines
            self.append_eventtools_inlines(inline_instances)
            return inline_instances
            

        def __init__(self, *args, **kwargs):
            super(_EventAdmin, self).__init__(*args, **kwargs)
            self.occurrence_model = EventModel.OccurrenceModel()

        def unicode_bold_if_listed(self, obj):
            if obj.is_listed():
                result = "<span style='font-weight:bold;padding-left:%spx'>%s</span>"
            else:
                result = "<span style='font-weight:normal;padding-left:%spx'>%s</span>"

            return result % (
                (5 + MPTT_ADMIN_LEVEL_INDENT * obj.level),
                unicode(obj),
            )
        unicode_bold_if_listed.allow_tags = True
        unicode_bold_if_listed.short_description = _("title (items in bold will be listed; other items are templates or variations)")

        def occurrence_edit_url(self, event):
            return reverse("%s:%s_%s_changelist_for_event" % (
                        self.admin_site.name,
                        self.occurrence_model._meta.app_label,
                        self.occurrence_model._meta.module_name),
                        args=(event.id,)
                )

        def occurrence_link(self, event):
            count = event.occurrences_in_listing().count()
            direct_count = event.occurrences.count()

            url = self.occurrence_edit_url(event)

            if count == 0:
                return _('No occurrences yet')
            elif count == 1:
                r = '<a href="%s">1 Occurrence</a>' % url
            else:
                r = '<a href="%s">%s Occurrences</a>' % (
                    url,
                    count,
                )
            return r + ' (%s direct)' % direct_count
        occurrence_link.short_description = _('Edit Occurrences')
        occurrence_link.allow_tags = True

        def get_urls(self):
            return patterns(
                '',
                url(r'(?P<parent_id>\d+)/create_variation/',
                    self.admin_site.admin_view(self._create_variation))
                ) + super(_EventAdmin, self).get_urls()

        def _create_variation(self, request, parent_id):
            """
            We don't want to try to save child yet, as it is potentially incomplete.
            Instead, we'll get the parent and inheriting fields out of Event
            and put them into a GET string for the new_event form.

            To get values, we first try inheritable_FOO, to populate the form.

            @property
            def inheritable_price:
                return self.price.raw
            """
            parent = get_object_or_404(EventModel, id=parent_id)
            GET = QueryDict("parent=%s" % parent.id).copy()

            for field_name in EventModel._event_meta.fields_to_inherit:
                inheritable_field_name = "inheritable_%s" % field_name
                parent_attr =  getattr(parent, inheritable_field_name, getattr(parent, field_name))
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
                'occurrence_edit_url': self.occurrence_edit_url(event=obj),
            }
            extra_context.update(extra_extra_context)
            return super(_EventAdmin, self).change_view(request, object_id, extra_context=extra_context)
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


#TODO: Make a read-only display to show 'reassigned' generated occurrences.
class OccurrenceInlineFormSet(BaseInlineFormSet):
    """
    Shows non-generated occurrences
    """
    def __init__(self, *args, **kwargs):
        event = kwargs.get('instance')
        if event:
            # Exclude occurrences that are generated by one of my generators
            my_generators = event.generators.all()
            kwargs['queryset'] = kwargs['queryset'].exclude(generated_by__in=my_generators)
        else:
            #new form
            pass
        super(OccurrenceInlineFormSet, self).__init__(*args, **kwargs)

def OccurrenceInline(OccurrenceModel):
    class _OccurrenceInline(admin.TabularInline):
        model = OccurrenceModel
        formset = OccurrenceInlineFormSet
        extra = 1
        fields = ('start', '_duration', 'generated_by')
        readonly_fields = ('generated_by', )
    return _OccurrenceInline

def ExclusionInline(ExclusionModel):
    class _ExclusionInline(admin.TabularInline):
        model = ExclusionModel
        extra = 0
        fields = ('start',)        
    return _ExclusionInline

def GeneratorInline(GeneratorModel):
    class _GeneratorInline(admin.TabularInline):
        model = GeneratorModel
        extra = 0
    return _GeneratorInline
    
admin.site.register(Rule)
