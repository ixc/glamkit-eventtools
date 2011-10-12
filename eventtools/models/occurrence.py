from datetime import date, time, datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil.tz import gettz
from vobject.icalendar import utc

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse
from django.db.models import signals
from django.db.models.base import ModelBase
from django.template.defaultfilters import urlencode
from django.utils.dateformat import format
from django.utils.translation import ugettext as _

from eventtools.utils import datetimeify, dayify
from eventtools.conf import settings
from eventtools.utils import dateranges
from eventtools.utils.viewutils import parse_GET_date
from eventtools.utils.pprint_timespan import pprint_datetime_span, pprint_time_span
from eventtools.utils.domain import django_root_url


class OccurrenceQuerySetFN(object):
    """
    All the query functions are defined here, so they can be easily inspected by the manager metaclass.
    """

    def starts_before(self, date):
        end = datetimeify(date, clamp="max")
        return self.filter(start__lte=end)
    def ends_before(self, date):
        end = datetimeify(date, clamp="max")
        return self.filter(end__lte=end)

    def starts_after(self, date):
        start = datetimeify(date, clamp="min")
        return self.filter(start__gte=start)
    def ends_after(self, date):
        start = datetimeify(date, clamp="min")
        return self.filter(end__gte=start)

    def starts_between(self, d1, d2, forthcoming_only=False):
        """
        returns the occurrences that start in a given date/datetime range
        if forthcoming_only == True, and now is between start and end, then 
        only occurrences that start AFTER datetime.now() are included.
        """
        if forthcoming_only:
            now = datetime.now()
            if d1 <= now <= d2:
                d1 = now
        return self.starts_after(d1).starts_before(d2)   
          
    def ends_between(self, d1, d2, forthcoming_only=False):
        if forthcoming_only:
            now = datetime.now()
            if d1 <= now <= d2:
                d1 = now
        return self.ends_after(d1).ends_before(d2)
        
    def entirely_between(self, d1, d2, forthcoming_only=False):
        """
        returns the occurrences that both start and end in a given datetime range
        """
        if forthcoming_only:
            now = datetime.now()
            if d1 <= now <= d2:
                d1 = now
        return self.starts_after(d1).ends_before(d2)

    def starts_on(self, day, forthcoming_only=False):
        d1, d2 = dayify(day)
        return self.starts_between(d1, d2, forthcoming_only)
    def ends_on(self, day, forthcoming_only=False):
        d1, d2 = dayify(day)
        return self.ends_between(d1, d2, forthcoming_only)
    def entirely_on(self, day, forthcoming_only=False):
        d1, d2 = dayify(day)
        return self.entirely_between(d1, d2, forthcoming_only)
    
    def starts_in_week_of(self, day, forthcoming_only=False):
        d1, d2 = dateranges.dates_for_week_of(day)
        return self.starts_between(d1, d2, forthcoming_only)
    def ends_in_week_of(self, day, forthcoming_only=False):
        d1, d2 = dateranges.dates_for_week_of(day)
        return self.ends_between(d1, d2, forthcoming_only)
    def entirely_in_week_of(self, day, forthcoming_only=False):
        d1, d2 = dateranges.dates_for_week_of(day)
        return self.entirely_between(d1, d2, forthcoming_only)

    def starts_in_weekend_of(self, day, forthcoming_only=False):
        d1, d2 = dateranges.dates_for_weekend_of(day)
        return self.starts_between(d1, d2, forthcoming_only)
    def ends_in_weekend_of(self, day, forthcoming_only=False):
        d1, d2 = dateranges.dates_for_weekend_of(day)
        return self.ends_between(d1, d2, forthcoming_only)
    def entirely_in_weekend_of(self, day, forthcoming_only=False):
        d1, d2 = dateranges.dates_for_weekend_of(day)
        return self.entirely_between(d1, d2, forthcoming_only)

    def starts_in_fortnight_of(self, day, forthcoming_only=False):
        d1, d2 = dateranges.dates_for_fortnight_of(day)
        return self.starts_between(d1, d2, forthcoming_only)
    def ends_in_fortnight_of(self, day, forthcoming_only=False):
        d1, d2 = dateranges.dates_for_fortnight_of(day)
        return self.ends_between(d1, d2, forthcoming_only)
    def entirely_in_fortnight_of(self, day, forthcoming_only=False):
        d1, d2 = dateranges.dates_for_fortnight_of(day)
        return self.entirely_between(d1, d2, forthcoming_only)

    def starts_in_month_of(self, day, forthcoming_only=False):
        d1, d2 = dateranges.dates_for_month_of(day)
        return self.starts_between(d1, d2, forthcoming_only)
    def ends_in_month_of(self, day, forthcoming_only=False):
        d1, d2 = dateranges.dates_for_month_of(day)
        return self.ends_between(d1, d2, forthcoming_only)
    def entirely_in_month_of(self, day, forthcoming_only=False):
        d1, d2 = dateranges.dates_for_month_of(day)
        return self.entirely_between(d1, d2, forthcoming_only)

    def starts_in_year_of(self, day, forthcoming_only=False):
        d1, d2 = dateranges.dates_for_year_of(day)
        return self.starts_between(d1, d2, forthcoming_only)
    def ends_in_year_of(self, day, forthcoming_only=False):
        d1, d2 = dateranges.dates_for_year_of(day)
        return self.ends_between(d1, d2, forthcoming_only)
    def entirely_in_year_of(self, day, forthcoming_only=False):
        d1, d2 = dateranges.dates_for_year_of(day)
        return self.entirely_between(d1, d2, forthcoming_only)

    #queries relative to now
    def starts_today(self, forthcoming_only=False):
        return self.starts_on(date.today(), forthcoming_only)
    def ends_today(self, forthcoming_only=False):
        return self.ends_on(date.today(), forthcoming_only)
    def entirely_today(self, forthcoming_only=False):
        return self.entirely_on(date.today(), forthcoming_only)

    def starts_this_week(self, forthcoming_only=False):
        return self.starts_in_week_of(date.today(), forthcoming_only)
    def ends_this_week(self, forthcoming_only=False):
        return self.ends_in_week_of(date.today(), forthcoming_only)
    def entirely_this_week(self, forthcoming_only=False):
        return self.entirely_in_week_of(date.today(), forthcoming_only)

    def starts_this_weekend(self, forthcoming_only=False):
        return self.starts_in_weekend_of(date.today(), forthcoming_only)
    def ends_this_weekend(self, forthcoming_only=False):
        return self.ends_in_weekend_of(date.today(), forthcoming_only)
    def entirely_this_weekend(self, forthcoming_only=False):
        return self.entirely_in_weekend_of(date.today(), forthcoming_only)

    def starts_this_fortnight(self, forthcoming_only=False):
        return self.starts_in_fortnight_of(date.today(), forthcoming_only)
    def ends_this_week(self, forthcoming_only=False):
        return self.ends_in_fortnight_of(date.today(), forthcoming_only)
    def entirely_this_week(self, forthcoming_only=False):
        return self.entirely_in_fortnight_of(date.today(), forthcoming_only)

    def starts_this_month(self, forthcoming_only=False):
        return self.starts_in_month_of(date.today(), forthcoming_only)
    def ends_this_month(self, forthcoming_only=False):
        return self.ends_in_month_of(date.today(), forthcoming_only)
    def entirely_this_month(self, forthcoming_only=False):
        return self.entirely_in_month_of(date.today(), forthcoming_only)

    def starts_this_year(self, forthcoming_only=False):
        return self.starts_in_year_of(date.today(), forthcoming_only)
    def ends_this_year(self, forthcoming_only=False):
        return self.ends_in_year_of(date.today(), forthcoming_only)
    def entirely_this_year(self, forthcoming_only=False):
        return self.entirely_in_year_of(date.today(), forthcoming_only)



    def starts_yesterday(self):
        return self.starts_on(date.today()-timedelta(1))
    def ends_yesterday(self):
        return self.ends_on(date.today()-timedelta(1))
    def entirely_yesterday(self):
        return self.entirely_on(date.today()-timedelta(1))

    def starts_last_week(self):
        return self.starts_in_week_of(date.today()-timedelta(7))
    def ends_last_week(self):
        return self.ends_in_week_of(date.today()-timedelta(7))
    def entirely_last_week(self):
        return self.entirely_in_week_of(date.today()-timedelta(7))

    def starts_last_weekend(self):
        return self.starts_in_weekend_of(date.today()-timedelta(7))
    def ends_last_weekend(self):
        return self.ends_in_weekend_of(date.today()-timedelta(7))
    def entirely_last_weekend(self):
        return self.entirely_in_weekend_of(date.today()-timedelta(7))

    def starts_last_fortnight(self):
        return self.starts_in_fortnight_of(date.today()-timedelta(14))
    def ends_last_week(self):
        return self.ends_in_fortnight_of(date.today()-timedelta(14))
    def entirely_last_week(self):
        return self.entirely_in_fortnight_of(date.today()-timedelta(14))

    def starts_last_month(self):
        return self.starts_in_month_of(date.today()+relativedelta(months=-1))
    def ends_last_month(self):
        return self.ends_in_month_of(date.today()+relativedelta(months=-1))
    def entirely_last_month(self):
        return self.entirely_in_month_of(date.today()+relativedelta(months=-1))

    def starts_last_year(self):
        return self.starts_in_year_of(date.today()+relativedelta(years=-1))
    def ends_last_year(self):
        return self.ends_in_year_of(date.today()+relativedelta(years=-1))
    def entirely_last_year(self):
        return self.entirely_in_year_of(date.today()+relativedelta(years=-1))



    def starts_tomorrow(self):
        return self.starts_on(date.today()+timedelta(1))
    def ends_tomorrow(self):
        return self.ends_on(date.today()+timedelta(1))
    def entirely_tomorrow(self):
        return self.entirely_on(date.today()+timedelta(1))

    def starts_next_week(self):
        return self.starts_in_week_of(date.today()+timedelta(7))
    def ends_next_week(self):
        return self.ends_in_week_of(date.today()+timedelta(7))
    def entirely_next_week(self):
        return self.entirely_in_week_of(date.today()+timedelta(7))

    def starts_next_weekend(self):
        return self.starts_in_weekend_of(date.today()+timedelta(7))
    def ends_next_weekend(self):
        return self.ends_in_weekend_of(date.today()+timedelta(7))
    def entirely_next_weekend(self):
        return self.entirely_in_weekend_of(date.today()+timedelta(7))

    def starts_next_fortnight(self):
        return self.starts_in_fortnight_of(date.today()+timedelta(14))
    def ends_next_week(self):
        return self.ends_in_fortnight_of(date.today()+timedelta(14))
    def entirely_next_week(self):
        return self.entirely_in_fortnight_of(date.today()+timedelta(14))

    def starts_next_month(self):
        return self.starts_in_month_of(date.today()+relativedelta(months=1))
    def ends_next_month(self):
        return self.ends_in_month_of(date.today()+relativedelta(months=1))
    def entirely_next_month(self):
        return self.entirely_in_month_of(date.today()+relativedelta(months=1))

    def starts_next_year(self):
        return self.starts_in_year_of(date.today()+relativedelta(years=+1))
    def ends_next_year(self):
        return self.ends_in_year_of(date.today()+relativedelta(years=+1))
    def entirely_next_year(self):
        return self.entirely_in_year_of(date.today()+relativedelta(years=+1))

    #defaults
    before = starts_before
    after = starts_after
    between = starts_between
    on = starts_on
    in_week_of = starts_in_week_of
    in_weekend_of = starts_in_weekend_of
    in_fortnight_of = starts_in_fortnight_of
    in_month_of = starts_in_month_of
    in_year_of = starts_in_year_of
    # default shortcuts
    today = starts_today
    this_week = starts_this_week
    this_weekend = starts_this_weekend
    this_fortnight = starts_this_fortnight
    this_month = starts_this_month
    this_year = starts_this_year
    yesterday = starts_yesterday
    last_week = starts_last_week
    last_weekend = starts_last_weekend
    last_fortnight = starts_last_fortnight
    last_month = starts_last_month
    last_year = starts_last_year
    tomorrow = starts_tomorrow
    next_week = starts_next_week
    next_weekend = starts_next_weekend
    next_fortnight = starts_next_fortnight
    next_month = starts_next_month
    next_year = starts_next_year

    #misc queries (note they assume starts_ and ends_)
    def forthcoming(self):
        return self.starts_after(datetime.now())

    def recent(self):
        return self.ends_before(datetime.now())
        
    def now_on(self):
        n = datetime.now()
        return self.starts_before(n).ends_after(n)
        
    def events(self):
        """
        Return a queryset corresponding to the events matched by these occurrences.
        """
        event_ids = self.values_list('event_id', flat=True).distinct()
        return self.model.Event()._event_manager.filter(id__in=event_ids)
        
    def from_GET(self, GET={}):
        fr, to = parse_GET_date(GET)

        if to is None:
            return self.after(fr), (fr, to)
        if fr is None:
            return self.before(to).reverse(), (fr, to)
        return self.between(fr, to), (fr, to)
                
        
