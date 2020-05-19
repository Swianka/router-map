from crispy_forms.helper import FormHelper
from django import forms
from django.core.validators import FileExtensionValidator

from diagram.models import Diagram
from utils.visualisation import get_visualisation_layout


class DiagramForm(forms.ModelForm):
    devices = forms.FileField(label='Add new devices', required=False,
                              help_text="Csv file with new device list. "
                                        "Every line describes one device and contains the following fields "
                                        "separated by comma: name, ip address, snmp community, position x, position y",
                              validators=[FileExtensionValidator(['csv'])])

    class Meta:
        model = Diagram
        fields = ['name', 'display_link_descriptions', 'links_default_width', 'highlighted_links_width',
                  'highlighted_links_range_min', 'highlighted_links_range_max']

    def __init__(self, *args, **kwargs):
        super(DiagramForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = get_visualisation_layout('')
