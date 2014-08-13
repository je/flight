import datetime
from django import forms
from django.contrib.auth.models import User, Group
from django.template.loader import render_to_string
from django.forms.widgets import CheckboxSelectMultiple
from guardian.shortcuts import assign
from flight.models import *
from localflavor.us.forms import USStateField, USStateSelect
#from olwidget.widgets import EditableMap

import csv
csv.field_size_limit(1000000000)

from django.utils.timezone import utc
from timezone_field import TimeZoneFormField

timenow = datetime.datetime.utcnow().replace(tzinfo=utc)
datenow = datetime.datetime.utcnow().replace(tzinfo=utc).date()

#timenow = datetime.datetime.now
#datenow = datetime.datetime.now().date()

### Pops

class SelectWithPop(forms.Select):
    def render(self, name, *args, **kwargs):
        html = super(SelectWithPop, self).render(name, *args, **kwargs)
        popupplus = render_to_string("flight/popupplus.html", {'field': name})
        return html+popupplus

class MultipleSelectWithPop(forms.SelectMultiple):
    def render(self, name, *args, **kwargs):
        html = super(MultipleSelectWithPop, self).render(name, *args, **kwargs)
        popupplus = render_to_string("flight/popupplus.html", {'field': name})
        return html+popupplus

### Permissions

class Permissions(forms.Form):
    users = forms.ModelMultipleChoiceField(required = False, widget=CheckboxSelectMultiple, queryset=User.objects.filter(groups__name='flight-user'),) #widget=forms.CheckboxSelectMultiple(attrs={'class':'form-control'})) 
    class Meta:
        fields = ['users',]

class Requestform(forms.Form):
    remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={'class':'form-control', 'placeholder':'Type a message to include with your request', 'rows': 2}))
    class Meta:
        fields = ['remarks',]

### Airbase

class AirbaseAdd(forms.ModelForm):
    name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Airbase Name'}))
    tla = forms.CharField(label='Airport Code', required=True, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'TLA', 'onfocus': 'if (this.value==\'TLA\') this.value = \'\''}), initial='TLA')
    address = forms.CharField(required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Street Address'}))
    city = forms.CharField(required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'City'}))
    st = USStateField(label='State',required=False, widget=USStateSelect(attrs={'class':'form-control', 'placeholder':'State',}), initial='')
    region = forms.CharField(label='Region', required=True, min_length=2, max_length=2, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'00',}), initial='')
    tz = TimeZoneFormField(label='TimeZone', required=True, widget=forms.Select(attrs={'class':'form-control',}),)
    postal = forms.CharField(label='Zip', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'00000-0000'}))
    phone = forms.CharField(required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'0005551234'}))
    fax = forms.CharField(required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'0005551234'}))
    manager = forms.ModelChoiceField(required = False, queryset=User.objects.filter(groups__name='flight-user'), widget=forms.Select(attrs={'class':'form-control'})) 
    remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={'class':'form-control', 'rows': 2}))
    rtype = forms.ChoiceField(label='Default Retardant Type', required = False, choices=RET_CHOICES, widget=forms.Select(attrs={'class':'form-control', }),)
    #geom = forms.CharField(required=False, widget=EditableMap({ 'defaultZoom': 3, 'default_lat': 37.09024, 'default_lon': -95.712891, 'map_div_style': {'width': '100%', 'height': '220px'},'map_options': {'controls': ['LayerSwitcher', 'Navigation', 'PanZoom', 'MousePosition']},'map_div_class': 'form-control', 'isCollection': True, 'geometry': ['point', 'linestring', 'polygon']},))
    class Meta:
        model = Airbase
        exclude = ['author',]
        fields = ('name', 'tla', 'manager', 'address', 'city', 'st', 'region', 'tz', 'postal', 'phone', 'fax', 'remarks', 'rtype', )

    def save(self, commit=True):
        obj = super(AirbaseAdd, self).save(commit=False)
        try:
            manager = User.objects.get(id=obj.manager.id)
            if commit:
                obj.save()
                if not manager.has_perm('change_airbase', obj):
                    assign('change_airbase', manager, obj)
                if not manager.has_perm('delete_airbase', obj):
                    assign('delete_airbase', manager, obj)
        except:
            manager = None
            if commit:
                obj.save()
        return obj
  
class AirbaseDelete(forms.ModelForm):
    class Meta:
        model = Airbase
        fields = []

### Airplane

class AirplaneAdd(forms.ModelForm):
    name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Airplane Name'}))
    tail = forms.CharField(required=True, label='N#', widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'N#', 'onfocus': 'if (this.value==\'N#\') this.value = \'\''}), initial='')
    make = forms.CharField(required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Make'}))
    modelname = forms.ChoiceField(label='Model', required=False, choices=MOD_CHOICES, widget=forms.Select(attrs={'class':'form-control',}))
    takeoffweight = forms.IntegerField(label='Takeoff Wt', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'lbs'}))
    landingweight = forms.IntegerField(label='Landing Wt', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'lbs'}))
    maxgrosswt = forms.IntegerField(label='MaxGross Wt', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'lbs'}))
    airspeed = forms.IntegerField(label='Air Speed', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'mph'}))
    remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={'class':'form-control', 'rows': 2}))
    class Meta:
        model = Airplane
        exclude = ['author','dailypost','dailypostbegins',]
        fields = ('name', 'tail', 'make', 'modelname', 'takeoffweight', 'landingweight', 'maxgrosswt', 'airspeed', 'remarks',)

class AirbaseAirplaneAdd(forms.ModelForm):
    name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Airplane Name'}))
    tail = forms.CharField(required=True, label='N#', widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'N#', 'onfocus': 'if (this.value==\'N#\') this.value = \'\''}), initial='')
    make = forms.CharField(required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Make'}))
    modelname = forms.ChoiceField(label='Model', required=False, choices=MOD_CHOICES, widget=forms.Select(attrs={'class':'form-control',}))
    takeoffweight = forms.IntegerField(label='Takeoff Wt', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'lbs'}))
    landingweight = forms.IntegerField(label='Landing Wt', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'lbs'}))
    maxgrosswt = forms.IntegerField(label='MaxGross Wt', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'lbs'}))
    airspeed = forms.IntegerField(label='Air Speed', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'mph'}))
    remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={'class':'form-control', 'rows': 2}))
    class Meta:
        model = Airplane
        exclude = ['author','adminbase','dailypost','dailypostbegins',]
        fields = ('name', 'tail', 'make', 'modelname', 'takeoffweight', 'landingweight', 'maxgrosswt', 'airspeed', 'remarks',)

class AirplaneDelete(forms.ModelForm):
    class Meta:
        model = Airplane
        fields = []

### Person