class OccurrenceQuerySet(models.query.QuerySet, OccurrenceQuerySetFN):
    pass #all the goodness is inherited from OccurrenceQuerySetFN

class OccurrenceManagerType(type):
    """
    Injects proxies for all the queryset's functions into the Manager
    """
    @staticmethod
    def _fproxy(name):
        def f(self, *args, **kwargs):
            return getattr(self.get_query_set(), name)(*args, **kwargs)
        return f

    def __init__(cls, *args):
        for fname in dir(OccurrenceQuerySetFN):
            if not fname.startswith("_"):
                setattr(cls, fname, OccurrenceManagerType._fproxy(fname))
        super(OccurrenceManagerType, cls).__init__(*args)

class OccurrenceManager(models.Manager):    
    __metaclass__ = OccurrenceManagerType

    def get_query_set(self): 
        return OccurrenceQuerySet(self.model)

class OccurrenceModelBase(ModelBase):

    def __new__(meta, class_name, bases, class_dict):
        """
        Create subclasses of GeneratorModel. This:
         - registers signals for when related occurrences are saved or deleted.
        """
        cls = super(OccurrenceModelBase, meta).__new__(meta, class_name, bases, class_dict)
                
        try:
            OccurrenceModel
        except NameError:
            # We're defining the base class right now, so don't do anything
            # We only want to add this stuff to the subclasses.
            # (Otherwise if field names are customized, we'll end up adding two
            # copies)
            pass
        else:
            # Set up signal receivers
            pass
            
        signals.pre_delete.connect(cls._pre_delete, sender=cls)
        return cls

