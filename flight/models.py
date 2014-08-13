from django.db import models
from django.contrib.auth.models import User, Group
from django.core.files.storage import FileSystemStorage
from django.core.validators import RegexValidator
import re
from localflavor.us.models import USStateField
#from django.contrib.gis.db import models

# Used to display html 'help text' links within Admin App
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
import datetime
import uuid

from timezone_field import TimeZoneField

fs = FileSystemStorage(location='/app/ufs')

def get_userpath(instance, filename):
    return str(instance.user.username + "/" + filename)

def make_uuid():
    return str(uuid.uuid4())

name_regex = re.compile(r'^[a-zA-Z0-9 _\-]+$')
tla_regex = re.compile(r'^[a-zA-Z0-9_\-]+$')
tail_regex = re.compile(r'^[a-zA-Z0-9_\-]+$')
reg_regex = re.compile(r'^[a-zA-Z0-9_]{2}$')

class Person(models.Model):
    created = models.DateTimeField('Created', auto_now_add=True)
    modified = models.DateTimeField('Modified', auto_now=True)
    author = models.ForeignKey(User)
    firstname = models.CharField('FirstName', max_length=80, help_text="First name.", validators=[RegexValidator(regex=name_regex, message='Enter a \'name\' consisting of letters, numbers, spaces or hyphens.')])
    lastname = models.CharField('LastName', max_length=80, help_text="Last name.", validators=[RegexValidator(regex=name_regex, message='Enter a \'name\' consisting of letters, numbers, spaces or hyphens.')])
    job = models.CharField('Job', blank=True, null=True, max_length=20, help_text="Job.", )
    #avatar = models.ImageField('Avatar', blank=True, null=True, storage=ifs, upload_to=get_userpath)
    agency = models.CharField('Agency', max_length=200, blank=True, null=True, default='Not known')
    address = models.CharField('Address', max_length=80, blank=True, null=True, help_text="", )
    city = models.CharField('City', max_length=80, blank=True, null=True, help_text="", )
    state = USStateField('State', max_length=2, blank=True, null=True, help_text="", )
    zip4 = models.CharField('Zip+4', max_length=10, blank=True, null=True, help_text="", )
    telephone = models.CharField('Phone', max_length=10, blank=True, null=True, help_text="Telephone number. No dashes or spaces.", )
    telephone2 = models.CharField('Phone2', max_length=10, blank=True, null=True, help_text="Second telephone number. No dashes or spaces.", )
    email = models.CharField('Email', max_length=80, blank=True, null=True, help_text="Email address.", )
    bio = models.TextField('Bio', max_length=1000, blank=True, null=True, default='The origins of this person are thus far shrouded in mystery.')
    remarks = models.TextField('Remarks', max_length=800, blank=True, null=True, help_text="Remarks.", )

    class Meta:
        db_table = 'flight_person'
        verbose_name = _('person')
        ordering = ('lastname','firstname')
        verbose_name_plural = _('people')
        unique_together = ('firstname', 'lastname')

    def __unicode__(self):
        return u"%s %s" % (self.firstname, self.lastname)

    def get_absolute_url(self):
        return "/person/%s %s/" % self.firstname % self.lastname

    def _get_full_name(self):
        "Returns the person's full name."
        return '%s %s' % (self.firstname, self.lastname)
    full_name = property(_get_full_name)


RET_CHOICES = (
    ('', '--'),
    ('Water', 'Water'),
    ('Gel', 'Gel'),
    ('Foam', 'Foam'),
    ('D75-R', 'D75-R'),
    ('D75-F', 'D75-F'),
    ('P100-F', 'P100-F'),
    ('MVP-F', 'MVP-F'),
    ('259-F', '259-F'),
    ('G75-F', 'G75-F'),
    ('G75-W', 'G75-W'),
    ('LC-95A-R', 'LC-95A-R'),
    ('LC-95A-F', 'LC-95A-F'),
    ('LC-95-W', 'LC-95-W'),
)


