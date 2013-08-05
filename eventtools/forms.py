from django import forms
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.utils import simplejson

FORMAT_CHOICES = [
    ('webcal', 'iCal/Outlook'),
    ('google', 'Google Calendar'),
    ('ics', '.ics file'),
]

class ExceptionsWidget(forms.HiddenInput):
    """
    A widget that shows the exceptions JSON data in a user-friendly format.
    """
    is_hidden = False
    
    def render(self, name, value, attrs=None):
        # The form should display a JSON string, but we want to keep working
        # with the original dictionary loaded from the DB value
        form_value = value
        if isinstance(value, dict):
            form_value = simplejson.dumps(value)
        # Add an "event-exceptions" class to the hidden input
        if 'class' in attrs:
            attrs['class'] = '%s event-exceptions' % attrs['class']
        else:
            attrs['class'] = 'event-exceptions'
        # Get the hidden input containing the actual data
        output = super(ExceptionsWidget, self).render(name, form_value, attrs)
        # Generate a user-friendly list of exceptions
        if not value or value == '{}':
            exceptions = [('None', 'none'),]
        else:
            exceptions = value.items()[:10]
            if len(value) > 10:
                exceptions += [('%s more...' % (len(value) - 10), 'clear')]
        # Append the exception list to the hidden input
        output += render_to_string('admin/eventtools/_exception_widget.html',
            {'exceptions': exceptions})
        return output

class OccurrenceChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.html_timespan()
        

class ExportICalForm(forms.Form):
    """
    Form allows user to choose which occurrence (or all), and which format.
    """
    
    event = forms.ModelChoiceField(
        queryset=None,
        widget=forms.HiddenInput,
        required=True,
    ) #needed in case no (all) occurrence is selected.
    occurrence = OccurrenceChoiceField(
        queryset=None,
        empty_label="Save all",
        required=False,
        widget=forms.Select(attrs={'size':10}),
    )
    format = forms.ChoiceField(
        choices=FORMAT_CHOICES,
        required=True,
        widget=forms.RadioSelect,
        initial="webcal",
    )
    
    def __init__(self, event, *args, **kwargs):        
        self.base_fields['event'].queryset = type(event).objects.filter(id=event.id)
        self.base_fields['event'].initial = event.id
        self.base_fields['occurrence'].queryset = event.occurrences.forthcoming()            

        super(ExportICalForm, self).__init__(*args, **kwargs)

        
    def to_ical(self):
        format = self.cleaned_data['format']
        occurrence = self.cleaned_data['occurrence']

        if occurrence:
            if format == 'webcal':
                return HttpResponseRedirect(occurrence.webcal_url())
            if format == 'ics':
                return HttpResponseRedirect(occurrence.ics_url())
            if format == 'google':
                return HttpResponseRedirect(occurrence.gcal_url())
        else:
            event = self.cleaned_data['event']
            if format == 'webcal':
                return HttpResponseRedirect(event.webcal_url())
            if format == 'ics':
                return HttpResponseRedirect(event.ics_url())
            if format == 'google':
                return HttpResponseRedirect(event.gcal_url())


    # <p><a href="{% url occurrence_ical occurrence.id %}">Download .ics file</a></p>
    # <p><a href="{{ occurrence.webcal_url }}">Add to iCal/Outlook</a></p>
            