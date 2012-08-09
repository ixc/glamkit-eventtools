from datetime import date
from django.db import models
from eventtools.utils.pprint_timespan \
    import pprint_datetime_span, pprint_date_span
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext, ugettext_lazy as _

class SeasonQSFN(object):
    def current_on(self, date):
        return self.filter(start__lte=date, end__gte=date)
        
    def forthcoming_on(self, date):
        return self.filter(start__gt=date)
        
    def previous_on(self, date):
        return self.filter(end__lt=date)

class SeasonQuerySet(models.query.QuerySet, SeasonQSFN):
    pass #all the goodness is inherited from SeasonQSFN

class SeasonManagerType(type):
    """
    Injects proxies for all the queryset's functions into the Manager
    """
    @staticmethod
    def _fproxy(name):
        def f(self, *args, **kwargs):
            return getattr(self.get_query_set(), name)(*args, **kwargs)
        return f

    def __init__(cls, *args):
        for fname in dir(SeasonQSFN):
            if not fname.startswith("_"):
                setattr(cls, fname, SeasonManagerType._fproxy(fname))
        super(SeasonManagerType, cls).__init__(*args)

class SeasonManager(models.Manager):    
    __metaclass__ = SeasonManagerType

    def get_query_set(self): 
        return SeasonQuerySet(self.model)


class XSeasonModel(models.Model):
    """
    Describes an entity which takes place between start and end dates. For
    example, a festival or exhibition.
    
    The fields are optional - both omitted means 'ongoing'.
    """

    start = models.DateField(null=True, blank=True, verbose_name=_('start'))
    end = models.DateField(null=True, blank=True, verbose_name=_('end'))
    
    objects = SeasonManager()

    class Meta:
        abstract = True
        
    def clean(self):
        if (self.start is not None and self.end is None) or \
            (self.end is not None and self.start is None):
            raise ValidationError('Start and End must both be provided, or blank')

        if self.start > self.end:
            raise ValidationError('Start must be earlier than End')
            
    def season(self):
        """
        Returns a string describing the first and last dates of this event.
        """        
        if self.start and self.end:
            first = self.start
            last = self.end
        
            return pprint_date_span(first, last)
        
        return None
        
    def __unicode__(self):
        return self.season()

    def is_finished(self):
        return self.end < date.today()