class Airbase(models.Model):
    created = models.DateTimeField('Created', auto_now_add=True)
    modified = models.DateTimeField('Modified', auto_now=True)
    author = models.ForeignKey(User, related_name="airbase_author")
    tla = models.CharField('TLA', max_length=3, unique=True, help_text="Airport Code", validators=[RegexValidator(regex=tla_regex, message='Enter an \'airport code\' consisting of letters, numbers or hyphens.')])
    name = models.CharField('Name', max_length=120, unique=True, help_text="Base name.", )
    address = models.CharField('Address', max_length=120, help_text="Address.", )
    city = models.CharField('City', max_length=120, help_text="City.", )
    st = USStateField('State', max_length=2, help_text="State.", )
    tz = TimeZoneField()
    region = models.CharField('Region', max_length=2, help_text="Region number.", validators=[RegexValidator(regex=reg_regex, message='Enter a \'region code\' consisting of two letters or numbers.')])
    postal = models.CharField('Postal', max_length=10, help_text="Postal code.", )
    phone = models.CharField('Phone', max_length=10, help_text="Telephone number. No dashes or spaces.", )
    fax = models.CharField('Fax', max_length=10, blank=True, null=True, help_text="Fax number. No dashes or spaces.", )
    manager = models.ForeignKey(User, related_name="airbase_manager", blank=True, null=True, )
    remarks = models.TextField('Remarks', max_length=800, blank=True, null=True, help_text="Remarks.", )
    rtype = models.CharField('Default Ret Type', blank=True, null=True, max_length=40, choices=RET_CHOICES, help_text="Default retardant type.", )
    #geom = models.GeometryField(blank=True, null=True, )

    class Meta:
        db_table = 'flight_airbase'
        verbose_name = _('airbase')
        verbose_name_plural = _('airbases')
        ordering = ('tla',)

    def __unicode__(self):
        return u"%s" % (self.tla)

    def get_absolute_url(self):
        return "/airbase/%s/" % self.tla

MOD_CHOICES = (
    ('', '--'),
    ('AC-500', 'AC-500'),
    ('AC-690', 'AC-690'),
    ('AT-802', 'AT-802'),
    ('BAE-146', 'BAE-146'),
    ('C-130', 'C-130'),
    ('CL-215', 'CL-215'),
    ('CL-415', 'CL-415'),
    ('Convair 580', 'Convair 580'),
    ('DC-3', 'DC-3'),
    ('DC-7', 'DC-7'),
    ('DC-10', 'DC-10'),
    ('Dornier', 'Dornier'),
    ('King Air', 'King Air'),
    ('OV-10', 'OV-10'),
    ('P2V', 'P2V'),
    ('P3', 'P3'),
    ('S2T', 'S2T'),
    ('Sherpa', 'Sherpa'),
)

ROLE_CHOICES = (
    ('', '--'),
    ('airtanker', 'airtanker'),
    ('air attack', 'air attack'),
    ('lead plane', 'lead plane'),
    ('recon', 'recon'),
    ('jump ship', 'jump ship'),
)

class Airplane(models.Model):
    created = models.DateTimeField('Created', auto_now_add=True)
    modified = models.DateTimeField('Modified', auto_now=True)
    author = models.ForeignKey(User, related_name="airplane_author")
    tail = models.CharField('Tail', max_length=10, help_text="Tail number.", validators=[RegexValidator(regex=tail_regex, message='Enter an \'N#\' consisting of two letters, numbers or hyphens.')])
    name = models.CharField('Name', max_length=40, unique=True, help_text="Airplane name.", )
    # planerole = models.CharField('PlaneRole', max_length=12, choices=ROLE_CHOICES, help_text="Plane role e.g tanker.", ) # vol sorta
    make = models.CharField('Make', max_length=40, help_text="Manufacturer.", )
    modelname = models.CharField('Model', max_length=40, choices=MOD_CHOICES, help_text="Model name.", )
    takeoffweight = models.IntegerField('MaxTakeoffWt', blank=True, null=True, help_text="Max takeoff weight.", )
    landingweight = models.IntegerField('MaxLandingWt', blank=True, null=True, help_text="Max landing weight.", )
    airspeed = models.IntegerField('Airspeed', blank=True, null=True, help_text="Airspeed.", )
    # daysoff = models.CharField('Days Off', max_length=7, help_text="Days off.", ) # volatile
    # contractor = models.CharField('Contractor', max_length=40, help_text="Contractor.", ) # volatile
    # contract = models.CharField('Contract', max_length=40, help_text="Contract number.", ) # volatile
    # begins = models.DateTimeField('Begins', blank=True, null=True, help_text="Contract begins.", ) # volatile
    # ends = models.DateTimeField('Ends', blank=True, null=True, help_text="Contract ends.", ) # volatile
    # contractgallons = models.IntegerField('ContractGallons', blank=True, null=True, help_text="Contract gallons.", ) # volatile
    # cor = models.ForeignKey(User, related_name="airplane_cor", blank=True, null=True, ) # volatile
    # adminbase = models.ForeignKey(Airbase, related_name="airplane_adminbase") # volatile
    maxgrosswt = models.IntegerField('MaxGrossWt', blank=True, null=True, help_text="Max gross weight.", )
    remarks = models.TextField('Remarks', max_length=800, blank=True, null=True, help_text="Remarks.", )

    class Meta:
        db_table = 'flight_airplane'
        verbose_name = _('airplane')
        verbose_name_plural = _('airplanes')
        ordering = ('name','tail',)

    def __unicode__(self):
        return u"%s" % (self.name)

    def get_absolute_url(self):
        return "/airplane/%s/%s/" % (self.tail, self.name)

