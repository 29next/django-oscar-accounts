from decimal import Decimal as D

from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.db.models import get_model

Account = get_model('accounts', 'Account')

CATEGORIES = getattr(settings, 'ACCOUNTS_CATEGORIES', ())


class SearchForm(forms.Form):
    name = forms.CharField(required=False)
    code = forms.CharField(required=False)
    STATUS_CHOICES = (
        ('', "------"),
        (Account.OPEN, _("Open")),
        (Account.FROZEN, _("Frozen")),
        (Account.CLOSED, _("Closed")))
    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False)


class EditAccountForm(forms.ModelForm):
    name = forms.CharField(label=_("Name"), required=True)

    if CATEGORIES:
        choices = [(c, _(c)) for c in CATEGORIES]
        category = forms.ChoiceField(label=_("Category"), required=True,
                                     choices=choices)

    class Meta:
        model = Account
        exclude = ['status', 'code', 'credit_limit', 'balance', 'product_range',
                   'primary_user', 'secondary_users']
        if not CATEGORIES:
            exclude.append('category')


class NewAccountForm(EditAccountForm):
    initial_amount = forms.DecimalField(
        min_value=getattr(settings, 'ACCOUNTS_MIN_INITIAL_VALUE', D('0.00')),
        max_value=getattr(settings, 'ACCOUNTS_MAX_INITIAL_VALUE', None),
        decimal_places=2)


class UpdateAccountForm(EditAccountForm):
    pass


class ChangeStatusForm(forms.ModelForm):
    status = forms.CharField(widget=forms.widgets.HiddenInput)
    new_status = None

    def __init__(self, *args, **kwargs):
        kwargs['initial']['status'] = self.new_status
        super(ChangeStatusForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Account
        exclude = ['name', 'description', 'category', 'code', 'start_date',
                   'end_date', 'credit_limit', 'balance', 'product_range',
                   'primary_user', 'secondary_users']


class FreezeAccountForm(ChangeStatusForm):
    new_status = Account.FROZEN


class ThawAccountForm(ChangeStatusForm):
    new_status = Account.OPEN


class TopUpAccountForm(forms.Form):
    amount = forms.DecimalField(
        min_value=getattr(settings, 'ACCOUNTS_MIN_INITIAL_VALUE', D('0.00')),
        max_value=getattr(settings, 'ACCOUNTS_MAX_INITIAL_VALUE', None),
        decimal_places=2)

    def __init__(self, *args, **kwargs):
        self.account = kwargs.pop('instance')
        super(TopUpAccountForm, self).__init__(*args, **kwargs)

    def clean(self):
        if self.account.is_closed():
            raise forms.ValidationError(_("Account is closed"))
        elif self.account.is_frozen():
            raise forms.ValidationError(_("Account is frozen"))
        return self.cleaned_data
