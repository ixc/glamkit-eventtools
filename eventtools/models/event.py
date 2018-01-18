from operator import itemgetter

from django.db import models
from django.db.models.base import ModelBase
from django.db.models.fields import FieldDoesNotExist
from django.db.models import Count
from django.core.urlresolvers import reverse
from django.utils.timezone import localtime
from django.utils.translation import ugettext, ugettext_lazy as _
from django.template.defaultfilters import urlencode, slugify

from mptt.models import MPTTModel, MPTTModelBase
from mptt.managers import TreeManager

from eventtools.utils.inheritingdefault import ModelInstanceAwareDefault #TODO: deprecate
from eventtools.utils.pprint_timespan import pprint_datetime_span, pprint_date_span
from eventtools.conf import settings

class EventQuerySet(models.query.QuerySet):
    # much as you may be tempted to add "starts_between" and other
    # OccurrenceQuerySet methods, resist (for the sake of DRYness and some
    # performance). Instead, use OccurrenceQuerySet.starts_between().events().
    # We have to relax this for opening and closing occurrences, as they're 
    # relevant to a particular event.

    def in_listings(self):
        """
        Returns the events that should be in listings, namely, the top
        events in the tree that have occurrences attached.

        Event.objects.in_listings() is the (minimum) set of events for which
        occurrences_in_listing() for these events will return the entire
        Occurrence set, with no repetitions or overlaps. ie, this is probably
        what you want to show in listings.

        Given that the tree is likely to be quite shallow, let's do this breadth-first.

        For each level:
        * two filter: 1) children of qs having_occurrences and 2) children of qs having_no_occurrences.
        * 1) is added to result set.
        * 2) is used as qs for next level

        TODO: For subqueries, this will produce results that are not in the
        superqueries, because we don't have access to potential missing parents.
        Maybe this is desired behaviour?
        """
        max_level = self.aggregate(models.Max('level'))['level__max']

        result = self.filter(level=0).having_occurrences()
        qs = self.filter(level=0).having_no_occurrences()

        for level in range(1, max_level+1):
            if qs:
                result |= self.filter(parent__in=qs).having_occurrences()
                qs = self.filter(parent__in=qs).having_no_occurrences()

        return result

    def occurrences(self):
        """
        Returns the occurrences for events in this queryset. NB that only
        occurrences attached directly to events, ie not child events, are returned.
        """
        events = self
        # Since we're likely to be filtering occurrences against this a lot,
        # avoid having the query (which is complex due to the MAX filtering)
        # executed every time, unless there are a lot of results.
        if events.distinct().count() < 100:
            events = list(
                self.order_by().distinct().values_list('pk', flat=True)
            )
        return self.model.OccurrenceModel().objects\
            .filter(event__in=events)
                
    def opening_occurrences(self):
        """
        Returns the opening occurrences for the events in this queryset.
        """
        pks = []
        for e in self:
            try:
                pks.append(e.opening_occurrence().id)
            except AttributeError:
                pass
        return self.occurrences().filter(pk__in=pks)
        
    def closing_occurrences(self):
        """
        Returns the closing occurrences for the events in this queryset.
        """
        pks = []
        for e in self:
            try:
                pks.append(e.closing_occurrence().id)
            except AttributeError:
                pass
        return self.occurrences().filter(pk__in=pks)
                
    #some simple annotations
    def having_occurrences(self):
        return self.annotate(num_occurrences=Count('occurrences'))\
            .filter(num_occurrences__gt=0)

    def having_n_occurrences(self, n):
        return self.annotate(num_occurrences=Count('occurrences'))\
            .filter(num_occurrences=n)

    def having_no_occurrences(self):
        return self.having_n_occurrences(0)
        
        
