import datetime

from django.db import models
from django.utils.translation import ugettext as _
from eventtools.utils import datetimeify
from eventtools.utils.datetimeify import dayify
from eventtools.utils.managertype import ManagerType
from eventtools.utils.pprint_timespan import pprint_datetime_span, pprint_time_span
from django.utils.safestring import mark_safe
from django.utils.timezone import now, localtime, make_aware, \
    get_default_timezone, is_naive

class XTimespanQSFN(object):
    """
    All the query functions are defined here, so they can be easily introspected
    and injected by the OccurrenceManagerType metaclass.
    """

    def starts_before(self, date):
        end = datetimeify(date, clamp="max")
        if is_naive(end):
            end = make_aware(end, get_default_timezone())
        return self.filter(start__lte=end)
    def starts_after(self, date):
        start = datetimeify(date, clamp="min")
        if is_naive(start):
            start = make_aware(start, get_default_timezone())
        return self.filter(start__gte=start)
    def starts_between(self, d1, d2):
        """
        returns the occurrences that start in a given date/datetime range.
        """
        return self.starts_after(d1).starts_before(d2)

    def starts_on(self, day):
        d1, d2 = dayify(day)
        return self.starts_between(d1, d2)

    #defaults - implementers may wish to override with other kinds of queries
    before = starts_before
    after = starts_after
    between = starts_between
    on = starts_on

    #misc queries (note they assume starts_)
    def forthcoming(self):
        return self.starts_after(now())

    def recent(self):
        return self.starts_before(now())

class XTimespanQuerySet(models.query.QuerySet, XTimespanQSFN):
    pass #all the goodness is inherited from XTimespanQSFN

class XTimespanManager(models.Manager):
    __metaclass__ = ManagerType(XTimespanQSFN)

    def get_query_set(self):
        return XTimespanQuerySet(self.model)


class XTimespanModel(models.Model):
    start = models.DateTimeField(db_index=True, verbose_name=_('start'))
    _duration = models.PositiveIntegerField(_("duration (mins)"), blank=True, null=True, help_text=_("to create 'all day' events, set start time to 00:00 and leave duration blank"))

    objects = XTimespanManager()

    class Meta:
        abstract = True
        ordering = ('start', )

    def get_duration(self):
        """
        _duration is a value in minutes. The duration property returns a 
        timedelta representing this.
        """
        if self._duration:
            return datetime.timedelta(seconds = self._duration * 60)
        else:
            return datetime.timedelta(0)

    def set_duration(self, v):
        """
        Pass in a timedelta to convert to minutes; pass in something else to set directly.
        """
        if isinstance(v, datetime.timedelta):
            self._duration = v.days * 24 * 60 + v.seconds / 60
        else:
            self._duration = v

    duration = property(get_duration, set_duration)

    def duration_string(self):
        """
        Prints out the duration in plain-ish English.
        *cough* internationalisation *cough*
        """
        if self.all_day():
            return u"all day"
        d = self.duration
        result = []
        if d.days:
            plural = "" if d.days == 1 else "s"
            result.append("%s day%s" % (d.days, plural))
        if d.seconds:
            num_hours = d.seconds / 3600
            remaining_seconds = d.seconds - (3600 * num_hours)

            if num_hours:
                plural = "" if num_hours == 1 else "s"
                result.append("%s hour%s" % (num_hours, plural))

            num_minutes = remaining_seconds / 60
            if num_minutes:
                plural = "" if num_minutes == 1 else "s"
                result.append("%s min%s" % (num_minutes, plural))

        return " ".join(result)

    def end(self):
        return self.start + self.duration

    def all_day(self):
        """
        WARNING: the implementation of 'all day' may change, for example by 
        making it a BooleanField. If this is important to you, define it 
        yourself.

        By default, an event is 'all day' if the start time is time.min 
        (ie midnight) and the duration is not provided.

        'All day' is distinguished from events that last 24 hours, because 
        there is a reader assumption that opening hours are taken into account.

        Implementers may prefer their own definition, maybe adding a 
        BooleanField that overrides the given times.
        """
        return localtime(self.start).time() == datetime.time.min and not self._duration

    def timespan_description(self, html=False):
        start = localtime(self.start)
        end = localtime(self.end())
        if html:
            return mark_safe(pprint_datetime_span(start, end,
                infer_all_day=False,
                space="&nbsp;",
                date_range_str="&ndash;",
                time_range_str="&ndash;",
                separator=":",
                grand_range_str="&nbsp;&ndash;&nbsp;",
            ))
        return mark_safe(pprint_datetime_span(start, end, infer_all_day=False))

    def html_timespan(self):
        return self.timespan_description(html=True)

    def time_description(self, html=False, *args, **kwargs):
        start = localtime(self.start)
        end = localtime(self.end())
        if self.all_day():
            return mark_safe(_("all day"))

        t1 = start.time()
        if start.date() == end.date():
            t2 = end.time()
        else:
            t2 = t1

        if html:
            return mark_safe(pprint_time_span(t1, t2, range_str="&ndash;&#8203;", *args, **kwargs))
        return pprint_time_span(t1, t2, *args, **kwargs)

    def html_time_description(self):
        return self.time_description(html=True)

    def is_finished(self):
        return self.end() < now()

    def is_started(self):
        return self.start < now()

    def now_on(self):
        return self.is_started() and not self.is_finished()

    def time_to_go(self):
        """
        If self is in future, return + timedelta.
        If self is in past, return - timedelta.
        If self is now on, return timedelta(0)
        """
        if not self.is_started():
            return self.start - now()
        if self.is_finished():
            return self.end() - now()
        return datetime.timedelta(0)

    def start_date(self):
        """Used for regrouping in template"""
        return self.start.date()

    def humanised_day(self):
        if self.start.date() == now().date():
            return _("Today")
        elif self.start.date() == now().date() + datetime.timedelta(days=1):
            return _("Tomorrow")
        elif self.start.date() == now().date() - datetime.timedelta(days=1):
            return _("Yesterday")
        return self.start.strftime("%A, %d %B %Y")

"""
TODO:

timespan +/ timedelta = new timespan
"""
