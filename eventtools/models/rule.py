from datetime import timedelta
from dateutil import rrule

from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _


# The deltas don't need to be particularly precise, the minimum length will do
FREQUENCIES = (
    ("YEARLY", _("Yearly"), timedelta(365)),
    ("MONTHLY", _("Monthly"), timedelta(28)),
    ("WEEKLY", _("Weekly"), timedelta(7)),
    ("DAILY", _("Daily"), timedelta(1)),
    ("HOURLY", _("Hourly"), timedelta(hours=1)),
)

# The first two columns of the above to use as field choices
FREQUENCY_CHOICES = zip(*zip(*FREQUENCIES)[:2])
# A mapping of field value to corresponding minimum timespan
FREQUENCY_TIME_MAP = dict((f[0], f[2]) for f in FREQUENCIES)
# For backwards compatibility
freqs = FREQUENCY_CHOICES


class Rule(models.Model):
    """
    This defines a rule by which an occurrence will repeat.  This is defined by the
    rrule in the dateutil documentation.

    * name - the human friendly name of this kind of repetition.
    * frequency - the base repetition period
    * param - extra params required to define this type of repetition. The params
      should follow this format:

        param = [rruleparam:value;]*
        rruleparam = see list below
        value = int[,int]*

      The options are: (documentation for these can be found at
      http://labix.org/python-dateutil#head-470fa22b2db72000d7abe698a5783a46b0731b57)
        ** count
        ** bysetpos
        ** bymonth
        ** bymonthday
        ** byyearday
        ** byweekno
        ** byweekday
        ** byhour
        ** byminute
        ** bysecond
        ** byeaster
    """
    name = models.CharField(_("name"), max_length=100, help_text=_("a short friendly name for this repetition."))
    common = models.BooleanField(help_text=_("common rules appear at the top of the list."))
    frequency = models.CharField(_("frequency"), choices=FREQUENCY_CHOICES, max_length=10, blank=True, help_text=_("the base repetition period."))
    params = models.TextField(_("inclusion parameters"), blank=True, help_text=_("extra params required to define this type of repetition."))
    complex_rule = models.TextField(_("complex rules"), help_text=_("over-rides all other settings."), blank=True)

    class Meta:
        verbose_name = _('repetition rule')
        verbose_name_plural = _('repetition rules')
        ordering = ('-common', 'name')
        app_label = "eventtools"

    def get_params(self):
        """
        >>> rule = Rule(params = "count:1;bysecond:1;byminute:1,2,4,5")
        >>> rule.get_params()
        {'count': 1, 'byminute': [1, 2, 4, 5], 'bysecond': 1}
        """
    	params = self.params
        if params is None:
            return {}
        params = params.split(';')
        param_dict = []
        for param in params:
            param = param.split(':')
            if len(param) == 2:
                param = (str(param[0]), [int(p) for p in param[1].split(',')])
                if len(param[1]) == 1:
                    param = (param[0], param[1][0])
                param_dict.append(param)
        return dict(param_dict)
        
    def __unicode__(self):
        """Human readable string for Rule"""
        return self.name or unicode(self.frequency).lower()

    def get_rrule(self, dtstart):
        if self.complex_rule:
            try:
                return rrule.rrulestr(str(self.complex_rule), dtstart=dtstart)
            except: #Except what?
                pass
        params = self.get_params()
        frequency = 'rrule.%s' % self.frequency
        simple_rule = rrule.rrule(eval(frequency), dtstart=dtstart, **params)
        rs = rrule.rruleset()
        rs.rrule(simple_rule)
        return rs