class EventTreeManager(TreeManager):
    
    def get_query_set(self): 
        return EventQuerySet(self.model).order_by(
            self.tree_id_attr, self.left_attr)

    def in_listings(self):
        return self.get_query_set().in_listings()

    def occurrences(self, *args, **kwargs):
        return self.get_query_set().occurrences(*args, **kwargs)

    def opening_occurrences(self, *args, **kwargs):
        return self.get_query_set().opening_occurrences(*args, **kwargs)
    def closing_occurrences(self, *args, **kwargs):
        return self.get_query_set().closing_occurrences(*args, **kwargs)

    def having_occurrences(self):
        return self.get_query_set().having_occurrences()        
    def having_n_occurrences(self, n):
        return self.get_query_set().having_n_occurrences(n)        
    def having_no_occurrences(self):
        return self.get_query_set().having_no_occurrences()        
            
class EventOptions(object):
    """
    Options class for Event models. Use this as an inner class called EventMeta.
    ie.:
    
    class MyModel(EventModel):
        class EventMeta:
            fields_to_inherit = ['name', 'slug', 'description']
        ...     
    """
    
    fields_to_inherit = []
    event_manager_class = EventTreeManager
    event_manager_attr = 'eventobjects'
    
    def __init__(self, opts):
        # Override defaults with options provided
        if opts:
            for key, value in opts.__dict__.iteritems():
                setattr(self, key, value)


class EventModelBase(MPTTModelBase):
    def __new__(meta, class_name, bases, class_dict):
        """
        Create subclasses of EventModel. This:
         - (via super) adds the MPTT fields to the class
         - adds the EventManager to the model
         - overrides MPTT's TreeManager to the model, so that the treemanager
           includes eventtools methods.
        """
        event_opts = class_dict.pop('EventMeta', None)
        class_dict['_event_meta'] = EventOptions(event_opts)
        cls = super(EventModelBase, meta) \
            .__new__(meta, class_name, bases, class_dict)
                
        try:
            EventModel
        except NameError:
            # We're defining the base class right now, so don't do anything
            # We only want to add this stuff to the subclasses.
            # (Otherwise if field names are customized, we'll end up adding two
            # copies)
            pass
        else:
            for field_name in class_dict['_event_meta'].fields_to_inherit:
                try:
                    field = cls._meta.get_field(field_name)
                    #injecting our fancy inheriting default
                    field.default = ModelInstanceAwareDefault(
                        field_name,
                        field.default
                    )
                except models.FieldDoesNotExist:
                    continue
            
            # Add a custom manager
            assert issubclass(
                cls._event_meta.event_manager_class, EventTreeManager
            ), 'Custom Event managers must subclass EventTreeManager.'
            
            # since EventTreeManager subclasses TreeManager, it also needs the
            # mptt options. The code below mimics the behaviour in
            # mptt.models.MPTTModelBase.register
            manager = cls._event_meta.event_manager_class()
            manager.contribute_to_class(cls, cls._event_meta.event_manager_attr)
            manager.init_from_model(cls)

            setattr(cls, '_event_manager',
                getattr(cls, cls._event_meta.event_manager_attr)
            )
            
            # override the treemanager with self too,
            # so we don't need to recast all querysets
            manager.contribute_to_class(cls, '_tree_manager')
            setattr(cls, '_tree_manager', manager)

        return cls

