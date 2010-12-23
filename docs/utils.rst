=========
Utilities
=========

There are some utility classes found in the utils module that help with certain tasks.

EventListManager
----------------

EventListManager objects are instantiated with a list of events. That list of events dictates the following methods

``occurrences_after(after)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Creates a generator that produces the next occurrence inclusively after the datetime ``after``.

OccurrenceReplacer
------------------

If you get more into the internals of Glamkit-events, and decide to create your own method for producing occurrences, instead of using one of the public facing methods for this, you are going to want to replace the default generated occurrence with an exceptional one, if an exceptional occurrence exists in the database.  To facilitate this in a standardised way you have the OccurrenceReplacer class.

To instantiate it you give it the pool of exceptional occurrences you would like to check in.

>>> exceptional_occurrences = my_event.occurrence_set.all()
>>> occ_replacer = OccurrenceReplacer(exceptional_occurrences)

Now you have two convenient methods:

``get_occurrence(occurrence)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This method returns either the passed in occurrence or the equivalent exceptional occurrences from the pool of exceptional occurrences with which this OccurrenceReplacer was instantiated.

>>> # my_generated_occurrence is an occurrence that was programatically
>>> # generated from an event
>>> occurrence = occ_replacer.get_occurrence(my_generated_occurrence)

``has_occurrence(occurrence)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This method returns a boolean. It returns True if the OccurrenceReplacer has an occurrence it would like to replace with the give occurrence, and false if it does not.

>>> hasattr(my_generated_occurrence, 'pk')
False
>>> occ_replacer.has_occurrence(my_generated_occurrence)
True
>>> occurrence = occ_replacer.get_occurrence(my_generated_occurrence)
>>> hasattr(occurrence, 'pk')
True
>>> # Now with my_other_occurrence which does not have a exceptional counterpart
>>> hasattr(my_other_occurrence, 'pk')
False
>>> occ_replacer.has_occurrence(my_other_occurrence)
False
>>> occurrence = occ_replacer.get_occurrence(my_other_occurrence)
>>> hasattr(occurrence, 'pk')
False