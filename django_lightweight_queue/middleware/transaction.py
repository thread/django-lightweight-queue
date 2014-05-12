from django.db import transaction, connection

class TransactionMiddleware(object):
    def process_job(self, job):
        if not connection.in_atomic_block:
            transaction.set_autocommit(False)

    def process_result(self, job, result, duration):
        if not connection.in_atomic_block:
            transaction.commit()

    def process_exception(self, job, time_taken, *exc_info):
        if not connection.in_atomic_block:
            transaction.rollback()

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
