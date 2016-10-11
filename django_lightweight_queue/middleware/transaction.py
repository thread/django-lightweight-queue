from django.db import transaction, connection

from ..task import task

class TransactionMiddleware(object):
    def __init__(self):
        self._transaction_started = False

    def _enable_transaction(self, job):
        return job.get_middleware_option('transaction.enabled', True)

    def process_job(self, job):
        if self._enable_transaction(job):
            transaction.atomic().__enter__()
            self._transaction_started = True

    def process_result(self, job, result, duration):
        if self._transaction_started:
            transaction.atomic().__exit__(None, None, None)

    def process_exception(self, job, time_taken, *exc_info):
        if self._transaction_started:
            transaction.atomic().__exit__(*exc_info)

def non_transactional_task(*args, **kwargs):
    kwargs.setdefault('transaction', {}).setdefault('enabled', False)
    return task(*args, **kwargs)

# Legacy
if not hasattr(connection, 'in_atomic_block'):
    class TransactionMiddleware(object):
        def process_job(self, job):
            transaction.enter_transaction_management()
            transaction.managed(True)

        def process_result(self, job, result, duration):
            if not transaction.is_managed():
                return
            if transaction.is_dirty():
                transaction.commit()
            transaction.leave_transaction_management()

        def process_exception(self, job, time_taken, *exc_info):
            if transaction.is_dirty():
                transaction.rollback()
            transaction.leave_transaction_management()
