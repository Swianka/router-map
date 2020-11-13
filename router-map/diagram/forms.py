from crispy_forms.helper import FormHelper
from django import forms
from django.core.validators import FileExtensionValidator
from django.forms import ModelForm, modelformset_factory

from diagram.models import Diagram, DeviceDiagramRelationship
from utils.formsets import UniqueDeviceFormSet
from visualisation.views import get_visualisation_layout


class DiagramAddDevicesCsv(forms.Form):
    devices = forms.FileField(label='Add new devices',
                              help_text="Csv file with new device list. "
                                        "Every line describes one device and contains the following fields "
                                        "separated by comma: name, ip address, connection type (snmp/netconf), "
                                        "snmp community(empty if not requested), position x, position y "
                                        "(position defined in pixels); "
                                        "for example: router_1,10.234.149.1,snmp,read,150,200",
                              validators=[FileExtensionValidator(['csv'])])

    def __init__(self, *args, **kwargs):
        super(DiagramAddDevicesCsv, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_show_labels = False


class DiagramForm(forms.ModelForm):
    class Meta:
        model = Diagram
        fields = ['name', 'display_link_descriptions', 'links_default_width', 'highlighted_links_width',
                  'highlighted_links_range_min', 'highlighted_links_range_max', 'parent']

    def __init__(self, *args, **kwargs):
        super(DiagramForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = get_visualisation_layout()


class DiagramFormSetHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super(DiagramFormSetHelper, self).__init__(*args, **kwargs)
        self.form_tag = False
        self.template = 'bootstrap4/table_inline_formset.html'


class DeviceDiagramRelationshipForm(ModelForm):
    class Meta:
        model = DeviceDiagramRelationship
        fields = ['device', 'device_position_x', 'device_position_y']

    def __init__(self, *arg, **kwarg):
        super(DeviceDiagramRelationshipForm, self).__init__(*arg, **kwarg)
        self.empty_permitted = False


DiagramFormSet = modelformset_factory(DeviceDiagramRelationship, form=DeviceDiagramRelationshipForm,
                                      extra=0, can_delete=True, formset=UniqueDeviceFormSet, min_num=1)
