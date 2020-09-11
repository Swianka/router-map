from crispy_forms.helper import FormHelper
from django import forms
from django.core.validators import FileExtensionValidator
from django.forms import ModelForm, modelformset_factory
from django.urls import reverse

from diagram.models import Diagram, DeviceDiagramRelationship
from utils.formsets import UniqueDeviceFormSet
from visualisation.views import get_visualisation_layout


class DiagramForm(forms.ModelForm):
    devices = forms.FileField(label='Add new devices', required=False,
                              help_text="Csv file with new device list. "
                                        "Every line describes one device and contains the following fields "
                                        "separated by comma: name, ip address, connection type (snmp/netconf), "
                                        "snmp community(empty if not requested), position x, position y "
                                        "(position defined in pixels); "
                                        "for example: router_1,10.234.149.1,snmp,read,150,200",
                              validators=[FileExtensionValidator(['csv'])])

    class Meta:
        model = Diagram
        fields = ['name', 'display_link_descriptions', 'links_default_width', 'highlighted_links_width',
                  'highlighted_links_range_min', 'highlighted_links_range_max', 'parent']

    def __init__(self, *args, **kwargs):
        super(DiagramForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        instance = kwargs.get('instance')
        cancel_url = reverse('index') if instance is None else reverse('diagram:index',
                                                                       kwargs={'diagram_pk': instance.pk})
        self.helper.layout = get_visualisation_layout(cancel_url)


class DiagramFormSetHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super(DiagramFormSetHelper, self).__init__(*args, **kwargs)
        self.form_tag = False
        self.template = 'bootstrap4/table_inline_formset.html'


class DeviceDiagramRelationshipForm(ModelForm):
    class Meta:
        model = DeviceDiagramRelationship
        fields = ['device', 'device_position_x', 'device_position_y']


DiagramFormSet = modelformset_factory(DeviceDiagramRelationship, form=DeviceDiagramRelationshipForm,
                                      extra=0, can_delete=True, formset=UniqueDeviceFormSet)