class PersonAdd(forms.ModelForm):
    firstname = forms.CharField(label='First Name', required=True, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'First Name'}))
    lastname = forms.CharField(label='Last Name', required=True, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Last Name'}))
    #avatar = forms.ImageField(required=False)
    job = forms.CharField(label='Job', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Job'}))
    agency = forms.CharField(label='Agency', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Agency'}))
    address = forms.CharField(required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Street Address'}))
    city = forms.CharField(required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'City'}))
    state = USStateField(label='State',required=False, widget=USStateSelect(attrs={'class':'form-control', 'placeholder':'State',}), initial='')
    zip4 = forms.CharField(label='Zip', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'00000-0000'}))
    telephone = forms.CharField(label='Phone', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'0005551234'}))
    telephone2 = forms.CharField(label='Phone', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'0005551234'}))
    email = forms.CharField(label='Email', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'user@domain.org'}))
    bio = forms.CharField(required=False, widget=forms.Textarea(attrs={'class':'form-control', 'rows': 2}))
    remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={'class':'form-control', 'rows': 2}))
    class Meta:
        model = Person
        exclude = ['author',]
        fields = ('firstname', 'lastname', 'job', 'agency', 'address', 'city', 'state', 'zip4', 'telephone', 'telephone2', 'email', 'bio', 'remarks',)

class PersonDelete(forms.ModelForm):
    class Meta:
        model = Person
        fields = []

### Incident

class IncidentAdd(forms.ModelForm):
    name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Incident Name'}))
    begins = forms.DateField(label='Begin', required=False, widget=forms.TextInput(attrs={'class': 'form-control', }), initial=datenow)
    ends = forms.DateField(label='End', required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder':'YYYY-MM-DD',}))
    resourceorder = forms.CharField(label='Order Number', required=True, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Order Number'}))
    firechargenum = forms.CharField(label='Charge No', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Charge No'}))
    userunit = forms.CharField(label='Override', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'0000'}))
    landstatus = forms.CharField(label='Agency', required=False, widget=forms.TextInput(attrs={'class':'form-control',}))
    forest = forms.CharField(label='Forest', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Forest'}))
    st = USStateField(label='State', required=False, widget=USStateSelect(attrs={'class':'form-control',}))
    remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={'class':'form-control', 'rows': 2}))
    #geom = forms.CharField(required=False, widget=EditableMap({ 'defaultZoom': 3, 'default_lat': 37.09024, 'default_lon': -95.712891, 'map_div_style': {'width': '100%', 'height': '220px'},'map_div_class': 'form-control','map_options': {'controls': ['LayerSwitcher', 'Navigation', 'PanZoom', 'MousePosition']}, 'hide_textarea': True, 'isCollection': True, 'geometry': ['point', 'linestring', 'polygon']},))

    class Meta:
        model = Incident
        exclude = ['author',]
        fields = ('name', 'begins', 'ends', 'resourceorder', 'firechargenum', 'userunit', 'landstatus', 'forest', 'st', 'remarks', )

class IncidentDelete(forms.ModelForm):
    class Meta:
        model = Incident
        fields = []

### Mission

class HiddenDateAndTimeWidget(forms.widgets.SplitDateTimeWidget):
    """
    A Widget that splits datetime input into two <input type="hidden"> inputs.
    """
    #is_hidden = True

    def __init__(self, attrs=None, date_format=None, time_format='%H%M'):
        super(HiddenDateAndTimeWidget, self).__init__(attrs, date_format, time_format)
        first = True
        for widget in self.widgets:
            if first:
                widget.input_type = 'hidden'
                widget.is_hidden = True
                first = False

class MissionAdd(forms.ModelForm):
    airplane = forms.ModelChoiceField(label='Airplane', required=True, queryset=Airplane.objects.all(), widget=forms.Select(attrs={'class':'form-control'})) 
    startdate = forms.DateField(label='Start', required=True, widget=forms.DateInput(attrs={'class':'form-control', }), initial=timenow)
    pilot = forms.ModelChoiceField(label='Pilot', required=False, queryset=Person.objects.filter(job__iexact='Pilot'), widget=forms.Select(attrs={'class':'form-control'}))
    copilot = forms.ModelChoiceField(label='Copilot', required=False, queryset=Person.objects.filter(job__iexact='Pilot'), widget=forms.Select(attrs={'class':'form-control'}))
    othercrew = forms.ModelChoiceField(label='Other', required=False, queryset=Person.objects.all(), widget=forms.Select(attrs={'class':'form-control'}))
    dailyavailstart_1 = forms.TimeField(label='On Duty', required=True, widget=forms.TimeInput(attrs={'class':'form-control', }, format='%H%M'), input_formats=['%H%M'], initial=None)
    dailyavailstop_1 = forms.TimeField(label='Off Duty', required=False, widget=forms.TimeInput(attrs={'class':'form-control', }, format='%H%M'), input_formats=['%H%M'], initial=None)
    remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={'class':'form-control', 'rows': 2}))
    class Meta:
        model = Mission
        exclude = ['author', 'dailyavailstart', 'dailyavailstop', 'nonavailstart','nonavailstop',]
        fields = ('airplane', 'startdate', 'remarks', 'dailyavailstart_1', 'dailyavailstop_1', 'pilot', 'copilot', 'othercrew')

 
class MissionEdit(forms.ModelForm):
    airplane = forms.ModelChoiceField(label='Airplane', required=True, queryset=Airplane.objects.all(), widget=forms.Select(attrs={'class':'form-control'})) 
    startdate = forms.DateField(label='Start', required=True, widget=forms.DateInput(attrs={'class':'form-control', }), initial=timenow)
    pilot = forms.ModelChoiceField(label='Pilot', required=False, queryset=Person.objects.filter(job__iexact='Pilot'), widget=forms.Select(attrs={'class':'form-control'}))
    copilot = forms.ModelChoiceField(label='Copilot', required=False, queryset=Person.objects.filter(job__iexact='Pilot'), widget=forms.Select(attrs={'class':'form-control'}))
    othercrew = forms.ModelChoiceField(label='Other', required=False, queryset=Person.objects.all(), widget=forms.Select(attrs={'class':'form-control'}))
    dailyavailstart_1 = forms.TimeField(label='On Duty', required=True, widget=forms.TimeInput(attrs={'class':'form-control', }, format='%H%M'), input_formats=['%H%M'],)
    dailyavailstop_1 = forms.TimeField(label='Off Duty', required=False, widget=forms.TimeInput(attrs={'class':'form-control', }, format='%H%M'), input_formats=['%H%M'],)
    remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={'class':'form-control', 'rows': 2}))
    ldo = forms.DateField(label='Last Day Off', required=False, widget=forms.DateInput(attrs={'class':'form-control', }), initial=datenow)
    opsbase = forms.ModelChoiceField(label='Ops Base', required = False, queryset=Airbase.objects.all(), widget=forms.Select(attrs={'class':'form-control', })) 
    crewcount = forms.IntegerField(label='Crew Count', required=False, widget=forms.TextInput(attrs={'class':'form-control',}))
    class Meta:
        model = Mission
        exclude = ['author', 'dailyavailstart', 'dailyavailstop', 'nonavailstart','nonavailstop',]
        fields = ('airplane', 'startdate', 'remarks', 'dailyavailstart_1', 'dailyavailstop_1', 'pilot', 'copilot', 'othercrew', 'ldo', 'opsbase', 'crewcount', )

