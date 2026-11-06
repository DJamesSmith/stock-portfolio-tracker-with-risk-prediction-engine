from django import forms


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if not data:
            return []

        if not isinstance(data, (list, tuple)):
            data = [data]

        files = []
        for uploaded_file in data:
            files.append(super().clean(uploaded_file, initial))

        return files