CT_CHOICES = (
    ('', '--'),
    ('CWN', 'CWN'),
    ('EXCL', 'EXCL'),
    ('BPA', 'BPA'),
    ('OD', 'OD'),
)

class Contract(models.Model):
    created = models.DateTimeField('Created', auto_now_add=True)
    modified = models.DateTimeField('Modified', auto_now=True)
    author = models.ForeignKey(User, related_name="contract_author")
    airplane = models.ForeignKey(Airplane, related_name="contract_airplane")
    planerole = models.CharField('PlaneRole', max_length=12, choices=ROLE_CHOICES, help_text="Plane role e.g tanker.", )
    ct = models.CharField('Type', max_length=4, choices=CT_CHOICES, help_text="Contract type.", )
    #cwn = models.BooleanField('CWN?', blank=True, null=True, help_text="Call When Needed billing.", )
    effectivedate = models.DateField('Effective Date', help_text="Effective date.",)
    ends = models.DateField('Ends', blank=True, null=True, help_text="Contract ends.", ) # a
    contractor = models.CharField('Contractor', blank=True, null=True, max_length=40, help_text="Contractor.", ) # a
    contract = models.CharField('Contract', blank=True, null=True, max_length=40, help_text="Contract number.", ) # a
    adminbase = models.ForeignKey(Airbase, blank=True, null=True, related_name="contract_adminbase") # volatile
    cor = models.ForeignKey(User, related_name="contract_cor", blank=True, null=True, ) # a
    contractgallons = models.IntegerField('ContractGallons', blank=True, null=True, help_text="Contract gallons.", ) # a
    daysoff = models.CharField('Days Off', max_length=7, help_text="Days off.", ) # volatile
    crewcount = models.IntegerField('Crew Count', blank=True, null=True, help_text="Crew count for extended if crew not known", ) # a
    remarks = models.TextField('Remarks', max_length=800, blank=True, null=True, help_text="Remarks.", )

    class Meta:
        db_table = 'flight_contract'
        verbose_name = _('contract')
        verbose_name_plural = _('contracts')
        ordering = ('-effectivedate','airplane')

    def __unicode__(self):
        return u"%s" % (self.id)

class Incident(models.Model):
    created = models.DateTimeField('Created', auto_now_add=True)
    modified = models.DateTimeField('Modified', auto_now=True)
    author = models.ForeignKey(User, related_name="incident_author")
    resourceorder = models.CharField('Order Number', max_length=40,  unique=True, help_text="Resource order or incident number, e.g. CA-KNF-4692, ID-PAF-004070.", )
    name = models.CharField('Name', max_length=40, help_text="Incident name, e.g. Swiss Spring.", )
    begins = models.DateField('Start', blank=True, null=True, help_text="Incident start.", )
    ends = models.DateField('End', blank=True, null=True, help_text="Incident end.", )
    userunit = models.CharField('Override', max_length=4, blank=True, null=True, help_text="Override code, e.g. 0602.", )
    st = USStateField('State', max_length=2, blank=True, null=True, help_text="State, e.g. OR.", )
    landstatus = models.CharField('Agency', blank=True, null=True, max_length=40, help_text="Agency, e.g. USFS.", )
    forest = models.CharField('Forest', blank=True, null=True, max_length=80, help_text="Forest, e.g. San Luis Unit.", )
    firechargenum = models.CharField('Charge No', max_length=40,  blank=True, null=True, help_text="Incident charge code, e.g. PNE7KA09.", )
    remarks = models.TextField('Remarks', max_length=800, blank=True, null=True, help_text="Remarks.", )
    #geom = models.GeometryField(blank=True, null=True, )

    class Meta:
        db_table = 'flight_incident'
        verbose_name = _('incident')
        verbose_name_plural = _('incidents')
        ordering = ('name',)

    def __unicode__(self):
        #return u"%s" % (self.name)
        return u"%s/%s" % (self.name, self.resourceorder)

    def get_absolute_url(self):
        #return "/flight/incident/%s/" % self.name
        return "/incident/%s/%s/" % (self.name, self.resourceorder)

