from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import HttpResponseRedirect, Http404
import datetime
from django.core import urlresolvers
from eventtools.periods import Month
from django.utils.translation import ugettext as _

def occurrences(request, id, modeladmin):
    
    EventModel = modeladmin.model
    
    event = EventModel.objects.get(pk=id)
    
    hasnext = False
    hasprev = False
    period = None
    occurrences = event.get_all_occurrences_if_possible()
    if not occurrences:
        generators = event.generators.all()
        first = event.get_first_occurrence().start
        last = event.get_last_occurrence()
        
        if 'year' in request.GET and 'month' in request.GET: # month is specified by user
            period = Month(generators, datetime.datetime(int(request.GET.get('year')),int(request.GET.get('month')),1))
        else: # we need to give a sane default month
            now = datetime.datetime.now()
            if first > now: # first occurrence is in future
                period = Month(generators, first)
            elif last < now: # occurrences are all in past
                period = Month(generators, last)
            else:
                period = Month(generators, now)
        hasprev = first < period.start
        if not last:
            hasnext = True
        else:
            hasnext = last > period.end
        occurrences = period.get_even_hidden_occurrences()
    title = _("Select an occurrence to change")
    
    admin_url_name = ('admin:%s_%s_change' % (EventModel._meta.app_label, event.OccurrenceModel.__name__)).lower()
    occ_change_url = urlresolvers.reverse(admin_url_name, args=(0,))[:-3] # we don't want a real parameter yet, so strip off the last /0/
    
    return render_to_response('admin/eventtools/list_occurrences.html', {"event": event, 'occurrences': occurrences, 'period': period, 'hasprev': hasprev, 'hasnext': hasnext, 'title': title, 'occ_change_url': occ_change_url, 'opts': EventModel._meta }, context_instance=RequestContext(request))

def make_exceptional_occurrence(request, event_id, gen_id, year, month, day, hour, minute, second, modeladmin):
    
    
    EventModel = modeladmin.model  
    event = EventModel.objects.get(pk=int(event_id))
        
    # import pdb; pdb.set_trace()
    generator = get_object_or_404(event.GeneratorModel, id=int(gen_id))
    occurrence = generator.get_occurrence(datetime.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second)))

    occurrence.save()
    OccurrenceModel = occurrence.__class__
    admin_url_name = ('admin:%s_%s_change' % (OccurrenceModel._meta.app_label, OccurrenceModel.__name__)).lower()
    event_change_url = urlresolvers.reverse(admin_url_name, args=(occurrence.id,))
    return HttpResponseRedirect(event_change_url)
