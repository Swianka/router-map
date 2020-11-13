from django.forms import BaseModelFormSet


class UniqueDeviceFormSet(BaseModelFormSet):
    def clean(self):
        if any(self.errors):
            return
        devices = []
        for form in self.forms:
            if form.cleaned_data:
                try:
                    device = form.cleaned_data['device']
                    if device in devices:
                        form.add_error('device', 'The device must be unique')
                    else:
                        devices.append(device)
                except KeyError:
                    pass
