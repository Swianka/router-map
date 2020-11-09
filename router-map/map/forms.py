from crispy_forms.helper import FormHelper
from django import forms
from django.contrib.gis.geos import Point
from django.core.validators import FileExtensionValidator
from django.forms import ModelForm, modelformset_factory

from map.models import Map, DeviceMapRelationship
from utils.formsets import UniqueDeviceFormSet
from visualisation.views import get_visualisation_layout


class MapAddDevicesCsv(forms.Form):
    devices = forms.FileField(label='Add new devices',
                              help_text="Csv file with new device list. "
                                        "Every line describes one device and contains the following fields "
                                        "separated by comma: name, ip address, connection type (snmp/netconf), "
                                        "snmp community(empty if not requested), longitude, latitude; "
                                        "for example: router_1,10.234.149.1,snmp,read,18.008437,53.123480",
                              validators=[FileExtensionValidator(['csv'])])

    def __init__(self, *args, **kwargs):
        super(MapAddDevicesCsv, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False


class MapForm(forms.ModelForm):
    class Meta:
        model = Map
        fields = ['name', 'display_link_descriptions', 'links_default_width', 'highlighted_links_width',
                  'highlighted_links_range_min', 'highlighted_links_range_max', 'parent']

    def __init__(self, *args, **kwargs):
        super(MapForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = get_visualisation_layout()


class MapFormSetHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super(MapFormSetHelper, self).__init__(*args, **kwargs)
        self.form_tag = False
        self.template = 'bootstrap4/table_inline_formset.html'


class DeviceMapRelationshipForm(ModelForm):
    latitude = forms.FloatField(required=True, min_value=-90, max_value=+90)
    longitude = forms.FloatField(required=True, min_value=-180, max_value=+180)

    class Meta:
        model = DeviceMapRelationship
        fields = ['device']

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        super(DeviceMapRelationshipForm, self).__init__(*args, **kwargs)
        if instance:
            self.initial['latitude'] = instance.point.y
            self.initial['longitude'] = instance.point.x

    def save(self, commit=True):
        instance = super(DeviceMapRelationshipForm, self).save(commit=False)
        latitude = self.cleaned_data['latitude']
        longitude = self.cleaned_data['longitude']
        instance.point = Point(longitude, latitude)
        if commit:
            instance.save()
        return instance


MapFormSet = modelformset_factory(DeviceMapRelationship, form=DeviceMapRelationshipForm, extra=0, can_delete=True,
                                  formset=UniqueDeviceFormSet)