class Mission(models.Model):
    created = models.DateTimeField('Created', auto_now_add=True)
    modified = models.DateTimeField('Modified', auto_now=True)
    author = models.ForeignKey(User, related_name="mission_author")
    startdate = models.DateField('Start Date', help_text="Mission start date", )
    #incident = models.ForeignKey(Incident, related_name="mission_incident")
    #userunit = models.CharField('Override', max_length=4, help_text="Override code, e.g. 0602.", )
    airplane = models.ForeignKey(Airplane, related_name="mission_airplane")
    ldo = models.DateField('Last Day Off', blank=True, null=True, help_text="Airplane Last Day Off", ) # init from a.daysoff
    #contractor = models.CharField('Contractor', blank=True, null=True, max_length=40, help_text="Contractor.", ) # a
    #contract = models.CharField('Contract', blank=True, null=True, max_length=40, help_text="Contract number.", ) # a
    #begins = models.DateTimeField('Begins', blank=True, null=True, help_text="Contract begins.", ) # a
    #ends = models.DateTimeField('Ends', blank=True, null=True, help_text="Contract ends.", ) # a
    #contractgallons = models.IntegerField('ContractGallons', blank=True, null=True, help_text="Contract gallons.", ) # a
    #cor = models.ForeignKey(User, related_name="mission_cor", blank=True, null=True, ) # a
    #adminbase = models.ForeignKey(Airbase, blank=True, null=True, related_name="mission_adminbase") # a
    crewcount = models.IntegerField('Crew Count', blank=True, null=True, help_text="Crew count for extended if crew not known", ) # a
    #planerole = models.CharField('PlaneRole', max_length=12, help_text="Supplemental plane role e.g tanker.", )
    opsbase = models.ForeignKey(Airbase, related_name="mission_opsbase", blank=True, null=True,)
    pilot = models.ForeignKey(Person, related_name="mission_pilot", blank=True, null=True, )
    copilot = models.ForeignKey(Person, related_name="mission_copilot", blank=True, null=True, )
    othercrew = models.ForeignKey(Person, related_name="mission_othercrew", blank=True, null=True, )
    #cor = models.ForeignKey(Person, related_name="cor", blank=True, null=True,  help_text="Supplemental COR.", )
    dailyavailstart = models.DateTimeField('On Duty', help_text="On Duty.",)
    dailyavailstop = models.DateTimeField('Off Duty', blank=True, null=True, help_text="Off Duty.",)
    #nonavailstart = models.DateTimeField('Out of Service', blank=True, null=True, help_text="Out of Service.",)
    #nonavailstop = models.DateTimeField('In Service', blank=True, null=True, help_text="In Service.",)
    remarks = models.TextField('Remarks', max_length=1024, blank=True, null=True, help_text="Remarks.", )

    class Meta:
        db_table = 'flight_mission'
        unique_together = (('airplane', 'startdate',),)
        verbose_name = _('mission')
        verbose_name_plural = _('missions')
        ordering = ('startdate','airplane')

    def __unicode__(self):
        return u"%s" % (self.id)

    def get_absolute_url(self):
        return "/mission/%s/%s/%s/" % (self.airplane.tail, self.airplane.name, self.startdate) # YYYY-MM-DD

FMSO_CHOICES = (
    ('f', 'Flight'),
    ('m', 'Move'),
    ('s', 'NonAvail'),
    ('x', 'Extended'),
    ('d', 'Divert'),
    #('o', 'Other'),
)

DROP_CHOICES = (
    ('', '--'),
    ('d', 'drop'),
    ('j', 'jettison'),
    ('s', 'spill'),
)

