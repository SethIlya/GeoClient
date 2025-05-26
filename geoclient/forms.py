# geoclient/forms.py
from django import forms

class RinexUploadForm(forms.Form):
    rinex_file = forms.FileField(
        label='Выберите RINEX файл (.25o, .25g, .25n)',
        widget=forms.ClearableFileInput(attrs={'accept': '.25o,.25g,.25n,.o,.g,.n, .rnx'}) # Расширьте по необходимости
    )
    # Можно добавить поле для выбора типа файла, если не можем определить по расширению
    # file_type = forms.ChoiceField(choices=[('o', 'Observation'), ('n', 'Navigation GPS'), ('g', 'Navigation GLONASS')], required=False)