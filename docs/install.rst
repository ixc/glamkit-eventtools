.. _ref-install:

================
Getting The Code
================

The project is available through `Github <http://github.com/glamkit/glamkit-events/tree>`_.

.. _ref-configure:

=============
Configuration
=============

1. Add ``eventtools`` to your ``INSTALLED_APPS``

2. Add ``(r'^events/', include('events.urls')),`` to your urls.py (changing ``r`^events/'`` to whatever url pattern you'd like glamkit-events to live at)

3. Resync your database ``./manage.py syncdb``
 





Installation
------------

Download the code; put it into your project's directory or run ``python setup.py install`` to install system-wide.

REQUIREMENTS: python-vobject (comes with most distribution as a package).

Settings.py
-----------

REQUIRED
^^^^^^^^

`INSTALLED_APPS` - add: 
    'events',

`TEMPLATE_CONTEXT_PROCESSORS` - add:
    "django.core.context_processors.request",

Optional
^^^^^^^^

`FIRST_DAY_OF_WEEK`

This setting determines which day of the week your calendar begins on if your locale doesn't already set it. Default is 0, which is Sunday.

`OCCURRENCE_CANCEL_REDIRECT`

This setting controls the behaviour of :func:`Views.get_next_url`. If set, all calendar modifications will redirect here (unless there is a `next` set in the request.)

`SHOW_CANCELLED_OCCURRENCES`

This setting controls the behaviour of :func:`Period.classify_occurence`. If True, then occurrences that have been cancelled will be displayed with a CSS class of cancelled, otherwise they won't appear at all.

Defaults to False

