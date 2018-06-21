import warnings

from django.db import transaction

class TransactionMiddleware(object):
    def _raise_deprecation_warning(self):
        warnings.warn(
            "Using legacy `TransactionMiddleware`, set atomic=True on the "
            "@task instead or set ATOMIC_JOBS to True.",
            category=DeprecationWarning,
            stacklevel=2,
        )

    def process_job(self, job):
        self._raise_deprecation_warning()
        transaction.atomic().__enter__()

    def process_result(self, job, result, duration):
        self._raise_deprecation_warning()
        transaction.atomic().__exit__(None, None, None)

    def process_exception(self, job, time_taken, *exc_info):
        self._raise_deprecation_warning()
        transaction.atomic().__exit__(*exc_info)
