from optparse import make_option

from django.core.management.base import LabelCommand
from django.db.models import Model
from django.db.models.loading import get_model

from ...models import GeneratorModel, FREQUENCY_TIME_MAP

class Command(LabelCommand):
    args = '<app.Model app.Model ...>'
    label = 'app.Model'
    option_list = LabelCommand.option_list + (
        make_option('--dry-run',
            action='store_true', dest='dry_run', default=False,
            help='Output violating occurrences without fixing anything.'),
        )
    help = ('Remove occurrences that span longer than their repeat frequency '
        'for the specified generator model (in app.Model format).')

    def handle_label(self, arg, **options):
        dry_run = options.pop('dry_run', False)
        verbosity = int(options.get('verbosity', 1))
        assert len(arg.split('.')) == 2, 'Arguments must be in app.Model format.'
        generator_model = get_model(*arg.split('.'))
        assert issubclass(generator_model, GeneratorModel), ('The model must '
            'inherit from GeneratorModel.')
        
        for generator in generator_model.objects.filter(rule__isnull=False):
            bad_occurrences = 0
            generator_length = generator.event_end - generator.event_start
            for occurrence in generator.occurrences.all():
                # Check if occurrence length doesn't match the generator length
                # and make sure it's not an exception. We can't use
                # .is_exception() because it tries to modify stuff.
                if (not generator.exceptions
                    or not generator.exceptions.has_key(
                        occurrence.start.isoformat())
                ) and occurrence.end - occurrence.start != generator_length:
                    bad_occurrences += 1
                    # Don't do anything on a dry run
                    if not dry_run:
                        # Disassociate with generator, so exception isn't added
                        occurrence.generator = None
                        occurrence.delete()
            if verbosity and bad_occurrences:
                print 'Generator "%s" has %s bad occurrences.' % (
                    generator, bad_occurrences)
            # Skip unexpected frequencies
            if generator.rule.frequency not in FREQUENCY_TIME_MAP:
                continue
            # Check if the generator length is longer than its frequency
            if generator_length > FREQUENCY_TIME_MAP[generator.rule.frequency]:
                if verbosity:
                    print 'Generator "%s" is too long for its frequency.' \
                        % generator
                if not dry_run:
                    generator.event_end = generator.event_end.replace(
                        *generator.event_start.timetuple()[:3])
                    # It would be great to simply let the generator modify the
                    # occurrences, but since the current ones won't pass 
                    # validation, it will fail
                    Model.save(generator)
                    for occurrence in generator.occurrences.all():
                        if (not generator.exceptions
                            or not generator.exceptions.has_key(
                                occurrence.start.isoformat())
                        ):
                            occurrence.end = occurrence.end.replace(
                                *occurrence.start.timetuple()[:3])
                            Model.save(occurrence)
            # Check for duplicates
            deleted_pks = []
            duplicates = 0
            for occurrence in generator.occurrences.all():
                if not generator.exceptions \
                        or not generator.exceptions.has_key(
                            occurrence.start.isoformat()) \
                        and not occurrence.pk in deleted_pks:
                    possible_duplicates = generator.occurrences.filter(
                        start=occurrence.start, end=occurrence.end).exclude(
                            pk=occurrence.pk)
                    if possible_duplicates:
                        for duplicate in possible_duplicates:
                            if not generator.exceptions \
                                    or not generator.exceptions.has_key(
                                        duplicate.start.isoformat()):
                                duplicates += 1
                                deleted_pks += [duplicate.pk]
                                if not dry_run:
                                    duplicate.generator = None
                                    duplicate.delete()
            if verbosity and duplicates:
                print 'Generator "%s" has %s duplicate occurrences.' % (
                    generator, duplicates)