class EventModel(MPTTModel):
    __metaclass__ = EventModelBase
    
    parent = models.ForeignKey('self',
        null=True, blank=True, related_name='children',
        verbose_name=_('parent'),
        help_text=_("Which event is this event derived from. Use the 'create a variation' on the parent event to inherit the parent's information."))
    # 'parent' is more flexible than 'template'.
    title = models.CharField(_('title'), max_length=255)
    slug = models.SlugField(_("URL name"), unique=True, help_text=_("This is used in\
     the event's URL, and should be unique and unchanging."))
    season_description = models.CharField(_("season"), blank=True, null=True, 
        max_length=200, help_text=_("a summary description of when this event \
        is on (e.g. 24 August - 12 September 2012). One will be generated from \
        the occurrences if not provided)")
    )
    sessions_description = models.TextField(_("sessions"), blank=True,
        null=True, help_text=_("a detailed description of when sessions are\
        (e.g. \'Tuesdays and Thursdays throughout February, at 10:30am\')")
    )

    class Meta:
        abstract = True
        ordering = ['tree_id', 'lft'] 
    
    def __unicode__(self):
        return self.title

    @classmethod
    def OccurrenceModel(cls):
        """
        Returns the class used for occurrences
        """
        return cls.occurrences.related.model

    @classmethod
    def GeneratorModel(cls):
        """
        Returns the class used for generators
        """
        return cls.generators.related.model
        
    @classmethod
    def ExclusionModel(cls):
        """
        Returns the class used for exclusions
        """
        return cls.exclusions.related.model

    def save(self, *args, **kwargs):
        """
        When an event is saved, the changes to fields are cascaded to children,
        and any endless generators are updated, so that a few more occurrences
        are generated
        """
        #this has to happen before super.save, so that we can tell what's
        #changed
        if not self.slug:
            self.slug = slugify(unicode(self))

        self._cascade_changes_to_children()
        r = super(EventModel, self).save(*args, **kwargs)

        endless_generators = self.generators.filter(repeat_until__isnull=True)
        [g.save() for g in endless_generators]

        return r
                
    def reload(self):
        """
        Used for refreshing events in a queryset that may have changed.        
        Call with x = x.reload() - it doesn't change self.
        """
        return type(self)._event_manager.get(pk=self.pk)
        
    def _cascade_changes_to_children(self):
        """
        Go through the fields_to_inherit, and apply my values to my children,
        if my children don't have altered values.

        Now tries 'inheritable_FOO' attributes for getting attributes where the
        native value isn't in the right form,
        e.g. MarkItUp fields, where the "Field" is the value.

        @property
        def inheritable_price:
            return self.price.raw
        """
        if self.pk:
            saved_self = type(self)._event_manager.get(pk=self.pk)
            attribs = type(self)._event_meta.fields_to_inherit
        
            for child in self.get_children():
                for a in attribs:
                    inheritable_attr = "inheritable_%s" % a
                    try:
                        saved_value = getattr(saved_self, inheritable_attr, getattr(saved_self, a))
                        ch_value =  getattr(child, inheritable_attr, getattr(child, a))
                        if ch_value == saved_value:
                            #the child's value is unchanged from the parent
                            new_value = getattr(self, inheritable_attr, getattr(self, a))
                            setattr(child, a, new_value)
                    except AttributeError:
                        continue
                child.save() #cascades to grandchildren

    def occurrences_in_listing(self):
        """
        The occurrences_in_listing set is the occurrences that are 'relevant' to
        this event, by dint of being directly attached, or attached to one of its
        children.

        Event.objects.in_listings() is the (minimum) set of events for which
        occurrences_in_listing() for these events will return the entire
        Occurrence set, with no repetitions or overlaps. ie, this is probably
        what you want to show in listings.
        """
        return self.get_descendants(include_self=True).occurrences()

    def opening_occurrence(self):
        try:
            return self.occurrences_in_listing().all()[0]
        except IndexError:
            return None
        
    def closing_occurrence(self):
        try:
            return self.occurrences_in_listing().all().reverse()[0]
        except IndexError:
            return None

    def get_absolute_url(self):
        return reverse('events:event', kwargs={'event_slug': self.slug })
        
    def is_finished(self):
        """ the event has finished if the closing occurrence has finished. """
        closing_occurrence = self.closing_occurrence()
        if closing_occurrence:
            return closing_occurrence.is_finished()

    def listed_under(self):
        """
        This event is listed under the highest ancestor that has Occurrences directly attached.
        """
        try:
            return self.get_ancestors().having_occurrences().order_by('level')[0]
        except (IndexError, AttributeError):
            if self.occurrences.count():
                return self
        return None

    def is_listed(self):
        return self.listed_under() == self
    is_listed.boolean = True

    def season(self):
        """
        Returns a string describing the first and last dates of this event.
        """
        if self.season_description:
            return self.season_description
        
        o = self.opening_occurrence()
        c = self.closing_occurrence()
        
        if o and c:
            first = localtime(o.start).date()
            last = localtime(c.start).date()
            return pprint_date_span(first, last)
            
        return None

    def sessions(self):
        return self.sessions_description

    def occurrence_statuses(self):
        #returns a set of statuses of my occurrences
        return set(self.occurrences_in_listing().values_list('status', flat=True).distinct())

    def status(self):
        #returns a status if all occurrences have the same status.
        #Used in admin listing
        statuses = self.occurrence_statuses()
        if len(statuses) == 1:
            return list(statuses)[0]
        return "(various)"

    def is_cancelled(self):
        """Return True if all occurrences are cancelled"""
        cancelled = self.cancelled_occurrences().count()
        return cancelled > 0 and self.occurrences_in_listing().count() == cancelled

    def forthcoming_is_cancelled(self):
        """Return True if all forthcoming occurrences are cancelled"""
        forthcoming = self.occurrences_in_listing().forthcoming().count()
        cancelled_forthcoming = self.cancelled_occurrences().forthcoming().count()
        return cancelled_forthcoming > 0 and forthcoming == cancelled_forthcoming

    def is_fully_booked(self):
        """
        Return True if no occurrences are available and at least one is fully booked. (a mix of cancelled and fully booked is allowed)
        """
        return self.available_occurrences().count() == 0 and self.fully_booked_occurrences().count() > 0

    def forthcoming_is_fully_booked(self):
        """
        Return True if no forthcoming occurrences are available and at least one is fully booked. (a mix of cancelled and fully booked is allowed)
        """
        return self.available_occurrences().forthcoming().count() == 0 and self.fully_booked_occurrences().forthcoming().count() > 0

    def is_available(self):
        """
        Return True if any sessions are available (ie not cancelled or fully booked)
        """
        return self.available_occurrences().count() > 0

    def unavailable_status_message(self):
        if self.is_finished():
            return "This event has finished."
        if self.is_cancelled() or self.forthcoming_is_cancelled():
            return "This event is CANCELLED."
        if self.is_fully_booked() or self.forthcoming_is_fully_booked():
            return "This event is fully booked." #If there are no available sessions and some are fully booked, the whole event is treated as fully booked.
        return None

    def available_occurrences(self):
        return self.occurrences_in_listing().available()

    def unavailable_occurrences(self):
        return self.occurrences_in_listing().unavailable()

    def cancelled_occurrences(self):
        return self.occurrences_in_listing().cancelled()

    def fully_booked_occurrences(self):
        return self.occurrences_in_listing().fully_booked()

    def variation_occurrences(self):
        return self.occurrences_in_listing().exclude(event=self)

    def times_description(self, formatting=None):
        """
        Produces a string representing the regular time in which an event occurs.

        Ex: for an event only ever occurring at 5:30pm each day, it returns '5.30pm'.

        Ex: for an event with irregular times or multiple occurrences per day, it
            returns 'Times vary'
        """

        if not formatting: # use default formatting
            formatting = '%I.%M%p'

        starting_times = list(set([
            localtime(occurrence.start).time()
            for occurrence in self.occurrences.all()
        ]))

        if len(starting_times) == 1:
            # `lower` converts Django's 'PM' into 'pm' and `lstrip` removes any leading '0'
            return starting_times[0].strftime(formatting).lower().lstrip('0')
        else:
            return 'Times vary'

    def ical_url(self):
         # Needs to be fully-qualified (for sending to calendar apps)
         return settings.ICAL_ROOT_URL + reverse("events:event_ical", args=[self.slug])

    def webcal_url(self):
         return self.ical_url().replace("http://", "webcal://").replace("https://", "webcal://")

    def gcal_url(self):
         return  "http://www.google.com/calendar/render?cid=%s" % urlencode(self.ical_url())