class AirbaseMissionAdd(forms.ModelForm):
    airplane = forms.ModelChoiceField(label='Airplane', required=True, queryset=Airplane.objects.all(), widget=forms.Select(attrs={'class':'form-control'})) 
    startdate = forms.DateField(label='Start', required=True, widget=forms.DateInput(attrs={'class':'form-control', }), initial=timenow)
    pilot = forms.ModelChoiceField(label='Pilot', required=False, queryset=Person.objects.filter(job__iexact='Pilot'), widget=forms.Select(attrs={'class':'form-control'}))
    copilot = forms.ModelChoiceField(label='Copilot', required=False, queryset=Person.objects.filter(job__iexact='Pilot'), widget=forms.Select(attrs={'class':'form-control'}))
    othercrew = forms.ModelChoiceField(label='Other', required=False, queryset=Person.objects.all(), widget=forms.Select(attrs={'class':'form-control'}))
    dailyavailstart_1 = forms.TimeField(label='On Duty', required=True, widget=forms.TimeInput(attrs={'class':'form-control', }, format='%H%M'), input_formats=['%H%M'],)
    dailyavailstop_1 = forms.TimeField(label='Off Duty', required=False, widget=forms.TimeInput(attrs={'class':'form-control', }, format='%H%M'), input_formats=['%H%M'],)
    remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={'class':'form-control', 'rows': 2}))
    class Meta:
        model = Mission
        exclude = ['author', 'dailyavailstart', 'dailyavailstop', 'nonavailstart','nonavailstop', ]
        fields = ('airplane', 'startdate', 'remarks', 'dailyavailstart_1', 'dailyavailstop_1', 'pilot', 'copilot', 'othercrew')

class AirplaneMissionAdd(forms.ModelForm):
    startdate = forms.DateField(label='Start', required=True, widget=forms.DateInput(attrs={'class':'form-control', }), initial=timenow)
    airplane = forms.ModelChoiceField(label='Airplane', required=True, queryset=Airplane.objects.all(), widget=forms.HiddenInput(attrs={'class':'form-control'}))
    pilot = forms.ModelChoiceField(label='Pilot', required=False, queryset=Person.objects.filter(job__iexact='Pilot'), widget=forms.Select(attrs={'class':'form-control'}))
    copilot = forms.ModelChoiceField(label='Copilot', required=False, queryset=Person.objects.filter(job__iexact='Pilot'), widget=forms.Select(attrs={'class':'form-control'}))
    othercrew = forms.ModelChoiceField(label='Other', required=False, queryset=Person.objects.all(), widget=forms.Select(attrs={'class':'form-control'}))
    dailyavailstart_1 = forms.TimeField(label='On Duty', required=True, widget=forms.TimeInput(attrs={'class':'form-control', }, format='%H%M'), input_formats=['%H%M'],)
    dailyavailstop_1 = forms.TimeField(label='Off Duty', required=False, widget=forms.TimeInput(attrs={'class':'form-control', }, format='%H%M'), input_formats=['%H%M'],)
    remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={'class':'form-control', 'rows': 2}))
    class Meta:
        model = Mission
        exclude = ['author', 'dailyavailstart', 'dailyavailstop', 'nonavailstart','nonavailstop',]
        fields = ('airplane', 'startdate', 'remarks', 'dailyavailstart_1', 'dailyavailstop_1', 'pilot', 'copilot', 'othercrew')

class IncidentMissionAdd(forms.ModelForm):
    airplane = forms.ModelChoiceField(label='Airplane', required=True, queryset=Airplane.objects.all(), widget=forms.Select(attrs={'class':'form-control'})) 
    startdate = forms.DateField(label='Start', required=True, widget=forms.DateInput(attrs={'class':'form-control', }),)
    pilot = forms.ModelChoiceField(label='Pilot', required=False, queryset=Person.objects.filter(job__iexact='Pilot'), widget=forms.Select(attrs={'class':'form-control'}))
    copilot = forms.ModelChoiceField(label='Copilot', required=False, queryset=Person.objects.filter(job__iexact='Pilot'), widget=forms.Select(attrs={'class':'form-control'}))
    othercrew = forms.ModelChoiceField(label='Other', required=False, queryset=Person.objects.all(), widget=forms.Select(attrs={'class':'form-control'}))
    dailyavailstart_1 = forms.TimeField(label='On Duty', required=True, widget=forms.TimeInput(attrs={'class':'form-control', }, format='%H%M'), input_formats=['%H%M'],)
    dailyavailstop_1 = forms.TimeField(label='Off Duty', required=False, widget=forms.TimeInput(attrs={'class':'form-control', }, format='%H%M'), input_formats=['%H%M'],)
    remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={'class':'form-control', 'rows': 2}))
    class Meta:
        model = Mission
        exclude = ['author', 'dailyavailstart', 'dailyavailstop', 'nonavailstart','nonavailstop',]
        fields = ('airplane', 'startdate', 'remarks', 'dailyavailstart_1', 'dailyavailstop_1', 'pilot', 'copilot', 'othercrew')

class AirplaneIncidentMissionAdd(forms.ModelForm):
    airplane = forms.ModelChoiceField(label='Airplane', required=True, queryset=Airplane.objects.all(), widget=forms.HiddenInput(attrs={'class':'form-control'})) 
    startdate = forms.DateField(label='Start', required=True, widget=forms.DateInput(attrs={'class':'form-control', }),)
    pilot = forms.ModelChoiceField(label='Pilot', required=False, queryset=Person.objects.filter(job__iexact='Pilot'), widget=forms.Select(attrs={'class':'form-control'}))
    copilot = forms.ModelChoiceField(label='Copilot', required=False, queryset=Person.objects.filter(job__iexact='Pilot'), widget=forms.Select(attrs={'class':'form-control'}))
    othercrew = forms.ModelChoiceField(label='Other', required=False, queryset=Person.objects.all(), widget=forms.Select(attrs={'class':'form-control'}))
    dailyavailstart_1 = forms.TimeField(label='On Duty', required=True, widget=forms.TimeInput(attrs={'class':'form-control', }, format='%H%M'), input_formats=['%H%M'],)
    dailyavailstop_1 = forms.TimeField(label='Off Duty', required=False, widget=forms.TimeInput(attrs={'class':'form-control', }, format='%H%M'), input_formats=['%H%M'],)
    remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={'class':'form-control', 'rows': 2}))
    class Meta:
        model = Mission
        exclude = ['author', 'dailyavailstart', 'dailyavailstop', 'nonavailstart','nonavailstop',]
        fields = ('airplane', 'startdate', 'remarks', 'dailyavailstart_1', 'dailyavailstop_1', 'pilot', 'copilot', 'othercrew')

class MissionDelete(forms.ModelForm):
    class Meta:
        model = Mission
        fields = []

### Flight

class TripAdd(forms.ModelForm):
    class Meta:
        model = Trip
        exclude = ['author',]

EXTRA_CHOICES = [
   ('', '---'),
   ('m', '.Move'),
   ('s', '.NonAvail'),
   ('x', '.Extended'),
   ('d', '.Divert'),
   ('o', '.Other'),
]

