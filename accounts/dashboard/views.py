from django.views import generic
from django.core.urlresolvers import reverse
from django.conf import settings
from django import http
from django.shortcuts import get_object_or_404
from django.db.models import get_model
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from oscar.templatetags.currency_filters import currency

from accounts.dashboard import forms
from accounts import facade, codes, core

AccountType = get_model('accounts', 'AccountType')
Account = get_model('accounts', 'Account')
Transfer = get_model('accounts', 'Transfer')
Transaction = get_model('accounts', 'Transaction')


class CodeAccountListView(generic.ListView):
    model = Account
    context_object_name = 'accounts'
    template_name = 'dashboard/accounts/account_list.html'
    form_class = forms.SearchForm
    description = _("All %ss") % settings.ACCOUNTS_UNIT_NAME

    def get_context_data(self, **kwargs):
        ctx = super(CodeAccountListView, self).get_context_data(**kwargs)
        ctx['form'] = self.form
        ctx['title'] = "%ss" % settings.ACCOUNTS_UNIT_NAME
        ctx['unit_name'] = settings.ACCOUNTS_UNIT_NAME
        ctx['queryset_description'] = self.description
        return ctx

    def get_queryset(self):
        account_type = AccountType.objects.get(
            name="Giftcards")
        queryset = self.model.objects.filter(
            account_type=account_type)
        if 'code' not in self.request.GET:
            # Form not submitted
            self.form = self.form_class()
            return queryset

        self.form = self.form_class(self.request.GET)
        if not self.form.is_valid():
            # Form submitted but invalid
            return queryset

        # Form valid - build queryset and description
        data = self.form.cleaned_data
        desc_template = _(
            "%(status)s %(unit)ss %(code_filter)s %(name_filter)s")
        desc_ctx = {
            'unit': settings.ACCOUNTS_UNIT_NAME.lower(),
            'status': "All",
            'code_filter': "",
            'name_filter': "",
        }
        if data['name']:
            queryset = queryset.filter(name__icontains=data['name'])
            desc_ctx['name_filter'] = _(
                " with name matching '%s'") % data['name']
        if data['code']:
            queryset = queryset.filter(code=data['code'])
            desc_ctx['code_filter'] = _(
                " with code '%s'") % data['code']
        if data['status']:
            queryset = queryset.filter(status=data['status'])
            desc_ctx['status'] = data['status']

        self.description = desc_template % desc_ctx

        return queryset


class CodeAccountCreateView(generic.CreateView):
    model = Account
    context_object_name = 'account'
    template_name = 'dashboard/accounts/account_form.html'
    form_class = forms.NewAccountForm

    def get_context_data(self, **kwargs):
        ctx = super(CodeAccountCreateView, self).get_context_data(**kwargs)
        ctx['title'] = _("Create a new %s") % settings.ACCOUNTS_UNIT_NAME
        return ctx

    def get_account_type(self):
        return AccountType.objects.get(name="Giftcards")

    def get_form_kwargs(self):
        kwargs = super(CodeAccountCreateView, self).get_form_kwargs()
        kwargs['account_type'] = self.get_account_type()
        return kwargs

    def form_valid(self, form):
        # Create new account and make a transfer from the global source account
        account = form.save(commit=False)
        code = codes.generate()
        account.code = code
        account.save()

        amount = form.cleaned_data['initial_amount']
        facade.transfer(core.unpaid_source_account(), account, amount,
                        user=self.request.user,
                        description=_("Creation of account"))
        messages.success(
            self.request,
            _("New account created with code '%s'") % code)

        return http.HttpResponseRedirect(
            reverse('accounts-detail', kwargs={'pk': account.id}))


class CodeAccountUpdateView(generic.UpdateView):
    model = Account
    context_object_name = 'account'
    template_name = 'dashboard/accounts/account_form.html'
    form_class = forms.UpdateAccountForm

    def get_context_data(self, **kwargs):
        ctx = super(CodeAccountUpdateView, self).get_context_data(**kwargs)
        ctx['title'] = _("Update '%s' account") % self.object.name
        return ctx

    def form_valid(self, form):
        account = form.save()
        messages.success(self.request, _("Account saved"))
        return http.HttpResponseRedirect(
            reverse('accounts-detail', kwargs={'pk': account.id}))


class AccountFreezeView(generic.UpdateView):
    model = Account
    template_name = 'dashboard/accounts/account_freeze.html'
    form_class = forms.FreezeAccountForm

    def get_success_url(self):
        messages.success(self.request, _("Account frozen"))
        return reverse('code-accounts-list')


class AccountThawView(generic.UpdateView):
    model = Account
    template_name = 'dashboard/accounts/account_thaw.html'
    form_class = forms.ThawAccountForm


class AccountTopUpView(generic.UpdateView):
    model = Account
    template_name = 'dashboard/accounts/account_top_up.html'
    form_class = forms.TopUpAccountForm

    def form_valid(self, form):
        account = self.object
        amount = form.cleaned_data['amount']
        facade.transfer(facade.source(), account, amount,
                        user=self.request.user,
                        description=_("Top-up account"))
        messages.success(
            self.request, _("%s added to account") % currency(amount))
        return http.HttpResponseRedirect(reverse('code-accounts-list'))

    def get_success_url(self):
        messages.success(self.request, _("Account re-opened"))
        return reverse('code-accounts-list')


class AccountTransactionsView(generic.ListView):
    model = Transaction
    context_object_name = 'transactions'
    template_name = 'dashboard/accounts/account_detail.html'

    def get(self, request, *args, **kwargs):
        self.account = get_object_or_404(Account, id=kwargs['pk'])
        return super(AccountTransactionsView, self).get(
            request, *args, **kwargs)

    def get_queryset(self):
        return self.account.transactions.all().order_by('-date_created')

    def get_context_data(self, **kwargs):
        ctx = super(AccountTransactionsView, self).get_context_data(**kwargs)
        ctx['account'] = self.account
        return ctx


class TransferListView(generic.ListView):
    model = Transfer
    context_object_name = 'transfers'
    template_name = 'dashboard/accounts/transfer_list.html'


class TransferDetailView(generic.DetailView):
    model = Transfer
    context_object_name = 'transfer'
    template_name = 'dashboard/accounts/transfer_detail.html'
