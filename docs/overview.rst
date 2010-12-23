=======================
GLAMkit-events Overview
=======================

Different institutions have event calendars of differing complexity. GLAMkit-events attempts to cover all the possible scenarios. Before developing with GLAMkit-events, you should spend some time determining what sort of schedule structure you need to model.


Events, Occurrences and OccurrenceGenerators
--------------------------------------------

GLAMkit-events draws a distinction between **events**, and **occurrences** of those events. **Events** contain all the scheduling information *except* for the times and dates. **Events** know where, why and how things happen, but not when. **OccurrenceGenerators** contain all the *when* information. By combining the two, you can specify individual occurrences of an event. The best way to grasp this is with an example:

    Imagine a museum that has a tour for the blind every Sunday at 2pm. The tour always starts at the same place, costs the same amount etc. The only thing that changes is the date. You can define an event model which has field for storing all the non-time information. By making this model subclass EventBase, you get access to an OccurrenceGenerator which you can use to specify that the tour happens every Sunday at 2pm, and an Occurrence model which handles each specific instance of the tour. This three model structure is handled transparently - you only need to define the event model.
    
This separation into three models allows us to do some very cool things:

* we can specify complex repetition rules (eg. every Sunday at 2pm, unless it happens to be Easter Sunday, or Christmas day);
* we can attach multiple repetition rules to the same event (eg. the same tour might also happen at 11am every weekday, except during December and January);
* we can specify an end date for these repetition rules, or have them repeat infinitely;
* we can cancel or vary the timing of any specific occurrence irrespective of the underlying rules (eg. on Sunday January 17, 2010, the tour starts two hours earlier);
* we can store special one-off information with any occurrence (eg. on Sunday January 24, 2010, the tour includes lunch);
* we can access all this complexity through an intuitive Django admin interface.

Of course we can also handle ‘one-time’ events. These are simply events with an OccurrenceGenerator that only generates one occurrence

Different event structures
--------------------------
Let’s unpack this further by looking at some of the specific event structures that Glamkit-events can model.

One-off Events
^^^^^^^^^^^^^^

In this paradigm, each event occurs only once. 

=====  =====  =====  =====  =====  =====  =====  =====
..      Mon    Tue    Wed    Thu    Fri    Sat    Sun
=====  =====  =====  =====  =====  =====  =====  =====
9am    A      ..     ..     ..     ..     ..     ..  
10am   ..     ..     ..     ..     ..     ..     ..  
11am   ..     ..     ..     ..     ..     ..     .. 
noon   ..     C      ..     ..     ..     ..     G
1pm    ..     ..     ..     D      ..     ..     .. 
2pm    ..     ..     ..     ..     ..     ..     .. 
3pm    ..     ..     ..     ..     E      ..     .. 
4pm    B      ..     ..     ..     ..     ..     .. 
5pm    ..     ..     ..     ..     F      ..     .. 
=====  =====  =====  =====  =====  =====  =====  =====

In the table above, events A to G each have their own database record, with their own names, descriptions, durations, and any other data that belongs to each event. You might conceivably have relationships with other tables (eg. categories, locations, prices etc.), but the temporal structure of your schedule is very straightforward, and can be modelled with a single database table (and hence a single Django model). 

If these are the only seven events you have entered, then next week's schedule will be empty. 

If this is how your event schedule works, you're lucky, you can build a workable schedule with a few simple Django models. Glamkit provides an EventBase model that provides a few useful methods, as well as some handy templatetags and admin tweaks.


Simple Recurring Events
^^^^^^^^^^^^^^^^^^^^^^^

Now let's add the concepts of recurring events.

This is where Glamkit-events starts to hit its stride. As well as having a start and end time, events can also have rules that define how the event recurs over time. 


