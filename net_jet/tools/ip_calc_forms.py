from django import forms


class IpCalcForm(forms.Form):
    network = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control py-3', 'placeholder': 'Введите адрес подсети в формате х.х.х.х'}))
    mask = forms.DecimalField(min_value=1, max_value=32, widget=forms.NumberInput(attrs={
        'class': 'form-control py-3', 'placeholder': 'Введите префикс'}))
