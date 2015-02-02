__author__ = 'gturner'

def ManagerType(QSFN, supertype=type):
    """
    This metaclass generator injects proxies for given queryset functions into the manager.

    This allows the function f to be called from .objects.f() and .objects.filter().f()

    class QSFN(object):
        # define your queryset functions here
        def f(self):
            return self.filter(**kwargs)
        ...

    class MyQuerySet(models.query.QuerySet, QSFN):
        # trivial inheritance of the QS functions
        pass

    class MyManager(models.Manager):
        __metaclass__ = ManagerType(QSFN) # injects the QS functions

        def get_queryset(self):
            return MyQuerySet(self.model)

    class MyModel(models.Model):
        ...
        objects = MyManager()

    """

    #TODO: move to glamkit-convenient.

    class _MT(supertype):
        @staticmethod
        def _fproxy(name):
            def f(self, *args, **kwargs):
                return getattr(self.get_queryset(), name)(*args, **kwargs)
            return f

        def __init__(cls, *args):
            for fname in dir(QSFN):
                if not fname.startswith("_"):
                    setattr(cls, fname, _MT._fproxy(fname))
            super(_MT, cls).__init__(*args)
    return _MT