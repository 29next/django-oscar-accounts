from decimal import Decimal as D
import datetime

from django.contrib.auth.models import User
from django.test import TestCase
from django_dynamic_fixture import G, N

from accounts import exceptions
from accounts.models import Account, Transfer, Transaction


class TestAnAccount(TestCase):

    def setUp(self):
        self.account = N(Account)

    def test_is_open_by_default(self):
        self.assertEqual(Account.OPEN, self.account.status)

    def test_can_be_closed(self):
        self.account.close()
        self.assertEqual(Account.CLOSED, self.account.status)

    def test_always_saves_the_code_as_uppercase(self):
        self.account.code = 'abc'
        self.account.save()
        self.assertEquals('ABC', self.account.code)


class TestAnAccountWithFunds(TestCase):

    def setUp(self):
        self.account = Account()
        self.account.balance = D('100.00')

    def test_cannot_be_closed(self):
        with self.assertRaises(exceptions.AccountNotEmpty):
            self.account.close()


class TestANewZeroCreditLimitAccount(TestCase):

    def setUp(self):
        self.account = Account()

    def test_defaults_to_zero_credit_limit(self):
        self.assertEqual(D('0.00'), self.account.credit_limit)

    def test_does_not_permit_any_debits(self):
        self.assertFalse(self.account.is_debit_permitted(D('1.00')))

    def test_has_zero_balance(self):
        self.assertEqual(D('0.00'), self.account.balance)

    def test_has_zero_transactions(self):
        self.assertEqual(0, self.account.num_transactions())


class TestAFixedCreditLimitAccount(TestCase):

    def setUp(self):
        self.account = G(Account, credit_limit=D('500'))

    def test_permits_smaller_and_equal_debits(self):
        for amt in (D('0.00'), D('1.00'), D('500')):
            self.assertTrue(self.account.is_debit_permitted(amt))

    def test_does_not_permit_larger_amounts(self):
        for amt in (D('501'), D('1000')):
            self.assertFalse(self.account.is_debit_permitted(amt))


class TestAnUnlimitedCreditLimitAccount(TestCase):

    def setUp(self):
        self.account = G(Account, credit_limit=None)

    def test_permits_any_debit(self):
        for amt in (D('0.00'), D('1.00'), D('1000000')):
            self.assertTrue(self.account.is_debit_permitted(amt))


class TestAccountExpiredManager(TestCase):

    def test_includes_only_expired_accounts(self):
        today = datetime.date.today()
        G(Account, end_date=today - datetime.timedelta(days=1))
        G(Account, end_date=today + datetime.timedelta(days=1))
        accounts = Account.expired.all()
        self.assertEqual(1, accounts.count())

    def test_excludes_accounts_that_end_on_filter_date(self):
        today = datetime.date.today()
        G(Account, end_date=today)
        accounts = Account.expired.all()
        self.assertEqual(0, accounts.count())


class TestAccountActiveManager(TestCase):

    def test_includes_only_active_accounts(self):
        accounts = Account.active.all()
        today = datetime.date.today()
        G(Account, end_date=today - datetime.timedelta(days=1))
        G(Account, end_date=today + datetime.timedelta(days=1))
        G(Account, start_date=today, end_date=today + datetime.timedelta(days=1))
        accounts = Account.active.all()
        self.assertEqual(2, accounts.count())


class TestATransaction(TestCase):

    def test_cannot_be_deleted(self):
        txn = G(Transaction)
        with self.assertRaises(RuntimeError):
            txn.delete()

    def test_is_not_deleted_when_the_authorisor_is_deleted(self):
        user = G(User)
        source = G(Account, credit_limit=None)
        destination = G(Account)
        txn = Transfer.objects.create(source, destination,
                                      D('20.00'), user)
        self.assertEqual(2, txn.transactions.all().count())
        user.delete()
        self.assertEqual(2, txn.transactions.all().count())