class MissionTripAdd(forms.ModelForm):
    incident = forms.ModelChoiceField(label='Incident', required=True, queryset=Incident.objects.all(), widget=forms.Select(attrs={'class':'form-control', })) 
    frombase = forms.ModelChoiceField(queryset=Airbase.objects.all(), widget=forms.Select(attrs={'class':'form-control', }))
    tobase = forms.ChoiceField(choices=(), required=False, widget=forms.Select(attrs={'class':'form-control pull-right', }))
    planestart = forms.SplitDateTimeField(label='Plane Start', required=True, widget=forms.SplitDateTimeWidget(attrs={'class':'form-control', 'placeholder':'0000', }, time_format='%H%M'), input_time_formats=['%H%M'],)
    planestop = forms.SplitDateTimeField(label='Plane Stop', required=False, widget=forms.SplitDateTimeWidget(attrs={'class':'form-control', 'placeholder':'0000', }, time_format='%H%M'), input_time_formats=['%H%M'],)
    retardantgal = forms.IntegerField(required=True, widget=forms.TextInput(attrs={ 'class': 'form-control', 'placeholder':'0', }), initial="0")
    rtype = forms.ChoiceField(label='Retardant Type', required=False, choices=RET_CHOICES, widget=forms.Select(attrs={'class':'form-control', }),)
    misccost = forms.DecimalField(required=False, widget=forms.TextInput(attrs={ 'class': 'form-control prepended-input', 'placeholder':'0',}), initial="0")
    movecount = forms.IntegerField(required=False, widget=forms.TextInput(attrs={ 'class': 'form-control', 'placeholder':'0',}), initial="0")
    fmso = forms.CharField(label='Action', required=False, widget=forms.HiddenInput(attrs={'class':'form-control', }),)

    class Meta:
        model = Trip
        exclude = ['author','mission','weightbalance','movecount']

    def __init__(self, *args, **kwargs):
        super(MissionTripAdd, self).__init__(*args, **kwargs)
        qchoices = [(a.id, a) for a in Airbase.objects.all()]
        choices = EXTRA_CHOICES
        choices.extend(qchoices)
        self.fields['tobase'].choices = choices

    def clean(self):
        cleaned_data = super(MissionTripAdd, self).clean()
        tobase = cleaned_data.get('tobase')
        if tobase not in 'msxdo':
            cleaned_data['tobase'] = Airbase.objects.get(id=tobase)
            cleaned_data['fmso'] = 'f'
        #cleaned_data('tobase') = Airbase.objects.get(id=tobase)
        if tobase == 'm':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'm'
        if tobase == 's':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 's'
        if tobase == 'x':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'x'
        if tobase == 'd':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'd'
        if tobase == 'o':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'o'
        if tobase == '':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = ''
        return cleaned_data

class AirplaneTripAdd(forms.ModelForm):
    incident = forms.ModelChoiceField(label='Incident', required=True, queryset=Incident.objects.all(), widget=forms.Select(attrs={'class':'form-control', })) 
    frombase = forms.ModelChoiceField(queryset=Airbase.objects.all(), widget=forms.Select(attrs={'class':'form-control', }))
    tobase = forms.ChoiceField(choices=(), required=False, widget=forms.Select(attrs={'class':'form-control pull-right', }))
    planestart = forms.SplitDateTimeField(label='Plane Start', required=True, widget=forms.SplitDateTimeWidget(attrs={'class':'form-control', 'placeholder':'0000', }, time_format='%H%M'), input_time_formats=['%H%M'],)
    planestop = forms.SplitDateTimeField(label='Plane Stop', required=False, widget=forms.SplitDateTimeWidget(attrs={'class':'form-control', 'placeholder':'0000', }, time_format='%H%M'), input_time_formats=['%H%M'],)
    retardantgal = forms.IntegerField(required=True, widget=forms.TextInput(attrs={ 'class': 'form-control', 'placeholder':'0', }), initial="0")
    rtype = forms.ChoiceField(label='Retardant Type', required=False, choices=RET_CHOICES, widget=forms.Select(attrs={'class':'form-control', }),)
    misccost = forms.DecimalField(required=False, widget=forms.TextInput(attrs={ 'class': 'form-control prepended-input', 'placeholder':'0',}), initial="0")
    movecount = forms.IntegerField(required=False, widget=forms.TextInput(attrs={ 'class': 'form-control', 'placeholder':'0',}), initial="0")
    fmso = forms.CharField(label='Action', required=False, widget=forms.HiddenInput(attrs={'class':'form-control', }),)
    class Meta:
        model = Trip
        exclude = ['author','mission','weightbalance','movecount']

    def __init__(self, *args, **kwargs):
        super(AirplaneTripAdd, self).__init__(*args, **kwargs)
        qchoices = [(a.id, a) for a in Airbase.objects.all()]
        choices = EXTRA_CHOICES
        choices.extend(qchoices)
        self.fields['tobase'].choices = choices

    def clean(self):
        cleaned_data = super(AirplaneTripAdd, self).clean()
        tobase = cleaned_data.get('tobase')
        if tobase not in 'msxdo':
            cleaned_data['tobase'] = Airbase.objects.get(id=tobase)
            cleaned_data['fmso'] = 'f'
        #cleaned_data('tobase') = Airbase.objects.get(id=tobase)
        if tobase == 'm':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'm'
        if tobase == 's':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 's'
        if tobase == 'x':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'x'
        if tobase == 'd':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'd'
        if tobase == 'o':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'o'
        if tobase == '':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = ''
        return cleaned_data

class IncidentTripAdd(forms.ModelForm):
    airplane = forms.ModelChoiceField(label='Airplane', required=True, queryset=Airplane.objects.all(), widget=forms.Select(attrs={'class':'form-control', })) 
    frombase = forms.ModelChoiceField(queryset=Airbase.objects.all(), widget=forms.Select(attrs={'class':'form-control', }))
    tobase = forms.ChoiceField(choices=(), required=False, widget=forms.Select(attrs={'class':'form-control pull-right', }))
    planestart = forms.SplitDateTimeField(label='Plane Start', required=True, widget=forms.SplitDateTimeWidget(attrs={'class':'form-control', 'placeholder':'0000', }, time_format='%H%M'), input_time_formats=['%H%M'],)
    planestop = forms.SplitDateTimeField(label='Plane Stop', required=False, widget=forms.SplitDateTimeWidget(attrs={'class':'form-control', 'placeholder':'0000', }, time_format='%H%M'), input_time_formats=['%H%M'],)
    retardantgal = forms.IntegerField(required=True, widget=forms.TextInput(attrs={ 'class': 'form-control', 'placeholder':'0', }), initial="0")
    rtype = forms.ChoiceField(label='Retardant Type', required=False, choices=RET_CHOICES, widget=forms.Select(attrs={'class':'form-control', }),)
    misccost = forms.DecimalField(required=False, widget=forms.TextInput(attrs={ 'class': 'form-control prepended-input', 'placeholder':'0',}), initial="0")
    movecount = forms.IntegerField(required=False, widget=forms.TextInput(attrs={ 'class': 'form-control', 'placeholder':'0',}), initial="0")
    fmso = forms.CharField(label='Action', required=False, widget=forms.HiddenInput(attrs={'class':'form-control', }),)
    class Meta:
        model = Trip
        exclude = ['author','mission','weightbalance','movecount']

    def __init__(self, *args, **kwargs):
        super(IncidentTripAdd, self).__init__(*args, **kwargs)
        qchoices = [(a.id, a) for a in Airbase.objects.all()]
        choices = EXTRA_CHOICES
        choices.extend(qchoices)
        self.fields['tobase'].choices = choices

    def clean(self):
        cleaned_data = super(IncidentTripAdd, self).clean()
        tobase = cleaned_data.get('tobase')
        if tobase not in 'msxdo':
            cleaned_data['tobase'] = Airbase.objects.get(id=tobase)
            cleaned_data['fmso'] = 'f'
        #cleaned_data('tobase') = Airbase.objects.get(id=tobase)
        if tobase == 'm':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'm'
        if tobase == 's':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 's'
        if tobase == 'x':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'x'
        if tobase == 'd':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'd'
        if tobase == 'o':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'o'
        if tobase == '':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = ''
        return cleaned_data