class Trip(models.Model):
    created = models.DateTimeField('Created', auto_now_add=True)
    modified = models.DateTimeField('Modified', auto_now=True)
    author = models.ForeignKey(User, related_name="trip_author")
    retardantgal = models.IntegerField('Ret Gal', help_text="Retardant loaded in gallons.", )
    rtype = models.CharField('Type', max_length=40, choices=RET_CHOICES, help_text="Retardant type.", )
    frombase = models.ForeignKey(Airbase, related_name="trip_frombase")
    tobase = models.ForeignKey(Airbase, related_name="trip_tobase", blank=True, null=True,)
    planestart = models.DateTimeField('Plane Start', help_text="Plane started.",)
    planestop = models.DateTimeField('Plane Stop', help_text="Plane stopped.", blank=True, null=True,)
    weightbalance = models.IntegerField('Weight Balance', blank=True, null=True, help_text="Weight balance.", )
    mission = models.ForeignKey(Mission, related_name="trip_mission")
    misccost = models.DecimalField('Misc Costs', max_digits=10, decimal_places=2, blank=True, null=True, help_text="Misc costs in dollars.", )
    movecount = models.IntegerField('Move Count', blank=True, null=True, help_text="Move count.", )
    moveonly = models.BooleanField('Move Only', help_text="Move only.", )
    fmso = models.CharField('Action', max_length=1, choices=FMSO_CHOICES, help_text="Flight, Move, NonAvail, Extended, Other.", )
    water = models.BooleanField('Water', help_text="Water?", )
    incident = models.ForeignKey(Incident, blank=True, null=True, related_name="trip_incident")
    pilot = models.ForeignKey(Person, related_name="trip_pilot", blank=True, null=True, )
    copilot = models.ForeignKey(Person, related_name="trip_copilot", blank=True, null=True, )
    othercrew = models.ForeignKey(Person, related_name="trip_othercrew", blank=True, null=True, )
    dropgal = models.IntegerField('Drop Gal', blank=True, null=True, help_text="Retardant dropped in gallons.", )
    drop = models.CharField('Drop Class', blank=True, null=True, max_length=1, choices=DROP_CHOICES, help_text="Drop, jettison, or spill", )
    #droploc = models.GeometryField('Location',blank=True, null=True, )

    class Meta:
        db_table = 'flight_trip'
        verbose_name = _('trip')
        verbose_name_plural = _('trips')
        ordering = ('planestart','planestop','mission__startdate','mission__airplane')

    def __unicode__(self):
        return u"%s" % (self.id)

RATE_CHOICES = (
    ('', '--'),
    ('flight', 'flight'),
    ('avail', 'avail'),
    ('nonavail', 'nonavail'),
    ('extended', 'extended'),
)

PER_CHOICES = (
    ('', '--'),
    ('hr', 'hr'),
    ('9hr', '9hr'),
    ('14hr', '14hr'),
    #('hr', 'hr per crew'),
)

class Rate(models.Model):
    created = models.DateTimeField('Created', auto_now_add=True)
    modified = models.DateTimeField('Modified', auto_now=True)
    author = models.ForeignKey(User, related_name="rate_author")
    airplane = models.ForeignKey(Airplane, related_name="rate_airplane")
    cost = models.DecimalField('Rate', max_digits=10, decimal_places=2, help_text="Rate in dollars per hour.", )
    perwhat = models.CharField('Per What', blank=True, null=True, max_length=10, choices=PER_CHOICES, help_text="Per what. Hour, 9hr day, 14 hr day.", )
    ratetype = models.CharField('Rate Type', max_length=10, choices=RATE_CHOICES, help_text="Rate type, e.g. flight, availability.", )
    incident = models.ForeignKey(Incident, blank=True, null=True, related_name="rate_incident", help_text="Funding, if different from mission incident",)
    #mop = models.NullBooleanField('MAP', blank=True, null=True, help_text="MAP?", )
    effectivedate = models.DateTimeField('Effective Date', help_text="Effective date.",)

    class Meta:
        db_table = 'flight_rate'
        verbose_name = _('rate')
        verbose_name_plural = _('rates')
        #ordering = ('effectivedate','airplane__name')

    def __unicode__(self):
        return u"%s" % (self.id)

class Landingfee(models.Model):
    created = models.DateTimeField('Created', auto_now_add=True)
    modified = models.DateTimeField('Modified', auto_now=True)
    author = models.ForeignKey(User, related_name="landingfee_author")
    airbase = models.ForeignKey(Airbase, related_name="landingfee_airbase")
    cost = models.DecimalField('Fee', max_digits=10, decimal_places=2, help_text="Dollars per landing.", )
    perwhat = models.CharField('Model', max_length=40, help_text="Airplane model, e.g. P2V-7, S2T, DC-10", )
    effectivedate = models.DateTimeField('Effective Date', help_text="Effective date.",)    

    class Meta:
        db_table = 'flight_landingfee'
        verbose_name = _('fee')
        verbose_name_plural = _('fees')
        #ordering = ('effectivedate','airbase__tla')

    def __unicode__(self):
        return u"%s" % (self.id)

class Retardantfee(models.Model):
    created = models.DateTimeField('Created', auto_now_add=True)
    modified = models.DateTimeField('Modified', auto_now=True)
    author = models.ForeignKey(User, related_name="retardantfee_author")
    airbase = models.ForeignKey(Airbase, related_name="retardantfee_airbase")
    rtype = models.CharField('Type', max_length=40, choices=RET_CHOICES, help_text="Retardant type.", )
    cost = models.DecimalField('Price', max_digits=10, decimal_places=3, help_text="Cost in dollars per gallon.", )
    flat = models.DecimalField('Flat Fee', max_digits=10, decimal_places=3, help_text="Flat fee in dollars.", )
    volume = models.IntegerField('Volume', help_text="Volume for price, in gallons.", ) # reset to 0 at each MAP
    effectivedate = models.DateTimeField('Effective Date', help_text="Effective date.",) # MAP start (always Apr 1)

    class Meta:
        db_table = 'flight_retardantfee'
        verbose_name = _('retardant price')
        verbose_name_plural = _('retardant prices')
        #ordering = ('effectivedate','airbase__tla')

    def __unicode__(self):
        return u"%s" % (self.id)

