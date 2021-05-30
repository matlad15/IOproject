from django.http import HttpResponse
from django.views.generic import ListView
import django_tables2 as tables
from django_tables2 import SingleTableView
import itertools
from django_filters.views import FilterView
from django_tables2.views import SingleTableMixin
from .models import *
import re
import django_filters
from django.shortcuts import redirect, render

import pandas as pd


def index(request):
    return render(request, 'searchEngine/index.html', {})

def get_dose(tab):
    cell = tab.split(" ")
    if (len(cell) == 5 or len(cell) == 4) and cell[1] == '+' and cell[2].isnumeric():
        value = cell[0] + "" + cell[1] + "" + cell[2]
        cell.pop(0)
        cell.pop(0)
        cell.pop(0)
        unit = " ".join(cell)
    elif len(cell) == 6 and cell[1] == '+' and cell[2].isnumeric() and cell[3] == '+':
        value = cell[0] + "" + cell[1] + "" + cell[2] + "" + cell[3] + "" + cell[4]
        unit = cell[5]
    elif len(cell) == 3 and cell[2] == 'mg)/g':
        value = cell[0] + "" + cell[1]
        value = value.replace('µg', '')
        value = value.replace('(', '')
        unit = 'µg+' + cell[2]
        unit = unit.replace(')', '')
    elif cell[0] == '3,2;':
        value = cell[1]
        unit = cell[2]
    elif len(cell) == 5 and cell[1] == 'mg' and cell[2] == '+' and cell[4] == 'mg':
        value = cell[0] + "" + cell[2] + "" + cell[3]
        unit = cell[1]
    elif len(cell) == 3 and cell[1] == 'mg/24':
        value = cell[0]
        cell = cell.pop(0)
        unit = "".join(cell)
    elif cell[0] == 'stężenie' or cell[0] == 'stężenie:':
        value = "-1"
        unit = " ".join(cell)
    elif len(cell) >= 5 and cell[3] == '+' and cell[4].isnumeric():
        value = cell[0] + "" + cell[3] + "" + cell[4]
        unit = cell[1] + "" + cell[2] + "" + cell[3] + "" + cell[5] + "" + cell[6]
    else:
        # print("normal")
        value = cell[0]
        value = value.replace("(", "")
        value = value.replace(")", "")
        cell.pop(0)
        unit = " ".join(cell)

    value = value.strip()
    value = value.replace(',', '.')
    unit = unit.strip()
    dose = MedicineDose(unit=unit, value=value)
    dose.save()
    return dose


def get_package_content(tab):
    orginal = tab
    cell = tab.split(" ")
    value = cell[0]
    unit = cell[1]
    unit = re.sub(r'\..*', '.', unit)

    if value == '30x1':
        value = '30'
        unit = 'kaps.'
    elif unit == 'x':
        value = '1'
        unit = 'but.'
    elif unit == 'butelka' or unit == 'butelki':
        unit = 'but.'

    value = value.strip()
    value = value.replace(',', '.')
    unit = unit.strip()
    content = PackageContent(unit=unit, value=value, original_content=orginal)
    content.save()
    return content


def get_medicine_name(cell):
    name = MedicineName(name=cell)
    name.save()
    return name


def get_medicine_form(cell):
    name = MedicineForm(name=cell)
    name.save()
    return name


def get_active_substance(cell):
    name = ActiveSubstance(name=cell)
    name.save()
    return name


def get_ean(cell):
    cell = int(cell)
    value = EAN(value=cell)
    value.save()
    return value


def get_refund(cell):
    cell = cell.replace("<1>", "")
    cell = cell.replace("<2>", "")
    if cell == 'x':
        cell = ''
    name = Refund(name=cell)
    name.save()
    return name


def get_surcharge(cell):
    cell = float(cell.replace(',', '.'))
    value = Surcharge(value=cell)
    value.save()
    return value