class TripDelete(forms.ModelForm):
    class Meta:
        model = Trip
        fields = []

class AirplaneIncidentTripAdd(forms.ModelForm):
    startdate = forms.DateField(label='Start', required=True, widget=forms.DateInput(attrs={'class':'form-control', }),)
    frombase = forms.ModelChoiceField(queryset=Airbase.objects.all(), widget=forms.Select(attrs={'class':'form-control', }))
    tobase = forms.ChoiceField(choices=(), required=False, widget=forms.Select(attrs={'class':'form-control pull-right',}))
    planestart = forms.SplitDateTimeField(label='Plane Start', required=True, widget=forms.SplitDateTimeWidget(attrs={'class':'form-control', 'placeholder':'0000', }, time_format='%H%M'), input_time_formats=['%H%M'],)
    planestop = forms.SplitDateTimeField(label='Plane Stop', required=False, widget=forms.SplitDateTimeWidget(attrs={'class':'form-control', 'placeholder':'0000', }, time_format='%H%M'), input_time_formats=['%H%M'],)
    retardantgal = forms.IntegerField(required=True, widget=forms.TextInput(attrs={ 'class': 'form-control', 'placeholder':'0', }), initial="0")
    rtype = forms.ChoiceField(label='Retardant Type', required=False, choices=RET_CHOICES, widget=forms.Select(attrs={'class':'form-control', }),)
    misccost = forms.DecimalField(required=False, widget=forms.TextInput(attrs={ 'class': 'form-control prepended-input', 'placeholder':'0',}), initial="0")
    movecount = forms.IntegerField(required=False, widget=forms.TextInput(attrs={ 'class': 'form-control', 'placeholder':'0',}), initial="0")
    fmso = forms.CharField(label='Action', required=False, widget=forms.HiddenInput(attrs={'class':'form-control', }),)

    class Meta:
        model = Trip
        exclude = ['author','mission','weightbalance','movecount']

    def __init__(self, *args, **kwargs):
        super(AirplaneIncidentTripAdd, self).__init__(*args, **kwargs)
        qchoices = [(a.id, a) for a in Airbase.objects.all()]
        choices = EXTRA_CHOICES
        choices.extend(qchoices)
        self.fields['tobase'].choices = choices

    def clean(self):
        cleaned_data = super(AirplaneIncidentTripAdd, self).clean()
        tobase = cleaned_data.get('tobase')
        if tobase not in 'msxdo':
            cleaned_data['tobase'] = Airbase.objects.get(id=tobase)
            cleaned_data['fmso'] = 'f'
        #cleaned_data('tobase') = Airbase.objects.get(id=tobase)
        if tobase == 'm':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'm'
        if tobase == 's':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 's'
        if tobase == 'x':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'x'
        if tobase == 'd':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'd'
        if tobase == 'o':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'o'
        if tobase == '':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = ''
        return cleaned_data

class AirplaneDetailAdd(forms.ModelForm):
    startdate = forms.DateField(label='Start', required=True, widget=forms.DateInput(attrs={'class':'form-control', }),)
    incident = forms.ModelChoiceField(label='Incident', required=True, queryset=Incident.objects.all(), widget=forms.Select(attrs={'class':'form-control', })) 
    frombase = forms.ModelChoiceField(queryset=Airbase.objects.all(), widget=forms.Select(attrs={'class':'form-control', }))
    tobase = forms.ChoiceField(choices=(), required=False, widget=forms.Select(attrs={'class':'form-control pull-right', }))
    planestart = forms.SplitDateTimeField(label='Plane Start', required=True, widget=forms.SplitDateTimeWidget(attrs={'class':'form-control', 'placeholder':'0000', }, time_format='%H%M'), input_time_formats=['%H%M'],)
    planestop = forms.SplitDateTimeField(label='Plane Stop', required=False, widget=forms.SplitDateTimeWidget(attrs={'class':'form-control', 'placeholder':'0000', }, time_format='%H%M'), input_time_formats=['%H%M'],)
    retardantgal = forms.IntegerField(required=True, widget=forms.TextInput(attrs={ 'class': 'form-control', 'placeholder':'0', }), initial="0")
    rtype = forms.ChoiceField(label='Retardant Type', required=False, choices=RET_CHOICES, widget=forms.Select(attrs={'class':'form-control', }),)
    misccost = forms.DecimalField(required=False, widget=forms.TextInput(attrs={ 'class': 'form-control prepended-input', 'placeholder':'0',}), initial="0")
    movecount = forms.IntegerField(required=False, widget=forms.TextInput(attrs={ 'class': 'form-control', 'placeholder':'0',}), initial="0")
    fmso = forms.CharField(label='Action', required=False, widget=forms.HiddenInput(attrs={'class':'form-control', }),)

    class Meta:
        model = Trip
        exclude = ['author','mission','weightbalance','movecount']

    def __init__(self, *args, **kwargs):
        super(AirplaneDetailAdd, self).__init__(*args, **kwargs)
        qchoices = [(a.id, a) for a in Airbase.objects.all()]
        choices = EXTRA_CHOICES
        choices.extend(qchoices)
        self.fields['tobase'].choices = choices

    def clean(self):
        cleaned_data = super(AirplaneDetailAdd, self).clean()
        tobase = cleaned_data.get('tobase')
        if tobase not in 'msxdo':
            cleaned_data['tobase'] = Airbase.objects.get(id=tobase)
            cleaned_data['fmso'] = 'f'
        #cleaned_data('tobase') = Airbase.objects.get(id=tobase)
        if tobase == 'm':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'm'
        if tobase == 's':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 's'
        if tobase == 'x':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'x'
        if tobase == 'd':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'd'
        if tobase == 'o':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'o'
        if tobase == '':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = ''
        return cleaned_data