class Printout(models.Model):
    created = models.DateTimeField('Created', auto_now_add=True)
    modified = models.DateTimeField('Modified', auto_now=True)
    author = models.ForeignKey(User, related_name="printout_author")
    obj_model = models.CharField('Model', max_length=10, help_text="Object model.", )
    obj_id = models.CharField('Object', max_length=10, help_text="Object id.", )
    serialized = models.TextField('Serialized', help_text="Serialized.", )
    remarks = models.TextField('Remarks', max_length=1024, blank=True, null=True, help_text="Remarks.", )

    class Meta:
        db_table = 'flight_printout'
        verbose_name = _('printout')
        verbose_name_plural = _('printouts')
        ordering = ('-created',)

    def __unicode__(self):
        return u"%s" % (self.id)

STATUS_CHOICES = (
    ('D', 'Debug'),
    ('I', 'Info'),
    ('S', 'Success'),
    ('W', 'Warning'),
    ('E', 'Error'),
)

class Logitem(models.Model):
    created = models.DateTimeField('Created', auto_now_add=True)
    author = models.ForeignKey(User)
    status = models.CharField('Status', max_length=1, choices=STATUS_CHOICES)
    message = models.TextField('Message',)
    obj_model = models.CharField('Model', max_length=80, help_text="Object model.", )
    obj_id = models.CharField('Object', max_length=999, help_text="Object id.", )
    obj_in = models.TextField('Object In', blank=True, null=True, help_text="Serialized in.", )
    obj_out = models.TextField('Object Out', blank=True, null=True, help_text="Serialized out.", )

    class Meta:
        db_table = 'flight_logitem'
        verbose_name = _('log item')
        verbose_name_plural = _('log items')
        ordering = ('-created',)

def get_path(instance, filename):
    ext = filename.split('.')[-1]
    #front = filename.split('.')[0]
    #front = str(unicodedata.normalize('NFKD', front).encode('ascii', 'ignore'))
    #front = re.sub('[^\w\s-]', '', front).strip().lower()
    #front = re.sub('[-\s]+', '-', front)
    #front = re.sub('^b', '', front)
    filename = "%s.%s" % (uuid.uuid4(), ext)
    #when = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
    #filename = "%s-%s.%s" % (front, when, ext)
    #return os.path.join('uploads/logos', filename)
    return str(filename)

class Fueling(models.Model):
    created = models.DateTimeField('Created', auto_now_add=True)
    modified = models.DateTimeField('Modified', auto_now=True)
    author = models.ForeignKey(User, related_name="fueling_author")
    airplane = models.ForeignKey(Airplane, related_name="fueling_airplane")
    fuelbase = models.ForeignKey(Airbase, related_name="fueling_base")
    fueltime = models.DateTimeField('Fueling Time', blank=True, null=True, help_text="Fueling time.",)
    fuelgal = models.DecimalField('Fuel Gal', max_digits=10, decimal_places=2, blank=True, null=True, help_text="Fuel pumped in gallons.", )
    galprice = models.DecimalField('Price', max_digits=10, decimal_places=3, blank=True, null=True, help_text="Fuel price in dollars per gallon.", )
    fuelcost = models.DecimalField('Fuel Costs', max_digits=10, decimal_places=2, blank=True, null=True, help_text="Total fuel cost in dollars.", )
    fueltype = models.CharField('Fuel Type', max_length=40, blank=True, null=True, help_text="Fuel type.", )
    afile = models.FileField('File', storage=fs, upload_to=get_path, blank=True,)

    class Meta:
        db_table = 'flight_fueling'
        verbose_name = _('fueling')
        verbose_name_plural = _('fuelings')
        ordering = ('fueltime','airplane')

    def __unicode__(self):
        return u"%s" % (self.id)

    def get_absolute_url(self):
        return "/fueling/%s" % (self.id)

### FAIRS