def parse_xlsx():
    file = pd.ExcelFile('leki.xlsx', engine='openpyxl')
    data = file.parse('A1', skiprows=1, index_col=None,
                      usecols=['Nazwa  postać i dawka', 'Zawartość opakowania',
                               'Substancja czynna', 'Numer GTIN lub inny kod jednoznacznie identyfikujący produkt',
                               'Zakres wskazań objętych refundacją', 'Wysokość dopłaty świadczeniobiorcy'])

    for i, row in data.iterrows():
        tab = row['Nazwa  postać i dawka'].split(", ")
        name = get_medicine_name(tab[0])
        dose = get_dose(tab[len(tab) - 1])
        tab.pop(len(tab) - 1)
        tab.pop(0)
        form = get_medicine_form("".join(tab))

        tab = row['Zawartość opakowania']
        content = get_package_content(tab)

        tab = row['Substancja czynna']
        substance = get_active_substance(tab)

        tab = row['Numer GTIN lub inny kod jednoznacznie identyfikujący produkt']
        ean = get_ean(tab)

        tab = row['Zakres wskazań objętych refundacją']
        refund = get_refund(tab)

        tab = row['Wysokość dopłaty świadczeniobiorcy']
        surcharge = get_surcharge(tab)

        new_row = RowA(name=name, form=form, dose=dose, substance=substance,
                       content=content, ean=ean, refund=refund, surcharge=surcharge)
        new_row.save()

class RowTable(tables.Table):
    class Meta:
        exclude = ['created_on']
        model = RowA
        template_name = "django_tables2/bootstrap.html"

    def order_name(self, queryset, is_descending):
        if not is_descending:
            queryset = queryset.order_by('name__name')
        else:
            queryset = queryset.order_by('-name__name')

        return queryset, True

    def order_form(self, queryset, is_descending):
        if not is_descending:
            queryset = queryset.order_by('form__name')
        else:
            queryset = queryset.order_by('-form__name')

        return queryset, True

    def order_dose(self, queryset, is_descending):
        if not is_descending:
            queryset = queryset.order_by('dose__unit', 'dose__value')
        else:
            queryset = queryset.order_by('-dose__unit', '-dose__value')

        return queryset, True

    def order_ean(self, queryset, is_descending):
        if not is_descending:
            queryset = queryset.order_by('ean__value')
        else:
            queryset = queryset.order_by('-ean__value')

        return queryset, True

    def order_substance(self, queryset, is_descending):
        if not is_descending:
            queryset = queryset.order_by('substance__name')
        else:
            queryset = queryset.order_by('-substance__name')

        return queryset, True

    def order_content(self, queryset, is_descending):
        if not is_descending:
            queryset = queryset.order_by('content__unit', 'content__value')
        else:
            queryset = queryset.order_by('-content__unit', '-content__value')

        return queryset, True

    def order_surcharge(self, queryset, is_descending):
        if not is_descending:
            queryset = queryset.order_by('surcharge__value')
        else:
            queryset = queryset.order_by('-surcharge__value')

        return queryset, True

    def order_refund(self, queryset, is_descending):
        if not is_descending:
            queryset = queryset.order_by('refund__name')
        else:
            queryset = queryset.order_by('-refund__name')

        return queryset, True


class RowFilter(django_filters.FilterSet):
    name__name = django_filters.CharFilter(lookup_expr='icontains')
    form__name = django_filters.CharFilter(lookup_expr='icontains')
    substance__name = django_filters.CharFilter(lookup_expr='icontains')
    refund__name = django_filters.CharFilter(lookup_expr='icontains')

    surcharge__value = django_filters.NumberFilter()
    surcharge__value__gt = django_filters.NumberFilter(field_name='surcharge__value', lookup_expr='gt')
    surcharge__value__lt = django_filters.NumberFilter(field_name='surcharge__value', lookup_expr='lt')

    ean__value = django_filters.NumberFilter()
    ean__value__gt = django_filters.NumberFilter(field_name='ean__value', lookup_expr='gt')
    ean__value__lt = django_filters.NumberFilter(field_name='ean__value', lookup_expr='lt')

    class Meta:
        model = RowA
        fields = ['name__name', 'form__name', 'substance__name', 'refund__name', 'surcharge__value', 'ean__value']


class FilteredRowListView(SingleTableMixin, FilterView):
    table_class = RowTable
    model = RowA
    template_name = "searchEngine/index.html"

    filterset_class = RowFilter
