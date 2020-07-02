from crispy_forms.helper import FormHelper
from django import forms
from django.core.validators import FileExtensionValidator
from django.urls import reverse

from map.models import Map
from visualisation.views import get_visualisation_layout


class MapForm(forms.ModelForm):
    devices = forms.FileField(label='Add new devices', required=False,
                              help_text="Csv file with new device list. "
                                        "Every line describes one device and contains the following fields "
                                        "separated by comma: name, ip address, snmp community, longitude, latitude; "
                                        "for example: router_1,10.234.149.1,read,18.008437,53.123480",
                              validators=[FileExtensionValidator(['csv'])])

    class Meta:
        model = Map
        fields = ['name', 'display_link_descriptions', 'links_default_width', 'highlighted_links_width',
                  'highlighted_links_range_min', 'highlighted_links_range_max', 'parent']

    def __init__(self, *args, **kwargs):
        super(MapForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        instance = kwargs.get('instance')
        cancel_url = reverse('index') if instance is None else reverse('map:index', kwargs={'map_pk': instance.pk})
        self.helper.layout = get_visualisation_layout(cancel_url)
