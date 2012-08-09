# -*- coding: utf-8 -*-


from django.db import models, transaction
from django.db.models.base import ModelBase
from django.utils.translation import ugettext, ugettext_lazy as _
from django.core import exceptions

from dateutil import rrule
from eventtools.models.xtimespan import XTimespanModel

from eventtools.conf import settings
from eventtools.utils.pprint_timespan import (
    pprint_datetime_span, pprint_date_span)

from datetime import date, time, datetime, timedelta

class GeneratorModel(XTimespanModel):
    """
    Stores information about repeating Occurrences, and generates them,
    unless they already exist, or match an Exception.
    
    The public API is quite simple:
    
    save() generates Occurrences.
    
    clean() makes sure the Generator has valid values (and is called by admin
    before the instance is saved)
       
    robot_description() attempts to provide an English description of this
    generator. It's not great at the moment and might be replaced or deprecated
    in favour of a hand-written description in the Event.
    
    EventModel() returns the Model of the Event that this Generator links to.
    """

    #define a FK called 'event' in the subclass
    rule = models.ForeignKey("eventtools.Rule", verbose_name=_('rule'))
    repeat_until = models.DateField(
        null=True, blank = True,
        verbose_name=_('repeat until'),
        help_text=_(u"Occurrences will repeat up to and including this date. If ommitted, the next year's worth of "
            "occurrences will be created."
        )
    )

    class Meta:
        abstract = True
        ordering = ('start',)
        verbose_name = _("repeating occurrence")
        verbose_name_plural = _("repeating occurrences")

    def __unicode__(self):
        return u"%s, %s" % (self.event, self.robot_description())
        
    @classmethod
    def EventModel(cls):
        return cls._meta.get_field('event').rel.to
        
    def clean(self, ExceptionClass=exceptions.ValidationError):
        super(GeneratorModel, self).clean()
        if not self.rule_id:
            raise ExceptionClass('A Rule must be given')
    
        if self.start and self.repeat_until and self.repeat_until < self.start.date():
            raise ExceptionClass(
                'Repeat until date must not be earlier than start date')
            
        self.is_clean = True

    @transaction.commit_on_success()
    def save(self, *args, **kwargs):
        """
        Generally (and for a combination of field changes), we take a
        two-pass approach:
    
         1) First update existing occurrences to match update-compatible fields.
         2) Then synchronise the candidate occurrences with the existing
            occurrences.
            * For candidate occurrences that exist, do nothing.
            * For candidate occurrences that do not exist, add them.
            * For existing occurrences that are not candidates, unhook them from
                the generator.

        Finally, we also update other generators, because they might have had
        clashing occurrences which no longer clash.
        """
        
        cascade = kwargs.pop('cascade', True)
        
        if not getattr(self, 'is_clean', False):
            # if we're saving directly, the ModelForm clean isn't called, so
            # we do it here.
            self.clean(ExceptionClass=AttributeError)
        
        # Occurrences updates/generates
        if self.pk:
            self._update_existing_occurrences() # need to do this before save, so we can detect changes
        r = super(GeneratorModel, self).save(*args, **kwargs)
        self._sync_occurrences() #need to do this after save, so we have a pk to hang new occurrences from.
    
        # finally, we should also update other generators, because they might 
        # have had clashing occurrences
        if cascade:
            for generator in self.event.generators.exclude(pk=self.pk):
                generator.save(cascade=False)
        
        return r
        
    def _generate_dates(self):
        rule = self.rule.get_rrule(dtstart=self.start)
        date_iter = iter(rule)
        drop_dead_date = datetime.combine(self.repeat_until or date.today() \
            + settings.DEFAULT_GENERATOR_LIMIT, time.max)
                
        while True:
            d = date_iter.next()
            if d > drop_dead_date:
                break
            yield d
    
    @transaction.commit_on_success()
    def _update_existing_occurrences(self):
        """
        When you change a generator and save it, it updates existing occurrences
        according to the following rules:
        
        Generally, if we can't automatically delete occurrences, we unhook them
        from the generator, and make them one-off. This is to prevent losing
        information like tickets sold or shout-outs (we leave implementors to
        decide the workflow in these cases). We want to minimise the number of
        events that are deleted or unhooked, however. So:
    
         * If start time or duration is changed, then no occurrences are
           added or removed - we timeshift all occurrences. We assume that
           visitors/ticket holders are alerted to the time change elsewhere.
    
         * If other fields are changed - repetition rule, repeat_until, start
           date - then there is a chance that Occurrences will be added or
           removed.
    
         * Occurrences that are added are fine, they are added in the normal
           way.
           
         * Occurrences that are removed are deleted or unhooked, for reasons
           described above.
        """
        
        """
        Pass 1)
        if start date or time is changed:
            update the start times of my occurrences
        if end date or time is changed:
            update the end times of my occurrences

        Pass 2 is in _sync_occurrences, below.
        """
        
        # TODO: it would be ideal to minimise the consequences of shifting one
        # occurrence to replace another - ie to leave most occurrences untouched 
        # and to create only new ones and unhook ungenerated ones.
        # I tried this by using start date (which is unique per generator) as
        # a nominal 'key', but it gets fiddly when you want to vary the end
        # date to before the old start date. For now we'll just update the dates
        # and times.

        saved_self = type(self).objects.get(pk=self.pk)
        
        start_shift = self.start - saved_self.start
        duration_changed = self._duration != saved_self._duration

        if start_shift or duration_changed:
            # Update occurrences in opposite direction to the adjustment of the
            # 'start' field, to avoid updating an occurrence to clash with an
            # existing one's (event_id, start) DB uniqueness constraint (#606)
            if start_shift.total_seconds() >= 0:
                start_order_by = '-start'  # Moving to future, start from latest
            else:
                start_order_by = 'start'  # Moving to past, start from earliest

            for o in self.occurrences.order_by(start_order_by):
                o.start += start_shift
                o._duration = self._duration
                o.save()

    
    @transaction.commit_on_success()
    def _sync_occurrences(self):
    
        """
        Pass 2)

        Generate a list of candidate occurrences.
        * For candidate occurrences that exist, do nothing.
        * For candidate occurrences that do not exist, add them.
        * For existing occurrences that are not candidates, delete them, or unhook them from the
          generator if they are protected by a Foreign Key.
            
        In detail:
        Get a list, A, of already-generated occurrences.
        
        Generate candidate Occurrences.
        For each candidate Occurrence:
            if it exists for the event:
                if I created it, unhook, and remove from the list A.
                else do nothing
            if it is an exclusion, do nothing
            otherwise create it.
            
        The items remaining in list A are 'orphan' occurrences, that were
        previously generated, but would no longer be. These are unhooked from
        the generator.
        """
        
        all_occurrences = self.event.occurrences_in_listing().all() #regardless of generator
        existing_but_not_regenerated = set(self.occurrences.all()) #generated by me only

        for start in self._generate_dates():
            # if the proposed occurrence exists, then don't make a new one.
            # However, if it belongs to me: 
            #       and if it is marked as an exclusion:
            #           do nothing (it will later get deleted/unhooked)
            #       else:
            #           remove it from the set of existing_but_not_regenerated
            #           occurrences so it stays hooked up

            try:
                o = all_occurrences.filter(start=start)[0]
                if o.generated_by == self:
                    if not o.is_exclusion():
                        existing_but_not_regenerated.discard(o)
                continue
            except IndexError:
                # no occurrence exists yet.
                pass

            # if the proposed occurrence is an exclusion, don't save it.
            if self.event.exclusions.filter(
                event=self.event, start=start
            ).count():
                continue            

            #OK, we're good to create the occurrence.
            o = self.occurrences.create(event=self.event, start=start, _duration=self._duration)
#            print "created %s" % o
            #implied generated_by = self
    
        # Finally, delete any unaccounted_for occurrences. If we can't delete, due to protection set by FKs to it, then
        # unhook it instead.
        for o in existing_but_not_regenerated:
#            print "deleting %s" % o
            o.delete()

    def delete(self, *args, **kwargs):
        """
        If I am deleted, then cascade to my Occurrences, UNLESS there is is something FKed to them that is protecting them,
        in which case the FK is set to NULL.
        """
        for o in self.occurrences.all():
            o.delete()

        super(GeneratorModel,self).delete(*args, **kwargs)

    def robot_description(self):
        r = "%s, repeating %s" % (
            pprint_datetime_span(self.start, self.end()),
            unicode(self.rule).lower(),
        )
        
        if self.repeat_until:
            r += " until %s" % pprint_date_span(self.repeat_until, self.repeat_until)
            
        return r