class IncidentDetailAdd(forms.ModelForm):
    startdate = forms.DateField(label='Start', required=True, widget=forms.DateInput(attrs={'class':'form-control', }),)
    airplane = forms.ModelChoiceField(label='Airplane', required=True, queryset=Airplane.objects.all(), widget=forms.Select(attrs={'class':'form-control', }))
    frombase = forms.ModelChoiceField(queryset=Airbase.objects.all(), widget=forms.Select(attrs={'class':'form-control', }))
    tobase = forms.ChoiceField(choices=(), required=False, widget=forms.Select(attrs={'class':'form-control pull-right',}))
    planestart = forms.SplitDateTimeField(label='Plane Start', required=True, widget=forms.SplitDateTimeWidget(attrs={'class':'form-control', 'placeholder':'0000', }, time_format='%H%M'), input_time_formats=['%H%M'],)
    planestop = forms.SplitDateTimeField(label='Plane Stop', required=False, widget=forms.SplitDateTimeWidget(attrs={'class':'form-control', 'placeholder':'0000', }, time_format='%H%M'), input_time_formats=['%H%M'],)
    retardantgal = forms.IntegerField(required=True, widget=forms.TextInput(attrs={ 'class': 'form-control', 'placeholder':'0', }), initial="0")
    rtype = forms.ChoiceField(label='Retardant Type', required=False, choices=RET_CHOICES, widget=forms.Select(attrs={'class':'form-control', }),)
    misccost = forms.DecimalField(required=False, widget=forms.TextInput(attrs={ 'class': 'form-control prepended-input', 'placeholder':'0',}), initial="0")
    movecount = forms.IntegerField(required=False, widget=forms.TextInput(attrs={ 'class': 'form-control', 'placeholder':'0',}), initial="0")
    fmso = forms.CharField(label='Action', required=False, widget=forms.HiddenInput(attrs={'class':'form-control', }),)

    class Meta:
        model = Trip
        exclude = ['author','mission','weightbalance','movecount']

    def __init__(self, *args, **kwargs):
        super(IncidentDetailAdd, self).__init__(*args, **kwargs)
        qchoices = [(a.id, a) for a in Airbase.objects.all()]
        choices = EXTRA_CHOICES
        choices.extend(qchoices)
        self.fields['tobase'].choices = choices

    def clean(self):
        cleaned_data = super(IncidentDetailAdd, self).clean()
        tobase = cleaned_data.get('tobase')
        if tobase not in 'msxdo':
            cleaned_data['tobase'] = Airbase.objects.get(id=tobase)
            cleaned_data['fmso'] = 'f'
        #cleaned_data('tobase') = Airbase.objects.get(id=tobase)
        if tobase == 'm':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'm'
        if tobase == 's':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 's'
        if tobase == 'x':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'x'
        if tobase == 'd':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'd'
        if tobase == 'o':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'o'
        if tobase == '':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = ''
        return cleaned_data


class AirplaneIncidentDateTripAdd(forms.ModelForm):
    frombase = forms.ModelChoiceField(queryset=Airbase.objects.all(), widget=forms.Select(attrs={'class':'form-control',}))
    tobase = forms.ChoiceField(choices=(), required=False, widget=forms.Select(attrs={'class':'form-control pull-right', }))
    planestart = forms.SplitDateTimeField(label='Plane Start', required=True, widget=forms.SplitDateTimeWidget(attrs={'class':'form-control', 'placeholder':'0000', }, time_format='%H%M'), input_time_formats=['%H%M'],)
    planestop = forms.SplitDateTimeField(label='Plane Stop', required=False, widget=forms.SplitDateTimeWidget(attrs={'class':'form-control', 'placeholder':'0000', }, time_format='%H%M'), input_time_formats=['%H%M'],)
    retardantgal = forms.IntegerField(required=True, widget=forms.TextInput(attrs={ 'class': 'form-control', 'placeholder':'0', }), initial="0")
    rtype = forms.ChoiceField(label='Retardant Type', required=False, choices=RET_CHOICES, widget=forms.Select(attrs={'class':'form-control', }),)
    misccost = forms.DecimalField(required=False, widget=forms.TextInput(attrs={ 'class': 'form-control prepended-input', 'placeholder':'0',}), initial="0")
    movecount = forms.IntegerField(required=False, widget=forms.TextInput(attrs={ 'class': 'form-control', 'placeholder':'0',}), initial="0")
    fmso = forms.CharField(label='Action', required=False, widget=forms.HiddenInput(attrs={'class':'form-control', }),)

    class Meta:
        model = Trip
        exclude = ['author','mission','weightbalance','movecount']

    def __init__(self, *args, **kwargs):
        super(AirplaneIncidentDateTripAdd, self).__init__(*args, **kwargs)
        qchoices = [(a.id, a) for a in Airbase.objects.all()]
        choices = EXTRA_CHOICES
        choices.extend(qchoices)
        self.fields['tobase'].choices = choices

    def clean(self):
        cleaned_data = super(AirplaneIncidentDateTripAdd, self).clean()
        tobase = cleaned_data.get('tobase')
        if tobase not in 'msxdo':
            cleaned_data['tobase'] = Airbase.objects.get(id=tobase)
            cleaned_data['fmso'] = 'f'
        #cleaned_data('tobase') = Airbase.objects.get(id=tobase)
        if tobase == 'm':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'm'
        if tobase == 's':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 's'
        if tobase == 'x':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'x'
        if tobase == 'd':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'd'
        if tobase == 'o':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = 'o'
        if tobase == '':
            cleaned_data['tobase'] = None
            cleaned_data['fmso'] = ''
        return cleaned_data

class TripDelete(forms.ModelForm):
    class Meta:
        model = Trip
        fields = []

### Fee, Cost, Rate

# ms = Airplane.objects.values_list('modelname', 'modelname').distinct()
# mx = [ tuple(item) for item in ms]
# mx = sorted(set(mx))

class LandingfeeAdd(forms.ModelForm):
    airbase = forms.ModelChoiceField(queryset=Airbase.objects.all(), widget=forms.Select())
    perwhat = forms.ChoiceField(label='Model', required=True, choices=MOD_CHOICES)
    cost = forms.DecimalField(required=True, widget=forms.TextInput(attrs={ 'class': 'form-control prepended-input', 'placeholder':'0.00',}),)
    effectivedate = forms.SplitDateTimeField(label='Date Effective', required=True, widget=forms.SplitDateTimeWidget(attrs={'class':'form-control', }, time_format='%H%M'), input_time_formats=['%H%M'], initial=timenow)
    class Meta:
        model = Landingfee
        exclude = ['author',]
        fields = ('airbase', 'perwhat', 'cost', 'effectivedate', )

class AirbaseLandingfeeAdd(forms.ModelForm):
    perwhat = forms.ChoiceField(label='Model', required=True, choices=MOD_CHOICES) 
    cost = forms.DecimalField(required=True, widget=forms.TextInput(attrs={ 'class': 'form-control prepended-input', 'placeholder':'0.00',}),)
    effectivedate = forms.SplitDateTimeField(label='Date Effective', required=True, widget=forms.SplitDateTimeWidget(attrs={'class':'form-control', }, time_format='%H%M'), input_time_formats=['%H%M'], initial=timenow)
    class Meta:
        model = Landingfee
        exclude = ['author','airbase',]
        fields = ('perwhat', 'cost', 'effectivedate', )