class MakeModel(models.Model):
    created = models.DateTimeField('Created', auto_now_add=True)
    modified = models.DateTimeField('Modified', auto_now=True)
    author = models.ForeignKey(User, related_name="makemodel_author")
    makemodel = models.CharField('Make:Model', max_length=400, unique=True, help_text="This page is intended to serve as a reference sheet for use in filling out the Cost data sheets in this template. This sheet contains accepted values for the \"Manufacturer Model\" field. Only values matching those presented in this list will be able to be uploaded. Any other values will cause the entire template to be rejected by the FAIRS system. Use the values in the table below.", )
    #make = models.CharField('Make', max_length=40, help_text="Manufacturer.", )
    #modelname = models.CharField('Model', max_length=40, choices=MOD_CHOICES, help_text="Model name.", )

    class Meta:
        db_table = 'flight_fairs_makemodel'
        verbose_name = _('aircraft model')
        verbose_name_plural = _('aircraft models')
        ordering = ('makemodel',)

    def __unicode__(self):
        return u"%s" % (self.makemodel)

    def get_absolute_url(self):
        return "/fairs/makemodel/%s/" % (self.makemodel)

class CostType(models.Model):
    created = models.DateTimeField('Created', auto_now_add=True)
    modified = models.DateTimeField('Modified', auto_now=True)
    author = models.ForeignKey(User, related_name="costtype_author")
    costtype = models.CharField('Cost Type', max_length=400, unique=True, help_text="Values in this field must match exactly with an accepted cost type value from the FAIRS system. Acceptable values can be found on the Cost Reference sheet included in this document. If you are not pasting from another source, use the dropdown list to select the value. Clicking inside the cell will make the dropdown list available.", )

    class Meta:
        db_table = 'flight_fairs_costtype'
        verbose_name = _('cost type')
        verbose_name_plural = _('cost types')
        ordering = ('costtype',)

    def __unicode__(self):
        return u"%s" % (self.costtype)

    def get_absolute_url(self):
        return "/fairs/costtype/%s/" % (self.costtype)

class MissionCode(models.Model):
    created = models.DateTimeField('Created', auto_now_add=True)
    modified = models.DateTimeField('Modified', auto_now=True)
    author = models.ForeignKey(User, related_name="missioncode_author")
    missioncode = models.CharField('Mission Code', max_length=400, unique=True, help_text="This page is intended to serve as a reference sheet for use in filling out the Hours data sheet in this template. This sheet contains accepted values for the \"Mission\" field. Only values matching those presented in this list will be able to be uploaded. Any other values will cause the entire template to be rejected by the FAIRS system. Use the yellow highlighted values in the tables below.", )

    class Meta:
        db_table = 'flight_fairs_missioncode'
        verbose_name = _('mission code')
        verbose_name_plural = _('mission codes')
        ordering = ('missioncode',)

    def __unicode__(self):
        return u"%s" % (self.missioncode)

    def get_absolute_url(self):
        return "/fairs/missioncode/%s/" % (self.missioncode)

class OrgAbbreviation(models.Model):
    created = models.DateTimeField('Created', auto_now_add=True)
    modified = models.DateTimeField('Modified', auto_now=True)
    author = models.ForeignKey(User, related_name="orgabbreviation_author")
    orgabbreviation = models.CharField('Org Abbreviation', max_length=40, unique=True, help_text="Values in this field must represent a valid abbreviation associated with an organization found in the FAIRS system. Data will only be imported for organizations for which you have permission to enter data. See the FAIRS system for a current list of valid organization abbreviations.", )

    class Meta:
        db_table = 'flight_fairs_orgabbreviation'
        verbose_name = _('org abbreviation')
        verbose_name_plural = _('org abbreviations')
        ordering = ('orgabbreviation',)

    def __unicode__(self):
        return u"%s" % (self.orgabbreviation)

    def get_absolute_url(self):
        return "/fairs/orgabbreviation/%s/" % (self.orgabbreviation)

class SerialNum(models.Model):
    created = models.DateTimeField('Created', auto_now_add=True)
    modified = models.DateTimeField('Modified', auto_now=True)
    author = models.ForeignKey(User, related_name="serialnum_author")
    serialnum = models.CharField('Serial Num', max_length=40, unique=True, help_text="Values in this field should correspond to an existing aircraft serial number in the FAIRS database. Make sure the value is entered exactly as it is found in FAIRS. Any values in this field that cannot be found in the FAIRS database will cause the import to fail.", )

    class Meta:
        db_table = 'flight_fairs_serialnum'
        verbose_name = _('serial num')
        verbose_name_plural = _('serial nums')
        ordering = ('serialnum',)

    def __unicode__(self):
        return u"%s" % (self.serialnum)

    def get_absolute_url(self):
        return "/fairs/serialnum/%s/" % (self.serialnum)