=====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====
..      Mon    Tue    Wed    Thu    Fri    Sat    Sun    Mon    Tue    Wed    Thu    Fri    Sat    Sun
=====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====
9am    A      ..     ..     ..     ..     ..     ..     A      ..     ..     ..     ..     ..     ..  
10am   ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..  
11am   B      B      B      B      B      ..     ..     B      B      B      B      B      ..     .. 
noon   ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..
1pm    ..     ..     ..     D      ..     ..     ..     ..     ..     ..     ..     ..     ..     .. 
2pm    C      ..     C      ..     C      ..     C      ..     C      ..     C      ..     C      ..
3pm    ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..  
4pm    ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..  
5pm    ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..  
=====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====

The schedule above could be achieved as follows:
Event A: 

Complex Recurring Events
^^^^^^^^^^^^^^^^^^^^^^^^

=====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====
..      Mon    Tue    Wed    Thu    Fri    Sat    Sun    Mon    Tue    Wed    Thu    Fri    Sat    Sun
=====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====
9am    A      ..     ..     ..     ..     ..     ..     A      ..     ..     ..     ..     ..     ..  
10am   ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..  
11am   B      B      B      B      B      ..     ..     B      B      B      B      B      ..     .. 
noon   ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..
1pm    ..     ..     ..     D      ..     ..     ..     ..     ..     ..     ..     ..     ..     .. 
2pm    B      ..     B      ..     B      ..     B      ..     B      ..     B      ..     B      ..
3pm    ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..  
4pm    ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..  
5pm    ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..  
=====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====


Variable Occurrences
^^^^^^^^^^^^^^^^^^^^

=====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====
..      Mon    Tue    Wed    Thu    Fri    Sat    Sun    Mon    Tue    Wed    Thu    Fri    Sat    Sun
=====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====
9am    A      ..     ..     ..     ..     ..     ..     A      ..     ..     ..     ..     ..     ..  
10am   ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..  
11am   B      B      B      B      B      ..     ..     B      B      B      B      B      ..     .. 
noon   ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..
1pm    ..     ..     ..     D      ..     ..     ..     ..     ..     ..     ..     ..     ..     .. 
2pm    C      ..     C      ..     C      ..     C      ..     ..     ..     C      ..     C      ..
3pm    ..     ..     ..     ..     ..     ..     ..     ..     C      ..     ..     ..     ..     ..  
4pm    ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..  
5pm    ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..  
=====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====



Cascading Occurrences
^^^^^^^^^^^^^^^^^^^^^

=====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====
..      Mon    Tue    Wed    Thu    Fri    Sat    Sun    Mon    Tue    Wed    Thu    Fri    Sat    Sun
=====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====
9am    A      ..     ..     ..     ..     ..     ..     A      ..     ..     ..     ..     ..     ..  
10am   ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..  
11am   B      B      B      B      B      ..     ..     B      B†     B      B      B      ..     .. 
noon   ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..
1pm    ..     ..     ..     D      ..     ..     ..     ..     ..     ..     ..     ..     ..     .. 
2pm    C      ..     C      ..     C      ..     C      ..     ..     ..     C      ..     C      ..
3pm    ..     ..     ..     ..     ..     ..     ..     ..     C*     ..     ..     ..     ..     ..  
4pm    ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..  
5pm    ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..     ..  
=====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====  =====


Exceptional Occurrences
-----------------------

Occurrences are generated programatically. This is because we cannot store all of the occurrences in the database, because there could be infinite occurrences. But we still want to be able to vary data about occurrences. Like, cancelling an occurrence, moving an occurrence to a different time or date, or storing a list of attendees with the occurrence.  

Exceptional, or Varied Occurrences are saved lazily. An occurrence is generated programatically until it needs to be varied, when saved to the database. When you use any function to get an occurrence, it will be completely transparent whether it was generated programatically or whether it is retrieved from the database (except that retrieved ones will have a ``pk`` and generated ones don't).  Just treat any occurrence like it could be varied and you shouldn't run into any trouble.