class LandingfeeDelete(forms.ModelForm):
    class Meta:
        model = Landingfee
        fields = []

class RetardantfeeAdd(forms.ModelForm):
    airbase = forms.ModelChoiceField(queryset=Airbase.objects.all(), widget=forms.Select(attrs={'class':'form-control', }))
    rtype = forms.ChoiceField(label='Retardant Type', choices=RET_CHOICES, widget=forms.Select(attrs={'class':'form-control', }),)
    cost = forms.DecimalField(required=True, widget=forms.TextInput(attrs={ 'class': 'form-control prepended-input', 'placeholder':'0.00',}),)
    flat = forms.DecimalField(required=True, widget=forms.TextInput(attrs={ 'class': 'form-control prepended-input', 'placeholder':'0.00',}),)
    volume = forms.IntegerField(required=True, widget=forms.TextInput(attrs={ 'class': 'form-control', 'placeholder':'0', }), initial="0")
    effectivedate = forms.SplitDateTimeField(label='Date Effective', required=True, widget=forms.SplitDateTimeWidget(attrs={'class':'form-control', }, time_format='%H%M'), input_time_formats=['%H%M'], initial=timenow)
    class Meta:
        model = Retardantfee
        exclude = ['author',]
        fields = ('airbase', 'rtype', 'cost', 'flat', 'volume', 'effectivedate', )

class AirbaseRetardantfeeAdd(forms.ModelForm):
    rtype = forms.ChoiceField(label='Retardant Type', choices=RET_CHOICES, widget=forms.Select(attrs={'class':'form-control', }),)
    cost = forms.DecimalField(required=True, widget=forms.TextInput(attrs={ 'class': 'form-control prepended-input', 'placeholder':'0.00',}),)
    flat = forms.DecimalField(required=True, widget=forms.TextInput(attrs={ 'class': 'form-control prepended-input', 'placeholder':'0.00',}),)
    volume = forms.IntegerField(required=True, widget=forms.TextInput(attrs={ 'class': 'form-control', 'placeholder':'0', }), initial="0")
    effectivedate = forms.SplitDateTimeField(label='Date Effective', required=True, widget=forms.SplitDateTimeWidget(attrs={'class':'form-control', }, time_format='%H%M'), input_time_formats=['%H%M'], initial=timenow)
    class Meta:
        model = Retardantfee
        exclude = ['author','airbase',]
        fields = ('rtype', 'cost', 'flat', 'volume', 'effectivedate', )

class RetardantfeeDelete(forms.ModelForm):
    class Meta:
        model = Retardantfee
        fields = []

class RateAdd(forms.ModelForm):
    airplane = forms.ModelChoiceField(label='Airplane', required=True, queryset=Airplane.objects.all(), widget=forms.Select(attrs={'class':'form-control',})) 
    ratetype = forms.ChoiceField(label='Rate Type', required=True, choices=RATE_CHOICES, widget=forms.Select(attrs={ 'class': 'form-control',}),)
    perwhat = forms.ChoiceField(label='Unit', required=True, choices=PER_CHOICES, widget=forms.Select(attrs={ 'class': 'form-control',}),)
    cost = forms.DecimalField(required=True, widget=forms.TextInput(attrs={ 'class': 'form-control prepended-input', 'placeholder':'0.00',}),)
    incident = forms.ModelChoiceField(label='Funding', required=False, queryset=Incident.objects.all(), widget=forms.Select(attrs={'class':'form-control', })) 
    effectivedate = forms.SplitDateTimeField(label='Date Effective', required=True, widget=forms.SplitDateTimeWidget(attrs={'class':'form-control', }, time_format='%H%M'), input_time_formats=['%H%M'], initial=timenow)

    class Meta:
        model = Rate
        exclude = ['author',]
        fields = ('airplane', 'ratetype', 'cost', 'perwhat', 'incident', 'effectivedate',  )

    def clean_ratetype(self):
        data = self.cleaned_data.get('ratetype')
        if data == self.fields['ratetype'].choices[0][0]:
            raise forms.ValidationError('This field is required.')
        return data

    def clean_perwhat(self):
        data = self.cleaned_data.get('perwhat')
        if data == self.fields['perwhat'].choices[0][0]:
            raise forms.ValidationError('This field is required.')
        return data

class AirplaneRateAdd(forms.ModelForm):
    ratetype = forms.ChoiceField(label='Rate Type', required=True, choices=RATE_CHOICES, widget=forms.Select(attrs={ 'class': 'form-control',}),)
    perwhat = forms.ChoiceField(label='Unit', required=True, choices=PER_CHOICES, widget=forms.Select(attrs={'class': 'form-control', }),)
    cost = forms.DecimalField(required=True, widget=forms.TextInput(attrs={ 'class': 'form-control prepended-input', 'placeholder':'0.00',}),)
    incident = forms.ModelChoiceField(label='Funding', required=False, queryset=Incident.objects.all(), widget=forms.Select(attrs={'class':'form-control',})) 
    effectivedate = forms.SplitDateTimeField(label='Date Effective', required=True, widget=forms.SplitDateTimeWidget(attrs={'class':'form-control', }, time_format='%H%M'), input_time_formats=['%H%M'], initial=timenow)
    class Meta:
        model = Rate
        exclude = ['author','airplane',]
        fields = ('ratetype', 'cost', 'perwhat', 'incident', 'effectivedate', )

    def clean_ratetype(self):
        data = self.cleaned_data.get('ratetype')
        if data == self.fields['ratetype'].choices[0][0]:
            raise forms.ValidationError('This field is required.')
        return data

    def clean_perwhat(self):
        data = self.cleaned_data.get('perwhat')
        if data == self.fields['perwhat'].choices[0][0]:
            raise forms.ValidationError('This field is required.')
        return data

class RateDelete(forms.ModelForm):
    class Meta:
        model = Rate
        fields = []

class ContractAdd(forms.ModelForm):
    airplane = forms.ModelChoiceField(label='Airplane', required=True, queryset=Airplane.objects.all(), widget=forms.Select(attrs={'class':'form-control'})) 
    ct = forms.ChoiceField(label='Contract Type', required=False, choices=CT_CHOICES, widget=forms.Select(attrs={'class': 'form-control',}),)
    effectivedate = forms.DateField(label='Date Effective', required=True, widget=forms.TextInput(attrs={'class': 'form-control',}), initial=datenow)
    cor = forms.ModelChoiceField(label='COR', required = False, queryset=User.objects.filter(groups__name='flight-user'), widget=forms.Select(attrs={'class':'form-control',})) 
    adminbase = forms.ModelChoiceField(label='Admin Base', required = True, queryset=Airbase.objects.all(), widget=forms.Select(attrs={'class':'form-control',})) 
    contractor = forms.CharField(label='Contractor', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Contractor'}))
    contract = forms.CharField(label='Contract', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Contract'}))
    contractgallons = forms.IntegerField(label='Contract Gal', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'gal'}))
    daysoff = forms.CharField(label='Days Off', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'0111110', 'onfocus': 'if (this.value==\'SMTWTFS\') this.value = \'\''}), initial='SMTWTFS')
    crewcount = forms.IntegerField(label='Crew Count', required=False, widget=forms.TextInput(attrs={'class':'form-control',}))
    class Meta:
        model = Contract
        exclude = ['author','ends',]
        fields = ('airplane','ct','effectivedate', 'contractor', 'contract', 'adminbase', 'cor', 'contractgallons', 'daysoff', 'crewcount', )

