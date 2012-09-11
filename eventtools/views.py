from dateutil.relativedelta import relativedelta

from django.conf.urls.defaults import *
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext
from django.utils.safestring import mark_safe

from eventtools.conf import settings
from eventtools.utils.pprint_timespan import humanized_date_range
from eventtools.utils.viewutils import paginate, response_as_ical, parse_GET_date

import datetime


class EventViews(object):

    # Have currently disabled icals.

    """
    use Event.eventobjects.all() for event_qs.

    It will get filtered to .in_listings() where appropriate.
    """

    def __init__(self, event_qs, occurrence_qs=None):
        self.event_qs = event_qs

        if occurrence_qs is None:
            occurrence_qs = self.event_qs.occurrences()
        self.occurrence_qs = occurrence_qs

    @property
    def urls(self):
        from django.conf.urls.defaults import patterns, url

        return (
            patterns('',
                url(r'^$', self.index, name='index'),
                url(r'^signage/$', self.signage, name='signage'),
                url(r'^signage/(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})/$',
                    self.signage_on_date, name='signage_on_date'),
                url(r'^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$', self.on_date, name='on_date'),
                url(r'^(?P<event_slug>[-\w]+)/$', self.event, name='event'),
                url(r'^(?P<event_slug>[-\w]+)/(?P<occurrence_pk>[\d]+)/$', self.occurrence, name='occurrence'),

                #ical - needs rethinking
                url(r'^ical\.ics$', self.occurrence_list_ical, name='occurrence_list_ical'),
                url(r'^(?P<event_slug>[-\w]+)/ical\.ics$', self.event_ical, name='event_ical'),
                # url(r'^(?P<event_slug>[-\w]+)/(?P<occurrence_id>\d+)/ical\.ics$', \
                  # self.occurrence_ical, name='occurrence_ical'),
            ),
            "events", # application namespace
            "events", # instance namespace
        )
                    
    def event(self, request, event_slug):
        event = get_object_or_404(self.event_qs, slug=event_slug)
        context = RequestContext(request)
        context['event'] = event

        return render_to_response('eventtools/event.html', context)

    def occurrence(self, request, event_slug, occurrence_pk):
        """
        Returns a page similar to eventtools/event.html, but for a specific occurrence.

        event_slug is ignored, since occurrences may move from event to sub-event, and
        it would be nice if URLs continued to work.
        """

        occurrence = get_object_or_404(self.occurrence_qs, pk=occurrence_pk)
        event = occurrence.event
        context = RequestContext(request)
        context['occurrence'] = occurrence
        context['event'] = event

        return render_to_response('eventtools/event.html', context)


    def event_ical(self, request, event_slug):
        event_context = self._event_context(request, event_slug)
        return response_as_ical(request, event_context['occurrence_pool'])

    #occurrence_list
    def _occurrence_list_context(self, request, qs):
        fr, to = parse_GET_date(request.GET)

        if to is None:
            occurrence_pool = qs.after(fr)
        else:
            occurrence_pool = qs.between(fr, to)

        pageinfo = paginate(request, occurrence_pool)

        return {
            'bounded': False,
            'pageinfo': pageinfo,
            'occurrence_pool': occurrence_pool,
            'occurrence_page': pageinfo.object_list,            
            'day': fr,
            'occurrence_qs': qs,
        }
        
    
    def occurrence_list(self, request): #probably want to override this for doing more filtering.
        template = 'eventtools/occurrence_list.html'
        context = RequestContext(request)
        context.update(self._occurrence_list_context(request, self.occurrence_qs))        
        return render_to_response(template, context)
    
    def occurrence_list_ical(self, request):
        occurrence_list_context = self._occurrence_list_context(request, self.occurrence_qs)
        pool = occurrence_list_context['occurrence_pool']
        return response_as_ical(request, pool)

    def on_date(self, request, year, month, day):
        template = 'eventtools/occurrence_list.html'
        day = datetime.date(int(year), int(month), int(day))
        event_pool = self.occurrence_qs.starts_on(day)

        context = RequestContext(request)
        context['occurrence_pool'] = event_pool
        context['day'] = day
        context['occurrence_qs'] = self.occurrence_qs
        return render_to_response(template, context)

    def today(self, request):
        today = datetime.date.today()
        return self.on_date(request, today.year, today.month, today.day)

    def signage(self, request):
        """
        Render a signage view of events that occur today.
        """
        today = datetime.date.today()
        return self.signage_on_date(request, today.year, today.month, today.day)

    def signage_on_date(self, request, year, month, day):
        """
        Render a signage view of events that occur on a given day.
        """
        template = 'eventtools/signage_on_date.html'
        dt = datetime.date(int(year), int(month), int(day))
        today = datetime.date.today()
        occurrences = self.occurrence_qs.starts_on(dt)

        context = RequestContext(request)
        context['occurrence_pool'] = occurrences
        context['day'] = dt
        context['is_today'] = dt == today
        return render_to_response(template, context)

    def index(self, request):
        # In your subclass, you may prefer:
        # return self.today(request)
        return self.occurrence_list(request)

