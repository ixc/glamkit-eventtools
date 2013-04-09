from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _

freqs = (
    ("YEARLY", _("Yearly")),
    ("MONTHLY", _("Monthly")),
    ("WEEKLY", _("Weekly")),
    ("DAILY", _("Daily")),
    ("HOURLY", _("Hourly")),
)

class Rule(models.Model):
    """
    This defines a rule by which an event will repeat.  This is defined by the
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
    frequency = models.CharField(_("frequency"), choices=freqs, max_length=10, blank=True, help_text=_("the base repetition period."))
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
        return self.name
        
    def normalize(self):
        return self.complex_rule or "FREQ=%s;%s" % (self.frequency, self.params.upper())

