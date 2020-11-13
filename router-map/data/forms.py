from crispy_forms.helper import FormHelper
from django.forms import modelformset_factory, ModelForm

from data.models import Device


class DeviceForm(ModelForm):
    class Meta:
        model = Device
        fields = ['name', 'ip_address', 'connection_type', 'snmp_community']
        help_texts = {
            'snmp_community': None,
        }


class DeviceFormSetHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super(DeviceFormSetHelper, self).__init__(*args, **kwargs)
        self.form_tag = False
        self.template = 'bootstrap4/table_inline_formset.html'


DeviceFormSet = modelformset_factory(Device, form=DeviceForm, extra=0, can_delete=True, min_num=1)