class AirplaneContractAdd(forms.ModelForm):
    ct = forms.ChoiceField(label='Contract Type', required=False, choices=CT_CHOICES, widget=forms.Select(attrs={'class': 'form-control', }),)
    effectivedate = forms.DateField(label='Date Effective', required=True, widget=forms.TextInput(attrs={'class': 'form-control',}), initial=datenow)
    cor = forms.ModelChoiceField(label='COR', required = False, queryset=User.objects.filter(groups__name='flight-user'), widget=forms.Select(attrs={'class':'form-control', })) 
    adminbase = forms.ModelChoiceField(label='Admin Base', required = False, queryset=Airbase.objects.all(), widget=forms.Select(attrs={'class':'form-control', })) 
    contractor = forms.CharField(label='Contractor', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Contractor'}))
    contract = forms.CharField(label='Contract', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Contract'}))
    contractgallons = forms.IntegerField(label='Contract Gal', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'gal'}))
    daysoff = forms.CharField(label='Days Off', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'0111110', 'onfocus': 'if (this.value==\'SMTWTFS\') this.value = \'\''}), initial='SMTWTFS')
    crewcount = forms.IntegerField(label='Crew Count', required=False, widget=forms.TextInput(attrs={'class':'form-control', }))
    class Meta:
        model = Contract
        exclude = ['author','airplane','ends',]
        fields = ('effectivedate', 'ct', 'contractor', 'contract', 'adminbase', 'cor', 'contractgallons', 'daysoff', 'crewcount', )

class ContractDelete(forms.ModelForm):
    class Meta:
        model = Contract
        fields = []

### Fueling

class AirplaneFuelingAdd(forms.ModelForm):
    #airplane = forms.ModelChoiceField(label='Airplane', required=True, queryset=Airplane.objects.all(), widget=forms.Select(attrs={'class':'form-control'})) 
    #ct = forms.ChoiceField(label='Contract Type', required=False, choices=CT_CHOICES, widget=forms.Select(attrs={'class': 'form-control',}),)
    #effectivedate = forms.DateField(label='Date Effective', required=True, widget=forms.TextInput(attrs={'class': 'form-control',}), initial=datenow)
    #cor = forms.ModelChoiceField(label='COR', required = False, queryset=User.objects.filter(groups__name='flight-user'), widget=forms.Select(attrs={'class':'form-control',})) 
    #adminbase = forms.ModelChoiceField(label='Admin Base', required = True, queryset=Airbase.objects.all(), widget=forms.Select(attrs={'class':'form-control',})) 
    #contractor = forms.CharField(label='Contractor', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Contractor'}))
    #contract = forms.CharField(label='Contract', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Contract'}))
    #contractgallons = forms.IntegerField(label='Contract Gal', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'gal'}))
    #daysoff = forms.CharField(label='Days Off', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'0111110', 'onfocus': 'if (this.value==\'SMTWTFS\') this.value = \'\''}), initial='SMTWTFS')
    #crewcount = forms.IntegerField(label='Crew Count', required=False, widget=forms.TextInput(attrs={'class':'form-control',}))
    class Meta:
        model = Fueling
        exclude = ['author','airplane',]
        #fields = ('airplane','ct','effectivedate', 'contractor', 'contract', 'adminbase', 'cor', 'contractgallons', 'daysoff', 'crewcount', )

class FuelingAdd(forms.ModelForm):
    airplane = forms.ModelChoiceField(label='Airplane', required=True, queryset=Airplane.objects.all(), widget=forms.Select(attrs={'class':'form-control'})) 
    #ct = forms.ChoiceField(label='Contract Type', required=False, choices=CT_CHOICES, widget=forms.Select(attrs={'class': 'form-control',}),)
    #effectivedate = forms.DateField(label='Date Effective', required=True, widget=forms.TextInput(attrs={'class': 'form-control',}), initial=datenow)
    #cor = forms.ModelChoiceField(label='COR', required = False, queryset=User.objects.filter(groups__name='flight-user'), widget=forms.Select(attrs={'class':'form-control',})) 
    #adminbase = forms.ModelChoiceField(label='Admin Base', required = True, queryset=Airbase.objects.all(), widget=forms.Select(attrs={'class':'form-control',})) 
    #contractor = forms.CharField(label='Contractor', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Contractor'}))
    #contract = forms.CharField(label='Contract', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Contract'}))
    #contractgallons = forms.IntegerField(label='Contract Gal', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'gal'}))
    #daysoff = forms.CharField(label='Days Off', required=False, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'0111110', 'onfocus': 'if (this.value==\'SMTWTFS\') this.value = \'\''}), initial='SMTWTFS')
    #crewcount = forms.IntegerField(label='Crew Count', required=False, widget=forms.TextInput(attrs={'class':'form-control',}))
    class Meta:
        model = Fueling
        exclude = ['author',]
        #fields = ('airplane','ct','effectivedate', 'contractor', 'contract', 'adminbase', 'cor', 'contractgallons', 'daysoff', 'crewcount', )

class FuelingDelete(forms.ModelForm):
    class Meta:
        model = Fueling
        fields = []

### Printout

class PrintMission(forms.ModelForm):
    remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={'class':'form-control', 'rows': 2}))
    class Meta:
        model = Printout
        exclude = ['author','obj_model','obj_id','serialized']

### FAIRS

class MakeModelLoadForm(forms.Form):
    csv = forms.CharField(required=True, widget=forms.Textarea(attrs={ 'class':'form-control', 'rows': 10,}))

    def save(self):
        for line in self.cleaned_data["csv"].splitlines():
            record = csv.reader(line, delimiter=',', quotechar = '"')
            makemodel = line
            amakemodel = MakeModel.objects.create(makemodel=makemodel, author=self.author)
            del line

class MissionCodeLoadForm(forms.Form):
    csv = forms.CharField(required=True, widget=forms.Textarea(attrs={ 'class':'form-control', 'rows': 10,}))

    def save(self):
        for line in self.cleaned_data["csv"].splitlines():
            record = csv.reader(line, delimiter=',', quotechar = '"')
            missioncode = line
            amissioncode = MissionCode.objects.create(missioncode=missioncode, author=self.author)
            del line

class CostTypeLoadForm(forms.Form):
    csv = forms.CharField(required=True, widget=forms.Textarea(attrs={ 'class':'form-control', 'rows': 10,}))

    def save(self):
        for line in self.cleaned_data["csv"].splitlines():
            record = csv.reader(line, delimiter=',', quotechar = '"')
            costtype = line
            acosttype = CostType.objects.create(costtype=costtype, author=self.author)
            del line

class CostEntryForm(forms.ModelForm):
    class Meta:
        model = CostEntry
        #exclude = []
        #exclude = ['author',]
        #fields = []
