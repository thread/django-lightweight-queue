from django.db import transaction, connection

class TransactionMiddleware(object):
    def process_job(self, job):
        transaction.atomic().__enter__()

    def process_result(self, job, result, duration):
        transaction.atomic().__exit__(None, None, None)

    def process_exception(self, job, time_taken, *exc_info):
        transaction.atomic().__exit__(*exc_info)

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
