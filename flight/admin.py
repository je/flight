from django.contrib import admin
from flight.models import *
from guardian.admin import GuardedModelAdmin

#from django.contrib.gis.admin import OSMGeoAdmin
#from olwidget.admin import GeoModelAdmin

class AirbaseAdmin(GuardedModelAdmin):
    list_display = ('region','name','tla','author','created', )
    list_display_links = ('name',)
    list_filter = ('region', 'author',)
    list_per_page = 50
    save_as = True

admin.site.register(Airbase, AirbaseAdmin)

class AirplaneAdmin(GuardedModelAdmin):
    list_display = ('name', 'tail', 'modelname', 'author','created', )
    list_display_links = ('name',)
    list_filter = ('modelname', 'author',)
    list_per_page = 50
    save_as = True

admin.site.register(Airplane, AirplaneAdmin)

class ContractAdmin(GuardedModelAdmin):
    date_hierarchy = 'effectivedate'
    list_display = ('airplane', 'effectivedate', 'author', 'created', )
    list_display_links = ('airplane',)
    list_filter = ('airplane', 'ct','author',)
    list_per_page = 50
    save_as = True

admin.site.register(Contract, ContractAdmin)

class PersonAdmin(GuardedModelAdmin):
    list_display = ('firstname', 'lastname', 'job', 'author','created', )
    list_display_links = ('lastname',)
    list_filter = ('job', 'author',)
    list_per_page = 50
    save_as = True

admin.site.register(Person, PersonAdmin)

class IncidentAdmin(GuardedModelAdmin):
    date_hierarchy = 'begins'
    list_display = ('name', 'resourceorder', 'author','created',)
    list_display_links = ('resourceorder',)
    list_filter = ('landstatus', 'st',)
    list_per_page = 50
    save_as = True

admin.site.register(Incident,IncidentAdmin)

class MissionAdmin(GuardedModelAdmin):
    date_hierarchy = 'startdate'
    list_display = ('airplane', 'startdate', 'author','created',)
    list_display_links = ('startdate',)
    list_filter = ('airplane',)
    list_per_page = 50
    save_as = True

admin.site.register(Mission,MissionAdmin)

class RateAdmin(admin.ModelAdmin):
    date_hierarchy = 'effectivedate'
    list_display_links = ('airplane',)
    list_display = ('airplane', 'ratetype', 'cost', 'perwhat',  'effectivedate', 'author', 'created',)
    list_filter = ('airplane', 'ratetype', 'perwhat', )
    list_per_page = 50
    save_as = True

admin.site.register(Rate,RateAdmin)

class RetardantfeeAdmin(admin.ModelAdmin):
    date_hierarchy = 'effectivedate'
    list_display = ('airbase', 'rtype', 'cost', 'flat', 'volume', 'effectivedate', 'author','created',)
    list_display_links = ('airbase',)
    list_filter = ('airbase', 'rtype',)
    list_per_page = 50
    save_as = True

admin.site.register(Retardantfee,RetardantfeeAdmin)

class LandingfeeAdmin(admin.ModelAdmin):
    date_hierarchy = 'effectivedate'
    list_display = ('airbase', 'cost', 'perwhat', 'effectivedate', 'author','created',)
    list_display_links = ('airbase',)
    list_filter = ('airbase', 'perwhat',)
    list_per_page = 50
    save_as = True

admin.site.register(Landingfee,LandingfeeAdmin)

class PrintoutAdmin(admin.ModelAdmin):
    list_display = ('created', 'author', 'obj_model', 'obj_id',)
    ordering = ['created', 'author',]
    list_per_page = 50
    list_filter = ('author', 'obj_model',)
    #list_display_links = ('name',)
    save_as = True

admin.site.register(Printout,PrintoutAdmin)

class LogitemAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    list_display = ('message', 'status', 'created', 'author',)
    #ordering = ['created', ]
    list_per_page = 50
    list_filter = ('status', 'obj_model', 'author', )
    #list_display_links = ('name',)
    save_as = True

admin.site.register(Logitem,LogitemAdmin)

class FuelingAdmin(admin.ModelAdmin):
    date_hierarchy = 'fueltime'
    list_display = ('airplane', 'fueltime', 'fuelgal', 'galprice', 'fuelcost', 'author',)
    #ordering = ['created', ]
    list_per_page = 50
    list_filter = ('airplane', 'fuelbase', 'author', )
    #list_display_links = ('airplane',)
    #list_select_related = True
    save_as = True

admin.site.register(Fueling,FuelingAdmin)

### FAIRS

class OrgAbbreviationAdmin(admin.ModelAdmin):
    list_display = ('orgabbreviation', 'author','created', )
    list_display_links = ('orgabbreviation',)
    list_filter = ('author',)
    list_per_page = 50
    save_as = True

admin.site.register(OrgAbbreviation,OrgAbbreviationAdmin)

class MakeModelAdmin(admin.ModelAdmin):
    list_display = ('makemodel', 'author','created', )
    list_display_links = ('makemodel',)
    list_filter = ('author',)
    list_per_page = 50
    save_as = True

admin.site.register(MakeModel,MakeModelAdmin)

class SerialNumAdmin(admin.ModelAdmin):
    list_display = ('serialnum', 'author','created', )
    list_display_links = ('serialnum',)
    list_filter = ('author',)
    list_per_page = 50
    save_as = True

admin.site.register(SerialNum,SerialNumAdmin)

class CostTypeAdmin(admin.ModelAdmin):
    list_display = ('costtype', 'author','created', )
    list_display_links = ('costtype',)
    list_filter = ('author',)
    list_per_page = 50
    save_as = True

admin.site.register(CostType,CostTypeAdmin)

class MissionCodeAdmin(admin.ModelAdmin):
    list_display = ('missioncode', 'author','created', )
    list_display_links = ('missioncode',)
    list_filter = ('author',)
    list_per_page = 50
    save_as = True

admin.site.register(MissionCode,MissionCodeAdmin)

class HoursEntryAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    list_display = ('reportstartdate', 'reportenddate', 'orgabbreviation', 'makemodel', 'serialnum', 'flighthours', 'randhours', 'alerthours', 'created', )
    list_display_links = ('reportstartdate',)
    list_filter = ('author',)
    list_per_page = 50
    save_as = True

admin.site.register(HoursEntry,HoursEntryAdmin)

class CostEntryAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    list_display = ('reportstartdate', 'reportenddate', 'orgabbreviation', 'makemodel', 'serialnum', 'costtype', 'cost', 'created', )
    list_display_links = ('reportstartdate',)
    list_filter = ('author',)
    list_per_page = 50
    save_as = True

admin.site.register(CostEntry,CostEntryAdmin)
