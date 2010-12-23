# −*− coding: UTF−8 −*−
from datetime import datetime, date, time

def datetimeify(d, clamp="start"):
    if isinstance(d, datetime):
        return d
    if clamp.lower()=="end":
        return datetime.combine(d, time.max)
    return datetime.combine(d, time.min)

def dateify(d):
    if isinstance(d, datetime):
        return d.date()
    return d


class MergedObject():
    """
    Objects of this class behave as though they are a merge of two other objects (which we'll call General and Special). The attributes of Special override the corresponding attributes of General, *unless* the value of the attribute in Special == None.
    
    All attributes are read-only, to save you from a world of pain.
    
    """

    def __init__(self, general, special):
        self._general = general
        self._special = special
        
    def __getattr__(self, value):
        
        try:
            result = getattr(self._special, value)
            if result == None:
                raise AttributeError
        except AttributeError:
            result = getattr(self._general, value)

        return result
        
    def __setattr__(self, attr, value):
        if attr in ['_general', '_special']:
            self.__dict__[attr] = value
        else:
            raise AttributeError("Set the attribute on one of the objects that are being merged.")
    
def occurrences_to_events(occurrences):
    """ returns a list of events pertaining to these occurrences, maintaining order """
    event_ids = []
    events = []
    for occurrence in occurrences:
        # import pdb; pdb.set_trace()
        if occurrence.unvaried_event.id not in event_ids: #just testing the id saves database lookups (er, maybe)
            event_ids.append(occurrence.unvaried_event.id)
            events.append(occurrence.unvaried_event)
    return events

def occurrences_to_event_qs(occurrences):
    """ returns a qs of events pertaining to these occurrences. Order is lost. """
    if occurrences:
        event_ids = [o.unvaried_event.id for o in occurrences]
        return type(occurrences[0].unvaried_event).objects.filter(id__in=event_ids)
    return None
    
    events = []
    for occurrence in occurrences:
        # import pdb; pdb.set_trace()
        if occurrence.unvaried_event.id not in event_ids: #just testing the id saves database lookups (er, maybe)
            event_ids.append(occurrence.unvaried_event.id)
            events.append(occurrence.unvaried_event)
    return events