class OccurrenceModel(models.Model):
    """
    An abstract model for an event occurrence.
    
    Implementing subclasses should define 'event' ForeignKey to an EventModel subclass. The related_name for the ForeignKey should be 'occurrences'.

    event = models.Foreignkey(SomeEvent, related_name="occurrences")
    """
    __metaclass__ = OccurrenceModelBase
    start = models.DateTimeField(db_index=True)
    end = models.DateTimeField(blank=True, db_index=True)

    objects = OccurrenceManager()
    
    class Meta:
        abstract = True
        ordering = ('start', 'end',)
        unique_together = ('event', 'start')

    def clean(self):
        if self.end is None:
            self.end = self.start
        
        if self.start > self.end:
            raise ValidationError('start must be earlier than end')
        super(OccurrenceModel, self).clean()

    def save(self, *args, **kwargs):
        if self.end is None:
            self.end = self.start

        self.start = datetimeify(self.start, clamp="min")
        self.end = datetimeify(self.end, clamp="max")
        if self.end.time == time.min:
            self.end.time == time.max

        if self.start > self.end:
            raise AttributeError('start must be earlier than end')
        
        #if i'm being detached from the generator, add the old time to the generator's exceptions.
        #TODO: add the new time if self.start is in exceptions and durations are equal
        if hasattr(self, 'generator') and self.pk:
            saved_self = type(self).objects.get(pk=self.pk)
            if self.generator != saved_self.generator:
                saved_self.generator.add_exception(saved_self.start)

            if self.generator is not None and self.generator.is_exception(self.start):
                if self.duration == self.generator.event_duration:
                    self.generator.remove_exception(self.start)

        super(OccurrenceModel, self).save(*args, **kwargs)

    @staticmethod #connected in the metaclass
    def _pre_delete(sender, **kwargs):
        occ = kwargs['instance']
        if hasattr(occ, 'generator') and occ.generator is not None:
            occ.generator.add_exception(occ.start)
       
    def __unicode__(self):
        return u"%s: %s" % (self.event, self.timespan_description())
        
    @classmethod
    def Event(cls):
        return cls._meta.get_field('event').rel.to
    
    @property
    def duration(self):
        return self.end - self.start
        
    @property
    def relative_duration(self):
        return relativedelta(self.end, self.start)

    @property
    def all_day(self):
        return self.start.time() == time.min and self.end.time() == time.max
    
    def timespan_description(self, html=False):
        if html:
            return mark_safe(pprint_datetime_span(self.start, self.end,
                infer_all_day=False,
                space="&nbsp;", 
                date_range_str="&ndash;", 
                time_range_str="&ndash;", 
                separator=":", 
                grand_range_str="&nbsp;&ndash;&nbsp;",
            ))
        return mark_safe(pprint_datetime_span(self.start, self.end, infer_all_day=False))

    def html_timespan(self):
        return self.timespan_description(html=True)
        
    def time_description(self, html=False):
        if self.all_day:
            return mark_safe(_("all day"))
        
        t1 = self.start.time()
        if self.start.date() == self.end.date():
            t2 = self.end.time()
        else:
            t2 = t1
        
        if html:
            return mark_safe(pprint_time_span(t1, t2, range_str="&ndash;&#8203;"))
        return pprint_time_span(t1, t2)
        
    def html_time_description(self):
        return self.time_description(html=True)

    @property
    def has_finished(self):
        return self.end < datetime.now()
        
    @property
    def has_started(self):
        return self.start < datetime.now()
        
    @property
    def now_on(self):
        return self.has_started and not self.has_finished
        
    def time_to_go(self):
        """
        If self is in future, return + timedelta.
        If self is in past, return - timedelta.
        If self is now on, return None
        """
        if not self.has_started:
            return self.start - datetime.now()
        if self.has_finished:
            return self.end - datetime.now()
        return None

    def relative_time_to_go(self):
        """
        If self is in future, return + timedelta.
        If self is in past, return - timedelta.
        If self is now on, return None
        """
        if not self.has_started:
            return relativedelta(self.start, datetime.now())
        if self.has_finished:
            return relativedelta(self.end, datetime.now())
        return None

    def start_date(self):
        return self.start.date()

    def humanised_day(self):
        if self.start.date() == date.today():
            return _("Today")
        elif self.start.date() == date.today() + timedelta(days=1):
            return _("Tomorrow")
        elif self.start.date() < date.today() + timedelta(days=7):
            return format(self.start, "l")
        else:
            return format(self.start, "m d")
        
    def get_absolute_url(self):
        return reverse('occurrence', kwargs={'occurrence_id': self.id })

    def _resolve_attr(self, attr):
        v = getattr(self, attr, None)
        if v is not None:
            if callable(v):
                v = v()
        return v
    
    def ical_summary(self):
        return unicode(self.event)
    
    def as_icalendar(self,
        ical,
        request,
        summary_attr='ical_summary',
        description_attr='ical_description',
        url_attr='get_absolute_url',
        location_attr='venue_description',
        latitude_attr='latitude',
        longitude_attr='longitude',
        cancelled_attr='is_cancelled',
    ):
        """
        Returns the occurrence as an iCalendar object.
        
        Pass in an iCalendar, and this function will add `self` to it, otherwise it will create a new iCalendar named `calname` described `caldesc`.
        
        The property parameters passed indicate properties of an Event that return the info to be shown in the ical.
        
        location_property is the string describing the location/venue.
        
        Props to Martin de Wulf, Andrew Turner, Derek Willis
        http://www.multitasked.net/2010/jun/16/exporting-schedule-django-application-google-calen/
        
        
        """
        vevent = ical.add('vevent')
        
        start = self.start
        end = self.end
        
        if self.all_day:            
            vevent.add('dtstart').value = start.date()
            vevent.add('dtend').value = end.date()
        else:
            # Add the timezone specified in the project settings to the event start
            # and end datetimes, if they don't have a timezone already
            if not start.tzinfo and not end.tzinfo \
                    and getattr(settings, 'TIME_ZONE', None):
                tz = gettz(settings.TIME_ZONE)
                start = start.replace(tzinfo=tz)
                end = end.replace(tzinfo=tz)
                # Since Google Calendar (and probably others) can't handle timezone
                # declarations inside ICS files, convert to UTC before adding.
                start = start.astimezone(utc)
                end = end.astimezone(utc)
            vevent.add('dtstart').value = start
            vevent.add('dtend').value = end
        
        cancelled = self._resolve_attr(cancelled_attr)
        if cancelled:
            vevent.add('method').value = 'CANCEL'
            vevent.add('status').value = 'CANCELLED'
                
        summary = self._resolve_attr(summary_attr)
        if summary:
            vevent.add('summary').value = summary
        
        description = self._resolve_attr(description_attr)
        if description:
            vevent.add('description').value = description
        
        url = self._resolve_attr(url_attr)
        if url:
            domain = "".join(('http', ('', 's')[request.is_secure()], '://', request.get_host()))
            vevent.add('url').value = "%s%s" % (domain, url)
        
        location = self._resolve_attr(location_attr)
        if location:
            vevent.add('location').value = location
            
        lat = self._resolve_attr(latitude_attr)
        lon = self._resolve_attr(longitude_attr)
        if lat and lon:
            vevent.add('geo').value = "%s;%s" % (lon, lat)
            
        return ical 

    def ics_url(self):
        """
        Needs to be fully-qualified (for sending to calendar apps). Your app needs to define
        an 'ics_for_occurrence' url, and properties for populating an ics for each event
        (see OccurrenceModel.as_icalendar)
        """
        return django_root_url() + reverse("ics_for_occurrence", args=[self.pk])

    def webcal_url(self):
        return self.ics_url().replace("http://", "webcal://").replace("https://", "webcal://")
        
    def gcal_url(self):
        return  "http://www.google.com/calendar/render?cid=%s" % urlencode(self.ics_url())