class HoursEntry(models.Model):
    created = models.DateTimeField('Created', auto_now_add=True)
    modified = models.DateTimeField('Modified', auto_now=True)
    author = models.ForeignKey(User, related_name="hoursentry_author")
    reportstartdate = models.DateTimeField('Report Start Date', help_text="Values in this field must represent a valid start date (e.g., mm/dd/yy) for which the data on the row is applicable. Additionally, the date must fall inside a fiscal quarter for which data entry remains open. The start and end date on any row may not span fiscal quarter boundaries (e.g., 12/15/05 - 1/15/06 covers parts of both FY06 first quarter and FY06 second quarter and is therefore not a valid time period).",)
    reportenddate = models.DateTimeField('Report End Date', help_text="Values in this field must represent a valid end date (e.g., mm/dd/yy) for which the data on the row is applicable. Additionally, the date must fall inside a fiscal quarter for which data entry remains open. The start and end date on any row may not span fiscal quarter boundaries (e.g., 12/15/05 - 1/15/06 covers parts of both FY06 first quarter and FY06 second quarter and is therefore not a valid time period).",)
    orgabbreviation = models.ForeignKey(OrgAbbreviation, related_name="hoursentry_orgabbreviation")
    makemodel = models.ForeignKey(MakeModel, related_name="hoursentry_makemodel")
    serialnum = models.ForeignKey(SerialNum, related_name="hoursentry_serialnum")
    missioncode = models.ForeignKey(MissionCode, related_name="hoursentry_missioncode")
    flighthours = models.DecimalField('Flight Hours', max_digits=10, decimal_places=2, help_text="Enter the total number of hours associated with the aircraft and mission on the row. Do not include commas or any other non-numeric characters in the field.", )
    randhours = models.DecimalField('R&D Hours', max_digits=10, decimal_places=2, help_text="R& D stuff goes here.", )
    alerthours = models.DecimalField('Alert Hours', max_digits=10, decimal_places=2, help_text="Alert stuff goes here.", )
    remarks = models.TextField('Remarks', max_length=1024, blank=True, null=True, help_text="Enter comments you want to accompany this row of data.", )

    class Meta:
        db_table = 'flight_fairs_hoursentry'
        verbose_name = _('hours entry')
        verbose_name_plural = _('hours entries')
        ordering = ('reportstartdate',)

    def __unicode__(self):
        return u"%s" % (self.id)

    def get_absolute_url(self):
        return "/fairs/hoursentry/%s/" % (self.id)

class CostEntry(models.Model):
    created = models.DateTimeField('Created', auto_now_add=True)
    modified = models.DateTimeField('Modified', auto_now=True)
    author = models.ForeignKey(User, related_name="costentry_author")
    reportstartdate = models.DateTimeField('Report Start Date', help_text="Values in this field must represent a valid start date (e.g., mm/dd/yy) for which the data on the row is applicable. Additionally, the date must fall inside a fiscal quarter for which data entry remains open. The start and end date on any row may not span fiscal quarter boundaries (e.g., 12/15/05 - 1/15/06 covers parts of both FY06 first quarter and FY06 second quarter and is therefore not a valid time period).",)
    reportenddate = models.DateTimeField('Report End Date', help_text="Values in this field must represent a valid end date (e.g., mm/dd/yy) for which the data on the row is applicable. Additionally, the date must fall inside a fiscal quarter for which data entry remains open. The start and end date on any row may not span fiscal quarter boundaries (e.g., 12/15/05 - 1/15/06 covers parts of both FY06 first quarter and FY06 second quarter and is therefore not a valid time period).",)
    orgabbreviation = models.ForeignKey(OrgAbbreviation, related_name="costentry_orgabbreviation")
    makemodel = models.ForeignKey(MakeModel, related_name="costentry_makemodel")
    serialnum = models.ForeignKey(SerialNum, related_name="costentry_serialnum")
    costtype = models.ForeignKey(CostType, related_name="costentry_costtype")
    cost = models.IntegerField('Cost', help_text="Enter the whole dollar value (no cents) for the cost associated with the aircraft and cost type on the row. Do not include dollar signs, commas or any other non-numeric characters in the field.", )
    remarks = models.TextField('Remarks', max_length=1024, blank=True, null=True, help_text="Enter comments you want to accompany this row of data.", )

    class Meta:
        db_table = 'flight_fairs_costentry'
        verbose_name = _('cost entry')
        verbose_name_plural = _('cost entries')
        ordering = ('reportstartdate',)

    def __unicode__(self):
        return u"%s" % (self.id)

    def get_absolute_url(self):
        return "/fairs/costentry/%s/" % (self.id)