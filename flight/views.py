from datetime import datetime, date, time, timedelta
from django.utils.timezone import utc
from django.utils import timezone
#from pytz import timezone
#timenow = datetime.datetime.utcnow().replace(tzinfo=utc)
#datenow = datetime.datetime.utcnow().replace(tzinfo=utc).date()

#import re
from decimal import *
#from reportlab.pdfgen import canvas
#from reportlab.platypus import Paragraph
#from reportlab.lib.pagesizes import letter, A5
#from cStringIO import StringIO
from django.template import Context, loader, RequestContext
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Q, F, Count, Max, Avg, Sum
from django.forms.models import inlineformset_factory
from django.utils.html import escape#, format_html_join
from django.core import serializers
from django.core.mail import send_mail, send_mass_mail
from django.core.mail import EmailMultiAlternatives
from django.core.urlresolvers import reverse_lazy

#from django.utils.safestring import mark_safe

from django.utils import simplejson
from localflavor.us.models import USStateField
from dateutil.relativedelta import relativedelta

from guardian.shortcuts import assign, get_users_with_perms, get_objects_for_user, remove_perm
from guardian.utils import clean_orphan_obj_perms

#from olwidget.widgets import InfoMap, Map, InfoLayer
#from django.contrib.gis.geos import LineString, GeometryCollection

from flight.models import *
from flight.forms import *

#from django.views.generic.list_detail import object_list
#from profiles import utils

class Stine(object):
    pass

def t2m(m, trip_list):
    try:
        m.c = Contract.objects.filter(airplane_id=m.airplane_id).filter(effectivedate__lte=m.startdate)[0]
    except:
        m.c = None
    m.ftime = m.fcost = m.mtime = m.ntime = m.nt = m.accmin = m.cftime = m.nmin = m.ncost = m.lcost = m.rgal = m.rcost = m.ocost = m.moves = m.mcost = m.tfs = m.tds = m.tbs = m.tms = m.tns = ns = nr = m.harate = 0
    m.shift = 9
    try:
        m.arate = Rate.objects.filter(
            Q(airplane_id=m.airplane_id),
            Q(ratetype='avail'),
            Q(effectivedate__lt=m.startdate)
            ).order_by('-effectivedate')[0]
        if m.arate.perwhat == '9hr':
            m.harate = m.arate.cost / 9
            m.shift = 9
        elif m.arate.perwhat == '14hr':
            m.harate = m.arate.cost / 14
            m.shift = 14
        elif m.arate.perwhat == 'hr':
            m.harate = m.arate.cost
            m.shift = 9
    except:
        try:
            m.arate = Rate.objects.filter(
                Q(airplane_id=m.airplane_id),
                Q(ratetype='avail'),
                Q(effectivedate__lt=m.startdate)
                )
            if m.arate.perwhat == '9hr':
                m.harate = m.arate.cost / 9
                m.shift = 9
            elif m.arate.perwhat == '14hr':
                m.harate = m.arate.cost / 14
                m.shift = 14
            elif m.arate.perwhat == 'hr':
                m.harate = m.arate.cost
                m.shift = 9
        except:
            m.arate = 0
            m.harate = 0
            m.shift = 9
    m.ms = m.dailyavailstart.replace(second=0) + timedelta(hours=m.shift)
    divs = 1 # START DIVERT CALC that doesn't work for incidents! also frombase needs to accum ret gal and make sure airbase to airbase diverts work. also, what if the divert isn't in the trip list but the diverted is? we got to check the mission for a previous trip on incident and airbase pages...
    div = 'No'
    for t in reversed(trip_list):
        t.div = 0
        if div == 'Yes': # this is the diverted flight
            t.div = 1
            div = 'No'
            t.landing = t.planestop
            t.planestop = d.time # set divert time
            #t.retardantgal = d.retardantgal
            #t.rtype = d.rtype
        if t.fmso == 'd': # this is the divert
            divs = divs + 1
            t.div = divs
            div = 'Yes'
            d = t # remember this trip! come back and add costs
            d.time = t.planestart # - timedelta(minutes=1)# get divert time and subtract a minute
    tobase = None
    planestop = None
    rtype = None
    retardantgal = 0
    for t in trip_list: # START OF TRIP CALC
        if t.div == 1: # this is the diverted flight
            tobase = t.tobase
            planestop = t.landing # store planestop
            retardantgal = t.retardantgal
            t.retardantgal = 0
            rtype = t.rtype
            t.rtype = None
        if t.div >= 2: # this is the divert
            t.tobase = tobase
            t.planestop = planestop # set planestop
            t.retardantgal = retardantgal
            t.rtype = rtype
            tobase = None
            planestop = None
            retardantgal = 0
            rtype = None # END DIVERT CALC
        # trip_list is all incident trips on the mission but we need
    for t in trip_list: # START OF TRIP CALC needs to be modded out of t2m independently of m
        try:
            t.min = ((t.planestop.replace(second=0) - t.planestart.replace(second=0)).seconds) / 60
            t.time = Decimal(round((Decimal(((t.planestop.replace(second=0) - t.planestart.replace(second=0)).seconds))) / 36)).quantize(Decimal('.01')) / 100
        except:
            t.min = 0
            t.time = 0
        if t.fmso == 'f':
            m.tfs = m.tfs + 1
            t.ftime = t.time
            m.ftime = m.ftime + t.ftime
            m.accmin = m.accmin + t.min
            t.cftime = m.cftime + t.ftime
            m.cftime = t.cftime
            try:
                t.frate = Rate.objects.filter(
                    Q(airplane_id=m.airplane_id),
                    Q(ratetype='flight'),
                    Q(effectivedate__lte=t.planestart)
                    ).order_by('-effectivedate')[0].cost
                t.fcost = t.time * Decimal(t.frate).quantize(Decimal('.01'))
                m.fcost = m.fcost + t.fcost
            except:
                t.frate = 0
                t.fcost = 0

        if t.fmso == '':
            m.tbs = m.tbs + 1
        if t.fmso == 'm':
            m.tms = m.tms + 1
            t.mtime = t.time
            m.mtime = m.mtime + t.mtime
            m.accmin = m.accmin + t.min
            t.cftime = m.cftime + t.mtime
            m.cftime = t.cftime
        if t.fmso == 's':
            m.tns = m.tns + 1
            t.ntime = t.time
            m.ntime = m.ntime + t.ntime
            m.nmin = m.nmin + t.min
            t.nt = t.time
            if t.planestart <= m.ms:
                #t.nx = m.ms - t.planestart  # int - time?
                t.nx = Decimal(round((Decimal(((m.ms.replace(second=0) - t.planestart.replace(second=0)).seconds))) / 36)).quantize(Decimal('.01')) / 100
                #t.nt = m.planestop.replace(second=0) + timedelta(hours=t.planestart)
                #t.nt = t.planestop - t.planestart # time - time
                if t.nt >= t.nx:
                    t.nt = t.nx
                m.nt = m.nt + t.nt
            try:
                t.nrate = Rate.objects.filter(
                    Q(airplane_id=m.airplane_id),
                    Q(ratetype='nonavail'),
                    Q(effectivedate__lte=t.planestart)
                    ).order_by('-effectivedate')[0].cost
                t.ncost = t.time * Decimal(t.nrate,2)
                m.ncost = m.ncost + t.ncost
                ns = ns + 1
                nr = nr + t.nrate
            except:
                t.ncost = 0
        if t.fmso == 'd':
            m.tds = m.tds + 1
            t.ftime = t.time
            m.ftime = m.ftime + t.ftime
            m.accmin = m.accmin + t.min
            t.cftime = m.cftime + t.ftime
            m.cftime = t.cftime
            try:
                t.frate = Rate.objects.filter(
                    Q(airplane_id=m.airplane_id),
                    Q(ratetype='flight'),
                    Q(effectivedate__lte=t.planestart)
                    ).order_by('-effectivedate')[0].cost
                t.fcost = t.time * Decimal(t.frate).quantize(Decimal('.01'))
                m.fcost = m.fcost + t.fcost
            except:
                t.frate = 0
                t.fcost = 0
        if t.div == 1:
            t.lcost = 0
        else:
            try:
                t.lcost = Landingfee.objects.filter(
                    Q(airbase_id=t.tobase_id),
                    Q(perwhat=m.airplane.modelname),
                    Q(effectivedate__lte=t.planestart)
                    ).order_by('-effectivedate')[0].cost
                m.lcost = m.lcost + t.lcost
            except:
                t.lcost = 0
        season = datetime.datetime(int(t.planestart.year), 1, 1, 0, 0) # jan 1 of trip year
        try: # start of new retcalc
            t.crgal = Trip.objects.filter(frombase_id=t.frombase_id).filter(planestart__range=(season, t.planestart)).filter(rtype=t.rtype).aggregate(retardant_sum=Sum('retardantgal'))['retardant_sum'] # we need trip.retgal for trip.rtype here
            #t.rbase = Airbase.objects.filter(id=t.frombase_id).annotate(trip_count=Count('trip_frombase'),retardant_sum=Sum('trip_frombase__retardantgal'))[0] # to get the ret pumped at the base but we have that above
            t.rprice = Retardantfee.objects.filter(
                Q(airbase_id=t.frombase_id),
                Q(rtype=t.rtype),
                Q(volume__lt=t.crgal),
                Q(effectivedate__lte=t.planestart)
                ).order_by('-volume','-effectivedate')[0] # this is price1 
            t.rprice2 = Retardantfee.objects.filter(
                Q(airbase_id=t.frombase_id),
                Q(rtype=t.rtype),
                Q(volume__lt=(t.crgal+t.retardantgal)),
                Q(effectivedate__lte=t.planestart)
                ).order_by('-volume','-effectivedate')[0] # this is price2 
            t.r1vol = t.rprice.volume
            t.r1cost = t.rprice.cost
            t.rflat = t.rprice.flat
            t.r2vol = t.rprice2.volume
            t.r2cost = t.rprice2.cost
            if t.r1vol != t.r2vol:
                t.rgal1 = t.r2vol - t.crgal # r.vol2 - t.crgal is 1
                t.rcost1 = t.r1cost * t.rgal1
                t.rgal2 = (t.crgal + t.retardantgal) - t.r2vol # t.crgal + + t.retgal - vol2 is 9 for price2 
                t.rcost2 = t.r2cost * t.rgal2
                #t.rprice = (t.r1cost + t.r2cost)/2
                t.rcost = t.rcost1 + t.rcost2
            else:
                t.rprice = t.r1cost
                t.rcost = t.rprice * t.retardantgal
            t.rcost = t.rcost + t.rflat
            t.rcost = Decimal(t.rcost).quantize(Decimal('.01'))
        except:
            t.rprice = 0
            t.rcost = 0 ## end of ner retcalc
        m.rgal = m.rgal + t.retardantgal
        m.rcost = m.rcost + t.rcost
        if t.misccost:
            m.ocost = m.ocost + t.misccost
            t.ocost = t.misccost
        else:
            m.ocost = m.ocost
            t.ocost = 0
        try:
            if t.fmso == 'm':
                t.mrate = Rate.objects.filter(
                    Q(airplane_id=m.airplane_id),
                    Q(ratetype='flight'),
                    Q(effectivedate__lte=t.planestart)
                    ).order_by('-effectivedate')[0].cost
                #t.mcost = t.movecount * Decimal(t.mrate).quantize(Decimal('.01')) / 10
                t.mcost = Decimal(t.mrate).quantize(Decimal('.01')) / 10
            else:
                t.mcost = 0
        except:
            t.mcost = 0
        m.mcost = m.mcost + t.mcost
        try:
            t.tcost = t.fcost + t.lcost + t.rcost + t.mcost + t.ocost
        except:
            try:
                t.tcost = t.lcost + t.rcost + t.mcost + t.ocost
            except:
                t.tcost = None # END OF TRIP CALC
    m.tos = trip_list.count() - (m.tfs + m.tms + m.tns + m.tbs)
    if ns >= 1:
        m.nrate = nr / ns # average trip nonavail rates
    try:
        m.harate = Decimal(m.harate).quantize(Decimal('.01'))
    except:
        m.harate = Decimal(0).quantize(Decimal('.01'))
    try:
        m.dtime = Decimal(((m.dailyavailstop.replace(second=0)) - (m.dailyavailstart.replace(second=0))).seconds).quantize(Decimal('.01'))/3600 # is 12.00
        m.stime = m.shift - m.nt #- m.ftime ( per cf # duty - nonavail ) # is 8.75
        m.etime = m.dtime - m.shift # is 3.00
        m.d1 = m.dtime
        if m.etime:
            #m.ms = m.dailyavailstart.replace(second=0) + timedelta(hours=m.shift) #+ timedelta(minutes=int(m.nmin)) #+ timedelta(hours=int(m.ftime))
            #m.etime = m.dtime - m.shift # ( per mb # duty - nonavail > 12 duty  - 9 shift - 1 nonavail = 2 ext )
            #m.d1 = m.etime # etime in hrs hundredths -- looks right
            # m.etime = Decimal(round(m.etime),0).quantize(Decimal('.01')) # rounds down
            m.etime = Decimal(m.etime).quantize(Decimal('1.'), rounding=ROUND_UP)
            #m.d2 = m.dtime # duty time in hours and hundredths -- this looks right!
            m.d2 = m.etime
            #if m.etime <= 0:
            #    m.etime = 0
            m.dtime = m.stime # is 8.75
    except:
        m.dtime = None
        m.etime = None
    try:
        m.tatime = m.dtime + m.ntime + m.etime
    except:
        m.tatime = 0
    try:
        m.fmtime = m.ftime + m.mtime
    except:
        m.fmtime = 0
    try:
        m.fmcost = m.fcost + m.mcost # flight + move cost
    except:
        pass
    try:
        if m.c.ct == 'CWN':
            m.cdtime = m.dtime - m.ftime
    except:
        m.cdtime = m.dtime
    try:
        if m.arate.perwhat == '9hr' and m.dtime == m.shift:
            m.acost = m.arate.cost
        elif m.arate.perwhat == '14hr' and m.dtime == m.shift:
            m.acost = m.arate.cost
        else:
            try:
                m.acost = m.cdtime * m.harate
            except:
                m.acost = 0
    except:
        m.acost = 0
    if m.crewcount:
        m.crews = m.crewcount
    else:
        m.crews = 1
        if m.copilot:
            m.crews = m.crews + 1
        if m.othercrew:
            m.crews = m.crews + 1
    try:
        m.erate = Rate.objects.filter(
            Q(airplane_id=m.airplane_id),
            Q(ratetype='extended'),
            Q(effectivedate__lt=m.startdate)
            ).order_by('-effectivedate')[0].cost
    except:
        try:
            m.erate = Rate.objects.filter(
                Q(airplane_id=m.airplane_id),
                Q(ratetype='extended'),
                Q(effectivedate__lt=m.startdate)
                ).cost
        except:
            m.erate = 0
    m.erate = Decimal(m.erate).quantize(Decimal('.01'))
    try:
        m.ecost = m.etime * m.erate * m.crews
    except:
        m.ecost = 0
    m.icost = m.fcost + m.lcost + m.rcost + m.ocost + m.mcost # all flight costs
    m.pcost = m.acost + m.ncost + m.ecost
    m.tcost = m.pcost + m.icost
    m.flsmrcost = m.icost + m.ecost + m.ncost
    try:
        m.fecost = m.fmcost + m.ecost # flight + ext cost 
    except:
        pass
    m.printout_list = Printout.objects.filter(
        Q(obj_model='mission'),
        Q(obj_id=m.id)
        )
    return(m, trip_list)

def airops(m):
    try:
        mac = timedelta(minutes=m.accmin)
        mac2 = datetime.datetime(1,1,1) + mac
        m.acchhmm = str(mac2.hour) + ' + ' + str(mac2.minute)
    except:
        m.acchhmm = "-- + --"
    # last day off is different to the last day with no hrs so
    # we need to add m.ldo as date to mission model using plane.dayoff as initial
    try:
        m.c = Contract.objects.filter(airplane_id=m.airplane_id).filter(effectivedate__lte=m.startdate)[0]
    except:
        m.c = None
    # try to get it from contract daysoff:
    days = []
    try:
        places = list(m.c.daysoff) # get contract dayoff and parse to weekdays
        if places[0] == '0':
            days.append('6') # SUN
        if places[1] == '0':
            days.append('0') # M
        if places[2] == '0':
            days.append('1') # T
        if places[3] == '0':
            days.append('2') # W
        if places[4] == '0':
            days.append('3') # R
        if places[5] == '0':
            days.append('4') # F
        if places[6] == '0':
            days.append('5') # SAT
        days = [int(l[0]) for l in days]
        m.weekday = m.startdate.weekday()
        m.ldo = None
        try:
            days.remove(m.startdate.weekday()) # startdate in daysoff, removed, daysoff maybe empty!
        except:
            pass
    except:
        pass
    if (m.startdate - timedelta(days=1)).weekday() in days: # day before the mission is off
        m.ldo = m.startdate - timedelta(days=1)
    elif (m.startdate - timedelta(days=2)).weekday() in days:
        m.ldo = m.startdate - timedelta(days=2)
    elif (m.startdate - timedelta(days=3)).weekday() in days:
        m.ldo = m.startdate - timedelta(days=3)
    elif (m.startdate - timedelta(days=4)).weekday() in days:
        m.ldo = m.startdate - timedelta(days=4)
    elif (m.startdate - timedelta(days=5)).weekday() in days: 
        m.ldo = m.startdate - timedelta(days=5)
    elif (m.startdate - timedelta(days=6)).weekday() in days:
        m.ldo = m.startdate - timedelta(days=6)
    elif (m.startdate - timedelta(days=7)).weekday() in days: # startdate weekday!
        m.ldo = m.startdate - timedelta(days=7)
    if m.ldo is not None:
        m.day1 = m.ldo + timedelta(days=1)
        m.day2 = m.ldo + timedelta(days=2)
        m.day3 = m.ldo + timedelta(days=3)
        m.day4 = m.ldo + timedelta(days=4)
        m.day5 = m.ldo + timedelta(days=5)
        m.day6 = m.ldo + timedelta(days=6)
        m.daytotalhrs = m.fmtime
        if m.day1 < m.startdate:
            m.day1hrs = 0
            trip_list = Trip.objects.filter(mission__airplane_id=m.airplane_id).filter(mission__startdate=m.day1)
            for t in trip_list:
                t.time = Decimal(round((Decimal(((t.planestop.replace(second=0) - t.planestart.replace(second=0)).seconds))) / 36)).quantize(Decimal('.01')) / 100
                m.day1hrs = m.day1hrs + t.time # get total airplane t.time for m.day1
            m.daytotalhrs = m.daytotalhrs + m.day1hrs
        if m.day2 < m.startdate:
            m.day2hrs = 0
            trip_list = Trip.objects.filter(mission__airplane_id=m.airplane_id).filter(mission__startdate=m.day2)
            for t in trip_list:
                t.time = Decimal(round((Decimal(((t.planestop.replace(second=0) - t.planestart.replace(second=0)).seconds))) / 36)).quantize(Decimal('.01')) / 100
                m.day2hrs = m.day2hrs + t.time # get total airplane t.time for m.day2
            m.daytotalhrs = m.daytotalhrs + m.day2hrs
        if m.day3 < m.startdate:
            m.day3hrs = 0
            trip_list = Trip.objects.filter(mission__airplane_id=m.airplane_id).filter(mission__startdate=m.day3)
            for t in trip_list:
                t.time = Decimal(round((Decimal(((t.planestop.replace(second=0) - t.planestart.replace(second=0)).seconds))) / 36)).quantize(Decimal('.01')) / 100
                m.day3hrs = m.day3hrs + t.time # get total airplane t.time for m.day3
            m.daytotalhrs = m.daytotalhrs + m.day3hrs
        if m.day4 < m.startdate:
            m.day4hrs = 0
            trip_list = Trip.objects.filter(mission__airplane_id=m.airplane_id).filter(mission__startdate=m.day4)
            for t in trip_list:
                t.time = Decimal(round((Decimal(((t.planestop.replace(second=0) - t.planestart.replace(second=0)).seconds))) / 36)).quantize(Decimal('.01')) / 100
                m.day4hrs = m.day4hrs + t.time # get total airplane t.time for m.day4
            m.daytotalhrs = m.daytotalhrs + m.day4hrs
        if m.day5 < m.startdate:
            m.day5hrs = 0
            trip_list = Trip.objects.filter(mission__airplane_id=m.airplane_id).filter(mission__startdate=m.day5)
            for t in trip_list:
                t.time = Decimal(round((Decimal(((t.planestop.replace(second=0) - t.planestart.replace(second=0)).seconds))) / 36)).quantize(Decimal('.01')) / 100
                m.day5hrs = m.day5hrs + t.time # get total airplane t.time for m.day6
            m.daytotalhrs = m.daytotalhrs + m.day5hrs
        if m.day6 < m.startdate:
            m.day6hrs = 0
            trip_list = Trip.objects.filter(mission__airplane_id=m.airplane_id).filter(mission__startdate=m.day6)
            for t in trip_list:
                t.time = Decimal(round((Decimal(((t.planestop.replace(second=0) - t.planestart.replace(second=0)).seconds))) / 36)).quantize(Decimal('.01')) / 100
                m.day6hrs = m.day6hrs + t.time # get total airplane t.time for m.day6
            m.daytotalhrs = m.daytotalhrs + m.day6hrs
    return(m)

def usermenu(u):
    u.missions = Mission.objects.filter(author=u).order_by('-startdate')
    u.trip_list = Trip.objects.filter(mission__in=u.missions).order_by('-planestart')
    u.airbases = Airbase.objects.filter(id__in=u.trip_list.values_list('frombase')).order_by('name')[:10]
    u.airplanes = Airplane.objects.filter(id__in=u.trip_list.values_list('mission__airplane'))[:10]
    u.people = Person.objects.filter(Q(id__in=u.trip_list.values_list('mission__pilot')) | Q(id__in=u.trip_list.values_list('mission__copilot')) | Q(id__in=u.trip_list.values_list('mission__othercrew')))[:10]
    u.incidents = Incident.objects.filter(id__in=u.trip_list.values_list('incident'))[:10]
    u.missions = u.missions[:10]
    return (u)

def mapents(trip_list):
    ents = []
    colors = ["black","cyan","red"]
    for i,trip in enumerate(trip_list):
        try:
            geom = trip.frombase.geom
            ents.append((geom, {
                'html': "<a class=\"alert-link\" href=\"/airbase/" + str(trip.frombase.tla) + "/\">" + str(trip.frombase.name) + " (" + str(trip.frombase.tla)  + ")" + "</a>",
                'style': {
                    'stroke_color': colors[0] , 'fill_color': colors[0]
                },
            }))
        except:
            pass
        try:
            igeom = trip.incident.geom.centroid
            ents.append((igeom, {
                'html': "<a class=\"alert-link\" href=\"/incident/" + str(trip.incident.name) + "/" + str(trip.incident.resourceorder) + "/\">" + str(trip.incident.name) + "/" + str(trip.incident.resourceorder) + "</a>",
                'style': {
                    'stroke_color': colors[0] , 'fill_color': colors[2]
                },
            }))
        except:
            pass
        try:
            if trip.frombase.geom is not None and trip.fmso == 'f' and trip.incident.geom is not None:
                pgeom = GeometryCollection(LineString(trip.frombase.geom.centroid, trip.incident.geom.centroid), srid=4326)
                ents.append((pgeom, {
                    'html': "<a class=\"alert-link\" href=\"/incident/" + str(trip.incident.name) + "/" + str(trip.incident.resourceorder) + "/\">" + str(trip.incident.name) + "/" + str(trip.incident.resourceorder) + "</a>",
                    'style': {
                        'stroke_color': colors[0] , 'color': colors[0]
                    },
                }))
        except:
            pass
        try:
            geom = trip.tobase.geom
            ents.append((geom, {
                'html': "<a class=\"alert-link\" href=\"/airbase/" + str(trip.tobase.tla) + "/\">" + str(trip.tobase.name) + " (" + str(trip.tobase.tla)  + ")" + "</a>",
                'style': {
                    'stroke_color': colors[0] , 'fill_color': colors[0]
                },
            }))
        except:
            pass
        try:
            if trip.tobase.geom is not None and trip.fmso == 'f' and trip.incident.geom is not None:
                pgeom = GeometryCollection(LineString(trip.incident.geom.centroid, trip.tobase.geom.centroid), srid=4326)
                ents.append((pgeom, {
                    'html': "<a class=\"alert-link\" href=\"/incident/" + str(trip.incident.name) + "/" + str(trip.incident.resourceorder) + "/\">" + str(trip.incident.name) + "/" + str(trip.incident.resourceorder) + "</a>",
                    'style': {
                        'stroke_color': colors[0] , 'color': colors[0]
                    },
                }))
        except:
            pass

    #trip_list.entmap = InfoMap(
    #    ents
    #    , { 'map_div_style': {'width': '100%', 'height': '100%'}, 'map_options': {'controls': ['LayerSwitcher', 'Navigation', 'PanZoom', 'MousePosition'], }, 'zoom_to_data_extent': True, },
    #)
    #trip_list.entmap.name = 'map1'
    return(trip_list)

def am(a,m):
    a.acost = a.acost + m.acost
    a.ecost = a.ecost + m.ecost
    a.fcount = a.fcount + m.tfs
    a.ftime = a.ftime + m.ftime
    a.fcost = a.fcost + m.fcost
    a.mtime = a.mtime + m.mtime
    a.ntime = a.ntime + m.ntime
    a.ncost = a.ncost + m.ncost
    a.lcost = a.lcost + m.lcost
    a.rgal = a.rgal + m.rgal
    a.rcost = a.rcost + m.rcost
    a.ocost = a.ocost + m.ocost
    a.moves = a.moves + m.moves
    a.mcost = a.mcost + m.mcost
    #a.flsmrcost = a.flsmrcost + m.flsmrcost
    #a.tcost = a.tcost + m.tcost
    a.tfs = a.tfs + m.tfs
    a.tbs = a.tbs + m.tbs
    a.tms = a.tms + m.tms
    a.tns = a.tns + m.tns
    return(a,m)

def a2(a):
    a.icost = a.fcost + a.lcost + a.rcost + a.ocost + a.mcost 
    a.pcost = a.acost + a.ncost + a.ecost
    a.tcost = a.pcost + a.icost
    return(a)

### D3 dashboard

@login_required
@permission_required('flight.add_airbase')
def flights_csv(request):
    trip_list = Trip.objects.all()
    for t in trip_list:
        try:
            t.min = ((t.planestop.replace(second=0) - t.planestart.replace(second=0)).seconds) / 60
            t.time = Decimal(round((Decimal(((t.planestop.replace(second=0) - t.planestart.replace(second=0)).seconds))) / 36)).quantize(Decimal('.01')) / 100
        except:
            t.min = 0
            t.time = 0
    #csv = simplejson.loads(q1.serialized)
    result = render_to_response('flight/flights.csv', { 'trip_list': trip_list, }, context_instance=RequestContext(request))
    return HttpResponse(result, mimetype='text/plain')

@login_required
@permission_required('flight.add_airbase')
def flights_d3(request):
    return render_to_response('flight/flights_d3.html', { }, context_instance=RequestContext(request))

### Logger

from django.contrib.auth.signals import user_logged_in

def update_user_login(sender, user, **kwargs):
    m = 'User %s login successful.' % (user)
    #messages.success(m)
    l = Logitem(author=user, status='S', message=m, obj_model='Session', obj_id='', obj_in='', obj_out='',)
    l.save()
    #user.userlogin_set.create(timestamp=timezone.now())
    #user.save()

user_logged_in.connect(update_user_login)

### Index and User

def index(request):
    try:
        u = User.objects.get(id=request.user.id)
        usermenu(u)
        dump = None
        u.acost = u.ecost = u.fcount = u.ftime = u.fcost = u.mtime = u.ntime = u.ncost = u.lcost = u.rgal = u.rcost = u.ocost= u.moves = u.mcost = u.tcost = u.tfs = u.tbs = u.tms = u.tns = 0
        m_list = Trip.objects.filter(author_id=u.id).order_by('-modified').values_list('mission_id')[:20]
        u.mission_list = Mission.objects.filter(id__in=m_list).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal')).order_by('-modified')
        u.trip_list = Trip.objects.filter(mission__in=u.mission_list)
        for m in u.mission_list:
            m.trip_list = u.trip_list.filter(mission_id=m.id)
            t2m(m,m.trip_list)
            u.acost = u.acost + m.acost
            u.ecost = u.ecost + m.ecost
            u.fcount = u.fcount + m.tfs
            u.ftime = u.ftime + m.ftime
            u.fcost = u.fcost + m.fcost
            u.mtime = u.mtime + m.mtime
            u.ntime = u.ntime + m.ntime
            u.ncost = u.ncost + m.ncost
            u.lcost = u.lcost + m.lcost
            u.rgal = u.rgal + m.rgal
            u.rcost = u.rcost + m.rcost
            u.ocost = u.ocost + m.ocost
            u.moves = u.moves + m.moves
            u.mcost = u.mcost + m.mcost
            u.tcost = u.tcost + m.tcost
            u.tfs = u.tfs + m.tfs
            u.tbs = u.tbs + m.tbs
            u.tms = u.tms + m.tms
            u.tns = u.tns + m.tns
        u.icost = u.fcost + u.lcost + u.rcost + u.ocost + u.mcost 
        u.pcost = u.acost + u.ncost + u.ecost
        u.tcost = u.pcost + u.icost
        #mapents(u.trip_list)
        entmap = None
        return render_to_response('flight/index.html', {'u': u, 'dump': dump, 'entmap': entmap, }, context_instance=RequestContext(request))
    except:
        u = None
        dump = None
        entmap = None
        return render_to_response('flight/index.html', {'u': u, 'dump': dump, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def user_list(request): # hook to extended user model
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    #profile_model = utils.get_profile_model()
    #queryset = profile_model._default_manager.all()
    fu = Group.objects.get(name="flight-user").user_set.all()
    #queryset = profile_model._default_manager.filter(user__in=fu)
    queryset = User.objects.filter(id__in=fu)
    #if public_profile_field is not None:
    #    queryset = queryset.filter(**{ public_profile_field: True })
    return render_to_response('flight/user_list.html', { 'u': u, 'object_list': queryset, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def user_detail(request, slug): # hook to extended user model
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = get_object_or_404(User, username=slug)
    when = datetime.datetime.utcnow().replace(tzinfo=utc).year
    m_list = Trip.objects.filter(mission__startdate__year=when).filter(author_id=a.id).order_by('-modified').values_list('mission_id')
    mission_list = Mission.objects.filter(id__in=m_list).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal')).order_by('-modified')
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/user_detail.html', { 'u' : u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def user_date_to_date(request, slug, yeara, moa, daa, yearb, mob, dab):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = get_object_or_404(User, username=slug)
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    bdate = datetime.datetime(int(yearb), int(mob), int(dab), 0, 0)
    m_list = Trip.objects.filter(author_id=a.id).order_by('-modified').values_list('mission_id')
    mission_list = Mission.objects.filter(id__in=m_list).filter(startdate__range=(adate, bdate)).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/user_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list,'adate': adate, 'bdate': bdate, 'entmap': entmap, }, context_instance=RequestContext(request))


@login_required
@permission_required('flight.add_airbase')
def user_date(request, slug, yeara, moa, daa):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = get_object_or_404(User, username=slug)
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    m_list = Trip.objects.filter(author_id=a.id).order_by('-modified').values_list('mission_id')
    mission_list = Mission.objects.filter(id__in=m_list).filter(startdate=adate).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/user_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list,'adate': adate, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def user_month(request, slug, yeara, moa):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = get_object_or_404(User, username=slug)
    adate = datetime.datetime(int(yeara), int(moa), 1, 0, 0)
    m_list = Trip.objects.filter(author_id=a.id).order_by('-modified').values_list('mission_id')
    mission_list = Mission.objects.filter(id__in=m_list).filter(Q(startdate__year=yeara) & Q(startdate__month=moa)).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/user_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list,'adate': adate, 'mo': moa, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def user_year(request, slug, yeara):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = get_object_or_404(User, username=slug)
    adate = datetime.datetime(int(yeara), 1, 1, 0, 0)
    m_list = Trip.objects.filter(author_id=a.id).order_by('-modified').values_list('mission_id')
    mission_list = Mission.objects.filter(id__in=m_list).filter(startdate__year=yeara).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/user_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list,'adate': adate, 'year': yeara, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def date_to_date(request, yeara, moa, daa, yearb, mob, dab):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = u
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    bdate = datetime.datetime(int(yearb), int(mob), int(dab), 0, 0)
    m_list = Trip.objects.filter(author_id=a.id).order_by('-modified').values_list('mission_id')
    mission_list = Mission.objects.filter(id__in=m_list).filter(startdate__range=(adate, bdate)).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/user_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list,'adate': adate, 'bdate': bdate, 'entmap': entmap, }, context_instance=RequestContext(request))


@login_required
@permission_required('flight.add_airbase')
def date(request, yeara, moa, daa):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = u
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    m_list = Trip.objects.filter(author_id=a.id).order_by('-modified').values_list('mission_id')
    mission_list = Mission.objects.filter(id__in=m_list).filter(startdate=adate).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/user_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list,'adate': adate, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def month(request, yeara, moa):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = u
    adate = datetime.datetime(int(yeara), int(moa), 1, 0, 0)
    m_list = Trip.objects.filter(author_id=a.id).order_by('-modified').values_list('mission_id')
    mission_list = Mission.objects.filter(id__in=m_list).filter(Q(startdate__year=yeara) & Q(startdate__month=moa)).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/user_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list,'adate': adate, 'mo': moa, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def year(request, yeara):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = u
    adate = datetime.datetime(int(yeara), 1, 1, 0, 0)
    m_list = Trip.objects.filter(author_id=a.id).order_by('-modified').values_list('mission_id')
    mission_list = Mission.objects.filter(id__in=m_list).filter(startdate__year=yeara).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/user_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list,'adate': adate, 'year': yeara, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def profile(request, username): # hook to extended user model
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    puser = get_object_or_404(User, username=username)
    airbases = get_objects_for_user(puser, 'flight.change_airbase')
    #models = get_objects_for_user(user, 'space.change_model')
    logitems = Logitem.objects.filter(author=puser)
    #try:
    #    profile_obj = user
    #except ObjectDoesNotExist:
    #    raise Http404
    #if public_profile_field is not None and \
    #   not getattr(profile_obj, public_profile_field):
    #    profile_obj = None
    now = datetime.datetime.today()
    first_month = datetime.datetime(now.year, now.month, 1)
    first_day = datetime.datetime(now.year, now.month, now.day)
    #last_day = datetime.datetime(2013, 1, 30)
    last_day = first_day - relativedelta(days = 120)
    rangemid = (first_day - last_day).days
    previous_days = (first_day - relativedelta(days = days) for days in range(0, rangemid, 1))
    thedays = previous_days
    #try:
    a = puser.id
    e=[]
    ud=[]
    cums = Logitem.objects.filter(status='S').count()
    cumw = Logitem.objects.filter(status='W').count()
    cume = Logitem.objects.filter(status='E').count()
    ucums = Logitem.objects.filter(status='S', author_id=a).count()
    ucumw = Logitem.objects.filter(status='W', author_id=a).count()
    ucume = Logitem.objects.filter(status='E', author_id=a).count()
    lcount = max(cums,cumw,cume)
    ucount = max(ucums,ucumw,ucume)
    maxs = 0
    maxw = 0
    maxe = 0
    umaxs = 0
    umaxw = 0
    umaxe = 0
    for day in thedays:
        iyear = day.year
        imonth = day.month
        iday = day.day
        label = ' '
        #if iday <= 1:
        label = day
        scount = Logitem.objects.filter(
            Q(created__year=iyear),
            Q(created__month=imonth),
            Q(created__day=iday),
            Q(status='S'),
            ).count()
        if scount >= maxs:
            maxs = scount
        wcount = Logitem.objects.filter(
            Q(created__year=iyear),
            Q(created__month=imonth),
            Q(created__day=iday),
            Q(status='W'),
            ).count()
        if wcount >= maxw:
            maxw = wcount
        ecount = Logitem.objects.filter(
            Q(created__year=iyear),
            Q(created__month=imonth),
            Q(created__day=iday),
            Q(status='E'),
            ).count()
        if ecount >= maxe:
            maxe = ecount
        dict = {'label': label, 'scount': scount, 'wcount': wcount, 'ecount': ecount, 'cums': cums, 'cumw': cumw, 'cume': cume }
        e.append(dict)
        cums = cums - scount
        cumw = cumw - wcount
        cume = cume - ecount
        uscount = Logitem.objects.filter(
            Q(created__year=iyear),
            Q(created__month=imonth),
            Q(created__day=iday),
            Q(status='S'),
            Q(author_id=a),
            ).count()
        if uscount >= umaxs:
            umaxs = uscount
        uwcount = Logitem.objects.filter(
            Q(created__year=iyear),
            Q(created__month=imonth),
            Q(created__day=iday),
            Q(status='W'),
            Q(author_id=a),
            ).count()
        if uwcount >= umaxw:
            umaxw = uwcount
        uecount = Logitem.objects.filter(
            Q(created__year=iyear),
            Q(created__month=imonth),
            Q(created__day=iday),
            Q(status='E'),
            Q(author_id=a),
            ).count()
        dict = {'label': label, 'scount': uscount, 'wcount': uwcount, 'ecount': uecount, 'cums': ucums, 'cumw': ucumw, 'cume': ucume }
        ud.append(dict)
        ucums = ucums - uscount
        ucumw = ucumw - uwcount
        ucume = ucume - uecount
    lmax = max(maxs,maxw,maxe)
    entry_dates = e
    umax = max(umaxs,umaxw,umaxe)
    u_dates = ud
    dump = entry_dates
    logitems = 'junk'
    return render_to_response('flight/profile.html', { 'u': u, 'puser': puser, 'airbases': airbases, 'logitems': logitems, 'entry_dates': entry_dates, 'lmax': lmax, 'lcount': lcount, 'u_dates': u_dates, 'umax': umax, 'ucount': ucount, 'dump': dump,}, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def log(request): # useless
    now = datetime.datetime.today()  
    first_month = datetime.datetime(now.year, now.month, 1)
    first_day = datetime.datetime(now.year, now.month, now.day)
    last_day = datetime.datetime(2013, 1, 30)
    rangemid = (first_day - last_day).days
    previous_days = (first_day - relativedelta(days = days) for days in range(0, rangemid, 1))
    thedays = previous_days
    #try:
    a = User.objects.get(id=request.user.id).id
    e=[]
    u=[]
    cums = Logitem.objects.filter(status='S').count()
    cumw = Logitem.objects.filter(status='W').count()
    cume = Logitem.objects.filter(status='E').count()
    ucums = Logitem.objects.filter(status='S', author_id=a).count()
    ucumw = Logitem.objects.filter(status='W', author_id=a).count()
    ucume = Logitem.objects.filter(status='E', author_id=a).count()
    lcount = max(cums,cumw,cume)
    ucount = max(ucums,ucumw,ucume)
    maxs = 0
    maxw = 0
    maxe = 0
    umaxs = 0
    umaxw = 0
    umaxe = 0
    for day in thedays:
        iyear = day.year
        imonth = day.month
        iday = day.day
        label = ' '
        if iday <= 1:
            label = day
        scount = Logitem.objects.filter(
            Q(created__year=iyear),
            Q(created__month=imonth),
            Q(created__day=iday),
            Q(status='S'),
            ).count()
        if scount >= maxs:
            maxs = scount
        wcount = Logitem.objects.filter(
            Q(created__year=iyear),
            Q(created__month=imonth),
            Q(created__day=iday),
            Q(status='W'),
            ).count()
        if wcount >= maxw:
            maxw = wcount
        ecount = Logitem.objects.filter(
            Q(created__year=iyear),
            Q(created__month=imonth),
            Q(created__day=iday),
            Q(status='E'),
            ).count()
        if ecount >= maxe:
            maxe = ecount
        dict = {'label': label, 'scount': scount, 'wcount': wcount, 'ecount': ecount, 'cums': cums, 'cumw': cumw, 'cume': cume }
        e.append(dict)
        cums = cums - scount
        cumw = cumw - wcount
        cume = cume - ecount
        uscount = Logitem.objects.filter(
            Q(created__year=iyear),
            Q(created__month=imonth),
            Q(created__day=iday),
            Q(status='S'),
            Q(author_id=a),
            ).count()
        if uscount >= umaxs:
            umaxs = uscount
        uwcount = Logitem.objects.filter(
            Q(created__year=iyear),
            Q(created__month=imonth),
            Q(created__day=iday),
            Q(status='W'),
            Q(author_id=a),
            ).count()
        if uwcount >= umaxw:
            umaxw = uwcount
        uecount = Logitem.objects.filter(
            Q(created__year=iyear),
            Q(created__month=imonth),
            Q(created__day=iday),
            Q(status='E'),
            Q(author_id=a),
            ).count()
        dict = {'label': label, 'scount': uscount, 'wcount': uwcount, 'ecount': uecount, 'cums': ucums, 'cumw': ucumw, 'cume': ucume }
        u.append(dict)
        ucums = ucums - uscount
        ucumw = ucumw - uwcount
        ucume = ucume - uecount
    lmax = max(maxs,maxw,maxe)
    entry_dates = e
    umax = max(umaxs,umaxw,umaxe)
    u_dates = u
    dump = entry_dates
    logitems = 'junk'
    return render_to_response('flight/log.html', {'logitems': logitems, 'entry_dates': entry_dates, 'lmax': lmax, 'lcount': lcount, 'u_dates': u_dates, 'umax': umax, 'ucount': ucount, 'dump': dump,}, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def search(request): # does nothing
    debug = None
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    when = datetime.datetime.utcnow().replace(tzinfo=utc).year
    a = Stine()
    a.q = 'q'
    build = '?'
    m_list = Trip.objects.all()
    try:
        out_string = request.GET['out']
        if out_string is not None:
            out_split = out_string.split(",")
            out_list = Airbase.objects.filter(tla__in=out_split)
            if out_list.exists():
                a.out_list = out_list
                m_list = m_list.filter(frombase__in=out_list)
                out_build  = str("out=" + out_string)
                build = str(build + out_build)
            else:
                out_string = None
    except:
        out_string = None
    try:
        in_string = request.GET['in']
        if in_string is not None:
            in_split = in_string.split(",")
            in_list = Airbase.objects.filter(tla__in=in_split)
            if in_list.exists():
                a.in_list = in_list
                m_list = m_list.filter(frombase__in=in_list)
                in_build  = str("&in=" + in_string)
                build = str(build + in_build)
            else:
                in_string = None
    except:
        in_string = None
    try:
        fire_string = request.GET['fire']
        if fire_string is not None:
            fire_split = fire_string.split(",")
            fire_list = Incident.objects.filter(name__in=fire_split)
            if fire_list.exists():
                a.fire_list = fire_list
                m_list = m_list.filter(incident__in=fire_list)
                fire_build  = str("&fire=" + fire_string)
                build = str(build + fire_build)
            else:
                fire_string = None
    except:
        fire_string = None
    try:
        plane_string = request.GET['plane']
        if plane_string is not None:
            plane_split = plane_string.split(",")
            plane_list = Airplane.objects.filter(name__in=plane_split)
            if plane_list.exists():
                a.plane_list = plane_list
                m_list = m_list.filter(mission__airplane__in=plane_list)
                plane_build  = str("&plane=" + plane_string)
                build = str(build + plane_build)
            else:
                plane_string = None
    except:
        plane_string = None
    try:
        from_string = request.GET['from']
        if from_string is not None:
            from_split = from_string.split("-")
            yeara = from_split[0]
            moa = from_split[1]
            daa = from_split[2]
            adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
            m_list = m_list.filter(mission__startdate__gte=adate)
            from_build  = str("&from=" + from_string)
            build = str(build + from_build)
    except:
        adate = None
    try:
        to_string = request.GET['to']
        if to_string is not None:
            to_split = to_string.split("-")
            yearb = to_split[0]
            mob = to_split[1]
            dab = to_split[2]
            bdate = datetime.datetime(int(yearb), int(mob), int(dab), 0, 0)
            m_list = m_list.filter(mission__startdate__lte=bdate)
            to_build  = str("&to=" + to_string)
            build = str(build + to_build)
    except:
        bdate = None
    if out_string == in_string == fire_string == plane_string == adate == bdate == None:
           m_list = Trip.objects.none()
           mission_list = Mission.objects.none()
           trip_list = Trip.objects.none()
           a.q = 'q'
    else:
        a.q = build
        m_list = m_list.values_list('mission_id')
        #m_list = Trip.objects.filter(mission__startdate__year=when).filter(Q(frombase_id=base.id) | Q(tobase_id=base.id)).order_by('-modified').values_list('mission_id')
        mission_list = Mission.objects.filter(id__in=m_list).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal')).order_by('-modified')
        trip_list = Trip.objects.filter(mission_id__in=m_list)
        a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
        a.mission_count = mission_list.count()
        #trip_list = Trip.objects.filter(mission__in=mission_list) # what for?
        for m in mission_list:
            m.trip_list = trip_list.filter(mission_id=m.id)
            t2m(m,m.trip_list)
            am(a,m)
        a2(a)
        #mapents(trip_list)
    entmap = None
    return render_to_response('flight/mission_list.html', { 'u': u, 'adate': adate, 'bdate': bdate, 'mission_list': mission_list, 'flight_list': trip_list, 'o': a, 'entmap': entmap, 'debug': debug }, context_instance=RequestContext(request))


FlightFormSet = inlineformset_factory(Mission, Trip, form=MissionTripAdd, can_delete=True)

@login_required
@permission_required('flight.add_airbase')
def mission_add_more(request): # this is the formset thing, unfinished
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    if request.method == 'POST':
        form = MissionAdd(request.POST)
        formset = FlightFormSet(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            if request.user.has_perm('change_airplane', obj.airplane):
                obj.author_id = request.user.id
                if form.cleaned_data['dailyavailstart_1']:
                    obj.dailyavailstart = datetime.datetime.combine(obj.startdate, form.cleaned_data['dailyavailstart_1'])
                if form.cleaned_data['dailyavailstop_1']:
                    obj.dailyavailstop = datetime.datetime.combine(obj.startdate, form.cleaned_data['dailyavailstop_1'])
                else:
                    obj.dailyavailstop = None
                #if form.cleaned_data['nonavailstart_1']:
                #    obj.nonavailstart = datetime.datetime.combine(obj.startdate, form.cleaned_data['nonavailstart_1'])
                #else:
                #    obj.nonavailstart = None
                #if form.cleaned_data['nonavailstop_1']:
                #    obj.nonavailstop = datetime.datetime.combine(obj.startdate, form.cleaned_data['nonavailstop_1'])
                #else:
                #    obj.nonavailstop = None
                obj.save()
                assign('change_mission', request.user, obj)
                assign('delete_mission', request.user, obj)
                nominaldate = obj.startdate.strftime("%Y/%m/%d")
                m = 'Mission %s/%s/%s/ created.' % (obj.airplane.tail, obj.airplane.name, nominaldate)
                formset = FlightFormSet(request.POST, instance=obj)
                if formset.is_valid():
                    for form in formset:
                        form.instance.author_id = obj.author_id
                    formset.save()
                    m = 'Mission %s/%s/%s/ and flights created.' % (obj.airplane.tail, obj.airplane.name, nominaldate)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Mission', obj_id=obj.id, obj_in='', obj_out='',)
                l.save()
                return HttpResponseRedirect('/mission/%s/%s/%s/' % (obj.airplane.tail, obj.airplane.name, nominaldate))
            else:
                m = 'Permission at Airbase %s required.' % (obj.airbase)
                messages.warning(request, m) 
                l = Logitem(author=request.user, status='W', message=m, obj_model='Mission',)
                l.save() 
                return render_to_response('flight/mission_edit.html', { 'u': u, 'form': form, }, context_instance=RequestContext(request))
    else:
        form = MissionAdd()
        formset = FlightFormSet()

    return render_to_response('flight/mission_edit.html', { 'u': u, 'form': form, 'formset': formset,
    }, context_instance=RequestContext(request))

### FAIRS

from functools import wraps  # adapt if you need python 2.4 support

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import login

def alogin_required(view_callable):
    def check_login(request, *args, **kwargs):
        if request.user.is_authenticated():
            return view_callable(request, *args, **kwargs)

        assert hasattr(request, 'session'), "Session middleware needed."
        login_kwargs = {
            'extra_context': {
                REDIRECT_FIELD_NAME: request.get_full_path(),
            },
        }
        return login(request, **login_kwargs)
    return wraps(view_callable)(check_login)

@alogin_required
@permission_required('flight.add_airbase')
def fairs(request):
    u = 'u'
    dump = 'dump'
    entmap = None
    return render_to_response('flight/fairs.html', {'u': u, 'dump': dump, 'entmap': entmap, }, context_instance=RequestContext(request))

@permission_required('flight.add_airbase')
def fairs_load(request, table):
    table = table
    form =[]
    header = []
    if table == 'OrgAbbreviation':
        form = OrgAbbreviationLoadForm(request.POST or None)
    if table == 'MakeModel':
        form = MakeModelLoadForm(request.POST or None)
    if table == 'SerialNum':
        form = SerialNumLoadForm(request.POST or None)
    if table == 'MissionCode':
        form = MissionCodeLoadForm(request.POST or None)
    if table == 'CostType':
        form = CostTypeLoadForm(request.POST or None)
    if form.is_valid():
        form.header = header
        form.author = request.user
        obj = form.save()
        messages.success(request, 'Data loaded.')
        return HttpResponseRedirect('/fairs/')

    return render_to_response("flight/fairs_load.html", { 'table': table, 'form': form }, context_instance=RequestContext(request))

from vanilla import CreateView, DeleteView, ListView, UpdateView

class ListCostEntry(ListView):
    model = CostEntry

class CreateCostEntry(CreateView):
    model = CostEntry
    success_url = reverse_lazy('list_costentry')

    def get_formx(self, data=None, files=None, **kwargs):
        #author = self.request.user
        #data = { 'author': author, }
        return CostEntryForm(data, files, **kwargs)

    def get_formxx(self, data=None, files=None, **kwargs):
        user = self.request.user
        data = {'author_id': user.id,}
        #if user.is_staff:
        #    return AdminAccountForm(data, files, owner=user, **kwargs)
        return CostEntryForm(data, files, **kwargs)

    def form_validx(self, form):
        self.author_id=request.user.id
        #author = self.request.user
        #data = { 'author': author, }
        return self

class EditCostEntry(UpdateView):
    model = CostEntry
    success_url = reverse_lazy('list_costentry')

class DeleteCostEntry(DeleteView):
    model = CostEntry
    success_url = reverse_lazy('list_costentry')

class ListHoursEntry(ListView):
    model = HoursEntry

class CreateHoursEntry(CreateView):
    model = HoursEntry
    success_url = reverse_lazy('list_hoursentry')

class EditHoursEntry(UpdateView):
    model = HoursEntry
    success_url = reverse_lazy('list_hoursentry')

class DeleteHoursEntry(DeleteView):
    model = HoursEntry
    success_url = reverse_lazy('list_hoursentry')

class ListOrgAbbreviation(ListView):
    model = OrgAbbreviation

class CreateOrgAbbreviation(CreateView):
    model = OrgAbbreviation
    success_url = reverse_lazy('list_orgabbreviation')

class EditOrgAbbreviation(UpdateView):
    model = OrgAbbreviation
    success_url = reverse_lazy('list_orgabbreviation')

class DeleteOrgAbbreviation(DeleteView):
    model = OrgAbbreviation
    success_url = reverse_lazy('list_orgabbreviation')

class ListMakeModel(ListView):
    model = MakeModel

class CreateMakeModel(CreateView):
    model = MakeModel
    success_url = reverse_lazy('list_makemodel')

class EditMakeModel(UpdateView):
    model = MakeModel
    success_url = reverse_lazy('list_makemodel')

class DeleteMakeModel(DeleteView):
    model = MakeModel
    success_url = reverse_lazy('list_makemodel')

class ListSerialNum(ListView):
    model = SerialNum

class CreateSerialNum(CreateView):
    model = SerialNum
    success_url = reverse_lazy('list_serialnum')

class EditSerialNum(UpdateView):
    model = SerialNum
    success_url = reverse_lazy('list_serialnum')

class DeleteSerialNum(DeleteView):
    model = SerialNum
    success_url = reverse_lazy('list_serialnum')

class ListCostType(ListView):
    model = CostType

class CreateCostType(CreateView):
    model = CostType
    success_url = reverse_lazy('list_costtype')

class EditCostType(UpdateView):
    model = CostType
    success_url = reverse_lazy('list_costtype')

class DeleteCostType(DeleteView):
    model = CostType
    success_url = reverse_lazy('list_costtype')

class ListMissionCode(ListView):
    model = MissionCode

class CreateMissionCode(CreateView):
    model = MissionCode
    success_url = reverse_lazy('list_missioncode')

class EditMissionCode(UpdateView):
    model = MissionCode
    success_url = reverse_lazy('list_missioncode')

class DeleteMissionCode(DeleteView):
    model = MissionCode
    success_url = reverse_lazy('list_missioncode')

### Flight Forms (!!! have no perms yet)

@login_required
@permission_required('flight.add_airbase')
def airplane_detail_add(request, tail, name): # needs airbase perm checks on post
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    if request.user.has_perm('flight.add_airbase'):
        mission_list = None
        trip_list = None
        if request.method == 'POST':
            a = Airplane.objects.get(name=name)
            form = AirplaneDetailAdd(request.POST)
            if form.is_valid():
                incident = form['incident']
                ax = incident.value()
                inc = Incident.objects.get(id=ax)
                adate = form['startdate']
                x = adate.value()
                xtime = datetime.datetime.strptime(x, "%Y-%m-%d")
                #form['planestart'].value = 
                #incident = Incident.objects.get(id=x)
                created_trip = form.save(commit=False)
                try:
                    created_trip.mission = Mission.objects.get(Q(airplane_id=a.id) & Q(startdate=x))
                    ndate = datetime.datetime.combine(created_trip.mission.startdate, time(00, 00))
                except:
                    created_mission = Mission(airplane=a, startdate=x, dailyavailstart=x, author=request.user)
                    created_mission.save()
                    assign('change_mission', request.user, created_mission)
                    assign('delete_mission', request.user, created_mission)
                    created_trip.mission = created_mission
                    ndate = datetime.datetime.strptime(created_trip.mission.startdate, "%Y-%m-%d")
                nominaldate = ndate.strftime("%Y/%m/%d")
                dashdate = ndate.strftime("%Y-%m-%d")
                #xtime = ndate
                created_trip.planestart = created_trip.planestart.replace(year=xtime.year, month=xtime.month, day=xtime.day)
                created_trip.planestop = created_trip.planestop.replace(year=xtime.year, month=xtime.month, day=xtime.day)
                created_trip.incident_id = inc.id
                try:
                    created_trip.pilot_id = created_trip.mission.pilot_id
                except:
                    pass
                try:
                    created_trip.copilot_id = created_trip.mission.copilot_id
                except:
                    pass
                try:
                    created_trip.othercrew_id = created_trip.mission.othercrew_id
                except:
                    pass
                created_trip.author_id = request.user.id
                created_trip.save()
                msg = 'Flight added to Airplane %s/%s on %s/%s on %s.' % (created_trip.mission.airplane.tail, created_trip.mission.airplane.name, created_trip.incident.name, created_trip.incident.resourceorder, dashdate)
                messages.success(request, msg)
                l = Logitem(author=request.user, status='S', message=msg, obj_model='Flight', obj_id=created_trip.id, obj_in='', obj_out='',)
                l.save()
                #return HttpResponseRedirect('/flight/airplane/%s/%s/' % (a.tail, a.name))
                return HttpResponseRedirect('/mission/%s/%s/%s/add/' % (a.tail, a.name, nominaldate))
        else:
            a = Airplane.objects.prefetch_related('rate_airplane',).annotate(mission_count=Count('mission_airplane')).get(name=name)
            a.frate_list = a.rate_airplane.filter(ratetype__iexact='flight').order_by('-effectivedate')
            if a.frate_list:
                a.frate_list = a.frate_list[:1]
            a.arate_list = a.rate_airplane.filter(ratetype__iexact='avail').order_by('-effectivedate')
            if a.arate_list:
                a.arate_list = a.arate_list[:1]
            a.srate_list = a.rate_airplane.filter(ratetype__iexact='nonavail').order_by('-effectivedate')
            if a.srate_list:
                a.srate_list = a.srate_list[:1]
            a.erate_list = a.rate_airplane.filter(ratetype__iexact='extended').order_by('-effectivedate')
            if a.erate_list:
                a.erate_list = a.erate_list[:1]
            #if a.begins and a.ends:
            #    a.map = (a.ends-a.begins).days
            artypes = a.rate_airplane.exclude(Q(ratetype__iexact='flight') | Q(ratetype__iexact='avail') | Q(ratetype__iexact='nonavail')| Q(ratetype__iexact='extended')).distinct('ratetype').values_list('ratetype')
            a.rtypes = []
            for rtype in artypes:
                rtype = a.rate_airplane.filter(ratetype__iexact=rtype).order_by('-effectivedate')[:1]
                a.rtypes.append(rtype)
            a.mission_count = Mission.objects.filter(airplane_id=a.id).count()
            if a.mission_count:
                mission_list = Mission.objects.filter(airplane_id=a.id).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
                trip_list = Trip.objects.filter(mission__in=mission_list)
                a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
                for m in mission_list:
                    m.trip_list = trip_list.filter(mission_id=m.id)
                    t2m(m,m.trip_list)
                    am(a,m)
                a2(a)
            else:
                mission_list = None
                trip_list = None
            now = datetime.datetime.now()
            laststop = now.replace(hour=0, minute=0)
            form = AirplaneDetailAdd(initial={ 'planestart': laststop, 'planestop': laststop, },)

        return render_to_response('flight/airplane_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list, 'form': form, }, context_instance=RequestContext(request))
    else:
        form = 'form'
        #msg = 'Permission for Mission %s/%s/%s/%s/ or one of its Airbases required.' % (m.airplane.tail, m.incident.name, m.incident.resourceorder, nominaldate)
        msg = 'Permission required.' #% (m.airplane.tail, m.incident.name, m.incident.resourceorder, nominaldate)
        messages.warning(request, msg) 
        l = Logitem(author=request.user, status='W', message=msg, obj_model='Flight',)
        l.save()
        return HttpResponseRedirect('/airplane/%s/%s/' % (a.tail, a.name))

@login_required
@permission_required('flight.add_airbase')
def incident_detail_add(request, slug, ro): # needs airbase perm checks on post
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    #if request.user.has_perm('change_mission', m) or up == 1:
    a = Incident.objects.get(resourceorder=ro)
    if request.user.has_perm('flight.add_airbase'):
        mission_list = None
        trip_list = None
        if request.method == 'POST':
            form = IncidentDetailAdd(request.POST)
            if form.is_valid():
                airplane = form['airplane']
                ax = airplane.value()
                pl = Airplane.objects.get(id=ax)
                adate = form['startdate']
                x = adate.value()
                xtime = datetime.datetime.strptime(x, "%Y-%m-%d")
                #incident = Incident.objects.get(id=x)
                created_trip = form.save(commit=False)
                try:
                    created_trip.mission = Mission.objects.get(Q(airplane_id=pl.id) & Q(startdate=x))
                    ndate = datetime.datetime.combine(created_trip.mission.startdate, time(00, 00))
                except:
                    created_mission = Mission(airplane=pl, startdate=x, dailyavailstart=x, author=request.user)
                    created_mission.save()
                    assign('change_mission', request.user, created_mission)
                    assign('delete_mission', request.user, created_mission)
                    created_trip.mission = created_mission
                    ndate = datetime.datetime.strptime(created_trip.mission.startdate, "%Y-%m-%d")
                nominaldate = ndate.strftime("%Y/%m/%d")
                dashdate = ndate.strftime("%Y-%m-%d")
                created_trip.planestart = created_trip.planestart.replace(year=xtime.year, month=xtime.month, day=xtime.day)
                created_trip.planestop = created_trip.planestop.replace(year=xtime.year, month=xtime.month, day=xtime.day)
                created_trip.incident_id = a.id
                try:
                    created_trip.pilot_id = created_trip.mission.pilot_id
                except:
                    pass
                try:
                    created_trip.copilot_id = created_trip.mission.copilot_id
                except:
                    pass
                try:
                    created_trip.othercrew_id = created_trip.mission.othercrew_id
                except:
                    pass
                created_trip.author_id = request.user.id
                created_trip.save()
                msg = 'Flight added to Airplane %s/%s on %s/%s on %s.' % (created_trip.mission.airplane.tail, created_trip.mission.airplane.name, a.name, a.resourceorder, dashdate)
                messages.success(request, msg)
                l = Logitem(author=request.user, status='S', message=msg, obj_model='Flight', obj_id=created_trip.id, obj_in='', obj_out='',)
                l.save()
                return HttpResponseRedirect('/incident/%s/%s/add/' % (a.name, a.resourceorder))
                #return HttpResponseRedirect('/flight/mission/%s/%s/%s/add/' % (created_trip.mission.airplane.tail, created_trip.mission.airplane.name, nominaldate))
        else:
            a.mission_count = Mission.objects.filter(trip_mission__incident=a.id).count() # do we want every m with t on i?
            if a.mission_count:
                mission_list = Mission.objects.filter(trip_mission__incident_id=a.id).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal')) # what are we counting here?
                trip_list = Trip.objects.filter(incident_id=a.id)
                a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
                for m in mission_list:
                    m.trip_list = trip_list.filter(mission_id=m.id)
                    t2m(m,m.trip_list)
                    am(a,m)
                a2(a)
            else:
                mission_list = None
                trip_list = None
            now = datetime.datetime.now()
            laststop = now.replace(hour=0, minute=0)
            form = IncidentDetailAdd(initial={'startdate': a.begins, 'planestart': laststop, 'planestop': laststop, },)
        return render_to_response('flight/incident_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list, 'form': form, }, context_instance=RequestContext(request))
    else:
        form = 'form'
        #msg = 'Permission for Mission %s/%s/%s/%s/ or one of its Airbases required.' % (m.airplane.tail, m.incident.name, m.incident.resourceorder, nominaldate)
        msg = 'Permission required.' #% (m.airplane.tail, m.incident.name, m.incident.resourceorder, nominaldate)
        messages.warning(request, msg) 
        l = Logitem(author=request.user, status='W', message=msg, obj_model='Flight',)
        l.save()
        return HttpResponseRedirect('/incident/%s/%s/' % (a.name, a. resourceorder))

    return render_to_response('flight/incident_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list, 'form': form, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def airplane_date_add(request, tail, name, yeara, moa, daa): # needs airbase perm checks on post
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = Airplane.objects.get(name=name)
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    #bdate = datetime.datetime(int(yearb), int(mob), int(dab), 0, 0)
    #mission_list = Mission.objects.filter(Q(airplane=a) & Q(startdate=adate)).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    #object.mission_list = Mission.objects.filter(airplane=object)
    #a = Airplane.objects.get(name=name)
    #user_list = get_users_with_perms(a)
    #a.frate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='flight').order_by('-effectivedate')
    #if a.frate_list:
    #    a.frate_list = a.frate_list[:1]
    #a.arate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='avail').order_by('-effectivedate')
    #if a.arate_list:
    #    a.arate_list = a.arate_list[:1]
    #a.srate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='nonavail').order_by('-effectivedate')
    #if a.srate_list:
    #    a.srate_list = a.srate_list[:1]
    #a.erate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='extended').order_by('-effectivedate')
    #if a.erate_list:
    #    a.erate_list = a.erate_list[:1]
    #if a.begins and a.ends:
    #    a.map = (a.ends-a.begins).days
    #arates = Rate.objects.filter(airplane=a).exclude(ratetype__iexact='flight').exclude(ratetype__iexact='avail').exclude(ratetype__iexact='nonavail').exclude(ratetype__iexact='extended').order_by('-effectivedate')
    #artypes = Rate.objects.filter(airplane=a).exclude(ratetype__iexact='flight').exclude(ratetype__iexact='avail').exclude(ratetype__iexact='nonavail').exclude(ratetype__iexact='extended').distinct('ratetype').values_list('ratetype')
    #a.rtypes = []
    #for rtype in artypes:
    #    rtype = Rate.objects.filter(airplane=a).filter(ratetype__iexact=rtype).order_by('-effectivedate')[:1]
    #    a.rtypes.append(rtype)
    if request.user.has_perm('flight.add_airbase'):
        mission_list = None
        trip_list = None
        if request.method == 'POST':
            form = AirplaneTripAdd(request.POST)
            if form.is_valid():
                incident = form['incident']
                x = incident.value()
                xtime = adate
                incident = Incident.objects.get(id=x)
                created_trip = form.save(commit=False)
                try:
                    created_trip.mission = Mission.objects.get(Q(airplane_id=a.id) & Q(startdate=adate))
                except:
                    created_mission = Mission(airplane=a, startdate=adate, dailyavailstart=adate, author=request.user)
                    created_mission.save()
                    assign('change_mission', request.user, created_mission)
                    assign('delete_mission', request.user, created_mission)
                    created_trip.mission = created_mission
                created_trip.planestart = created_trip.planestart.replace(year=xtime.year, month=xtime.month, day=xtime.day)
                created_trip.planestop = created_trip.planestop.replace(year=xtime.year, month=xtime.month, day=xtime.day)
                created_trip.incident_id = incident.id
                try:
                    created_trip.pilot_id = created_trip.mission.pilot_id
                except:
                    pass
                try:
                    created_trip.copilot_id = created_trip.mission.copilot_id
                except:
                    pass
                try:
                    created_trip.othercrew_id = created_trip.mission.othercrew_id
                except:
                    pass
                created_trip.author_id = request.user.id
                created_trip.save()
                nominaldate = created_trip.mission.startdate.strftime("%Y/%m/%d")
                dashdate = created_trip.mission.startdate.strftime("%Y-%m-%d")
                msg = 'Flight added to Airplane %s/%s on %s/%s on %s.' % (created_trip.mission.airplane.tail, created_trip.mission.airplane.name, created_trip.incident.name, created_trip.incident.resourceorder, dashdate)
                messages.success(request, msg)
                l = Logitem(author=request.user, status='S', message=msg, obj_model='Flight', obj_id=created_trip.id, obj_in='', obj_out='',)
                l.save()
                #return HttpResponseRedirect('/flight/airplane/%s/%s/%s/' % (a.tail, a.name, dashdate))
                return HttpResponseRedirect('/mission/%s/%s/%s/add/' % (a.tail, a.name, nominaldate))
        else:      
            a.mission_count = Mission.objects.filter(Q(airplane=a) & Q(startdate=adate)).count()
            if a.mission_count:
                mission_list = Mission.objects.filter(Q(airplane=a) & Q(startdate=adate)).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
                trip_list = Trip.objects.filter(mission__in=mission_list)
                a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
                for m in mission_list:
                    m.trip_list = trip_list.filter(mission_id=m.id)
                    t2m(m,m.trip_list)
                    am(a,m)
                a2(a)
            else:
                mission_list = None
                trip_list = None
            laststop = datetime.datetime.combine(adate, time(00, 00))
            thebase = None
            rtype = None
            i = 0
            if trip_list:
                for t in trip_list.order_by('-planestart'):
                    i = i + 1
                    if i == 1:
                        try:
                            thebase = t.frombase
                        except:
                            pass
                        try:
                            rtype = thebase.rtype
                        except:
                            rtype = None
                        try:
                            thebase = t.tobase
                        except:
                            pass
                        if t.planestop is not None:
                            try:
                                laststop = t.planestop
                            except:
                                pass
            form = AirplaneTripAdd(initial={'frombase': thebase, 'planestart': laststop, 'planestop': laststop, 'rtype': rtype, },)
            #if m.printout_list.count() >= 1:
            #    msg = 'Mission %s/%s/%s/%s/ has been printed already. Check the printer before adding flights.' % (m.airplane.tail, m.incident.name, m. incident.resourceorder, m.nominaldate)
            #    messages.warning(request, msg)
            #    l = Logitem(author=request.user, status='W', message=msg, obj_model='Flight',)
            #    l.save() 
        return render_to_response('flight/airplane_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list,'adate': adate, 'form': form, }, context_instance=RequestContext(request))

    else:
        form = 'form'
        #msg = 'Permission for Mission %s/%s/%s/%s/ or one of its Airbases required.' % (m.airplane.tail, m.incident.name, m.incident.resourceorder, nominaldate)
        msg = 'Permission required.' #% (m.airplane.tail, m.incident.name, m.incident.resourceorder, nominaldate)
        messages.warning(request, msg) 
        l = Logitem(author=request.user, status='W', message=msg, obj_model='Flight',)
        l.save()
        dashdate = adate.strftime("%Y-%m-%d")
        return HttpResponseRedirect('/airplane/%s/%s/%s/' % (a.tail, a.name, dashdate))

    return render_to_response('flight/airplane_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list,'adate': adate, 'form': form, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def incident_date_add(request, slug, ro, yeara, moa, daa): # needs airbase perm checks on post
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = Incident.objects.get(resourceorder=ro)
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    if request.user.has_perm('flight.add_airbase'):
        mission_list = None
        trip_list = None
        if request.method == 'POST':
            form = IncidentTripAdd(request.POST)
            if form.is_valid():
                airplane = form['airplane']
                x = airplane.value()
                airplane = Airplane.objects.get(id=x)
                xtime = adate
                #ax = adate.value()
                #xtime = datetime.datetime.strptime(ax, "%Y-%m-%d")
                created_trip = form.save(commit=False)
                try:
                    created_trip.mission = Mission.objects.get(Q(airplane_id=airplane.id) & Q(startdate=adate))
                except:
                    created_mission = Mission(airplane=airplane, startdate=adate, dailyavailstart=adate, author=request.user)
                    created_mission.save()
                    assign('change_mission', request.user, created_mission)
                    assign('delete_mission', request.user, created_mission)
                    created_trip.mission = created_mission
                created_trip.planestart = created_trip.planestart.replace(year=xtime.year, month=xtime.month, day=xtime.day)
                created_trip.planestop = created_trip.planestop.replace(year=xtime.year, month=xtime.month, day=xtime.day)
                created_trip.incident_id = a.id
                try:
                    created_trip.pilot_id = created_trip.mission.pilot_id
                except:
                    pass
                try:
                    created_trip.copilot_id = created_trip.mission.copilot_id
                except:
                    pass
                try:
                    created_trip.othercrew_id = created_trip.mission.othercrew_id
                except:
                    pass
                created_trip.author_id = request.user.id
                created_trip.save()
                nominaldate = created_trip.mission.startdate.strftime("%Y/%m/%d")
                dashdate = created_trip.mission.startdate.strftime("%Y-%m-%d")
                msg = 'Flight added to Airplane %s/%s on %s/%s on %s.' % (created_trip.mission.airplane.tail, created_trip.mission.airplane.name, a.name, a.resourceorder, dashdate)
                messages.success(request, msg)
                l = Logitem(author=request.user, status='S', message=msg, obj_model='Flight', obj_id=created_trip.id, obj_in='', obj_out='',)
                l.save()
                #return HttpResponseRedirect('/flight/incident/%s/%s/%s/' % (a.name, a.resourceorder, dashdate))
                return HttpResponseRedirect('/mission/%s/%s/%s/add/' % (created_trip.mission.airplane.tail, created_trip.mission.airplane.name, nominaldate))
        else:
            a.mission_count = Mission.objects.filter(trip_mission__incident_id=a.id).filter(startdate=adate).count()
            if a.mission_count:
                mission_list = Mission.objects.filter(trip_mission__incident_id=a.id).filter(startdate=adate).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
                trip_list = Trip.objects.filter(incident_id=a.id)
                a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
                for m in mission_list:
                    m.trip_list = trip_list.filter(mission_id=m.id)
                    t2m(m,m.trip_list)
                    am(a,m)
                a2(a)
            else:
                mission_list = None
                trip_list = None
            laststop = datetime.datetime.combine(adate, time(00, 00))
            thebase = None
            rtype = None
            i = 0
            if trip_list:
                for t in trip_list.order_by('-planestart'):
                    i = i + 1
                    if i == 1:
                        try:
                            thebase = t.frombase
                        except:
                            pass
                        try:
                            rtype = thebase.rtype
                        except:
                            rtype = None
                        try:
                            thebase = t.tobase
                        except:
                            pass
                        if t.planestop is not None:
                            try:
                                laststop = t.planestop
                            except:
                                pass
            form = IncidentTripAdd(initial={'frombase': thebase, 'planestart': laststop, 'planestop': laststop, 'rtype': rtype, },)
            #if m.printout_list.count() >= 1:
            #    msg = 'Mission %s/%s/%s/%s/ has been printed already. Check the printer before adding flights.' % (m.airplane.tail, m.incident.name, m. incident.resourceorder, m.nominaldate)
            #    messages.warning(request, msg)
            #    l = Logitem(author=request.user, status='W', message=msg, obj_model='Flight',)
            #    l.save() 
        return render_to_response('flight/incident_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list, 'adate': adate, 'form': form, }, context_instance=RequestContext(request))

    else:
        form = 'form'
        #msg = 'Permission for Mission %s/%s/%s/%s/ or one of its Airbases required.' % (m.airplane.tail, m.incident.name, m.incident.resourceorder, nominaldate)
        msg = 'Permission required.' #% (m.airplane.tail, m.incident.name, m.incident.resourceorder, nominaldate)
        messages.warning(request, msg) 
        l = Logitem(author=request.user, status='W', message=msg, obj_model='Flight',)
        l.save()
        dashdate = adate.strftime("%Y-%m-%d")
        return HttpResponseRedirect('/incident/%s/%s/%s/' % (a.name, a. resourceorder, dashdate))

    return render_to_response('flight/incident_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list, 'adate': adate, 'form': form, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def airplane_incident_add(request, tail, name, incident, ro): # needs post refactor, airbase perm checks on post
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = Airplane.objects.get(name=name)
    inc = Incident.objects.get(resourceorder=ro)
    a.mission_count = Mission.objects.filter(airplane_id=a.id).filter(trip_mission__incident_id=inc.id).count()
    if a.mission_count:
        mission_list = Mission.objects.filter(airplane_id=a.id).filter(trip_mission__incident_id=inc.id).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
        trip_list = Trip.objects.filter(incident_id=inc.id)
        a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
        for m in mission_list:
            m.trip_list = trip_list.filter(mission_id=m.id)
            t2m(m,m.trip_list)
            am(a,m)
        a2(a)
    else:
        mission_list = None
        trip_list = None
    if request.user.has_perm('flight.change_mission'):
        if request.method == 'POST':
            form = AirplaneIncidentTripAdd(request.POST)
            if form.is_valid():
                adate = form['startdate']
                x = adate.value()
                #incident = Incident.objects.get(id=x)
                #xtime = adate
                ax = adate.value()
                xtime = datetime.datetime.strptime(ax, "%Y-%m-%d")
                #xtime = adate
                created_trip = form.save(commit=False)
                try:
                    created_trip.mission = Mission.objects.get(Q(airplane_id=a.id) & Q(startdate=x))
                    ndate = datetime.datetime.combine(created_trip.mission.startdate, time(00, 00))
                except:
                    created_mission = Mission(airplane=a, startdate=x, dailyavailstart=x, author=request.user)
                    created_mission.save()
                    assign('change_mission', request.user, created_mission)
                    assign('delete_mission', request.user, created_mission)
                    created_trip.mission = created_mission
                    ndate = datetime.datetime.strptime(created_trip.mission.startdate, "%Y-%m-%d")
                created_trip.planestart = created_trip.planestart.replace(year=xtime.year, month=xtime.month, day=xtime.day)
                created_trip.planestop = created_trip.planestop.replace(year=xtime.year, month=xtime.month, day=xtime.day)
                created_trip.incident_id = inc.id
                try:
                    created_trip.pilot_id = created_trip.mission.pilot_id
                except:
                    pass
                try:
                    created_trip.copilot_id = created_trip.mission.copilot_id
                except:
                    pass
                try:
                    created_trip.othercrew_id = created_trip.mission.othercrew_id
                except:
                    pass
                created_trip.author_id = request.user.id
                created_trip.save()
                nominaldate = ndate.strftime("%Y/%m/%d")
                dashdate = ndate.strftime("%Y-%m-%d")
                msg = 'Flight added to Airplane %s/%s on %s/%s on %s.' % (a.tail, a.name, inc.name, inc.resourceorder, dashdate)
                messages.success(request, msg)
                l = Logitem(author=request.user, status='S', message=msg, obj_model='Flight', obj_id=created_trip.id, obj_in='', obj_out='',)
                l.save()
                #return HttpResponseRedirect('/flight/airplane/%s/%s/%s/%s/' % (a.tail, a.name, inc.name, inc.resourceorder))
                return HttpResponseRedirect('/mission/%s/%s/%s/add/' % (a.tail, a.name, nominaldate))
        else:
            now = datetime.datetime.now()
            laststop = now.replace(hour=0, minute=0)
            #laststop = datetime.datetime.combine(adate, time(00, 00))
            thebase = None
            rtype = None
            i = 0
            if trip_list:
                for t in trip_list.order_by('-planestart'):
                    i = i + 1
                    if i == 1:
                        try:
                            thebase = t.frombase
                        except:
                            pass
                        try:
                            rtype = thebase.rtype
                        except:
                            rtype = None
                        try:
                            thebase = t.tobase
                        except:
                            pass
                        if t.planestop is not None:
                            try:
                                laststop = t.planestop
                            except:
                                pass
            form = AirplaneIncidentTripAdd(initial={'frombase': thebase, 'planestart': laststop, 'planestop': laststop, 'rtype': rtype, },)
            #if m.printout_list.count() >= 1:
            #    msg = 'Mission %s/%s/%s/%s/ has been printed already. Check the printer before adding flights.' % (m.airplane.tail, m.incident.name, m. incident.resourceorder, m.nominaldate)
            #    messages.warning(request, msg)
            #    l = Logitem(author=request.user, status='W', message=msg, obj_model='Flight',)
            #    l.save() 
        return render_to_response('flight/airplane_detail.html', { 'u': u, 'object': a, 'incident': inc, 'mission_list': mission_list, 'flight_list': trip_list, 'form': form, }, context_instance=RequestContext(request))
    else:
        form = 'form'
        #msg = 'Permission for Mission %s/%s/%s/%s/ or one of its Airbases required.' % (m.airplane.tail, m.incident.name, m.incident.resourceorder, nominaldate)
        msg = 'Permission required.' #% (m.airplane.tail, m.incident.name, m.incident.resourceorder, nominaldate)
        messages.warning(request, msg) 
        l = Logitem(author=request.user, status='W', message=msg, obj_model='Flight',)
        l.save()
        return HttpResponseRedirect('/airplane/%s/%s/%s/%s/' % (a.tail, a.name, inc.name, inc.resourceorder))

    return render_to_response('flight/airplane_detail.html', { 'u': u, 'object': a, 'incident': inc, 'mission_list': mission_list, 'flight_list': trip_list, 'form': form, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def airplane_incident_date_add(request, tail, name, incident, ro, yeara, moa, daa): # needs post refactor, airbase perm checks on post
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = Airplane.objects.get(name=name)
    inc = Incident.objects.get(resourceorder=ro)
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    a.mission_count = Mission.objects.filter(airplane_id=a.id).filter(trip_mission__incident_id=inc.id).filter(startdate=adate).count()
    if a.mission_count:
        mission_list = Mission.objects.filter(airplane_id=a.id).filter(trip_mission__incident_id=inc.id).filter(startdate=adate).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
        trip_list = Trip.objects.filter(Q(mission__in=mission_list),Q(incident_id=inc.id))
        a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
        for m in mission_list:
            m.trip_list = trip_list.filter(mission_id=m.id)
            t2m(m,m.trip_list)
            am(a,m)
        a2(a)
    else:
        mission_list = None
        trip_list = None
    if request.user.has_perm('flight.change_mission'):
        if request.method == 'POST':
            form = AirplaneIncidentDateTripAdd(request.POST)
            if form.is_valid():
                #airplane = form['airplane']
                #x = airplane.value()
                #airplane = Airplane.objects.get(id=x)
                #created_trip = form.save(commit=False)
                #adate = form['startdate']
                #x = incident.value()
                #incident = Incident.objects.get(id=x)
                xtime = adate
                created_trip = form.save(commit=False)
                try:
                    created_trip.mission = Mission.objects.get(Q(airplane_id=a.id) & Q(startdate=adate))
                except:
                    created_mission = Mission(airplane=a, startdate=adate, dailyavailstart=adate, author=request.user)
                    created_mission.save()
                    assign('change_mission', request.user, created_mission)
                    assign('delete_mission', request.user, created_mission)
                    created_trip.mission = created_mission
                created_trip.planestart = created_trip.planestart.replace(year=xtime.year, month=xtime.month, day=xtime.day)
                created_trip.planestop = created_trip.planestop.replace(year=xtime.year, month=xtime.month, day=xtime.day)
                created_trip.incident_id = inc.id
                try:
                    created_trip.pilot_id = created_trip.mission.pilot_id
                except:
                    pass
                try:
                    created_trip.copilot_id = created_trip.mission.copilot_id
                except:
                    pass
                try:
                    created_trip.othercrew_id = created_trip.mission.othercrew_id
                except:
                    pass
                created_trip.author_id = request.user.id
                created_trip.save()
                nominaldate = created_trip.mission.startdate.strftime("%Y/%m/%d")
                dashdate = created_trip.mission.startdate.strftime("%Y-%m-%d")
                msg = 'Flight added to Airplane %s/%s on %s/%s on %s.' % (a.tail, a.name, inc.name, inc.resourceorder, dashdate)
                messages.success(request, msg)
                l = Logitem(author=request.user, status='S', message=msg, obj_model='Flight', obj_id=created_trip.id, obj_in='', obj_out='',)
                l.save()
                #return HttpResponseRedirect('/flight/airplane/%s/%s/%s/%s/%s/' % (a.tail, a.name, inc.name, inc.resourceorder, dashdate))
                return HttpResponseRedirect('/mission/%s/%s/%s/add/' % (a.tail, a.name, nominaldate))
        else:
            laststop = datetime.datetime.combine(adate, time(00, 00))
            thebase = None
            rtype = None
            i = 0
            if trip_list:
                for t in trip_list.order_by('-planestart'):
                    i = i + 1
                    if i == 1:
                        try:
                            thebase = t.frombase
                        except:
                            pass
                        try:
                            rtype = thebase.rtype
                        except:
                            rtype = None
                        try:
                            thebase = t.tobase
                        except:
                            pass
                        if t.planestop is not None:
                            try:
                                laststop = t.planestop
                            except:
                                pass
            form = AirplaneIncidentDateTripAdd(initial={'frombase': thebase, 'planestart': laststop, 'planestop': laststop, 'rtype': rtype, },)
            #if m.printout_list.count() >= 1:
            #    msg = 'Mission %s/%s/%s/%s/ has been printed already. Check the printer before adding flights.' % (m.airplane.tail, m.incident.name, m. incident.resourceorder, m.nominaldate)
            #    messages.warning(request, msg)
            #    l = Logitem(author=request.user, status='W', message=msg, obj_model='Flight',)
            #    l.save() 
        return render_to_response('flight/airplane_detail.html', { 'u': u, 'object': a, 'incident': inc, 'mission_list': mission_list, 'flight_list': trip_list, 'adate': adate, 'form': form, }, context_instance=RequestContext(request))
    else:
        form = 'form'
        #msg = 'Permission for Mission %s/%s/%s/%s/ or one of its Airbases required.' % (m.airplane.tail, m.incident.name, m.incident.resourceorder, nominaldate)
        msg = 'Permission required.' #% (m.airplane.tail, m.incident.name, m.incident.resourceorder, nominaldate)
        messages.warning(request, msg) 
        l = Logitem(author=request.user, status='W', message=msg, obj_model='Flight',)
        l.save()
        dashdate = adate.strftime("%Y-%m-%d")
        return HttpResponseRedirect('/airplane/%s/%s/%s/%s/%s/' % (a.tail, a.name, inc.name, inc.resourceorder, dashdate))

### Mission Forms (!!! have no perms yet)

@login_required
@permission_required('flight.add_airbase')
def mission_edit(request, tail, name, year, mo, da):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    iyear = int(year)
    imo = int(mo)
    ida = int(da)
    themission = Mission.objects.get(
        Q(airplane__name=name),
        Q(startdate__year=iyear),
        Q(startdate__month=imo),
        Q(startdate__day=ida),
        )
    try:
        themission.c = Contract.objects.filter(airplane_id=themission.airplane_id).filter(effectivedate__lte=themission.startdate)[0]
    except:
        themission.c = None
    if request.user.has_perm('change_mission', themission) or request.user.has_perm('change_airplane', themission.airplane) or request.user.has_perm('change_airbase', themission.opsbase): # or request.user.has_perm('change_airbase', themission.c.adminbase) 
        if request.method == 'POST':
            form = MissionEdit(request.POST, instance=themission)
            if form.is_valid():
                obj = form.save(commit=False)
                try:
                    obj.c = Contract.objects.filter(airplane_id=obj.airplane_id).filter(effectivedate__lte=obj.startdate)[0]
                except:
                    obj.c = None
                if request.user.has_perm('change_mission', obj) or request.user.has_perm('change_airplane', obj.airplane) or request.user.has_perm('change_airbase', themission.opsbase): # or request.user.has_perm('change_airbase', obj.c.adminbase) 
                    if form.cleaned_data['dailyavailstart_1']:
                        obj.dailyavailstart = datetime.datetime.combine(obj.startdate, form.cleaned_data['dailyavailstart_1'])
                    if form.cleaned_data['dailyavailstop_1']:
                        obj.dailyavailstop = datetime.datetime.combine(obj.startdate, form.cleaned_data['dailyavailstop_1'])
                    else:
                        obj.dailyavailstop = None
                    obj.save()
                    flights = Trip.objects.filter(mission_id=obj.id)#.update(planestart=themission.startdate)
                    for flight in flights:
                        flight.planestart = flight.planestart.replace(year=obj.startdate.year, month=obj.startdate.month, day=obj.startdate.day)
                        try:
                            flight.pilot_id = obj.pilot_id
                        except:
                            pass
                        try:
                            flight.copilot_id = obj.copilot_id
                        except:
                            pass
                        try:
                            flight.othercrew_id = obj.othercrew_id
                        except:
                            pass
                        if flight.planestop is not None:
                            flight.planestop = flight.planestop.replace(year=obj.startdate.year, month=obj.startdate.month, day=obj.startdate.day)
                        flight.save()
                    nominaldate = obj.startdate.strftime("%Y/%m/%d")
                    m = 'Mission %s/%s/%s/ edited.' % (obj.airplane.tail, obj.airplane.name, nominaldate)
                    messages.success(request, m)
                    l = Logitem(author=request.user, status='S', message=m, obj_model='Mission', obj_id=obj.id, obj_in='', obj_out='',)
                    l.save()
                    return HttpResponseRedirect('/mission/%s/%s/%s/' % (obj.airplane.tail, obj.airplane.name, nominaldate))
                else:
                    m = 'You need permission at Airbase %s, Airbase %s, or on Airplane %s to edit this mission.' % (themission.c.adminbase, themission.opsbase, themission.airplane.name)
                    messages.warning(request, m) 
                    l = Logitem(author=request.user, status='W', message=m, obj_model='Mission',)
                    l.save() 
                    return render_to_response('flight/mission_edit.html', { 'u': u, 'form': form, 'themission': themission, }, context_instance=RequestContext(request))
        else:
            form = MissionEdit(instance=themission, initial={'dailyavailstart_1': themission.dailyavailstart, 'dailyavailstop_1': themission.dailyavailstop, },)
            themission.a = Airplane.objects.get(id=themission.airplane_id)
            themission.printout_list = Printout.objects.filter(
                Q(obj_model='mission'),
                Q(obj_id=themission.id)
                )
            nominaldate = themission.startdate.strftime("%Y/%m/%d")
            if themission.printout_list.count() >= 1:
                m = 'Mission %s/%s/%s/ has been printed already. Check the printer before editing.' % (themission.airplane.tail, themission.airplane.name, nominaldate)
                messages.info(request, m) 
                l = Logitem(author=request.user, status='W', message=m, obj_model=' Mission',)
                l.save() 
        return render_to_response('flight/mission_edit.html', { 'u': u, 'form': form, 'themission': themission }, context_instance=RequestContext(request))
    else:
        form = 'form'
        nominaldate = themission.startdate.strftime("%Y/%m/%d")
        #m = 'You need permission at Airbase %s, Airbase %s, or on Airplane %s to edit this mission.' % (themission.c.adminbase, themission.opsbase, themission.airplane.name)
        m = 'You need permission at Airbase %s or on Airplane %s to edit this mission.' % (themission.opsbase, themission.airplane.name)
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Mission',)
        l.save() 
        return HttpResponseRedirect('/mission/%s/%s/%s/' % (themission.airplane.tail, themission.airplane.name, nominaldate))

@login_required
@permission_required('flight.add_airbase')
def mission_delete(request, tail, name, year, mo, da):
    iyear = int(year)
    imo = int(mo)
    ida = int(da)
    themission = Mission.objects.get(
        Q(airplane__name=name),
        Q(startdate__year=iyear),
        Q(startdate__month=imo),
        Q(startdate__day=ida),
        )
    try:
        themission.c = Contract.objects.filter(airplane_id=themission.airplane_id).filter(effectivedate__lte=themission.startdate)[0]
    except:
        themission.c = None
    if request.user.has_perm('delete_mission', themission) or request.user.has_perm('change_airplane', themission.airplane) or request.user.has_perm('change_airbase', themission.opsbase): # or request.user.has_perm('change_airbase', themission.c.adminbase)
        if request.method == 'POST':
            form = MissionDelete(request.POST, instance=themission)
            if form.is_valid():
                obj = form.save(commit=False)
                #clean_orphan_obj_perms()
                nominaldate = obj.startdate.strftime("%Y/%m/%d")
                m = 'Mission %s/%s/%s/ deleted.' % (obj.airplane.tail, obj.airplane.name, nominaldate)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Mission', obj_id=obj.id, obj_in='', obj_out='',)
                obj.delete()
                l.save()
                dashdate = obj.startdate.strftime("%Y-%m-%d")
                return HttpResponseRedirect('/airplane/%s/%s/%s/' % (obj.airplane.tail, obj.airplane.name, dashdate))
        else:
            form = MissionDelete(instance=themission)
        return render_to_response('flight/mission_delete.html', { 'form': form, 'themission': themission }, context_instance=RequestContext(request))
    else:
        form = 'form'
        nominaldate = themission.startdate.strftime("%Y/%m/%d")
        m = 'You need permission at Airbase %s, Airbase %s, or on Airplane %s to delete this mission.' % (themission.c.adminbase, themission.opsbase, themission.airplane.name)
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Mission',)
        l.save()   
        return HttpResponseRedirect('/mission/%s/%s/%s/' % (themission.airplane.tail, themission.airplane.name, nominaldate))

@login_required
@permission_required('flight.add_airbase')
def mission_flight_add(request, tail, name, year, mo, da): # this might as well redirect to airplane-date-add because no incident
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    iyear = int(year)
    imo = int(mo)
    ida = int(da)
    m = Mission.objects.get(
        Q(airplane__name=name),
        Q(startdate__year=iyear),
        Q(startdate__month=imo),
        Q(startdate__day=ida),
        )
    m.nominaldate = m.startdate.strftime("%Y/%m/%d")
    trip_list = Trip.objects.filter(mission_id=m.id)
    t2m(m,trip_list)
    up = None
    incident = None
    thebase = None
    laststop = datetime.datetime.combine(m.startdate, time(00, 00))
    i = 0
    for t in trip_list.order_by('-planestart'):
        i = i + 1
        if i == 1:
            if t.incident is not None:
                try:
                    incident = t.incident
                except:
                    pass
            try:
                thebase = t.frombase
            except:
                pass
            try:
                thebase = t.tobase
            except:
                pass
            if t.planestop is not None:
                try:
                    laststop = t.planestop
                except:
                    pass
        if up == None:
            try:
                if request.user in get_users_with_perms(t.frombase):
                    up = 1
            except:
                pass
            try:
                if request.user in get_users_with_perms(t.tobase):
                    up = 1
            except:
                pass
    if request.user.has_perm('change_mission', m) or request.user.has_perm('change_airplane', m.airplane) or request.user.has_perm('change_airbase', m.opsbase) or up == 1: # add contract adminbase
        if request.method == 'POST':
            form = MissionTripAdd(request.POST)
            #form.planestop = form.planestart
            #form['planestop'] = form['planestart']
            if form.is_valid():
                created_trip = form.save(commit=False)
                created_trip.mission_id = m.id
                try:
                    created_trip.pilot_id = m.pilot_id
                except:
                    pass
                try:
                    created_trip.copilot_id = m.copilot_id
                except:
                    pass
                try:
                    created_trip.othercrew_id = m.othercrew_id
                except:
                    pass
                created_trip.author_id = request.user.id
                created_trip.save()
                nominaldate = m.startdate.strftime("%Y/%m/%d")
                msg = 'Flight added to Mission %s/%s/%s/.' % (m.airplane.tail, m.airplane.name, nominaldate)
                messages.success(request, msg)
                l = Logitem(author=request.user, status='S', message=msg, obj_model='Flight', obj_id=created_trip.id, obj_in='', obj_out='',)
                l.save()
                return HttpResponseRedirect('/mission/%s/%s/%s/add/' % (m.airplane.tail, m.airplane.name, m.nominaldate))
        else:
            try:
                rtype = thebase.rtype
            except:
                rtype = None
            form = MissionTripAdd(initial={'incident': incident, 'frombase': thebase, 'planestart': laststop, 'planestop': laststop, 'rtype': rtype, },)
            if m.printout_list.count() >= 1:
                msg = 'Mission %s/%s/%s/ has been printed already. Check the printer before adding flights.' % (m.airplane.tail, m.airplane.name, m.nominaldate)
                messages.info(request, msg)
                l = Logitem(author=request.user, status='W', message=msg, obj_model='Flight',)
                l.save() 
        return render_to_response('flight/mission_tripadd.html', { 'u': u, 'form': form, 'object': m, 'trip_list': trip_list, }, context_instance=RequestContext(request))
    else:
        form = 'form'
        nominaldate = m.startdate.strftime("%Y/%m/%d")
        msg = 'You need permission for Mission %s/%s/%s/ or on one of its Airbases to add a flight.' % (m.airplane.tail, m.airplane.name, nominaldate)
        messages.warning(request, msg) 
        l = Logitem(author=request.user, status='W', message=msg, obj_model='Flight',)
        l.save() 
        return HttpResponseRedirect('/mission/%s/%s/%s/' % (m.airplane.tail, m.airplane.name, nominaldate))

@permission_required('flight.add_airbase')
def mission_flight_edit(request, tail, name, year, mo, da, flight):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    thetrip = Trip.objects.get(pk=flight)
    m = thetrip.mission
    m.nominaldate = m.startdate.strftime("%Y/%m/%d")
    trip_list = Trip.objects.filter(mission_id=m.id)
    t2m(m,trip_list)
    up = None
    for trip in trip_list:
        if up == None:
            try:
                if request.user in get_users_with_perms(trip.frombase):
                    up = 1
            except:
                pass
            try:
                if request.user in get_users_with_perms(trip.tobase):
                    up = 1
            except:
                pass
    if request.user.has_perm('change_mission', m) or request.user.has_perm('change_airplane', m.airplane) or request.user.has_perm('change_airbase', m.opsbase) or up == 1:
        if request.method == 'POST':
            form = MissionTripAdd(request.POST, instance=thetrip)
            if form.is_valid():
                created_trip = form.save(commit=False)
                #created_trip.incident_id = m.incident_id
                created_trip.author_id = request.user.id
                created_trip.save()
                nominaldate = m.startdate.strftime("%Y/%m/%d")
                msg = 'Flight edited on Mission %s/%s/%s/.' % (m.airplane.tail, m.airplane.name, nominaldate)
                messages.success(request, msg)
                l = Logitem(author=request.user, status='S', message=msg, obj_model='Flight', obj_id=created_trip.id, obj_in='', obj_out='',)
                l.save()
                return HttpResponseRedirect('/mission/%s/%s/%s/add/' % (m.airplane.tail, m.airplane.name, m.nominaldate))
        else:
            form = MissionTripAdd(instance=thetrip)
            if m.printout_list.count() >= 1:
                msg = 'Mission %s/%s/%s/ has been printed already. Check the printer before editing flights.' % (m.airplane.tail, m.airplane.name, m.nominaldate)
                messages.info(request, msg) 
                l = Logitem(author=request.user, status='W', message=msg, obj_model='Flight',)
                l.save() 
        return render_to_response('flight/mission_tripedit.html', { 'u': u, 'form': form, 'thetrip': thetrip, 'object': m, 'trip_list': trip_list, }, context_instance=RequestContext(request))
    else:
        form = 'form'
        nominaldate = m.startdate.strftime("%Y/%m/%d")
        msg = 'You need permission for Mission %s/%s/%s/ or on one of its Airbases to edit its flights.' % (m.airplane.tail, m.airplane.name, nominaldate)
        messages.warning(request, msg) 
        l = Logitem(author=request.user, status='W', message=msg, obj_model='Flight',)
        l.save() 
        return HttpResponseRedirect('/mission/%s/%s/%s/' % (m.airplane.tail, m.airplane.name, m.nominaldate))

@permission_required('flight.add_airbase')
def mission_flight_delete(request, tail, name, year, mo, da, flight):
    thetrip = Trip.objects.get(pk=flight)
    object = thetrip.mission
    object.nominaldate = object.startdate.strftime("%Y/%m/%d")
    trip_list = Trip.objects.filter(mission_id=object.id)
    object.minutes = object.cost = object.retardantgal = object.retardantcost = object.landingfee = object.watercost = object.misccost = object.move_count = object.move_cost = 0 #
    object.printout_list = Printout.objects.filter(
        Q(obj_model='mission'),
        Q(obj_id=object.id)
        )
    if request.user.has_perm('change_mission', object) or request.user.has_perm('change_airplane', object.airplane) or request.user.has_perm('change_airbase', object.opsbase):
        if request.method == 'POST':
            form = TripDelete(request.POST, instance=thetrip)
            if form.is_valid():
                obj = form.save(commit=False)
                #clean_orphan_obj_perms()
                nominaldate = object.startdate.strftime("%Y/%m/%d")
                m = 'Flight deleted from Mission %s/%s/%s/.' % (object.airplane.tail, object.airplane.name, nominaldate)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Flight', obj_id=obj.id, obj_in='', obj_out='',)
                obj.delete()
                l.save()
                return HttpResponseRedirect('/mission/%s/%s/%s/add/' % (object.airplane.tail, object.airplane.name, object.nominaldate))
        else:
            form = TripDelete(instance=thetrip)
            if object.printout_list.count() >= 1:
                m = 'Mission %s/%s/%s/ has been printed already. Check the printer before deleting flights.' % (object.airplane.tail, object.airplane.name, object.nominaldate)
                messages.info(request, m) 
                l = Logitem(author=request.user, status='W', message=m, obj_model='Flight',)
                l.save() 
        return render_to_response('flight/trip_delete.html', { 'form': form, 'thetrip': thetrip, 'object': object, 'trip_list': trip_list, }, context_instance=RequestContext(request))
    else:
        form = 'form'
        nominaldate = object.startdate.strftime("%Y/%m/%d")
        m = 'You need permission for Mission %s/%s/%s/ or one of its Airbases to delete its flights.' % (object.airplane.tail, object.airplane.name, nominaldate)
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Flight',)
        l.save() 
        return HttpResponseRedirect('/mission/%s/%s/%s/' % (object.airplane.tail, object.airplane.name, nominaldate))

### Printout Stuff (!!! needs like everything)

@login_required
@permission_required('flight.add_airbase')
def mission_print(request, tail, name, year, mo, da):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    iyear = int(year)
    imo = int(mo)
    ida = int(da)
    m = Mission.objects.get(
        Q(airplane__name=name),
        Q(startdate__year=iyear),
        Q(startdate__month=imo),
        Q(startdate__day=ida),
        )
    m.nominaldate = m.startdate.strftime("%Y/%m/%d")
    trip_list = Trip.objects.filter(mission_id=m.id)
    t2m(m,trip_list)
    for p in m.printout_list:
        #p.dserialized = serializers.json.Deserializer(p.serialized)
        p.dserialized = simplejson.loads(p.serialized)
        for item in p.dserialized:
            p.item = item
            if item['model'] == 'flight.mission':
                mission = item['fields']
                airplane = str(mission['airplane'])
                startdate = str(mission['startdate'])
                p.mission = str(airplane + " " + startdate)
            else:
                if item['model'] == 'flight.trip':
                    p.trips = item['fields']
                    #for trip in p.trips:
                        #frombase = trip[1]
                        #tobase = trip[2]
                        #frombase = trip['frombase']
                        #tobase = trip['tobase']
                        #trip.line = str(frombase + " " + tobase)
    if request.user.has_perm('flight.add_airbase'):
        if request.method == 'POST':
            form = PrintMission(request.POST)
            if form.is_valid():
                theprint = form.save(commit=False)
                #serialized = list([m]) + list(trip_list)
                serialized = list([m])
                theprint.serialized = serializers.serialize('json', serialized)
                theprint.obj_model = 'mission'
                theprint.obj_id = m.id
                theprint.author_id = request.user.id
                theprint.save()
                msg = 'Mission %s/%s/%s/ printed.' % (m.airplane.tail, m.airplane.name, m.nominaldate)
                messages.success(request, msg)
                l = Logitem(author=request.user, status='S', message=msg, obj_model='Printout', obj_id=theprint.id, obj_in='', obj_out='',)
                l.save()
                return HttpResponseRedirect('/mission/%s/%s/%s/' % (m.airplane.tail, m.airplane.name, m.nominaldate))
        else:
            form = PrintMission()
        return render_to_response('flight/mission_detail.html', { 'u': u, 'form': form, 'object': m, 'trip_list': trip_list, }, context_instance=RequestContext(request))
    else:
        form = 'form'
        nominaldate = m.startdate.strftime("%Y/%m/%d")
        msg = 'Permission for Mission %s/%s/%s/ or one of its Airbases required.' % (m.airplane.tail, m.airplane.name, nominaldate)
        messages.warning(request, msg) 
        l = Logitem(author=request.user, status='W', message=msg, obj_model='Printout',)
        l.save()  
        return HttpResponseRedirect('/mission/%s/%s/%s/' % (m.airplane.tail, m.airplane.name, nominaldate))

@login_required
@permission_required('flight.add_airbase')
def mission_printout_list(request, tail, name, year, mo, da):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    iyear = int(year)
    imo = int(mo)
    ida = int(da)
    m = Mission.objects.get(
        Q(airplane__name=name),
        Q(startdate__year=iyear),
        Q(startdate__month=imo),
        Q(startdate__day=ida),
        )
    m.nominaldate = m.startdate.strftime("%Y/%m/%d")
    trip_list = Trip.objects.filter(mission_id=m.id)
    t2m(m,trip_list)
    printout_list = m.printout_list

    return render_to_response('flight/mission_detail.html', { 'u': u, 'object': m, 'trip_list': trip_list, 'printout_list': printout_list, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def mission_printout_detail(request, tail, name, year, mo, da, id):
    #iyear = int(year)
    #imo = int(mo)
    #ida = int(da)
    #thedate = datetime.date(int(year),int(mo),int(da))
    #object = Mission.objects.get(
    #    Q(airplane__name=name),
    #    Q(startdate__year=iyear),
    #    Q(startdate__month=imo),
    #    Q(startdate__day=ida),
    #    )
    # Create the HttpResponse object with the appropriate PDF headers.
    response = HttpResponse(mimetype='application/pdf')
    response['Content-Disposition'] = 'filename=somefilename.pdf'

    #buffer = StringIO()

    # Create the PDF object, using the StringIO object as its "file."
    #p = canvas.Canvas(buffer, pagesize=A5)
    #p.setFont("Helvetica", 7)
    #p.setFillColorRGB(0,0,0)
                        
    # Draw things on the PDF. Here's where the PDF generation happens.
    # See the ReportLab documentation for the full list of functionality.
    #q1 = Name._default_manager.filter(is_active=True).exclude(last_name__iexact='vacant').exclude(last_name__iexact='last name').order_by('district__tla','district__name','last_name','first_name')
    #q2 = District.objects.select_related('phonebook_district',)
    q1 = Printout.objects.get(id=id)

    #for obj in serializers.deserialize("json", q1.serialized):
    serialized = simplejson.loads(q1.serialized)
    x1 = int(550)
    y1 = int(50)
    #p.setFillColorRGB(0.1,0.1,0.1)
    #p.rect(y1-2,x1-1,360,12, fill=1)
    #p.setFillColorRGB(1,1,1)
    #mission = str(my_data.airplane + " " + obj.startdate)
    #mission = str(my_data)
    for item in serialized:
        #textobject.textOut(item)
        #textobject.setFillColorRGB(1,0,0)
        #p.drawText(textobject)      
        #textobject = p.beginText()
        if item['model'] == 'flight.mission':
            mission = item['fields']
            #airbase = str(mission['airbase'])
            airplane = str(mission['airplane'])
            #incident = mission['incident']
            startdate = str(mission['startdate'])
            mission = str(airplane + " " + startdate)
            #textobject.setFillColorRGB(1,0,0)
            #textobject.setTextOrigin(y1, x1+2)
            #textobject.textOut(mission)
        else:
            if item['model'] == 'flight.trip':
                trips = item['fields']
                for trip in trips:
                    #frombase = trip['frombase']
                    #tobase = trip['tobase']
                    #line = str(frombase + " " + tobase)
                    #textobject.setFillColorRGB(0.5,0.5,0.5)
                    #textobject.setTextOrigin(y1, x1+2)
                    #textobject.textOut(trip)
                    x1 = x1 - 50
        #p.drawText(textobject)
        x1 = x1 - 50
        page = 1
        if x1 <= 50:
            page = page + 1
            #p.showPage()
    #p.save()

    # Get the value of the StringIO buffer and write it to the response.
    #pdf = buffer.getvalue()
    #buffer.close()
    #response.write(pdf)
    return response

@login_required
@permission_required('flight.add_airbase')
def mission_printout_json(request, tail, name, year, mo, da, id):
    q1 = Printout.objects.get(id=id)
    serialized = simplejson.loads(q1.serialized)
    return HttpResponse(serialized, mimetype='application/json')

@login_required
@permission_required('flight.add_airbase')
def mission_printout_jsond(request, tail, name, year, mo, da, id):
    q1 = Printout.objects.get(id=id)
    return render_to_response('flight/json.html', { 'object': q1, }, context_instance=RequestContext(request))

### Object Permissions

@login_required
@permission_required('flight.add_airbase')
def airbase_permissions(request, slug):
    airbase = Airbase.objects.get(tla=slug)
    if request.user.has_perm('change_airbase', airbase):
        user_list = get_users_with_perms(airbase)
        if request.method == 'POST':
            form = Permissions(request.POST)
            if form.is_valid():
                obj = form.cleaned_data['users']
                for user in user_list:
                    if user not in obj and user != airbase.manager:
                        if user.has_perm('change_airbase', airbase):
                            remove_perm('change_airbase', user, airbase)
                        if user.has_perm('delete_airbase', airbase):
                            remove_perm('delete_airbase', user, airbase)
                for user in obj:
                    if not user.has_perm('change_airbase', airbase):
                        assign('change_airbase', user, airbase)
                        mtxt = str(user.first_name) + " " + str(user.last_name) + " [" + str(user.email) + "]" + " has been added to the user list for " + str(airbase.name) + " [//flight.ordvac.com/airbase/" + str(airbase.tla) + "/]."
                        mhtm = str(user.first_name) + " " + str(user.last_name) + " [" + str(user.email) + "]" + " has been added to the user list for " + str(airbase.name) + ". [<a class=\"alert-link\" href=\"//flight.ordvac.com/airbase/" + str(airbase.tla) + "/\">//flight.ordvac.com/airbase/" + str(airbase.tla) + "/</a>]."
                        msg = EmailMultiAlternatives('FLiGHT Permissions Updated', mtxt, 'flight@ordvac.com', [user.email])
                        msg.attach_alternative(mhtm, "text/html")
                        msg.send()
                    if not user.has_perm('delete_airbase', airbase):
                        assign('delete_airbase', user, airbase)
                m = 'Permissions updated at Airbase %s.' % (airbase.name)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Airbase', obj_id=airbase.id, obj_in='', obj_out='',)
                l.save()
            return HttpResponseRedirect('/airbase/%s/' % (airbase.tla))
        else:
            values = []
            for user in user_list:
                values.append(user.id)
            form = Permissions(initial={'users': values})
        return render_to_response('flight/airbase_edit.html', { 'userform': form, 'object': airbase, }, context_instance=RequestContext(request))
    else:
        if request.method == 'POST':
            form = Requestform(request.POST)
            if form.is_valid():
                remarks = form.cleaned_data['remarks']
                user = request.user
                mtxt = str(user.first_name) + " " + str(user.last_name) + " [" + str(user.email) + "]" + " requests edit permission at " + str(airbase.name) + ". You can grant this request at [//flight.ordvac.com/airbase/" + str(airbase.tla) + "/permissions/].\r\n" + remarks + "\r\n"
                mhtm = str(user.first_name) + " " + str(user.last_name) + " [" + str(user.email) + "]" + " requests edit permission at " + str(airbase.name) + ". You can grant this request at [<a class=\"alert-link\" href=\"//flight.ordvac.com/airbase/" + str(airbase.tla) + "/permissions/\">//flight.ordvac.com/airbase/" + str(airbase.tla) + "/permissions/</a>].<br/><br/>" + remarks + "<br/>"
                try:
                    msg = EmailMultiAlternatives('FLiGHT Permission Request', mtxt, 'flight@ordvac.com', [airbase.manager.email])
                except:
                    msg = EmailMultiAlternatives('FLiGHT Permission Request', mtxt, 'flight@ordvac.com', ['flight@ordvac.com'])
                msg.attach_alternative(mhtm, "text/html")
                msg.send()
                m = 'Permission requested at Airbase %s (%s). You will be notified by email upon approval.' % (airbase.name, airbase.tla)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Airbase', obj_id=airbase.id, obj_in='', obj_out='',)
                l.save() 
                return HttpResponseRedirect('/airbase/%s/' % (airbase.tla)) 
        else:
            form = Requestform()
        return render_to_response('flight/airbase_edit.html', { 'permform': form, 'object': airbase, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def airplane_permissions(request, tail, name):
    airplane = Airplane.objects.get(name=name) # add contract adminbase check
    ming = False
    try:
        c = Contract.objects.filter(airplane_id=a.id).filter(effectivedate__lte=datetime.date.today())[0]
        if request.user.has_perm('change_airplane', airplane) or request.user.has_perm('change_airbase', c.adminbase):
            ming = True
    except:
        c = None
        if request.user.has_perm('change_airplane', airplane):
            ming = True
    if ming == True:
        user_list = get_users_with_perms(airplane)
        if request.method == 'POST':
            form = Permissions(request.POST)
            if form.is_valid():
                obj = form.cleaned_data['users']
                for user in user_list:
                    if c != None:
                        if user not in obj and user != c.adminbase.manager and user != c.cor:
                            if user.has_perm('change_airplane', airplane):
                                remove_perm('change_airplane', user, airplane)
                            if user.has_perm('delete_airplane', airplane):
                                remove_perm('delete_airplane', user, airplane)
                    else:
                        if user not in obj:
                            if user.has_perm('change_airplane', airplane):
                                remove_perm('change_airplane', user, airplane)
                            if user.has_perm('delete_airplane', airplane):
                                remove_perm('delete_airplane', user, airplane)
                for user in obj:
                    if not user.has_perm('change_airplane', airplane):
                        assign('change_airplane', user, airplane)
                        mtxt = str(user.first_name) + " " + str(user.last_name) + " [" + str(user.email) + "]" + " has been added to the user list for " + str(airplane.name) + " [//flight.ordvac.com/airplane/" + str(airplane.tail) + "/" + str(airplane.name) + "/]."
                        mhtm = str(user.first_name) + " " + str(user.last_name) + " [" + str(user.email) + "]" + " has been added to the user list for " + str(airplane.name) + ". [<a class=\"alert-link\" href=\"//flight.ordvac.com/airplane/" + str(airplane.tail) + "/" + str(airplane.name) + "/\">//flight.ordvac.com/airplane/" + str(airplane.tail) + "/" + str(airplane.name) + "/</a>]."
                        msg = EmailMultiAlternatives('FLiGHT Permissions Updated', mtxt, 'flight@ordvac.com', [user.email])
                        msg.attach_alternative(mhtm, "text/html")
                        msg.send()
                    if not user.has_perm('delete_airplane', airplane):
                        assign('delete_airplane', user, airplane)
                m = 'Permissions updated on Airplane %s.' % (airplane.name)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Airplane', obj_id=airplane.id, obj_in='', obj_out='',)
                l.save()
            return HttpResponseRedirect('/airplane/%s/%s/' % (airplane.tail, airplane.name))
        else:
            values = []
            for user in user_list:
                values.append(user.id)
            form = Permissions(initial={'users': values})
        return render_to_response('flight/airplane_edit.html', { 'userform': form, 'object': airplane, }, context_instance=RequestContext(request))
    else:
        if request.method == 'POST':
            form = Requestform(request.POST)
            if form.is_valid():
                remarks = form.cleaned_data['remarks']
                user = request.user
                mtxt = str(user.first_name) + " " + str(user.last_name) + " [" + str(user.email) + "]" + " requests edit permission on " + str(airplane.name) + ". You can grant this request at [//flight.ordvac.com/airplane/" + str(airplane.tail) + "/" + str(airplane.name) + "/permissions/].\r\n" + remarks + "\r\n"
                mhtm = str(user.first_name) + " " + str(user.last_name) + " [" + str(user.email) + "]" + " requests edit permission on " + str(airplane.name) + ". You can grant this request at [<a class=\"alert-link\" href=\"//flight.ordvac.com/airplane/" + str(airplane.tail) + "/" + str(airplane.name) + "/permissions/\">//flight.ordvac.com/airplane/" + str(airplane.tail) + "/" + str(airplane.name) + "/permissions/</a>].<br/><br/>" + remarks + "<br/>"
                try:
                    msg = EmailMultiAlternatives('FLiGHT Permission Request', mtxt, 'flight@ordvac.com', [c.adminbase.manager.email])
                except:
                    msg = EmailMultiAlternatives('FLiGHT Permission Request', mtxt, 'flight@ordvac.com', ['flight@ordvac.com'])
                msg.attach_alternative(mhtm, "text/html")
                msg.send()
                m = 'Permission requested on Airplane %s. You will be notified by email upon approval.' % (airplane.name)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Airplane', obj_id=airplane.id, obj_in='', obj_out='',)
                l.save() 
                return HttpResponseRedirect('/airplane/%s/%s/' % (airplane.tail, airplane.name)) 
        else:
            form = Requestform()
        return render_to_response('flight/airplane_edit.html', { 'permform': form, 'object': airplane, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def person_permissions(request, slug):
    persons = Person.objects.all()
    object = 'None'
    while object == 'None':
        for person in persons:
            person.slug = str(person.firstname + " " + person.lastname)
            if person.slug == slug:
                object = person
    person = object
    if request.user.has_perm('change_person', person):
        user_list = get_users_with_perms(person)
        if request.method == 'POST':
            form = Permissions(request.POST)
            if form.is_valid():
                obj = form.cleaned_data['users']
                for user in user_list:
                    if user not in obj:
                        if user.has_perm('change_person', person):
                            remove_perm('change_person', user, person)
                        if user.has_perm('delete_person', person):
                            remove_perm('delete_person', user, person)
                for user in obj:
                    if not user.has_perm('change_person', person):
                        assign('change_person', user, person)
                        mtxt = str(user.first_name) + " " + str(user.last_name) + " [" + str(user.email) + "]" + " has been added to the user list for " + str(person.firstname) + " [//flight.ordvac.com/person/" + str(person.firstname) + " " + str(person.lastname) + "/]."
                        mhtm = str(user.first_name) + " " + str(user.last_name) + " [" + str(user.email) + "]" + " has been added to the user list for " + str(person.firstname) + ". [<a class=\"alert-link\" href=\"//flight.ordvac.com/person/" + str(person.firstname) + " " + str(person.lastname) + "/\">//flight.ordvac.com/person/" + str(person.firstname) + " " + str(person.lastname) + "/</a>]."
                        msg = EmailMultiAlternatives('FLiGHT Permissions Updated', mtxt, 'flight@ordvac.com', [user.email])
                        msg.attach_alternative(mhtm, "text/html")
                        msg.send()
                    if not user.has_perm('delete_person', person):
                        assign('delete_person', user, person)
                m = 'Permissions updated for Person %s %s.' % (person.firstname, person.lastname)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='person', obj_id=person.id, obj_in='', obj_out='',)
                l.save()
            return HttpResponseRedirect('/person/%s %s/' % (person.firstname, person.lastname))
        else:
            values = []
            for user in user_list:
                values.append(user.id)
            form = Permissions(initial={'users': values})
        return render_to_response('flight/person_edit.html', { 'userform': form, 'object': person, }, context_instance=RequestContext(request))
    else:
        if request.method == 'POST':
            form = Requestform(request.POST)
            if form.is_valid():
                remarks = form.cleaned_data['remarks']
                user = request.user
                mtxt = str(user.first_name) + " " + str(user.last_name) + " [" + str(user.email) + "]" + " requests edit permission for " + str(person.firstname) + " " + str(person.lastname) + ". You can grant this request at [//flight.ordvac.com/person/" + str(person.firstname) + "/" + str(person.lastname) + "/permissions/].\r\n" + remarks + "\r\n"
                mhtm = str(user.first_name) + " " + str(user.last_name) + " [" + str(user.email) + "]" + " requests edit permission for " + str(person.firstname) + " " + str(person.lastname) + ". You can grant this request at [<a class=\"alert-link\" href=\"//flight.ordvac.com/person/" + str(person.firstname) + "/" + str(person.lastname) + "/permissions/\">//flight.ordvac.com/person/" + str(person.firstname) + "/" + str(person.lastname) + "/permissions/</a>].<br/><br/>" + remarks + "<br/>"
                try:
                    msg = EmailMultiAlternatives('FLiGHT Permission Request', mtxt, 'flight@ordvac.com', [person.author.email])
                except:
                    msg = EmailMultiAlternatives('FLiGHT Permission Request', mtxt, 'flight@ordvac.com', ['flight@ordvac.com'])
                msg.attach_alternative(mhtm, "text/html")
                msg.send()
                m = 'Permission requested for Person %s %s. You will be notified by email upon approval.' % (person.firstname, person.lastname)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='person', obj_id=person.id, obj_in='', obj_out='',)
                l.save() 
                return HttpResponseRedirect('/person/%s %s/' % (person.firstname, person.lastname)) 
        else:
            form = Requestform()
        return render_to_response('flight/person_edit.html', { 'permform': form, 'object': person, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def incident_permissions(request, slug, ro):
    incident = Incident.objects.get(resourceorder=ro)
    if request.user.has_perm('change_incident', incident):
        user_list = get_users_with_perms(incident)
        if request.method == 'POST':
            form = Permissions(request.POST)
            if form.is_valid():
                obj = form.cleaned_data['users']
                for user in user_list:
                    if user not in obj:
                        if user.has_perm('change_incident', incident):
                            remove_perm('change_incident', user, incident)
                        if user.has_perm('delete_incident', incident):
                            remove_perm('delete_incident', user, incident)
                for user in obj:
                    if not user.has_perm('change_incident', incident):
                        assign('change_incident', user, incident)
                        mtxt = str(user.first_name) + " " + str(user.last_name) + " [" + str(user.email) + "]" + " has been added to the user list for " + str(incident.name) + " [//flight.ordvac.com/incident/" + str(incident.name) + "/" + str(incident.resourceorder) + "/]."
                        mhtm = str(user.first_name) + " " + str(user.last_name) + " [" + str(user.email) + "]" + " has been added to the user list for " + str(incident.name) + ". [<a class=\"alert-link\" href=\"//flight.ordvac.com/incident/" + str(incident.name) + "/" + str(incident.resourceorder) + "/\">//flight.ordvac.com/incident/" + str(incident.name) + "/" + str(incident.resourceorder) + "/</a>]."
                        msg = EmailMultiAlternatives('FLiGHT Permissions Updated', mtxt, 'flight@ordvac.com', [user.email])
                        msg.attach_alternative(mhtm, "text/html")
                        msg.send()
                    if not user.has_perm('delete_incident', incident):
                        assign('delete_incident', user, incident)
                m = 'Permissions updated on Incident %s.' % (incident.name)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='incident', obj_id=incident.id, obj_in='', obj_out='',)
                l.save()
            return HttpResponseRedirect('/incident/%s/%s/' % (incident.name, incident.resourceorder))
        else:
            values = []
            for user in user_list:
                values.append(user.id)
            form = Permissions(initial={'users': values})
        return render_to_response('flight/incident_edit.html', { 'userform': form, 'object': incident, }, context_instance=RequestContext(request))
    else:
        if request.method == 'POST':
            form = Requestform(request.POST)
            if form.is_valid():
                remarks = form.cleaned_data['remarks']
                user = request.user
                mtxt = str(user.first_name) + " " + str(user.last_name) + " [" + str(user.email) + "]" + " requests edit permission on " + str(incident.name) + ". You can grant this request at [//flight.ordvac.com/incident/" + str(incident.name) + "/" + str(incident.resourceorder) + "/permissions/].\r\n" + remarks + "\r\n"
                mhtm = str(user.first_name) + " " + str(user.last_name) + " [" + str(user.email) + "]" + " requests edit permission on " + str(incident.name) + ". You can grant this request at [<a class=\"alert-link\" href=\"//flight.ordvac.com/incident/" + str(incident.name) + "/" + str(incident.resourceorder) + "/permissions/\">//flight.ordvac.com/incident/" + str(incident.name) + "/" + str(incident.resourceorder) + "/permissions/</a>].<br/><br/>" + remarks + "<br/>"
                try:
                    msg = EmailMultiAlternatives('FLiGHT Permission Request', mtxt, 'flight@ordvac.com', [incident.author.email])
                except:
                    msg = EmailMultiAlternatives('FLiGHT Permission Request', mtxt, 'flight@ordvac.com', ['flight@ordvac.com'])
                msg.attach_alternative(mhtm, "text/html")
                msg.send()
                m = 'Permission requested on Incident %s. You will be notified by email upon approval.' % (incident.name)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='incident', obj_id=incident.id, obj_in='', obj_out='',)
                l.save() 
                return HttpResponseRedirect('/incident/%s/%s/' % (incident.name, incident.resourceorder)) 
        else:
            form = Requestform()
        return render_to_response('flight/incident_edit.html', { 'permform': form, 'object': incident, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def mission_permissions(request, name, year, mo, da): # TO BE DEPRECATED
    iyear = int(year)
    imo = int(mo)
    ida = int(da)
    mission = Mission.objects.get(
        Q(airplane__name=name),
        Q(startdate__year=iyear),
        Q(startdate__month=imo),
        Q(startdate__day=ida),
        )
    nominaldate = mission.startdate.strftime("%Y/%m/%d")
    user_list = get_users_with_perms(mission)
    if request.user.has_perm('change_mission', mission):
        if request.method == 'POST':
            form = Permissions(request.POST)
            if form.is_valid():
                obj = form.cleaned_data['users']
                for user in user_list:
                    if user not in obj:
                        if user.has_perm('change_mission', mission):
                            remove_perm('change_mission', user, mission)
                        if user.has_perm('delete_mission', mission):
                            remove_perm('delete_mission', user, mission)
                for user in obj:
                    assign('change_mission', user, mission)
                messages.success(request, 'Permissions updated.')
            return HttpResponseRedirect('/mission/%s/%s/%s/' % (mission.airplane.tail, mission.airplane.name, nominaldate))
        else:
            values = []
            for user in user_list:
                values.append(user.id)
            form = Permissions(initial={'users': values})
        return render_to_response('flight/mission_edit.html', { 'userform': form, 'themission': mission, }, context_instance=RequestContext(request))
    else:
        userform = 'form'
        messages.warning(request, 'Permission required.') 
        return HttpResponseRedirect('/mission/%s/%s/%s/' % (mission.airplane.tail, mission.airplane.name, nominaldate))

### Airbase Forms

@login_required
@permission_required('flight.add_airbase')
def airbase_add(request):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    if request.method == 'POST':
        form = AirbaseAdd(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.author_id = request.user.id
            obj.save()
            if not request.user.has_perm('change_airbase', obj):
                assign('change_airbase', request.user, obj)
            if not request.user.has_perm('delete_airbase', obj):
                assign('delete_airbase', request.user, obj)
            m = 'Airbase %s (%s) created.' % (obj.name, obj.tla)
            messages.success(request, m)
            l = Logitem(author=request.user, status='S', message=m, obj_model='Airbase', obj_id=obj.id, obj_in='', obj_out='',)
            l.save()
            return HttpResponseRedirect('/airbase/%s/' % (obj.tla))
    else:
        form = AirbaseAdd()
    return render_to_response('flight/airbase_edit.html', { 'u': u, 'form': form, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def airbase_edit(request, slug):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    airbase = Airbase.objects.get(tla=slug)
    if request.user.has_perm('change_airbase', airbase):
        if request.method == 'POST':
            form = AirbaseAdd(request.POST, instance=airbase)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.save()
                m = 'Airbase %s (%s) edited.' % (obj.name, obj.tla)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Airbase', obj_id=obj.id, obj_in='', obj_out='',)
                l.save()
                return HttpResponseRedirect('/airbase/%s/' % (obj.tla))
        else:
            form = AirbaseAdd(instance=airbase)
        return render_to_response('flight/airbase_edit.html', { 'u': u, 'form': form, 'object': airbase, }, context_instance=RequestContext(request))
    else:
        m = 'You need permission at Airbase %s (%s) to edit it. <a class="alert-link" href="/airbase/%s/permissions/">Request access</a>.' % (airbase.name, airbase.tla, airbase.tla)
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Airbase',)
        l.save()         
        return HttpResponseRedirect('/airbase/%s/' % (airbase.tla))

@login_required
@permission_required('flight.add_airbase')
def airbase_delete(request, slug):
    airbase = Airbase.objects.get(tla=slug)
    if request.user.has_perm('delete_airbase', airbase):
        if request.method == 'POST':
            form = AirbaseDelete(request.POST, instance=airbase)
            if form.is_valid():
                obj = form.save(commit=False)
                m = 'Airbase %s (%s) deleted.' % (obj.name, obj.tla)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Airbase', obj_id=obj.id, obj_in='', obj_out='',)
                obj.delete()
                l.save()
                return HttpResponseRedirect('/airbase/')
        else:
            form = AirbaseDelete(instance=airbase)
        return render_to_response('flight/airbase_delete.html', { 'form': form, 'airbase': airbase, }, context_instance=RequestContext(request))
    else:
        m = 'You need permission at Airbase %s (%s) to delete it. <a class="alert-link" href="/airbase/%s/permissions/">Request access</a>.' % (airbase.name, airbase.tla, airbase.tla)
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Airbase',)
        l.save()              
        return HttpResponseRedirect('/airbase/%s/' % (airbase.tla))

@login_required
@permission_required('flight.add_airbase')
def airbase_airplane_add(request, slug): # deprecate if airplane no longer has airbase
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    airbase = Airbase.objects.get(tla=slug)
    if request.user.has_perm('change_airbase', airbase):
        if request.method == 'POST':
            form = AirbaseAirplaneAdd(request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.author_id = request.user.id
                #obj.adminbase = airbase
                obj.save()
                assign('change_airplane', request.user, obj)
                assign('delete_airplane', request.user, obj)
                m = 'Airplane %s created.' % (obj)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Airplane', obj_id=obj.id, obj_in='', obj_out='',)
                l.save()
                return HttpResponseRedirect('/airplane/%s/%s/' % (obj.tail, obj.name))
        else:
            form = AirbaseAirplaneAdd()
        return render_to_response('flight/airplane_edit.html', { 'u': u, 'form': form, 'airbase': airbase, }, context_instance=RequestContext(request))
    else:
        m = 'You need permission at Airbase %s (%s) to add airplanes there. <a class="alert-link" href="/airbase/%s/permissions/">Request access</a>.' % (airbase.name, airbase.tla, airbase.tla)
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Airplane',)
        l.save()      
        return HttpResponseRedirect('/airbase/%s/' % (airbase.tla))

@login_required
@permission_required('flight.add_airbase')
def airbase_lfee_add(request, slug):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    airbase = Airbase.objects.get(tla=slug)
    object_list = Landingfee.objects.filter(airbase=airbase).order_by('perwhat','-effectivedate')
    if request.user.has_perm('change_airbase', airbase):
        if request.method == 'POST':
            form = AirbaseLandingfeeAdd(request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.author_id = request.user.id
                obj.airbase = airbase
                obj.save()
                assign('change_landingfee', request.user, obj)
                assign('delete_landingfee', request.user, obj)
                m = 'Airbase %s (%s) landing fee created.' % (obj.airbase.name, obj.airbase.tla)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Landingfee', obj_id=obj.id, obj_in='', obj_out='',)
                l.save()
                return HttpResponseRedirect('/airbase/%s/fee/' % (obj.airbase.tla))
        else:
            form = AirbaseLandingfeeAdd()
        return render_to_response('flight/lfee_edit.html', { 'u': u, 'form': form, 'object': airbase, 'object_list': object_list }, context_instance=RequestContext(request))
    else:
        m = 'You need permission at Airbase %s (%s) to edit its landing fees. <a class="alert-link" href="/airbase/%s/permissions/">Request access</a>.' % (airbase.name, airbase.tla, airbase.tla)
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Landingfee',)
        l.save()         
        return HttpResponseRedirect('/airbase/%s/fee/' % (airbase.tla))

@login_required
@permission_required('flight.add_airbase')
def airbase_lfee_edit(request, slug, lfee):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    airbase = Airbase.objects.get(tla=slug)
    object_list = Landingfee.objects.filter(airbase=airbase).order_by('perwhat','-effectivedate')
    thelfee = Landingfee.objects.get(id=lfee)
    if request.user.has_perm('change_airbase', airbase):
        if request.method == 'POST':
            form = AirbaseLandingfeeAdd(request.POST, instance=thelfee)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.author_id = request.user.id
                obj.airbase = airbase
                obj.save()
                m = 'Airbase %s (%s) landing fee edited.' % (obj.airbase.name, obj.airbase.tla)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Landingfee', obj_id=obj.id, obj_in='', obj_out='',)
                l.save()
                return HttpResponseRedirect('/airbase/%s/fee/' % (obj.airbase.tla))
        else:
            form = AirbaseLandingfeeAdd(instance=thelfee)
        return render_to_response('flight/lfee_edit.html', { 'u': u, 'form': form, 'object': airbase, 'object_list': object_list, 'thelfee': thelfee}, context_instance=RequestContext(request))
    else:
        m = 'You need permission at Airbase %s (%s) to edit this landing fee. <a class="alert-link" href="/airbase/%s/permissions/">Request access</a>.' % (airbase.name, airbase.tla, airbase.tla)
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Landingfee',)
        l.save()      
        return HttpResponseRedirect('/airbase/%s/fee/' % (airbase.tla))

@login_required
@permission_required('flight.add_airbase')
def airbase_lfee_delete(request, slug, lfee):
    airbase = Airbase.objects.get(tla=slug)
    thelfee = Landingfee.objects.get(id=lfee)
    if request.user.has_perm('change_airbase', airbase):
        if request.method == 'POST':
            form = LandingfeeDelete(request.POST, instance=thelfee)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.airbase = airbase
                m = 'Airbase %s (%s) landing fee deleted.' % (obj.airbase.name, obj.airbase.tla)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Landingfee', obj_id=obj.id, obj_in='', obj_out='',)
                obj.delete()
                l.save()
                return HttpResponseRedirect('/airbase/%s/fee/' % (airbase.tla))
        else:
            form = LandingfeeDelete(instance=thelfee)
        return render_to_response('flight/lfee_delete.html', { 'form': form, 'object': airbase, 'thelfee': thelfee}, context_instance=RequestContext(request))
    else:
        m = 'You need permission at Airbase %s (%s) to delete this landing fee. <a class="alert-link" href="/airbase/%s/permissions/">Request access</a>.' % (airbase.name, airbase.tla, airbase.tla)
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Landingfee',)
        l.save()       
        return HttpResponseRedirect('/airbase/%s/fee/' % (airbase.tla))

@login_required
@permission_required('flight.add_airbase')
def airbase_rfee_add(request, slug):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    airbase = Airbase.objects.get(tla=slug)
    object_list = Retardantfee.objects.filter(airbase=airbase).order_by('rtype','-effectivedate','-volume')
    if request.user.has_perm('change_airbase', airbase):
        if request.method == 'POST':
            form = AirbaseRetardantfeeAdd(request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.author_id = request.user.id
                obj.airbase = airbase
                obj.save()
                assign('change_retardantfee', request.user, obj)
                assign('delete_retardantfee', request.user, obj)
                m = 'Airbase %s (%s) retardant price created.' % (obj.airbase.name, obj.airbase.tla)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Retardantfee', obj_id=obj.id, obj_in='', obj_out='',)
                l.save()
                return HttpResponseRedirect('/airbase/%s/retardant/' % (obj.airbase.tla))
        else:
            form = AirbaseRetardantfeeAdd()
        return render_to_response('flight/rfee_edit.html', { 'u': u, 'form': form, 'object': airbase, 'object_list': object_list, }, context_instance=RequestContext(request))
    else:
        m = 'You need permission at Airbase %s (%s) to edit its retardant prices. <a class="alert-link" href="/airbase/%s/permissions/">Request access</a>.' % (airbase.name, airbase.tla, airbase.tla)
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Retardantfee',)
        l.save()        
        return HttpResponseRedirect('/airbase/%s/retardant/' % (airbase.tla))

@login_required
@permission_required('flight.add_airbase')
def airbase_rfee_edit(request, slug, rfee):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    airbase = Airbase.objects.get(tla=slug)
    object_list = Retardantfee.objects.filter(airbase=airbase).order_by('rtype','-effectivedate','-volume')
    therfee = Retardantfee.objects.get(id=rfee)
    if request.user.has_perm('change_airbase', airbase):
        if request.method == 'POST':
            form = AirbaseRetardantfeeAdd(request.POST, instance=therfee)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.author_id = request.user.id
                obj.airbase = airbase
                obj.save()
                m = 'Airbase %s (%s) retardant price edited.' % (obj.airbase.name, obj.airbase.tla)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Retardantfee', obj_id=obj.id, obj_in='', obj_out='',)
                l.save()
                return HttpResponseRedirect('/airbase/%s/retardant/' % (obj.airbase.tla))
        else:
            form = AirbaseRetardantfeeAdd(instance=therfee)
        return render_to_response('flight/rfee_edit.html', { 'u': u, 'form': form, 'object': airbase, 'object_list': object_list, 'therfee': therfee, }, context_instance=RequestContext(request))
    else:
        m = 'You need permission at Airbase %s (%s) to edit this retardant price. <a class="alert-link" href="/airbase/%s/permissions/">Request access</a>.' % (airbase.name, airbase.tla, airbase.tla)
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Retardantfee',)
        l.save()             
        return HttpResponseRedirect('/airbase/%s/retardant/' % (airbase.tla))

@login_required
@permission_required('flight.add_airbase')
def airbase_rfee_delete(request, slug, rfee):
    airbase = Airbase.objects.get(tla=slug)
    therfee = Retardantfee.objects.get(id=rfee)
    if request.user.has_perm('change_airbase', airbase):
        if request.method == 'POST':
            form = RetardantfeeDelete(request.POST, instance=therfee)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.airbase = airbase
                m = 'Airbase %s (%s) retardant price deleted.' % (obj.airbase.name, obj.airbase.tla)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Retardantfee', obj_id=obj.id, obj_in='', obj_out='',)
                obj.delete()
                l.save()
                return HttpResponseRedirect('/airbase/%s/retardant/' % (airbase.tla))
        else:
            form = RetardantfeeDelete(instance=therfee)
        return render_to_response('flight/rfee_delete.html', { 'form': form, 'object': airbase, 'therfee': therfee, }, context_instance=RequestContext(request))
    else:
        m = 'You need permission at Airbase %s (%s) to delete this retardant price. <a class="alert-link" href="/airbase/%s/permissions/">Request access</a>.' % (airbase.name, airbase.tla, airbase.tla)
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Retardantfee',)
        l.save()             
        return HttpResponseRedirect('/airbase/%s/retardant/' % (airbase.tla))

### Airplane Forms

@login_required
@permission_required('flight.add_airbase')
def airplane_add(request):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    if request.method == 'POST':
        form = AirplaneAdd(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            if request.user.has_perm('flight.add_airbase'):
                obj.author_id = request.user.id
                obj.save()
                assign('change_airplane', request.user, obj)
                assign('delete_airplane', request.user, obj)
                m = 'Airplane %s created.' % (obj)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Airplane', obj_id=obj.id, obj_in='', obj_out='',)
                l.save()
                return HttpResponseRedirect('/airplane/%s/%s/' % (obj.tail, obj.name))
            else:
                #m = 'You need permission at Airbase %s (%s) to add airplanes there. <a class="alert-link" href="/flight/airbase/%s/permissions/">Request access</a> or select another admin base.' % (obj.adminbase.name, obj.adminbase.tla, obj.adminbase.tla)
                m = 'You need permission to add airplanes.'
                messages.warning(request, m) 
                l = Logitem(author=request.user, status='W', message=m, obj_model='Airplane',)
                l.save() 
                return render_to_response('flight/airplane_edit.html', { 'u': u, 'form': form, }, context_instance=RequestContext(request))
    else:
        form = AirplaneAdd()
    return render_to_response('flight/airplane_edit.html', { 'u': u, 'form': form, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def airplane_edit(request, tail, name):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    airplane = Airplane.objects.get(name=name)
    try:
        c = Contract.objects.filter(airplane_id=airplane.id).filter(effectivedate__lte=datetime.date.today())[0]
    except:
        c = None
    if request.user.has_perm('change_airplane', airplane) or request.user.has_perm('change_airbase', c.adminbase):
        if request.method == 'POST':
            form = AirplaneAdd(request.POST, instance=airplane)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.save()
                m = 'Airplane %s edited.' % (obj)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Airplane', obj_id=obj.id, obj_in='', obj_out='',)
                l.save()
                return HttpResponseRedirect('/airplane/%s/%s/' % (obj.tail, obj.name))
        else:
            form = AirplaneAdd(instance=airplane)
        return render_to_response('flight/airplane_edit.html', { 'u': u, 'form': form, 'object': airplane, }, context_instance=RequestContext(request))
    else:
        m = 'Request access <a class="alert-link" href="/airplane/%s/%s/permissions/">on Airplane %s</a> or <a class="alert-link" href="/airbase/%s/permissions/">at Airbase %s</a> to edit this airplane.' % (airplane.tail, airplane.name, airplane.name, c.adminbase.tla, c.adminbase.name )
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Airplane',)
        l.save()       
        return HttpResponseRedirect('/airplane/%s/%s/' % (airplane.tail, airplane.name))

@login_required
@permission_required('flight.add_airbase')
def airplane_delete(request, tail, name):
    airplane = Airplane.objects.get(name=name)
    try:
        c = Contract.objects.filter(airplane_id=airplane.id).filter(effectivedate__lte=datetime.date.today())[0]
    except:
        c = None
    if request.user.has_perm('change_airplane', airplane):
        if request.method == 'POST':
            form = AirplaneDelete(request.POST, instance=airplane)
            if form.is_valid():
                obj = form.save(commit=False)
                m = 'Airplane %s deleted.' % (obj)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Airplane', obj_id=obj.id, obj_in='', obj_out='',)
                obj.delete()
                l.save()
                return HttpResponseRedirect('/airplane/')
        else:
            form = AirplaneDelete(instance=airplane)
        return render_to_response('flight/airplane_delete.html', { 'form': form, 'airplane': airplane, }, context_instance=RequestContext(request))
    else:
        m = 'Request access <a class="alert-link" href="/airplane/%s/%s/permissions/">on Airplane %s</a> or <a class="alert-link" href="/airbase/%s/permissions/">at Airbase %s</a> to delete this airplane.' % (airplane.tail, airplane.name, airplane.name, c.adminbase.tla, c.adminbase.name )
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Airplane',)
        l.save()       
        return HttpResponseRedirect('/airplane/%s/%s/' % (airplane.tail, airplane.name))

@login_required
@permission_required('flight.add_airbase')
def airplane_rate_add(request, tail, name):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    airplane = Airplane.objects.get(name=name)
    try:
        c = Contract.objects.filter(airplane_id=airplane.id).filter(effectivedate__lte=datetime.date.today())[0]
    except:
        c = None
    object_list = Rate.objects.filter(airplane=airplane).order_by('ratetype','-effectivedate')
    if request.user.has_perm('change_airplane', airplane) or request.user.has_perm('change_airbase', c.adminbase):
        if request.method == 'POST':
            form = AirplaneRateAdd(request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.author_id = request.user.id
                obj.airplane = airplane
                obj.save()
                assign('change_rate', request.user, obj)
                assign('delete_rate', request.user, obj)
                m = 'Airplane %s clock rate created.' % (obj.airplane)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Rate', obj_id=obj.id, obj_in='', obj_out='',)
                l.save()
                return HttpResponseRedirect('/airplane/%s/%s/rate/' % (obj.airplane.tail, obj.airplane.name))
        else:
            form = AirplaneRateAdd()
        return render_to_response('flight/rate_edit.html', { 'u': u, 'form': form, 'object': airplane, 'object_list': object_list, }, context_instance=RequestContext(request))
    else:
        m = 'Request access <a class="alert-link" href="/airplane/%s/%s/permissions/">on Airplane %s</a> or <a class="alert-link" href="/airbase/%s/permissions/">at Airbase %s</a> to edit this airplane\'s clock rates.' % (airplane.tail, airplane.name, airplane.name, c.adminbase.tla, c.adminbase.name )
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Rate',)
        l.save()       
        return HttpResponseRedirect('/airplane/%s/%s/rate/' % (airplane.tail, airplane.name))

@login_required
@permission_required('flight.add_airbase')
def airplane_rate_edit(request, tail, name, rate):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    airplane = Airplane.objects.get(name=name)
    try:
        c = Contract.objects.filter(airplane_id=airplane.id).filter(effectivedate__lte=datetime.date.today())[0]
    except:
        c = None
    object_list = Rate.objects.filter(airplane=airplane).order_by('ratetype','-effectivedate')
    therate = Rate.objects.get(id=rate)
    if request.user.has_perm('change_airplane', airplane) or request.user.has_perm('change_airbase', c.adminbase):
        if request.method == 'POST':
            form = AirplaneRateAdd(request.POST, instance=therate)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.author_id = request.user.id
                obj.airplane = airplane
                obj.save()
                m = 'Airplane %s clock rate edited.' % (obj.airplane)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Rate', obj_id=obj.id, obj_in='', obj_out='',)
                l.save()
                return HttpResponseRedirect('/airplane/%s/%s/rate/' % (obj.airplane.tail, obj.airplane.name))
        else:
            form = AirplaneRateAdd(instance=therate)
        return render_to_response('flight/rate_edit.html', { 'u': u, 'form': form, 'object': airplane, 'object_list': object_list, 'therate': therate, }, context_instance=RequestContext(request))
    else:
        m = 'Request access <a class="alert-link" href="/airplane/%s/%s/permissions/">on Airplane %s</a> or <a class="alert-link" href="/airbase/%s/permissions/">at Airbase %s</a> to edit this clock rate.' % (airplane.tail, airplane.name, airplane.name, c.adminbase.tla, c.adminbase.name )
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Rate',)
        l.save()         
        return HttpResponseRedirect('/airplane/%s/%s/rate/' % (airplane.tail, airplane.name))

@login_required
@permission_required('flight.add_airbase')
def airplane_rate_delete(request, tail, name, rate):
    airplane = Airplane.objects.get(name=name)
    try:
        c = Contract.objects.filter(airplane_id=airplane.id).filter(effectivedate__lte=datetime.date.today())[0]
    except:
        c = None
    therate = Rate.objects.get(id=rate)
    if request.user.has_perm('change_airplane', airplane) or request.user.has_perm('change_airbase', c.adminbase):
        if request.method == 'POST':
            form = RateDelete(request.POST, instance=therate)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.airplane = airplane
                m = 'Airplane %s clock rate deleted.' % (obj.airplane)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Rate', obj_id=obj.id, obj_in='', obj_out='',)
                obj.delete()
                l.save()
                return HttpResponseRedirect('/airplane/%s/%s/rate/' % (airplane.tail, airplane.name))
        else:
            form = RateDelete(instance=therate)
        return render_to_response('flight/rate_delete.html', { 'form': form, 'object': airplane, 'therate': therate, }, context_instance=RequestContext(request))
    else:
        m = 'Request access <a class="alert-link" href="/airplane/%s/%s/permissions/">on Airplane %s</a> or <a class="alert-link" href="/airbase/%s/permissions/">at Airbase %s</a> to delete this clock rate.' % (airplane.tail, airplane.name, airplane.name, c.adminbase.tla, c.adminbase.name )
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Rate',)
        l.save()         
        return HttpResponseRedirect('/airplane/%s/%s/rate/' % (airplane.tail, airplane.name))

@login_required
@permission_required('flight.add_airbase')
def airplane_contract_add(request, tail, name):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    airplane = Airplane.objects.get(name=name)
    try:
        c = Contract.objects.filter(airplane_id=airplane.id).filter(effectivedate__lte=datetime.date.today())[0]
    except:
        c = None
    object_list = Contract.objects.filter(airplane=airplane).order_by('-effectivedate')
    if request.user.has_perm('change_airplane', airplane) or request.user.has_perm('change_airbase', c.adminbase):
        if request.method == 'POST':
            form = AirplaneContractAdd(request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.author_id = request.user.id
                obj.airplane = airplane
                obj.save()
                assign('change_contract', request.user, obj)
                assign('delete_contract', request.user, obj)
                m = 'Airplane %s contract created.' % (obj.airplane)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Contract', obj_id=obj.id, obj_in='', obj_out='',)
                l.save()
                return HttpResponseRedirect('/airplane/%s/%s/contract/' % (obj.airplane.tail, obj.airplane.name))
        else:
            form = AirplaneContractAdd()
        return render_to_response('flight/contract_edit.html', { 'u': u, 'form': form, 'object': airplane, 'object_list': object_list, }, context_instance=RequestContext(request))
    else:
        m = 'Request access <a class="alert-link" href="/airplane/%s/%s/permissions/">on Airplane %s</a> or <a class="alert-link" href="/airbase/%s/permissions/">at Airbase %s</a> to edit this airplane\'s contracts.' % (airplane.tail, airplane.name, airplane.name, c.adminbase.tla, c.adminbase.name )
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Contract',)
        l.save()       
        return HttpResponseRedirect('/airplane/%s/%s/contract/' % (airplane.tail, airplane.name))

@login_required
@permission_required('flight.add_airbase')
def airplane_contract_edit(request, tail, name, contract):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    airplane = Airplane.objects.get(name=name)
    object_list = Contract.objects.filter(airplane=airplane).order_by('-effectivedate')
    thecontract = Contract.objects.get(id=contract)
    if request.user.has_perm('change_airplane', airplane) or request.user.has_perm('change_airbase', thecontract.adminbase):
        if request.method == 'POST':
            form = AirplaneContractAdd(request.POST, instance=thecontract)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.author_id = request.user.id
                obj.airplane = airplane
                obj.save()
                m = 'Airplane %s contract edited.' % (obj.airplane.name)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Contract', obj_id=obj.id, obj_in='', obj_out='',)
                l.save()
                return HttpResponseRedirect('/airplane/%s/%s/contract/' % (obj.airplane.tail, obj.airplane.name))
        else:
            form = AirplaneContractAdd(instance=thecontract)
        return render_to_response('flight/contract_edit.html', { 'u': u, 'form': form, 'object': airplane, 'object_list': object_list, 'thecontract': thecontract, }, context_instance=RequestContext(request))
    else:
        m = 'Request access <a class="alert-link" href="/airplane/%s/%s/permissions/">on Airplane %s</a> or <a class="alert-link" href="/airbase/%s/permissions/">at Airbase %s</a> to edit this contract.' % (airplane.tail, airplane.name, airplane.name, thecontract.adminbase.tla, thecontract.adminbase.name )
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Contract',)
        l.save()         
        return HttpResponseRedirect('/airplane/%s/%s/contract/' % (airplane.tail, airplane.name))

@login_required
@permission_required('flight.add_airbase')
def airplane_contract_delete(request, tail, name, contract): # no template
    airplane = Airplane.objects.get(name=name)
    thecontract = Contract.objects.get(id=contract)
    if request.user.has_perm('change_airplane', airplane) or request.user.has_perm('change_airbase', thecontract.adminbase):
        if request.method == 'POST':
            form = ContractDelete(request.POST, instance=thecontract)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.airplane = airplane
                m = 'Airplane %s contract deleted.' % (obj.airplane.name)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Contract', obj_id=obj.id, obj_in='', obj_out='',)
                obj.delete()
                l.save()
                return HttpResponseRedirect('/airplane/%s/%s/contract/' % (airplane.tail, airplane.name))
        else:
            form = ContractDelete(instance=thecontract)
        return render_to_response('flight/contract_delete.html', { 'form': form, 'object': airplane, 'thecontract': thecontract, }, context_instance=RequestContext(request))
    else:
        m = 'Request access <a class="alert-link" href="/airplane/%s/%s/permissions/">on Airplane %s</a> or <a class="alert-link" href="/airbase/%s/permissions/">at Airbase %s</a> to delete this contract.' % (airplane.tail, airplane.name, airplane.name, thecontract.adminbase.tla, thecontract.adminbase.name )
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Contract',)
        l.save()         
        return HttpResponseRedirect('/airplane/%s/%s/contract/' % (airplane.tail, airplane.name))

@login_required
@permission_required('flight.add_airbase')
def airplane_fueling_add(request, tail, name): # stub, maybe to replace generic add
    return render_to_response('flight/index.html')

@login_required
@permission_required('flight.add_airbase')
def airplane_fueling_edit(request, tail, name, fueling): # maybe to replace generic edit
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    airplane = Airplane.objects.get(name=name)
    # object_list = Fueling.objects.filter(airplane=airplane)#.order_by('-effectivedate')
    thefueling = Fueling.objects.get(id=fueling)
    if request.user.has_perm('change_airplane', airplane) or request.user.has_perm('change_airbase', thefueling.fuelbase):
        if request.method == 'POST':
            form = AirplaneFuelingAdd(request.POST, request.FILES, instance=thefueling)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.author_id = request.user.id
                obj.airplane = airplane
                obj.save()
                m = 'Airplane %s fueling edited.' % (obj.airplane.name)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Fueling', obj_id=obj.id, obj_in='', obj_out='',)
                l.save()
                # return HttpResponseRedirect('/fueling/%s/%s/' % (obj.airplane.tail, obj.airplane.name))
                return HttpResponseRedirect('/fueling/')
        else:
            form = AirplaneFuelingAdd(instance=thefueling)
        return render_to_response('flight/fueling_edit.html', { 'u': u, 'form': form, 'object': airplane, 'thefueling': thefueling, }, context_instance=RequestContext(request))
    else:
        m = 'Request access <a class="alert-link" href="/airplane/%s/%s/permissions/">on Airplane %s</a> or <a class="alert-link" href="/airbase/%s/permissions/">at Airbase %s</a> to edit this fueling.' % (airplane.tail, airplane.name, airplane.name, thefueling.fuelbase.tla, thefueling.fuelbase.name )
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Fueling',)
        l.save()         
        # return HttpResponseRedirect('/fueling/%s/%s/' % (airplane.tail, airplane.name))
        return HttpResponseRedirect('/fueling/')

@login_required
@permission_required('flight.add_airbase')
def airplane_fueling_delete(request, tail, name, fueling): # stub, maybe to replace generic delete
    return render_to_response('flight/index.html')

### Fueling Forms (to be moved to airplane above)

@login_required
@permission_required('flight.add_airbase')
def fueling_edit(request, fueling):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    #airplane = Airplane.objects.get(name=name)
    #object_list = Fueling.objects.filter(airplane=airplane)#.order_by('-effectivedate')
    thefueling = Fueling.objects.get(id=fueling)
    if request.user.has_perm('change_airplane', thefueling.airplane) or request.user.has_perm('change_airbase', thefueling.fuelbase):
        if request.method == 'POST':
            form = FuelingAdd(request.POST, request.FILES, instance=thefueling)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.author_id = request.user.id
                #obj.airplane = airplane
                obj.save()
                m = 'Airplane %s fueling edited.' % (obj.airplane.name)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Fueling', obj_id=obj.id, obj_in='', obj_out='',)
                l.save()
                # return HttpResponseRedirect('/fueling/%s/%s/' % (obj.airplane.tail, obj.airplane.name))
                return HttpResponseRedirect('/fueling/')
        else:
            form = FuelingAdd(instance=thefueling)
        return render_to_response('flight/fueling_edit.html', { 'u': u, 'form': form, 'thefueling': thefueling, }, context_instance=RequestContext(request))
    else:
        m = 'Request access <a class="alert-link" href="/airplane/%s/%s/permissions/">on Airplane %s</a> or <a class="alert-link" href="/airbase/%s/permissions/">at Airbase %s</a> to edit this fueling.' % (thefueling.airplane.tail, thefueling.airplane.name, thefueling.airplane.name, thefueling.fuelbase.tla, thefueling.fuelbase.name )
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Fueling',)
        l.save()         
        # return HttpResponseRedirect('/fueling/%s/%s/' % (thefueling.airplane.tail, thefueling.airplane.name))
        return HttpResponseRedirect('/fueling/')

@login_required
@permission_required('flight.add_airbase')
def fueling_delete(request, fueling):
    #airplane = Airplane.objects.get(name=name)
    thefueling = Fueling.objects.get(id=fueling)
    if request.user.has_perm('change_airplane', thefueling.airplane) or request.user.has_perm('change_airbase', thefueling.adminbase):
        if request.method == 'POST':
            form = FuelingDelete(request.POST, instance=thefueling)
            if form.is_valid():
                obj = form.save(commit=False)
                #obj.airplane = airplane
                m = 'Airplane %s fueling deleted.' % (obj.airplane.name)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Fueling', obj_id=obj.id, obj_in='', obj_out='',)
                obj.delete()
                l.save()
                #return HttpResponseRedirect('/fueling/%s/%s/' % (obj.airplane.tail, obj.airplane.name))
                return HttpResponseRedirect('/fueling/')
        else:
            form = FuelingDelete(instance=thefueling)
        return render_to_response('flight/fueling_delete.html', { 'form': form, 'object': thefueling.airplane, 'thefueling': thefueling, }, context_instance=RequestContext(request))
    else:
        m = 'Request access <a class="alert-link" href="/airplane/%s/%s/permissions/">on Airplane %s</a> or <a class="alert-link" href="/airbase/%s/permissions/">at Airbase %s</a> to delete this fueling.' % (thefueling.airplane.tail, thefueling.airplane.name, thefueling.airplane.name, thefueling.fuelbase.tla, thefueling.adminbase.name )
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Fueling',)
        l.save()         
        #return HttpResponseRedirect('/fueling/%s/%s/' % (thefueling.airplane.tail, thefueling.airplane.name))
        return HttpResponseRedirect('/fueling/')

### Person Forms

@login_required
@permission_required('flight.add_airbase')
def person_add(request):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    if request.method == 'POST':
        form = PersonAdd(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.author_id = request.user.id
            obj.save()
            assign('change_person', request.user, obj)
            assign('delete_person', request.user, obj)
            slug = str(obj.firstname + " " + obj.lastname)
            m = 'Person %s created.' % (slug)
            messages.success(request, m)
            l = Logitem(author=request.user, status='S', message=m, obj_model='Person', obj_id=obj.id, obj_in='', obj_out='',)
            l.save()
            return HttpResponseRedirect('/person/%s/' % (slug))
    else:
        form = PersonAdd()
    return render_to_response('flight/person_edit.html', { 'u': u, 'form': form, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def person_edit(request, slug):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    persons = Person.objects.all()
    theperson = 'None'
    while theperson == 'None': # textbook sloppy, please profile
        for person in persons:
            person.slug = str(person.firstname + " " + person.lastname)
            if person.slug == slug:
                theperson = person
    if request.user.has_perm('change_person', theperson):
        if request.method == 'POST':
            form = PersonAdd(request.POST, instance=theperson)
            if form.is_valid():
                theperson = form.save(commit=False)
                theperson.save()
                theperson.slug = str(theperson.firstname + " " + theperson.lastname)
                m = 'Person %s edited.' % (slug)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Person', obj_id=theperson.id, obj_in='', obj_out='',)
                l.save()
                return HttpResponseRedirect('/person/%s/' % (theperson.slug))
        else:
                form = PersonAdd(instance=theperson)
    else:
        form = 'form'
        m = 'You need permission to edit this person. <a class="alert-link" href="/person/%s/permissions/">Request access</a>.' % (theperson.slug)
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Person',)
        l.save()       
        return HttpResponseRedirect('/person/%s/' % (theperson.slug))

    return render_to_response('flight/person_edit.html', { 'u': u, 'form': form, 'object': theperson }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def person_delete(request, slug):
    persons = Person.objects.all()
    theperson = 'None'
    while theperson == 'None':
        for person in persons:
            person.slug = str(person.firstname + " " + person.lastname)
            if person.slug == slug:
                theperson = person
    if request.user.has_perm('delete_person', theperson):
        if request.method == 'POST':
            form = PersonDelete(request.POST, instance=theperson)
            if form.is_valid():
                obj = form.save(commit=False)
                slug = str(theperson.firstname + " " + theperson.lastname)
                m = 'Person %s deleted.' % (slug)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Person', obj_id=obj.id, obj_in='', obj_out='',)
                obj.delete()
                l.save()
                #clean_orphan_obj_perms()
                return HttpResponseRedirect('/person/')
        else:
                form = PersonDelete(instance=theperson)
    else:
        form = 'form'
        m = 'You need permission to delete this person. <a class="alert-link" href="/person/%s/permissions/">Request access</a>.' % (theperson.slug)
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Person',)
        l.save()   
        return HttpResponseRedirect('/person/%s/' % (theperson.slug))

    return render_to_response('flight/person_delete.html', {
        'form': form, 'theperson': theperson
    }, context_instance=RequestContext(request))

### Incident Forms

@login_required
@permission_required('flight.add_airbase')
def incident_add(request):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    if request.method == 'POST':
        form = IncidentAdd(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.author_id = request.user.id
            obj.save()
            assign('change_incident', request.user, obj)
            assign('delete_incident', request.user, obj)
            m = 'Incident %s created.' % (obj.name)
            messages.success(request, m)
            l = Logitem(author=request.user, status='S', message=m, obj_model='Incident', obj_id=obj.id, obj_in='', obj_out='',)
            l.save()
            return HttpResponseRedirect('/incident/%s/%s/' % (obj.name, obj.resourceorder))
    else:
        form = IncidentAdd()
    incidents = Incident.objects.all().only('name','resourceorder','firechargenum')
    return render_to_response('flight/incident_edit.html', { 'u': u, 'form': form, 'incidents': incidents ,}, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def incident_edit(request, slug, ro):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    incident = Incident.objects.get(resourceorder=ro)
    if request.user.has_perm('change_incident', incident) or request.user == incident.author:
        if request.method == 'POST':
            form = IncidentAdd(request.POST, instance=incident)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.save()
                m = 'Incident %s edited.' % (obj.name)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Incident', obj_id=obj.id, obj_in='', obj_out='',)
                l.save()
                return HttpResponseRedirect('/incident/%s/%s/' % (obj.name, obj.resourceorder))
        else:
            form = IncidentAdd(instance=incident)
        incidents = Incident.objects.all().only('name','resourceorder','firechargenum')
        return render_to_response('flight/incident_edit.html', { 'u': u, 'form': form, 'object': incident, }, context_instance=RequestContext(request))
    else:
        m = 'You need permission on Incident %s to edit it. <a class="alert-link" href="/incident/%s/%s/permissions/">Request access</a>.' % (incident.name, incident.name, incident.resourceorder)
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Incident',)
        l.save()       
        return HttpResponseRedirect('/incident/%s/%s/' % (incident.name, incident.resourceorder))

@login_required
@permission_required('flight.add_airbase')
def incident_delete(request, slug, ro):
    incident = Incident.objects.get(resourceorder=ro)
    if request.user.has_perm('delete_incident', incident):
        if request.method == 'POST':
            form = IncidentDelete(request.POST, instance=incident)
            if form.is_valid():
                obj = form.save(commit=False)
                m = 'Incident %s deleted.' % (obj.name)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Incident', obj_id=obj.id, obj_in='', obj_out='',)
                obj.delete()
                l.save()
                return HttpResponseRedirect('/incident/')
        else:
            form = IncidentDelete(instance=incident)
        return render_to_response('flight/incident_delete.html', { 'form': form, 'incident': incident, }, context_instance=RequestContext(request))
    else:
        m = 'You need permission on Incident %s to delete it. <a class="alert-link" href="/incident/%s/%s/permissions/">Request access</a>.' % (incident.name, incident.name, incident.resourceorder)
        messages.warning(request, m) 
        l = Logitem(author=request.user, status='W', message=m, obj_model='Incident',)
        l.save()        
        return HttpResponseRedirect('/incident/%s/%s/' % (incident.name, incident.resourceorder))

### Fee, Cost, Rate, Contract, Fueling Forms

@login_required
@permission_required('flight.add_airbase')
def lfee_add(request):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    object_list = Landingfee.objects.all().order_by('perwhat','-effectivedate')
    if request.method == 'POST':
        form = LandingfeeAdd(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            if request.user.has_perm('change_airbase', obj.airbase):
                obj.author_id = request.user.id
                obj.save()
                assign('change_landingfee', request.user, obj)
                assign('delete_landingfee', request.user, obj)
                m = 'Airbase %s (%s) landing fee created.' % (obj.airbase.name, obj.airbase.tla)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Landingfee', obj_id=obj.id, obj_in='', obj_out='',)
                l.save()
                return HttpResponseRedirect('/airbase/%s/fee/' % (obj.airbase.tla))
            else:
                m = 'You need permission at Airbase %s (%s) to edit its landing fees. <a class="alert-link" href="/airbase/%s/permissions/">Request access</a>.' % (obj.airbase.name, obj.airbase.tla, obj.airbase.tla)
                messages.warning(request, m) 
                l = Logitem(author=request.user, status='W', message=m, obj_model='Landingfee',)
                l.save() 
                return render_to_response('flight/lfee_edit.html', { 'u': u, 'form': form, 'object_list': object_list }, context_instance=RequestContext(request))
    else:
        form = LandingfeeAdd()
    return render_to_response('flight/lfee_edit.html', { 'u': u, 'form': form, 'object_list': object_list }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def rfee_add(request):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    object_list = Retardantfee.objects.all().order_by('airbase','rtype','-effectivedate','-volume')
    if request.method == 'POST':
        form = RetardantfeeAdd(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            if request.user.has_perm('change_airbase', obj.airbase):
                obj.author_id = request.user.id
                obj.save()
                assign('change_retardantfee', request.user, obj)
                assign('delete_retardantfee', request.user, obj)
                m = 'Airbase %s retardant price created.' % (obj.airbase)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Retardantfee', obj_id=obj.id, obj_in='', obj_out='',)
                l.save()
                return HttpResponseRedirect('/airbase/%s/retardant/' % (obj.airbase.tla))
            else:
                m = 'You need permission at Airbase %s (%s) to edit its retardant prices. <a class="alert-link" href="/airbase/%s/permissions/">Request access</a>.' % (obj.airbase.name, obj.airbase.tla, obj.airbase.tla)
                messages.warning(request, m) 
                l = Logitem(author=request.user, status='W', message=m, obj_model='Retardantfee',)
                l.save() 
                return render_to_response('flight/rfee_edit.html', { 'u': u, 'form': form, 'object_list': object_list }, context_instance=RequestContext(request))                
    else:
        form = RetardantfeeAdd()
    return render_to_response('flight/rfee_edit.html', { 'u': u, 'form': form, 'object_list': object_list, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def rate_add(request):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    object_list = Rate.objects.all().order_by('airplane','ratetype','-effectivedate')
    if request.method == 'POST':
        form = RateAdd(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            try:
                c = Contract.objects.filter(airplane_id=obj.airplane_id).filter(effectivedate__lte=obj.effectivedate())[0]
            except:
                c = None
            if request.user.has_perm('change_airplane', obj.airplane) or request.user.has_perm('change_airbase', c.adminbase):
                obj.author_id = request.user.id
                obj.save()
                assign('change_rate', request.user, obj)
                assign('delete_rate', request.user, obj)
                m = 'Airplane %s rate created.' % (obj.airplane)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Rate', obj_id=obj.id, obj_in='', obj_out='',)
                l.save()
                return HttpResponseRedirect('/airplane/%s/%s/rate/' % (obj.airplane.tail, obj.airplane.name))
            else:
                m = 'Request access <a class="alert-link" href="/airplane/%s/%s/permissions/">on Airplane %s</a> or <a class="alert-link" href="/airbase/%s/permissions/">at Airbase %s</a> to edit this airplane\'s clock rates.' % (obj.airplane.tail, obj.airplane.name, obj.airplane.name, c.adminbase.tla, c.adminbase.name )
                messages.warning(request, m) 
                l = Logitem(author=request.user, status='W', message=m, obj_model='Rate',)
                l.save()   
                return render_to_response('flight/rate_edit.html', { 'u': u, 'form': form, 'object_list': object_list, }, context_instance=RequestContext(request)) 
    else:
        form = RateAdd()
    return render_to_response('flight/rate_edit.html', { 'u': u, 'form': form, 'object_list': object_list }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def contract_add(request):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    object_list = Contract.objects.all().order_by('airplane','-effectivedate')
    if request.method == 'POST':
        form = ContractAdd(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            try:
                c = Contract.objects.filter(airplane_id=obj.airplane_id).filter(effectivedate__lte=obj.effectivedate())[0]
            except:
                c = None
            if request.user.has_perm('change_airplane', obj.airplane) or request.user.has_perm('change_airbase', c.adminbase):
                obj.author_id = request.user.id
                obj.save()
                assign('change_contract', request.user, obj)
                assign('delete_contract', request.user, obj)
                m = 'Airplane %s contract created.' % (obj.airplane)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Contract', obj_id=obj.id, obj_in='', obj_out='',)
                l.save()
                return HttpResponseRedirect('/airplane/%s/%s/contract/' % (obj.airplane.tail, obj.airplane.name))
            else:
                m = 'Request access <a class="alert-link" href="/airplane/%s/%s/permissions/">on Airplane %s</a> or <a class="alert-link" href="/airbase/%s/permissions/">at Airbase %s</a> to edit this airplane\'s contracts.' % (obj.airplane.tail, obj.airplane.name, obj.airplane.name, c.adminbase.tla, c.adminbase.name )
                messages.warning(request, m) 
                l = Logitem(author=request.user, status='W', message=m, obj_model='Contract',)
                l.save()   
                return render_to_response('flight/contract_edit.html', { 'u': u, 'form': form, 'object_list': object_list, }, context_instance=RequestContext(request)) 
    else:
        form = ContractAdd()
    return render_to_response('flight/contract_edit.html', { 'u': u, 'form': form, 'object_list': object_list }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def fueling_add(request):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    # object_list = Fueling.objects.all()#.order_by('airplane','-fueltime')
    if request.method == 'POST':
        form = FuelingAdd(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            if request.user.has_perm('change_airplane', obj.airplane) or request.user.has_perm('change_airbase', obj.fuelbase):
                obj.author_id = request.user.id
                obj.save()
                assign('change_fueling', request.user, obj)
                assign('delete_fueling', request.user, obj)
                m = 'Airplane %s fueling created.' % (obj.airplane.name)
                messages.success(request, m)
                l = Logitem(author=request.user, status='S', message=m, obj_model='Fueling', obj_id=obj.id, obj_in='', obj_out='',)
                l.save()
                # return HttpResponseRedirect('/fueling/%s/%s/' % (obj.airplane.tail, obj.airplane.name))
                return HttpResponseRedirect('/fueling/')
            else:
                m = 'Request access <a class="alert-link" href="/airplane/%s/%s/permissions/">on Airplane %s</a> or <a class="alert-link" href="/airbase/%s/permissions/">at Airbase %s</a> to edit this airplane\'s fuelings.' % (obj.airplane.tail, obj.airplane.name, obj.airplane.name, obj.fuelbase.tla, obj.fuelbase.name )
                messages.warning(request, m) 
                l = Logitem(author=request.user, status='W', message=m, obj_model='Fueling',)
                l.save()   
                return render_to_response('flight/fueling_edit.html', { 'u': u, 'form': form, }, context_instance=RequestContext(request)) 
    else:
        form = FuelingAdd()
    return render_to_response('flight/fueling_edit.html', { 'u': u, 'form': form }, context_instance=RequestContext(request))

### NO PERM CHECKS BELOW

### Table Lists

@login_required
@permission_required('flight.add_airbase')
def airbase_list(request):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    airbase_list = Airbase.objects.prefetch_related('landingfee_airbase','retardantfee_airbase','trip_frombase').all().annotate(mission_count=Count('trip_frombase__mission', distinct=True), trip_count=Count('trip_frombase'),retardant_sum=Sum('trip_frombase__retardantgal')).order_by('name') # check prefetch? do we use trip_frombase ever?
    when = datetime.datetime.utcnow().replace(tzinfo=utc)
    when2 = datetime.datetime.utcnow()
    for a in airbase_list:
        if a.tz is not None:
            a.now = when#.localize(a.tz)
            a.tzn = a.tz.localize(when2).tzname()
        #a.mission_count = Mission.objects.filter(trip_mission__frombase_id=a.id).count()
        lfee_list = a.landingfee_airbase.order_by('-effectivedate')
        lper_list = a.landingfee_airbase.distinct('perwhat')
        for lper in lper_list:
            lp = lfee_list.filter(Q(perwhat__iexact=lper.perwhat))[0]
            lper.cost = lp.cost
            lper.effectivedate = lp.effectivedate
        a.lfee_list = lper_list
        rfee_list = a.retardantfee_airbase.order_by('-effectivedate')
        #rper_list = Retardantfee.objects.filter(airbase=object).distinct('perwhat','volume') # dual-distinct problem here
        rper_list = a.retardantfee_airbase.distinct('rtype','volume')
        for rper in rper_list:
            vol = str(rper.volume)
            rty = str(rper.rtype)
            try:
                rp = rfee_list.filter(volume__iexact=vol).filter(rtype__iexact=rty)[0]
                rper.cost = rp.cost
                rper.effectivedate = rp.effectivedate
            except:
                rper.cost = 0
                rper.effectivedate = None
        a.rfee_list = rper_list
    entmap = None
    #if airbase_list:
    #    ents = []
    #    colors = ["black","cyan","red"]
    #    for i,ab in enumerate(airbase_list):
    #        try:
    #            geom = ab.geom
    #            ents.append((geom, {
    #                'html': "<a class=\"alert-link\" href=\"/airbase/" + str(ab) + "/\">" + str(ab.name) + " (" + str(ab)  + ")" + "</a>",
    #                'style': {
    #                    'stroke_color': colors[0] , 'fill_color': colors[0]
    #                },
    #            }))
    #        except:
    #            pass
        #entmap = InfoMap(
        #    ents
        #    , { 'map_div_style': {'width': '100%', 'height': '100%'}, 'map_options': {'controls': ['LayerSwitcher', 'Navigation', 'PanZoom', 'MousePosition'], }, 'zoom_to_data_extent': True, },
        #)
    return render_to_response('flight/airbase_list.html', {'u': u, 'airbase_list': airbase_list, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def airplane_list(request):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    airplane_list = Airplane.objects.all().annotate(trip_count=Count('mission_airplane__trip_mission'),retardant_sum=Sum('mission_airplane__trip_mission__retardantgal'))
    for a in airplane_list:
        try:
            a.c = Contract.objects.filter(airplane_id=a.id).filter(effectivedate__lte=datetime.date.today())[0]
        except:
            a.c = None
        a.frate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='flight').order_by('-effectivedate') # RATES!
        if a.frate_list:
            a.frate_list = a.frate_list[:1]
        a.arate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='avail').order_by('-effectivedate')
        if a.arate_list:
            a.arate_list = a.arate_list[:1]
        a.srate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='nonavail').order_by('-effectivedate')
        if a.srate_list:
            a.srate_list = a.srate_list[:1]
        a.mission_count = Mission.objects.filter(airplane_id=a.id).count()
        #if a.begins and a.ends:
        #    a.map = (a.ends-a.begins).days
    entmap = None
    #if airplane_list:
        #ents = []
        #colors = ["black","cyan","red"]
        #for i,ap in enumerate(airplane_list):
        #    try:
        #        geom = ap.c.adminbase.geom
        #        ents.append((geom, {
        #            'html': "<a class=\"alert-link\" href=\"/airplane/" + str(ap.tail) + "/" + str(ap.name) + "/\">" + str(ap) + "</a>",
        #            'style': {
        #                'stroke_color': colors[0] , 'fill_color': colors[0]
        #            },
        #        }))
        #    except:
        #        pass
        #entmap = InfoMap(
        #    ents
        #    , { 'map_div_style': {'width': '100%', 'height': '100%'}, 'map_options': {'controls': ['LayerSwitcher', 'Navigation', 'PanZoom', 'MousePosition'], }, 'zoom_to_data_extent': True, },
        #)
    return render_to_response('flight/airplane_list.html', { 'u': u, 'airplane_list': airplane_list, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def person_list(request):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    person_list = Person.objects.all()
    for p in person_list:
        p.mission_count = Mission.objects.filter(Q(pilot_id=p.id) | Q(copilot_id=p.id) | Q(othercrew_id=p.id)).count()
    for p in person_list:
        p.trip_count = Trip.objects.filter(Q(pilot_id=p.id) | Q(copilot_id=p.id) | Q(othercrew_id=p.id)).count()
    return render_to_response('flight/person_list.html', {'u': u, 'person_list': person_list, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def incident_list(request):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    incident_list = Incident.objects.all().annotate(trip_count=Count('trip_incident'),retardant_sum=Sum('trip_incident__retardantgal'))
    entmap = None
    #if incident_list:
    #    ents = []
    #    colors = ["black","cyan","red"]
    #    for i,inc in enumerate(incident_list):
    #        try:
    #            geom = inc.geom.centroid
    #            ents.append((geom, {
    #                'html': "<a class=\"alert-link\" href=\"/incident/" + str(inc.name) + "/" + str(inc.resourceorder) + "/\">" + str(inc) + "</a>",
    #                'style': {
    #                    'stroke_color': colors[0] , 'fill_color': colors[2]
    #                },
    #            }))
    #        except:
    #            pass
    #    entmap = InfoMap(
    #        ents
    #        , { 'map_div_style': {'width': '100%', 'height': '100%'}, 'map_options': {'controls': ['LayerSwitcher', 'Navigation', 'PanZoom', 'MousePosition'], }, 'zoom_to_data_extent': True, },
    #    )
    return render_to_response('flight/incident_list.html', {'u': u, 'incident_list': incident_list, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def mission_list(request):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    #mission_list = Mission.objects.all().select_related().prefetch_related('trip_mission').annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal')).order_by('-modified')
    m_list = Trip.objects.all().order_by('-modified').values_list('mission_id')[:20]
    mission_list = Mission.objects.filter(id__in=m_list).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal')).order_by('-modified')
    trip_list = Trip.objects.filter(mission_id__in=m_list)
    a = Stine()
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    #trip_list = Trip.objects.filter(mission__in=mission_list) # what for?
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/mission_list.html', { 'u': u, 'mission_list': mission_list, 'flight_list': trip_list, 'o': a, 'entmap': entmap, }, context_instance=RequestContext(request))

### Table Lists for Fees, Costs, Rates, Contracts, Fuelings

@login_required
@permission_required('flight.add_airbase')
def lfee_list(request):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    object_list = Landingfee.objects.all().order_by('airbase','perwhat','-effectivedate')
    when = datetime.datetime.utcnow().replace(tzinfo=utc)
    for r in object_list:
        if r.effectivedate >= when:
            r.upcoming = True
    return render_to_response('flight/lfee_list.html', { 'u': u, 'object_list': object_list, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def rfee_list(request):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    object_list = Retardantfee.objects.all().order_by('airbase','rtype','-effectivedate','-volume')
    when = datetime.datetime.utcnow().replace(tzinfo=utc)
    for r in object_list:
        if r.effectivedate >= when:
            r.upcoming = True
    return render_to_response('flight/rfee_list.html', { 'u': u, 'object_list': object_list, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def rate_list(request):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    rate_list = Rate.objects.all().order_by('airplane','ratetype','-effectivedate')
    when = datetime.datetime.utcnow().replace(tzinfo=utc)
    for r in rate_list:
        if r.effectivedate >= when:
            r.upcoming = True
    return render_to_response('flight/rate_list.html', { 'u': u, 'object_list': rate_list, 'when': when, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def contract_list(request):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    object_list = Contract.objects.all().order_by('airplane','-effectivedate')
    when = datetime.date.today()
    for r in reversed(object_list):
        if r.effectivedate >= when:
            r.upcoming = True
    return render_to_response('flight/contract_list.html', { 'u': u, 'object_list': object_list, 'when': when, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def fueling_list(request):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    object_list = Fueling.objects.all()#.order_by('-fueltime','airplane')
    when = datetime.date.today()
    #for r in reversed(object_list):
    #    if r.effectivedate >= when:
    #        r.upcoming = True
    return render_to_response('flight/fueling_list.html', { 'u': u, 'object_list': object_list, 'when': when, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def airbase_lfeelist(request, slug):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    object = Airbase.objects.get(tla=slug)
    object_list = Landingfee.objects.filter(airbase_id=object.id).order_by('perwhat','-effectivedate')
    when = datetime.datetime.utcnow().replace(tzinfo=utc)
    for r in object_list:
        if r.effectivedate >= when:
            r.upcoming = True
    return render_to_response('flight/lfee_list.html', { 'u': u, 'object': object, 'object_list': object_list, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def airbase_rfeelist(request, slug):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    object = Airbase.objects.get(tla=slug)
    object_list = Retardantfee.objects.filter(airbase_id=object.id).order_by('rtype','-effectivedate','-volume')
    when = datetime.datetime.utcnow().replace(tzinfo=utc)
    for r in object_list:
        if r.effectivedate >= when:
            r.upcoming = True
    return render_to_response('flight/rfee_list.html', { 'u': u, 'object': object, 'object_list': object_list, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def airplane_ratelist(request, tail, name):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    object = Airplane.objects.get(name=name)
    object_list = Rate.objects.filter(airplane_id=object.id).order_by('-effectivedate','ratetype',)
    when = datetime.datetime.utcnow().replace(tzinfo=utc)
    #ma = 'Start'
    #i = 0
    #for r in reversed(object_list):
        #if r.effectivedate >= when:
        #    r.upcoming = True
        #if r.mop != ma:
        #    r.ma = True
        #else:
        #    r.ma = False
        #r.oldma = ma
        #ma = r.mop
        #if i == 0:
        #    i = object.mop = r.mop
    #object_list = sorted(object_list)
    return render_to_response('flight/rate_list.html', { 'u': u, 'object': object, 'object_list': object_list, 'when': when, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def airplane_contractlist(request, tail, name):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    object = Airplane.objects.get(name=name)
    object_list = Contract.objects.filter(airplane_id=object.id).order_by('-effectivedate',)
    when = datetime.date.today()
    #ma = 'Start'
    #i = 0
    for r in reversed(object_list):
        if r.effectivedate >= when:
            r.upcoming = True
        #if r.mop != ma:
        #    r.ma = True
        #else:
        #    r.ma = False
        #r.oldma = ma
        #ma = r.mop
        #if i == 0:
        #    i = object.mop = r.mop
    #object_list = sorted(object_list)
    return render_to_response('flight/contract_list.html', { 'u': u, 'object': object, 'object_list': object_list, 'when': when, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def airplane_fueling_list(request, tail, name):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    object = Airplane.objects.get(name=name)
    object_list = Fueling.objects.filter(airplane_id=object.id)#.order_by('-effectivedate',)
    when = datetime.date.today()
    #ma = 'Start'
    #i = 0
    #for r in reversed(object_list):
    #    if r.effectivedate >= when:
    #        r.upcoming = True
        #if r.mop != ma:
        #    r.ma = True
        #else:
        #    r.ma = False
        #r.oldma = ma
        #ma = r.mop
        #if i == 0:
        #    i = object.mop = r.mop
    #object_list = sorted(object_list)
    return render_to_response('flight/fueling_list.html', { 'u': u, 'object': object, 'object_list': object_list, 'when': when, }, context_instance=RequestContext(request))

### Details

@login_required
@permission_required('flight.add_airbase')
def airbase_detail(request, slug):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = Airbase.objects.get(tla=slug)
    #user_list = get_users_with_perms(a)
    #airplane_list = Airplane.objects.filter(adminbase_id=a.id).annotate(trip_count=Count('mission_airplane__trip_mission'),retardant_sum=Sum('mission_airplane__trip_mission__retardantgal'))
    #for p in airplane_list:
    #    p.frate_list = Rate.objects.filter(airplane_id=p.id).filter(ratetype__iexact='flight').order_by('-effectivedate')
    #    if p.frate_list:
    #        p.frate_list = p.frate_list[:1]
    #    p.arate_list = Rate.objects.filter(airplane_id=p.id).filter(ratetype__iexact='avail').order_by('-effectivedate')
    #    if p.arate_list:
    #        p.arate_list = p.arate_list[:1]
    #    p.srate_list = Rate.objects.filter(airplane_id=p.id).filter(ratetype__iexact='nonavail').order_by('-effectivedate')
    #    if p.srate_list:
    #        p.srate_list = p.srate_list[:1]
    #    p.erate_list = Rate.objects.filter(airplane_id=p.id).filter(ratetype__iexact='extended').order_by('-effectivedate')
    #    if p.erate_list:
    #        p.erate_list = p.erate_list[:1]
    #    if p.begins and p.ends:
    #        p.map = (p.ends-p.begins).days
    #    arates = Rate.objects.filter(airplane_id=p.id).exclude(ratetype__iexact='flight').exclude(ratetype__iexact='avail').exclude(ratetype__iexact='nonavail').exclude(ratetype__iexact='extended').order_by('-effectivedate')
    #    artypes = Rate.objects.filter(airplane_id=p.id).exclude(ratetype__iexact='flight').exclude(ratetype__iexact='avail').exclude(ratetype__iexact='nonavail').exclude(ratetype__iexact='extended').distinct('ratetype').values_list('ratetype')
    #    p.rtypes = []
    #    for rtype in artypes:
    #        rtype = Rate.objects.filter(airplane_id=p.id).filter(ratetype__iexact=rtype).order_by('-effectivedate')[:1]
    #        p.rtypes.append(rtype)
    #    p.mission_count = Mission.objects.filter(airplane_id=p.id).count() # use aggregator and drop this
    #    p.tfs = Trip.objects.filter(mission__airplane_id=p.id).filter(fmso='f').count()
    #    if p.begins and p.ends:
    #        p.map = (p.ends-p.begins).days
    lfee_list = Landingfee.objects.filter(airbase_id=a.id).order_by('-effectivedate')
    lper_list = Landingfee.objects.filter(airbase_id=a.id).distinct('perwhat')
    for lper in lper_list:
        lp = lfee_list.filter(Q(perwhat__iexact=lper.perwhat))[0]
        lper.cost = lp.cost
        lper.effectivedate = lp.effectivedate
    lfee_list = lper_list
    rfee_list = Retardantfee.objects.filter(airbase_id=a.id).order_by('-effectivedate')
    rper_list = Retardantfee.objects.filter(airbase_id=a.id).distinct('rtype','volume') # dual-distinct problem here
    for rper in rper_list:
        vol = str(rper.volume)
        rty = str(rper.rtype)
        try:
            rp = rfee_list.filter(volume__iexact=vol).filter(rtype__iexact=rty)[0]
            rper.cost = rp.cost
            rper.effectivedate = rp.effectivedate
        except:
            rper.cost = 0
            rper.effectivedate = None
    rfee_list = rper_list
    when = datetime.datetime.utcnow().replace(tzinfo=utc).year
    m_list = Trip.objects.filter(mission__startdate__year=when).filter(Q(frombase_id=a.id) | Q(tobase_id=a.id)).order_by('-modified').values_list('mission_id')
    mission_list = Mission.objects.filter(id__in=m_list).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal')).order_by('-modified')
    #mission_list = Mission.objects.filter(Q(trip_mission__frombase_id=a.id) | Q(trip_mission__tobase_id=a.id)).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal')).order_by('-modified')[:10]
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a.total_cost = a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/airbase_detail.html', { 'u' : u, 'object': a, 'airplane_list': airplane_list, 'mission_list': mission_list, 'flight_list': trip_list, 'lfee_list': lfee_list, 'rfee_list': rfee_list, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def airplane_tail(request, tail):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    airplane_list = Airplane.objects.filter(tail=tail).annotate(trip_count=Count('mission_airplane__trip_mission'),retardant_sum=Sum('mission_airplane__trip_mission__retardantgal'))
    for a in airplane_list:
        try:
            a.c = Contract.objects.filter(airplane_id=a.id).filter(effectivedate__lte=datetime.date.today())[0]
        except:
            a.c = None
        a.frate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='flight').order_by('-effectivedate') # PLANE RATES!
        if a.frate_list:
            a.frate_list = a.frate_list[:1]
        a.arate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='avail').order_by('-effectivedate')
        if a.arate_list:
            a.arate_list = a.arate_list[:1]
        a.srate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='nonavail').order_by('-effectivedate')
        if a.srate_list:
            a.srate_list = a.srate_list[:1]
        a.mission_count = Mission.objects.filter(airplane_id=a.id).count()
        #if a.begins and a.ends:
        #    a.map = (a.ends-a.begins).days
    entmap = None
    #if airplane_list:
    #    ents = []
    #    colors = ["black","cyan","red"]
    #    for i,ap in enumerate(airplane_list):
    #        try:
    #            geom = ap.c.adminbase.geom
    #            ents.append((geom, {
    #                'html': "<a class=\"alert-link\" href=\"/airplane/" + str(ap.tail) + "/" + str(ap.name) + "/\">" + str(ap) + "</a>",
    #                'style': {
    #                    'stroke_color': colors[0] , 'fill_color': colors[0]
    #                },
    #            }))
    #        except:
    #            pass
    #    entmap = InfoMap(
    #        ents
    #        , { 'map_div_style': {'width': '100%', 'height': '100%'}, 'map_options': {'controls': ['LayerSwitcher', 'Navigation', 'PanZoom', 'MousePosition'], }, 'zoom_to_data_extent': True, },
    #    )
    return render_to_response('flight/airplane_list.html', { 'u': u, 'airplane_list': airplane_list, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def airplane_detail(request, tail, name):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = Airplane.objects.get(name=name)#.annotate(mission_count=Count('mission_airplane'))
    try:
        a.c = Contract.objects.filter(airplane_id=a.id).filter(effectivedate__lte=datetime.date.today())[0]
    except:
        a.c = None
    a.frate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='flight').order_by('-effectivedate') # PLANE RATES!
    if a.frate_list:
        a.frate_list = a.frate_list[:1]
    a.arate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='avail').order_by('-effectivedate')
    if a.arate_list:
        a.arate_list = a.arate_list[:1]
    a.srate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='nonavail').order_by('-effectivedate')
    if a.srate_list:
        a.srate_list = a.srate_list[:1]
    a.erate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='extended').order_by('-effectivedate')
    if a.erate_list:
        a.erate_list = a.erate_list[:1]
    # if a.begins and a.ends:
    #     a.map = (a.ends-a.begins).days
    #arates = a.rate_airplane.exclude(ratetype__iexact='flight').exclude(ratetype__iexact='avail').exclude(ratetype__iexact='nonavail').exclude(ratetype__iexact='extended').order_by('-effectivedate')
    #arates = a.rate_airplane.exclude(Q(ratetype__iexact='flight') | Q(ratetype__iexact='avail') | Q(ratetype__iexact='nonavail')| Q(ratetype__iexact='extended')).order_by('-effectivedate')
    #artypes = arates.distinct('ratetype').values_list('ratetype')
    artypes = Rate.objects.filter(airplane_id=a.id).exclude(Q(ratetype__iexact='flight') | Q(ratetype__iexact='avail') | Q(ratetype__iexact='nonavail')| Q(ratetype__iexact='extended')).distinct('ratetype').values_list('ratetype')
    a.rtypes = []
    for rtype in artypes:
        rtype = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact=rtype).order_by('-effectivedate')[:1]
        a.rtypes.append(rtype)
    #mission_list = Mission.objects.filter(airplane=a).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    #mission_list = a.mission_airplane#.prefetch_related('trip_mission')#.annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    #a.mission_count = mission_list.count()
    when = datetime.datetime.utcnow().replace(tzinfo=utc).year
    m_list = Trip.objects.filter(mission__startdate__year=when).filter(mission__airplane_id=a.id).order_by('-modified').values_list('mission_id')
    mission_list = Mission.objects.filter(id__in=m_list).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal')).order_by('-modified')
    trip_list = Trip.objects.filter(mission__in=mission_list)
    #mission_list = Mission.objects.filter(airplane_id=a.id).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))[:10]
    #trip_list = Trip.objects.filter(mission__in=mission_list).order_by('-modified')
    #trip_list = a.mission_airplane.all().trip_mission.all()
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    incidents = Incident.objects.all().only('name','resourceorder')
    return render_to_response('flight/airplane_detail.html', { 'u' : u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list, 'entmap': entmap, 'incidents': incidents, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def person_detail(request, slug):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    persons = Person.objects.all()
    a = 'None'
    while a == 'None':
        for person in persons:
            person.slug = str(person.firstname + " " + person.lastname)
            if person.slug == slug:
                a = person
    when = datetime.datetime.utcnow().replace(tzinfo=utc).year
    m_list = Trip.objects.filter(mission__startdate__year=when).filter(
        Q(mission__pilot_id=a.id) | Q(mission__copilot_id=a.id) | Q(mission__othercrew_id=a.id)
        ).order_by('-modified').values_list('mission_id')
    mission_list = Mission.objects.filter(id__in=m_list).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal')).order_by('-modified')
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/person_detail.html', { 'u' : u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def incident_named(request, slug):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    entmap = None
    incident_list = Incident.objects.filter(name__iexact=slug).annotate(trip_count=Count('trip_incident'),retardant_sum=Sum('trip_incident__retardantgal'))
    for a in incident_list:
        a.mission_list = Mission.objects.filter(trip_mission__incident_id=a.id).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
        a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
        a.mission_count = a.mission_list.count()
        for m in a.mission_list:
            m.trip_list = Trip.objects.filter(mission_id=m.id).filter(incident_id=a.id)
            t2m(m,m.trip_list)
            am(a,m)
        a2(a)
    entmap = None
    #if incident_list:
    #    ents = []
    #    colors = ["black","cyan","red"]
    #    for i,inc in enumerate(incident_list):
    #        try:
    #            geom = inc.geom.centroid
    #            ents.append((geom, {
    #                'html': "<a class=\"alert-link\" href=\"/incident/" + str(inc.name) + "/" + str(inc.resourceorder) + "/\">" + str(inc) + "</a>",
    #                'style': {
    #                    'stroke_color': colors[0] , 'fill_color': colors[2]
    #                },
    #            }))
    #        except:
    #            pass
    #    entmap = InfoMap(
    #        ents
    #        , { 'map_div_style': {'width': '100%', 'height': '100%'}, 'map_options': {'controls': ['LayerSwitcher', 'Navigation', 'PanZoom', 'MousePosition'], }, 'zoom_to_data_extent': True, },
    #    )
    return render_to_response('flight/incident_list.html', {'u': u, 'incident_list': incident_list, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def incident_detail(request, slug, ro):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = Incident.objects.get(resourceorder=ro)
    mission_list = Mission.objects.filter(trip_mission__incident_id=a.id).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal')) # do these counts apply at incident?
    trip_list = Trip.objects.filter(incident_id=a.id) # all trips on the incident
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list: # all missions with a trip on the incident
        m.trip_list = trip_list.filter(mission_id=m.id) # trips on incident on this mission
        t2m(m,m.trip_list) # mission and its trips on the incident
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    airplanes = Airplane.objects.all().only('tail','name')
    return render_to_response('flight/incident_detail.html', { 'u' : u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list, 'entmap': entmap, 'airplanes': airplanes, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def incident_dailycost(request, slug, ro):
    a = Incident.objects.get(resourceorder=ro)
    mission_list = Mission.objects.filter(trip_mission__incident_id=a.id).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal')) # do these counts apply at incident?
    trip_list = Trip.objects.filter(incident_id=a.id) # all trips on the incident
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = a.flsmrcost = 0
    dates = [] # set up the dates arrray
    for m in mission_list: # add unique dates from mission_list with var placeholders
        dates.append(m.startdate)
    dates = list(set(dates))
    datesums = []
    for d in dates: # all missions with a trip on the incident
        dx = Stine()
        dx.acost = dx.ecost = dx.fcount = dx.ftime = dx.fcost = dx.mtime = dx.ntime = dx.ncost = dx.lcost = dx.rgal = dx.rcost = dx.ocost = dx.moves = dx.mcost = dx.tcost = dx.tfs = dx.tbs = dx.tms = dx.tns = dx.flsmrcost = 0
        #d.flsmrcost = 0
        dmlist = mission_list.filter(startdate=d)
        for m in dmlist: # all missions with a trip on the incident
            m.trip_list = trip_list.filter(mission_id=m.id) # trips on incident on this mission
            t2m(m,m.trip_list) # mission and its trips on the incident
            am(dx,m)
            dx.flsmrcost = dx.flsmrcost + m.flsmrcost
            #d = dates(startdate) # how? maybe extend the dict and get the maxes?
            #d.flsmrcost = d.flsmrcost + m.flsmrcost # add the mission totals to the date total
        #a2(a)
        dict = {'date': d, 'ftime': dx.ftime, 'fcost': dx.fcost, 'lcost': dx.lcost, 'scost': dx.ecost, 'mcost': dx.mcost, 'rgal': dx.rgal, 'rcost': dx.rcost, 'flsmrcost': dx.flsmrcost }
        datesums.append(dict)
    a.datesums = datesums
    #for d in dates:
    #    d.flsmrcost = mission_list.filter(strtdate=d).annotate(flsmrcost=Sum('flsmrcost'))

    a.mission_count = mission_list.count()
    for m in mission_list: # all missions with a trip on the incident
        m.trip_list = trip_list.filter(mission_id=m.id) # trips on incident on this mission
        t2m(m,m.trip_list) # mission and its trips on the incident
        am(a,m)
        a.flsmrcost = a.flsmrcost + m.flsmrcost
    a2(a)
    return render_to_response('flight/incident_dailycost.html', { 'object': a, 'mission_list': mission_list, 'flight_list': trip_list, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def incident_dailyflight(request, slug, ro):
    a = Incident.objects.get(resourceorder=ro)
    mission_list = Mission.objects.filter(trip_mission__incident_id=a.id).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal')) # do these counts apply at incident?
    trip_list = Trip.objects.filter(incident_id=a.id) # all trips on the incident
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list: # all missions with a trip on the incident
        m.trip_list = trip_list.filter(mission_id=m.id) # trips on incident on this mission
        t2m(m,m.trip_list) # mission and its trips on the incident
        am(a,m)
    a2(a)
    return render_to_response('flight/incident_dailyflight.html', { 'object': a, 'mission_list': mission_list, 'flight_list': trip_list, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def mission_detail(request, tail, name, year, mo, da):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    iyear = int(year)
    imo = int(mo)
    ida = int(da)
    m = Mission.objects.get(
        Q(airplane__name=name),
        Q(startdate__year=iyear),
        Q(startdate__month=imo),
        Q(startdate__day=ida),
        )
    try:
        m.c = Contract.objects.filter(airplane_id=m.airplane_id).filter(effectivedate__lte=m.startdate)[0]
    except:
        m.c = None
        #m.c = Contract.objects.filter(airplane_id=m.airplane_id).filter(effectivedate__lte=m.startdate)[0]
    trip_list = Trip.objects.filter(mission_id=m.id)
    t2m(m,trip_list)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/mission_detail.html', { 'u' : u, 'object': m, 'trip_list': trip_list, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def mission_airops(request, tail, name, year, mo, da):
    #u = User.objects.get(id=request.user.id)
    #usermenu(u)
    iyear = int(year)
    imo = int(mo)
    ida = int(da)
    m = Mission.objects.get(
        Q(airplane__name=name),
        Q(startdate__year=iyear),
        Q(startdate__month=imo),
        Q(startdate__day=ida),
        )
    trip_list = Trip.objects.filter(mission_id=m.id)
    t2m(m,trip_list)
    airops(m)
    #mapents(trip_list)
    return render_to_response('flight/mission_airops.html', { 'object': m, 'trip_list': trip_list, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def mission_abssum(request, tail, name, year, mo, da):
    #u = User.objects.get(id=request.user.id)
    #usermenu(u)
    iyear = int(year)
    imo = int(mo)
    ida = int(da)
    m = Mission.objects.get(
        Q(airplane__name=name),
        Q(startdate__year=iyear),
        Q(startdate__month=imo),
        Q(startdate__day=ida),
        )
    trip_list = Trip.objects.filter(mission_id=m.id)
    t2m(m,trip_list)
    airops(m)
    #mapents(trip_list)
    return render_to_response('flight/mission_abssum.html', { 'object': m, 'trip_list': trip_list, }, context_instance=RequestContext(request))


### Date-to-date details

@login_required
@permission_required('flight.add_airbase')
def airbase_date_to_date(request, slug, yeara, moa, daa, yearb, mob, dab):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = Airbase.objects.get(tla=slug)
    lfee_list = Landingfee.objects.filter(airbase_id=a.id).order_by('-effectivedate') # WHY RATES?
    lper_list = Landingfee.objects.filter(airbase_id=a.id).distinct('perwhat')
    for lper in lper_list:
        lp = lfee_list.filter(Q(perwhat__iexact=lper.perwhat))[0]
        lper.cost = lp.cost
        lper.effectivedate = lp.effectivedate
    lfee_list = lper_list
    rfee_list = Retardantfee.objects.filter(airbase_id=a.id).order_by('-effectivedate')
    rper_list = Retardantfee.objects.filter(airbase_id=a.id).distinct('rtype','volume') # dual-distinct problem here
    for rper in rper_list:
        vol = str(rper.volume)
        rty = str(rper.rtype)
        try:
            rp = rfee_list.filter(volume__iexact=vol).filter(rtype__iexact=rty)[0]
            rper.cost = rp.cost
            rper.effectivedate = rp.effectivedate
        except:
            rper.cost = 0
            rper.effectivedate = None
    rfee_list = rper_list # WHY RATES?
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    bdate = datetime.datetime(int(yearb), int(mob), int(dab), 0, 0)
    mission_list = Mission.objects.filter(trip_mission__frombase_id=a.id).filter(startdate__range=(adate, bdate)).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/airbase_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list, 'adate': adate, 'bdate': bdate, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def airplane_date_to_date(request, tail, name, yeara, moa, daa, yearb, mob, dab):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = Airplane.objects.get(name=name)
    try:
        a.c = Contract.objects.filter(airplane_id=a.id).filter(effectivedate__lte=datetime.date.today())[0]
    except:
        a.c = None
    a.frate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='flight').order_by('-effectivedate') # WHY RATES?
    if a.frate_list:
        a.frate_list = a.frate_list[:1]
    a.arate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='avail').order_by('-effectivedate')
    if a.arate_list:
        a.arate_list = a.arate_list[:1]
    a.srate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='nonavail').order_by('-effectivedate')
    if a.srate_list:
        a.srate_list = a.srate_list[:1]
    a.erate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='extended').order_by('-effectivedate')
    if a.erate_list:
        a.erate_list = a.erate_list[:1]
    #if a.begins and a.ends:
    #    a.map = (a.ends-a.begins).days
    arates = Rate.objects.filter(airplane_id=a.id).exclude(ratetype__iexact='flight').exclude(ratetype__iexact='avail').exclude(ratetype__iexact='nonavail').exclude(ratetype__iexact='extended').order_by('-effectivedate')
    artypes = Rate.objects.filter(airplane_id=a.id).exclude(ratetype__iexact='flight').exclude(ratetype__iexact='avail').exclude(ratetype__iexact='nonavail').exclude(ratetype__iexact='extended').distinct('ratetype').values_list('ratetype')
    a.rtypes = []
    for rtype in artypes:
        rtype = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact=rtype).order_by('-effectivedate')[:1]
        a.rtypes.append(rtype) # WHY RATES?
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    bdate = datetime.datetime(int(yearb), int(mob), int(dab), 0, 0)
    mission_list = Mission.objects.filter(airplane_id=a.id).filter(startdate__range=(adate, bdate)).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    incidents = Incident.objects.all().only('name','resourceorder')
    return render_to_response('flight/airplane_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list, 'adate': adate, 'bdate': bdate, 'entmap': entmap, 'incidents': incidents, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def person_date_to_date(request, slug, yeara, moa, daa, yearb, mob, dab):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    persons = Person.objects.all()
    a = 'None'
    while a == 'None':
        for person in persons:
            person.slug = str(person.firstname + " " + person.lastname)
            if person.slug == slug:
                a = person
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    bdate = datetime.datetime(int(yearb), int(mob), int(dab), 0, 0)
    mission_list = Mission.objects.filter(Q(pilot_id=a.id) | Q(copilot_id=a.id) | Q(othercrew_id=a.id)).filter(startdate__range=(adate, bdate)).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/person_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list,'adate': adate, 'bdate': bdate, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def incident_date_to_date(request, slug, ro, yeara, moa, daa, yearb, mob, dab):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = Incident.objects.get(resourceorder=ro)
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    bdate = datetime.datetime(int(yearb), int(mob), int(dab), 0, 0)
    mission_list = Mission.objects.filter(trip_mission__incident_id=a.id).filter(startdate__range=(adate, bdate)).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(incident_id=a.id)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    airplanes = Airplane.objects.all().only('tail','name')
    return render_to_response('flight/incident_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list, 'adate': adate, 'bdate': bdate, 'entmap': entmap, 'airplanes': airplanes, }, context_instance=RequestContext(request))

### Date details

@login_required
@permission_required('flight.add_airbase')
def airbase_date(request, slug, yeara, moa, daa):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = Airbase.objects.get(tla=slug)
    lfee_list = Landingfee.objects.filter(airbase_id=a.id).order_by('-effectivedate') # WHY RATES?
    lper_list = Landingfee.objects.filter(airbase_id=a.id).distinct('perwhat')
    for lper in lper_list:
        lp = lfee_list.filter(Q(perwhat__iexact=lper.perwhat))[0]
        lper.cost = lp.cost
        lper.effectivedate = lp.effectivedate
    lfee_list = lper_list
    rfee_list = Retardantfee.objects.filter(airbase_id=a.id).order_by('-effectivedate')
    rper_list = Retardantfee.objects.filter(airbase_id=a.id).distinct('rtype','volume') # dual-distinct problem here
    for rper in rper_list:
        vol = str(rper.volume)
        rty = str(rper.rtype)
        try:
            rp = rfee_list.filter(volume__iexact=vol).filter(rtype__iexact=rty)[0]
            rper.cost = rp.cost
            rper.effectivedate = rp.effectivedate
        except:
            rper.cost = 0
            rper.effectivedate = None
    rfee_list = rper_list # WHY RATES?
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    mission_list = Mission.objects.filter(trip_mission__frombase_id=a.id).filter(startdate=adate).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/airbase_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list,'adate': adate, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def airbase_retuse(request, slug, yeara, moa, daa):
    a = Airbase.objects.get(tla=slug)
    a.rgal0 = a.rcost0 = a.rgal = a.rcost = a.rgalt = a.rcostt = 0
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    season = datetime.datetime(int(yeara), 1, 1, 0, 0) # jan 1 current year
    ydate = adate - timedelta(days=1)
    season_trips = Trip.objects.filter(frombase_id=a.id).filter(planestart__range=(season, ydate)) # agg rgal by rtype here?
    for t in season_trips: # get rgal and rcost for season to ydate per rtype
        try:
            t.crgal = Trip.objects.filter(frombase_id=a.id).filter(planestart__range=(season, t.planestart)).filter(rtype=t.rtype).aggregate(retardant_sum=Sum('retardantgal'))['retardant_sum'] # we need trip.retgal for trip.rtype here
            #t.rbase = Airbase.objects.filter(id=t.frombase_id).annotate(trip_count=Count('trip_frombase'),retardant_sum=Sum('trip_frombase__retardantgal'))[0] # to get the ret pumped at the base but we have that above
            t.rprice = Retardantfee.objects.filter(
                Q(airbase_id=t.frombase_id),
                Q(rtype=t.rtype),
                Q(volume__lt=t.crgal),
                Q(effectivedate__lte=t.planestart)
                ).order_by('-volume','-effectivedate')[0] # this is price1 
            t.rprice2 = Retardantfee.objects.filter(
                Q(airbase_id=t.frombase_id),
                Q(rtype=t.rtype),
                Q(volume__lt=(t.crgal+t.retardantgal)),
                Q(effectivedate__lte=t.planestart)
                ).order_by('-volume','-effectivedate')[0] # this is price2 
            t.r1vol = t.rprice.volume
            t.r1cost = t.rprice.cost
            t.rflat = t.rprice.flat
            t.r2vol = t.rprice2.volume
            t.r2cost = t.rprice2.cost
            if t.r1vol != t.r2vol:
                t.rgal1 = t.r2vol - t.crgal # r.vol2 - t.crgal is 1
                t.rcost1 = t.r1cost * t.rgal1
                t.rgal2 = (t.crgal + t.retardantgal) - t.r2vol # t.crgal + + t.retgal - vol2 is 9 for price2 
                t.rcost2 = t.r2cost * t.rgal2
                #t.rprice = (t.r1cost + t.r2cost)/2
                t.rcost = t.rcost1 + t.rcost2
            else:
                t.rprice = t.r1cost
                t.rcost = t.rprice * t.retardantgal
            t.rcost = t.rcost + t.rflat
            t.rcost = Decimal(t.rcost).quantize(Decimal('.01'))
        except:
            t.rprice = 0
            t.rcost = 0
        a.rgal0 = a.rgal0 + t.retardantgal # gallons pumped since beginning of season before today
        a.rcost0 = a.rcost0 + t.rcost # dollars pumped since beginning of season before today
    trip_list = Trip.objects.filter(frombase_id=a.id).filter(planestart__year=yeara, planestart__month=moa, planestart__day=daa)
    a.rgalt = a.rgal0
    a.rcostt = a.rcost0
    for t in trip_list:
        try:
            t.crgal = Trip.objects.filter(frombase_id=a.id).filter(planestart__range=(season, t.planestart)).filter(rtype=t.rtype).aggregate(retardant_sum=Sum('retardantgal'))['retardant_sum'] # we need trip.retgal for trip.rtype here
            #t.rbase = Airbase.objects.filter(id=t.frombase_id).annotate(trip_count=Count('trip_frombase'),retardant_sum=Sum('trip_frombase__retardantgal'))[0] # to get the ret pumped at the base but we have that above
            t.rprice = Retardantfee.objects.filter(
                Q(airbase_id=t.frombase_id),
                Q(rtype=t.rtype),
                Q(volume__lt=t.crgal),
                Q(effectivedate__lte=t.planestart)
                ).order_by('-volume','-effectivedate')[0] # this is price1 
            t.rprice2 = Retardantfee.objects.filter(
                Q(airbase_id=t.frombase_id),
                Q(rtype=t.rtype),
                Q(volume__lt=(t.crgal+t.retardantgal)),
                Q(effectivedate__lte=t.planestart)
                ).order_by('-volume','-effectivedate')[0] # this is price2 
            t.r1vol = t.rprice.volume
            t.r1cost = t.rprice.cost
            t.rflat = t.rprice.flat
            t.r2vol = t.rprice2.volume
            t.r2cost = t.rprice2.cost
            if t.r1vol != t.r2vol:
                t.rgal1 = t.r2vol - t.crgal # r.vol2 - t.crgal is 1
                t.rcost1 = t.r1cost * t.rgal1
                t.rgal2 = (t.crgal + t.retardantgal) - t.r2vol # t.crgal + + t.retgal - vol2 is 9 for price2 
                t.rcost2 = t.r2cost * t.rgal2
                #t.rprice = (t.r1cost + t.r2cost)/2
                t.rcost = t.rcost1 + t.rcost2
            else:
                t.rprice = t.r1cost
                t.rcost = t.rprice * t.retardantgal
            t.rcost = t.rcost + t.rflat
            t.rcost = Decimal(t.rcost).quantize(Decimal('.01'))
        except:
            t.rprice = 0
            t.rcost = 0
        a.rgal = a.rgal + t.retardantgal
        a.rcost = a.rcost + t.rcost
        t.pounds = None # no idea. wt of ret?
        t.rgalt = a.rgalt + t.retardantgal
        t.rcostt = a.rcostt + t.rcost
        a.rgalt = t.rgalt # gallons pumped since beginning of season
        a.rcostt = t.rcostt # dollars pumped since beginning of season
    if not request.user.is_superuser:
        m = 'In addition to assuming retardant volumes at %s roll back to zero on New Year\'s Day, this particular worksheet does not yet care about various retardant brands.' % (a.name)
        messages.info(request, m) 
        l = Logitem(author=request.user, status='I', message=m, obj_model='Airbase',)
        l.save() 
    return render_to_response('flight/airbase_retuse.html', { 'object': a, 'flight_list': trip_list,'adate': adate, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def airbase_date_to_date_retuse(request, slug, yeara, moa, daa, yearb, mob, dab):
    a = Airbase.objects.get(tla=slug)
    a.rgal0 = a.rcost0 = a.rgal = a.rcost = a.rgalt = a.rcostt = 0
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    bdate = datetime.datetime(int(yearb), int(mob), int(dab), 0, 0)
    season = datetime.datetime(int(yeara), 1, 1, 0, 0) # jan 1 current year
    ydate = adate - timedelta(days=1)
    season_trips = Trip.objects.filter(frombase_id=a.id).filter(planestart__range=(season, ydate)) # agg rgal by rtype here?
    for t in season_trips: # get rgal and rcost for season to ydate per rtype
        try:
            t.crgal = Trip.objects.filter(frombase_id=a.id).filter(planestart__range=(season, t.planestart)).filter(rtype=t.rtype).aggregate(retardant_sum=Sum('retardantgal'))['retardant_sum'] # we need trip.retgal for trip.rtype here
            #t.rbase = Airbase.objects.filter(id=t.frombase_id).annotate(trip_count=Count('trip_frombase'),retardant_sum=Sum('trip_frombase__retardantgal'))[0] # to get the ret pumped at the base but we have that above
            t.rprice = Retardantfee.objects.filter(
                Q(airbase_id=t.frombase_id),
                Q(rtype=t.rtype),
                Q(volume__lt=t.crgal),
                Q(effectivedate__lte=t.planestart)
                ).order_by('-volume','-effectivedate')[0] # this is price1 
            t.rprice2 = Retardantfee.objects.filter(
                Q(airbase_id=t.frombase_id),
                Q(rtype=t.rtype),
                Q(volume__lt=(t.crgal+t.retardantgal)),
                Q(effectivedate__lte=t.planestart)
                ).order_by('-volume','-effectivedate')[0] # this is price2 
            t.r1vol = t.rprice.volume
            t.r1cost = t.rprice.cost
            t.rflat = t.rprice.flat
            t.r2vol = t.rprice2.volume
            t.r2cost = t.rprice2.cost
            if t.r1vol != t.r2vol:
                t.rgal1 = t.r2vol - t.crgal # r.vol2 - t.crgal is 1
                t.rcost1 = t.r1cost * t.rgal1
                t.rgal2 = (t.crgal + t.retardantgal) - t.r2vol # t.crgal + + t.retgal - vol2 is 9 for price2 
                t.rcost2 = t.r2cost * t.rgal2
                #t.rprice = (t.r1cost + t.r2cost)/2
                t.rcost = t.rcost1 + t.rcost2
            else:
                t.rprice = t.r1cost
                t.rcost = t.rprice * t.retardantgal
            t.rcost = t.rcost + t.rflat
            t.rcost = Decimal(t.rcost).quantize(Decimal('.01'))
        except:
            t.rprice = 0
            t.rcost = 0
        a.rgal0 = a.rgal0 + t.retardantgal # gallons pumped since beginning of season before today
        a.rcost0 = a.rcost0 + t.rcost # dollars pumped since beginning of season before today
    trip_list = Trip.objects.filter(frombase_id=a.id).filter(planestart__range=(adate, bdate))
    a.rgalt = a.rgal0
    a.rcostt = a.rcost0
    for t in trip_list:
        try:
            t.crgal = Trip.objects.filter(frombase_id=a.id).filter(planestart__range=(season, t.planestart)).filter(rtype=t.rtype).aggregate(retardant_sum=Sum('retardantgal'))['retardant_sum'] # we need trip.retgal for trip.rtype here
            #t.rbase = Airbase.objects.filter(id=t.frombase_id).annotate(trip_count=Count('trip_frombase'),retardant_sum=Sum('trip_frombase__retardantgal'))[0] # to get the ret pumped at the base but we have that above
            t.rprice = Retardantfee.objects.filter(
                Q(airbase_id=t.frombase_id),
                Q(rtype=t.rtype),
                Q(volume__lt=t.crgal),
                Q(effectivedate__lte=t.planestart)
                ).order_by('-volume','-effectivedate')[0] # this is price1 
            t.rprice2 = Retardantfee.objects.filter(
                Q(airbase_id=t.frombase_id),
                Q(rtype=t.rtype),
                Q(volume__lt=(t.crgal+t.retardantgal)),
                Q(effectivedate__lte=t.planestart)
                ).order_by('-volume','-effectivedate')[0] # this is price2 
            t.r1vol = t.rprice.volume
            t.r1cost = t.rprice.cost
            t.rflat = t.rprice.flat
            t.r2vol = t.rprice2.volume
            t.r2cost = t.rprice2.cost
            if t.r1vol != t.r2vol:
                t.rgal1 = t.r2vol - t.crgal # r.vol2 - t.crgal is 1
                t.rcost1 = t.r1cost * t.rgal1
                t.rgal2 = (t.crgal + t.retardantgal) - t.r2vol # t.crgal + + t.retgal - vol2 is 9 for price2 
                t.rcost2 = t.r2cost * t.rgal2
                #t.rprice = (t.r1cost + t.r2cost)/2
                t.rcost = t.rcost1 + t.rcost2
            else:
                t.rprice = t.r1cost
                t.rcost = t.rprice * t.retardantgal
            t.rcost = t.rcost + t.rflat
            t.rcost = Decimal(t.rcost).quantize(Decimal('.01'))
        except:
            t.rprice = 0
            t.rcost = 0
        a.rgal = a.rgal + t.retardantgal
        a.rcost = a.rcost + t.rcost
        t.pounds = None # no idea. wt of ret?
        t.rgalt = a.rgalt + t.retardantgal
        t.rcostt = a.rcostt + t.rcost
        a.rgalt = t.rgalt # gallons pumped since beginning of season
        a.rcostt = t.rcostt # dollars pumped since beginning of season
    if not request.user.is_superuser:
        m = 'In addition to assuming retardant volumes at %s roll back to zero on New Year\'s Day, this particular worksheet does not yet care about various retardant brands.' % (a.name)
        messages.info(request, m) 
        l = Logitem(author=request.user, status='I', message=m, obj_model='Airbase',)
        l.save() 
    return render_to_response('flight/airbase_retuse.html', { 'object': a, 'flight_list': trip_list, 'adate': adate, 'bdate': bdate, }, context_instance=RequestContext(request))


@login_required
@permission_required('flight.add_airbase')
def airplane_date(request, tail, name, yeara, moa, daa):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = Airplane.objects.get(name=name)
    try:
        a.c = Contract.objects.filter(airplane_id=a.id).filter(effectivedate__lte=datetime.date.today())[0]
    except:
        a.c = None
    a.frate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='flight').order_by('-effectivedate') # WHY RATES?
    if a.frate_list:
        a.frate_list = a.frate_list[:1]
    a.arate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='avail').order_by('-effectivedate')
    if a.arate_list:
        a.arate_list = a.arate_list[:1]
    a.srate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='nonavail').order_by('-effectivedate')
    if a.srate_list:
        a.srate_list = a.srate_list[:1]
    a.erate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='extended').order_by('-effectivedate')
    if a.erate_list:
        a.erate_list = a.erate_list[:1]
    #if a.begins and a.ends:
    #    a.map = (a.ends-a.begins).days
    arates = Rate.objects.filter(airplane_id=a.id).exclude(ratetype__iexact='flight').exclude(ratetype__iexact='avail').exclude(ratetype__iexact='nonavail').exclude(ratetype__iexact='extended').order_by('-effectivedate')
    artypes = Rate.objects.filter(airplane_id=a.id).exclude(ratetype__iexact='flight').exclude(ratetype__iexact='avail').exclude(ratetype__iexact='nonavail').exclude(ratetype__iexact='extended').distinct('ratetype').values_list('ratetype')
    a.rtypes = []
    for rtype in artypes:
        rtype = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact=rtype).order_by('-effectivedate')[:1]
        a.rtypes.append(rtype) # WHY RATES?
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    mission_list = Mission.objects.filter(airplane_id=a.id).filter(startdate=adate).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    incidents = Incident.objects.all().only('name','resourceorder')
    return render_to_response('flight/airplane_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list,'adate': adate, 'entmap': entmap, 'incidents': incidents, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def person_date(request, slug, yeara, moa, daa):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    persons = Person.objects.all()
    a = 'None'
    while a == 'None':
        for person in persons:
            person.slug = str(person.firstname + " " + person.lastname)
            if person.slug == slug:
                a = person
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    mission_list = Mission.objects.filter(Q(pilot_id=a.id) | Q(copilot_id=a.id) | Q(othercrew_id=a.id)).filter(startdate=adate).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/person_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list,'adate': adate, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def incident_date(request, slug, ro, yeara, moa, daa):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = Incident.objects.get(resourceorder=ro)
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    mission_list = Mission.objects.filter(trip_mission__incident_id=a.id).filter(startdate=adate).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(incident_id=a.id)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    airplanes = Airplane.objects.all().only('tail','name')
    return render_to_response('flight/incident_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list, 'adate': adate, 'entmap': entmap, 'airplanes': airplanes, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def incident_date_dailycost(request, slug, ro, yeara, moa, daa):
    a = Incident.objects.get(resourceorder=ro)
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    mission_list = Mission.objects.filter(trip_mission__incident_id=a.id).filter(startdate=adate).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(incident_id=a.id)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = a.flsmrcost = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
        a.flsmrcost = a.flsmrcost + m.flsmrcost
    a2(a)
    #mapents(trip_list)
    #airplanes = Airplane.objects.all().only('tail','name')
    return render_to_response('flight/incident_dailycost.html', { 'object': a, 'mission_list': mission_list, 'flight_list': trip_list, 'adate': adate, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def airbase_month(request, slug, yeara, moa):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = Airbase.objects.get(tla=slug)
    lfee_list = Landingfee.objects.filter(airbase_id=a.id).order_by('-effectivedate') # WHY RATES?
    lper_list = Landingfee.objects.filter(airbase_id=a.id).distinct('perwhat')
    for lper in lper_list:
        lp = lfee_list.filter(Q(perwhat__iexact=lper.perwhat))[0]
        lper.cost = lp.cost
        lper.effectivedate = lp.effectivedate
    lfee_list = lper_list
    rfee_list = Retardantfee.objects.filter(airbase_id=a.id).order_by('-effectivedate')
    rper_list = Retardantfee.objects.filter(airbase_id=a.id).distinct('rtype','volume') # dual-distinct problem here
    for rper in rper_list:
        vol = str(rper.volume)
        rty = str(rper.rtype)
        try:
            rp = rfee_list.filter(volume__iexact=vol).filter(rtype__iexact=rty)[0]
            rper.cost = rp.cost
            rper.effectivedate = rp.effectivedate
        except:
            rper.cost = 0
            rper.effectivedate = None
    rfee_list = rper_list # WHY RATES?
    adate = datetime.datetime(int(yeara), int(moa), 1, 0, 0)
    mission_list = Mission.objects.filter(trip_mission__frombase_id=a.id).filter(Q(startdate__year=yeara) & Q(startdate__month=moa)).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/airbase_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list,'adate': adate, 'mo': moa, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def airplane_month(request, tail, name, yeara, moa):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = Airplane.objects.get(name=name)
    try:
        a.c = Contract.objects.filter(airplane_id=a.id).filter(effectivedate__lte=datetime.date.today())[0]
    except:
        a.c = None
    a.frate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='flight').order_by('-effectivedate')
    if a.frate_list:
        a.frate_list = a.frate_list[:1]
    a.arate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='avail').order_by('-effectivedate')
    if a.arate_list:
        a.arate_list = a.arate_list[:1]
    a.srate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='nonavail').order_by('-effectivedate')
    if a.srate_list:
        a.srate_list = a.srate_list[:1]
    a.erate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='extended').order_by('-effectivedate')
    if a.erate_list:
        a.erate_list = a.erate_list[:1]
    #if a.begins and a.ends:
    #    a.map = (a.ends-a.begins).days
    arates = Rate.objects.filter(airplane_id=a.id).exclude(ratetype__iexact='flight').exclude(ratetype__iexact='avail').exclude(ratetype__iexact='nonavail').exclude(ratetype__iexact='extended').order_by('-effectivedate')
    artypes = Rate.objects.filter(airplane_id=a.id).exclude(ratetype__iexact='flight').exclude(ratetype__iexact='avail').exclude(ratetype__iexact='nonavail').exclude(ratetype__iexact='extended').distinct('ratetype').values_list('ratetype')
    a.rtypes = []
    for rtype in artypes:
        rtype = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact=rtype).order_by('-effectivedate')[:1]
        a.rtypes.append(rtype) # WHY RATES?
    adate = datetime.datetime(int(yeara), int(moa), 1, 0, 0)
    mission_list = Mission.objects.filter(airplane_id=a.id).filter(Q(startdate__year=yeara),Q(startdate__month=moa)).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    incidents = Incident.objects.all().only('name','resourceorder')
    return render_to_response('flight/airplane_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list,'adate': adate, 'mo': moa, 'entmap': entmap, 'incidents': incidents,}, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def person_month(request, slug, yeara, moa):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    persons = Person.objects.all()
    a = 'None'
    while a == 'None':
        for person in persons:
            person.slug = str(person.firstname + " " + person.lastname)
            if person.slug == slug:
                a = person
    adate = datetime.datetime(int(yeara), int(moa), 1, 0, 0)
    mission_list = Mission.objects.filter(Q(pilot_id=a.id) | Q(copilot_id=a.id) | Q(othercrew_id=a.id)).filter(Q(startdate__year=yeara) & Q(startdate__month=moa)).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/person_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list,'adate': adate, 'mo': moa, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def incident_month(request, slug, ro, yeara, moa):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = Incident.objects.get(resourceorder=ro)
    adate = datetime.datetime(int(yeara), int(moa), 1, 0, 0)
    mission_list = Mission.objects.filter(trip_mission__incident_id=a.id).filter(Q(startdate__year=yeara) & Q(startdate__month=moa)).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(incident_id=a.id)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    airplanes = Airplane.objects.all().only('tail','name')
    return render_to_response('flight/incident_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list, 'adate': adate, 'mo': moa, 'entmap': entmap, 'airplanes': airplanes,}, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def airbase_year(request, slug, yeara):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = Airbase.objects.get(tla=slug)
    lfee_list = Landingfee.objects.filter(airbase_id=a.id).order_by('-effectivedate') # WHY RATES?
    lper_list = Landingfee.objects.filter(airbase_id=a.id).distinct('perwhat')
    for lper in lper_list:
        lp = lfee_list.filter(Q(perwhat__iexact=lper.perwhat))[0]
        lper.cost = lp.cost
        lper.effectivedate = lp.effectivedate
    lfee_list = lper_list
    rfee_list = Retardantfee.objects.filter(airbase_id=a.id).order_by('-effectivedate')
    rper_list = Retardantfee.objects.filter(airbase_id=a.id).distinct('rtype','volume') # dual-distinct problem here
    for rper in rper_list:
        vol = str(rper.volume)
        rty = str(rper.rtype)
        try:
            rp = rfee_list.filter(volume__iexact=vol).filter(rtype__iexact=rty)[0]
            rper.cost = rp.cost
            rper.effectivedate = rp.effectivedate
        except:
            rper.cost = 0
            rper.effectivedate = None
    rfee_list = rper_list # WHY RATES?
    adate = datetime.datetime(int(yeara), 1, 1, 0, 0)
    mission_list = Mission.objects.filter(trip_mission__frombase_id=a.id).filter(startdate__year=yeara).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/airbase_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list,'adate': adate, 'year': yeara, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def airplane_year(request, tail, name, yeara):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = Airplane.objects.get(name=name)
    try:
        a.c = Contract.objects.filter(airplane_id=a.id).filter(effectivedate__lte=datetime.date.today())[0]
    except:
        a.c = None
    a.frate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='flight').order_by('-effectivedate') # WHY RATES?
    if a.frate_list:
        a.frate_list = a.frate_list[:1]
    a.arate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='avail').order_by('-effectivedate')
    if a.arate_list:
        a.arate_list = a.arate_list[:1]
    a.srate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='nonavail').order_by('-effectivedate')
    if a.srate_list:
        a.srate_list = a.srate_list[:1]
    a.erate_list = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact='extended').order_by('-effectivedate')
    if a.erate_list:
        a.erate_list = a.erate_list[:1]
    #if a.begins and a.ends:
    #    a.map = (a.ends-a.begins).days
    arates = Rate.objects.filter(airplane_id=a.id).exclude(ratetype__iexact='flight').exclude(ratetype__iexact='avail').exclude(ratetype__iexact='nonavail').exclude(ratetype__iexact='extended').order_by('-effectivedate')
    artypes = Rate.objects.filter(airplane_id=a.id).exclude(ratetype__iexact='flight').exclude(ratetype__iexact='avail').exclude(ratetype__iexact='nonavail').exclude(ratetype__iexact='extended').distinct('ratetype').values_list('ratetype')
    a.rtypes = []
    for rtype in artypes:
        rtype = Rate.objects.filter(airplane_id=a.id).filter(ratetype__iexact=rtype).order_by('-effectivedate')[:1]
        a.rtypes.append(rtype) # WHY RATES?
    adate = datetime.datetime(int(yeara), 1, 1, 0, 0)
    mission_list = Mission.objects.filter(airplane_id=a.id).filter(startdate__year=yeara).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    incidents = Incident.objects.all().only('name','resourceorder')
    return render_to_response('flight/airplane_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list,'adate': adate, 'year': yeara, 'entmap': entmap, 'incidents': incidents }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def person_year(request, slug, yeara):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    persons = Person.objects.all()
    a = 'None'
    while a == 'None':
        for person in persons:
            person.slug = str(person.firstname + " " + person.lastname)
            if person.slug == slug:
                a = person
    adate = datetime.datetime(int(yeara), 1, 1, 0, 0)
    mission_list = Mission.objects.filter(Q(pilot_id=a.id) | Q(copilot_id=a.id) | Q(othercrew_id=a.id)).filter(startdate__year=yeara).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/person_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list,'adate': adate, 'year': yeara, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def incident_year(request, slug, ro, yeara):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    a = Incident.objects.get(resourceorder=ro)
    adate = datetime.datetime(int(yeara), 1, 1, 0, 0)
    mission_list = Mission.objects.filter(trip_mission__incident_id=a.id).filter(startdate__year=yeara).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(incident_id=a.id)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    airplanes = Airplane.objects.all().only('tail','name')
    return render_to_response('flight/incident_detail.html', { 'u': u, 'object': a, 'mission_list': mission_list, 'flight_list': trip_list, 'adate': adate, 'year': yeara, 'entmap': entmap, 'airplanes': airplanes,}, context_instance=RequestContext(request))

### Airplane Incident

@login_required
@permission_required('flight.add_airbase')
def airplane_incident(request, tail, name, incident, ro):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    try:
        a = Airplane.objects.get(name=name)
    except:
        return HttpResponseRedirect('/incident/%s/%s/' % (incident, ro))
    inc = Incident.objects.get(resourceorder=ro)
    mission_list = Mission.objects.filter(airplane_id=a.id).filter(trip_mission__incident_id=inc.id).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(incident_id=inc.id)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    incidents = Incident.objects.all().only('name','resourceorder')
    return render_to_response('flight/airplane_detail.html', { 'u': u, 'object': a, 'incident': inc, 'mission_list': mission_list, 'flight_list': trip_list, 'entmap': entmap, 'incidents': incidents, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def airplane_incident_date(request, tail, name, incident, ro, yeara, moa, daa):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    try:
        a = Airplane.objects.get(name=name)
    except:
        return HttpResponseRedirect('/incident/%s/%s/%s-%s-%s/' % (incident, ro, yeara, moa, daa))
    inc = Incident.objects.get(resourceorder=ro)
    mission_list = Mission.objects.filter(airplane_id=a.id).filter(trip_mission__incident_id=inc.id).filter(startdate=adate).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(incident_id=inc.id)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    incidents = Incident.objects.all().only('name','resourceorder')
    return render_to_response('flight/airplane_detail.html', { 'u': u, 'object': a, 'incident': inc, 'mission_list': mission_list, 'flight_list': trip_list,'adate': adate, 'entmap': entmap, 'incidents' : incidents, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def airplane_incident_month(request, tail, name, incident, ro, yeara, moa):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    adate = datetime.datetime(int(yeara), int(moa), 1, 0, 0)
    try:
        a = Airplane.objects.get(name=name)
    except:
        return HttpResponseRedirect('/incident/%s/%s/%s-%s/' % (incident, ro, yeara, moa))
    inc = Incident.objects.get(resourceorder=ro)
    mission_list = Mission.objects.filter(airplane_id=a.id).filter(trip_mission__incident_id=inc.id).filter(Q(startdate__year=yeara) & Q(startdate__month=moa)).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(incident_id=inc.id)
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    incidents = Incident.objects.all().only('name','resourceorder')
    return render_to_response('flight/airplane_detail.html', { 'u': u, 'object': a, 'incident': inc, 'mission_list': mission_list, 'flight_list': trip_list, 'adate': adate, 'mo': moa, 'entmap': entmap, 'incidents': incidents, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def airplane_incident_year(request, tail, name, incident, ro, yeara):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    adate = datetime.datetime(int(yeara), 1, 1, 0, 0)
    try:
        a = Airplane.objects.get(name=name)
    except:
        return HttpResponseRedirect('/incident/%s/%s/%s/' % (incident, ro, yeara))
    inc = Incident.objects.get(resourceorder=ro)
    mission_list = Mission.objects.filter(airplane_id=a.id).filter(trip_mission__incident_id=inc.id).filter(startdate__year=yeara).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(incident_id=inc.id) # filter to plane/year too if returned. check!
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    incidents = Incident.objects.all().only('name','resourceorder')
    return render_to_response('flight/airplane_detail.html', { 'u': u, 'object': a, 'incident': inc, 'mission_list': mission_list, 'flight_list': trip_list, 'adate': adate, 'year': yeara, 'entmap': entmap, 'incidents': incidents, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def airplane_incident_date_to_date(request, tail, name, incident, ro, yeara, moa, daa, yearb, mob, dab):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    bdate = datetime.datetime(int(yearb), int(mob), int(dab), 0, 0)
    try:
        a = Airplane.objects.get(name=name)
    except:
        return HttpResponseRedirect('/incident/%s/%s/%s-%s-%s/%s-%s-%s/' % (incident, ro, yeara, moa, daa, yearb, mob, dab))
    inc = Incident.objects.get(resourceorder=ro)
    mission_list = Mission.objects.filter(airplane_id=a.id).filter(trip_mission__incident_id=inc.id).filter(startdate__range=(adate, bdate)).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(incident_id=inc.id) ### it is returned! in all airplane incident. fix it!
    a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    incidents = Incident.objects.all().only('name','resourceorder')
    return render_to_response('flight/airplane_detail.html', { 'u': u, 'object': a, 'incident': inc, 'mission_list': mission_list, 'flight_list': trip_list, 'adate': adate, 'bdate': bdate, 'entmap': entmap, 'incidents': incidents, }, context_instance=RequestContext(request))

### State and Region

@login_required
@permission_required('flight.add_airbase')
def state(request, slug):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    m_list = Trip.objects.filter(Q(frombase__st__iexact=slug) | Q(tobase__st__iexact=slug)).order_by('-modified').values_list('mission_id')[:20]
    mission_list = Mission.objects.filter(id__in=m_list).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal')).order_by('-modified')
    trip_list = Trip.objects.filter(mission__in=mission_list) ### all  trips in any state mission
    a = Stine()
    a.slug = slug
    a.state = 'this State'
    airbase_list = Airbase.objects.filter(st__iexact=slug).annotate(trip_count=Count('trip_frombase'),retardant_sum=Sum('trip_frombase__retardantgal'))
    for b in airbase_list:
        a.state = b.get_st_display()
    a.total_cost = a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/mission_list.html', { 'u': u, 'airbase_list': None, 'airplane_list': None, 'mission_list': mission_list, 'flight_list': trip_list, 'state': a, 'o': a, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def state_date(request, slug, yeara, moa, daa):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    mission_list = Mission.objects.filter(trip_mission__frombase__st__iexact=slug).filter(startdate=adate).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list) ### all trips in any state mission
    a = Stine()
    a.slug = slug
    a.state = 'this State'
    airbase_list = Airbase.objects.filter(st__iexact=slug).annotate(trip_count=Count('trip_frombase'),retardant_sum=Sum('trip_frombase__retardantgal'))
    for b in airbase_list:
        a.state = b.get_st_display()
    a.total_cost = a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/mission_list.html', { 'u': u, 'airbase_list': None, 'airplane_list': None, 'mission_list': mission_list, 'flight_list': trip_list, 'state': a, 'o': a, 'adate': adate, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def state_date_to_date(request, slug, yeara, moa, daa, yearb, mob, dab):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    bdate = datetime.datetime(int(yearb), int(mob), int(dab), 0, 0)
    mission_list = Mission.objects.filter(trip_mission__frombase__st__iexact=slug).filter(startdate__range=(adate, bdate)).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal')) ### better ways to do this
    trip_list = Trip.objects.filter(mission__in=mission_list) ### all trips in mission with any activity in state
    a = Stine()
    a.slug = slug
    a.state = 'this State'
    airbase_list = Airbase.objects.filter(st__iexact=slug).annotate(trip_count=Count('trip_frombase'),retardant_sum=Sum('trip_frombase__retardantgal'))
    for b in airbase_list:
        a.state = b.get_st_display()
    a.total_cost = a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/mission_list.html', { 'u': u, 'airbase_list': None, 'airplane_list': None, 'mission_list': mission_list, 'flight_list': trip_list, 'state': a, 'o': a, 'adate': adate, 'bdate': bdate, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def state_month(request, slug, yeara, moa, ):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    adate = datetime.datetime(int(yeara), int(moa), 1, 0, 0)
    mission_list = Mission.objects.filter(trip_mission__frombase__st__iexact=slug).filter(Q(startdate__year=yeara) & Q(startdate__month=moa)).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list) ### trips on all missions in the state -- wrong i think
    a = Stine()
    a.slug = slug
    a.state = 'this State'
    airbase_list = Airbase.objects.filter(st__iexact=slug).annotate(trip_count=Count('trip_frombase'),retardant_sum=Sum('trip_frombase__retardantgal'))
    for b in airbase_list:
        a.state = b.get_st_display()
    a.total_cost = a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/mission_list.html', { 'u': u, 'airbase_list': None, 'airplane_list': None, 'mission_list': mission_list, 'flight_list': trip_list, 'state': a, 'o': a, 'adate': adate, 'mo': moa, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def state_year(request, slug, yeara, ):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    adate = datetime.datetime(int(yeara), 1, 1, 0, 0)
    mission_list = Mission.objects.filter(trip_mission__frombase__st__iexact=slug).filter(startdate__year=yeara).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list) ### limit to trips/actions at in-state bases
    a = Stine()
    a.slug = slug
    a.state = 'this State'
    airbase_list = Airbase.objects.filter(st__iexact=slug).annotate(trip_count=Count('trip_frombase'),retardant_sum=Sum('trip_frombase__retardantgal'))
    for b in airbase_list:
        a.state = b.get_st_display()
    a.total_cost = a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/mission_list.html', { 'u': u, 'airbase_list': None, 'airplane_list': None, 'mission_list': mission_list, 'flight_list': trip_list, 'state': a, 'o': a, 'adate': adate, 'year': yeara, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def region(request, slug):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    m_list = Trip.objects.filter(Q(frombase__region__iexact=slug) | Q(tobase__region__iexact=slug)).order_by('-modified').values_list('mission_id')[:20]
    mission_list = Mission.objects.filter(id__in=m_list).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal')).order_by('-modified')
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a = Stine()
    a.slug = slug
    a.total_cost = a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/mission_list.html', { 'u': u, 'airbase_list': None, 'airplane_list': None, 'mission_list': mission_list, 'flight_list': trip_list, 'region': a, 'o': a, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def region_date(request, slug, yeara, moa, daa):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    mission_list = Mission.objects.filter(trip_mission__frombase__region__iexact=slug).filter(startdate=adate).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a = Stine()
    a.slug = slug
    a.total_cost = a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/mission_list.html', { 'u': u, 'airbase_list': None, 'airplane_list': None, 'mission_list': mission_list, 'flight_list': trip_list, 'region': a, 'o': a, 'adate': adate, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def region_date_to_date(request, slug, yeara, moa, daa, yearb, mob, dab):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    bdate = datetime.datetime(int(yearb), int(mob), int(dab), 0, 0)
    mission_list = Mission.objects.filter(trip_mission__frombase__region__iexact=slug).filter(startdate__range=(adate, bdate)).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list) ### limit all of these to in region trips
    a = Stine()
    a.slug = slug
    a.total_cost = a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/mission_list.html', { 'u': u, 'airbase_list': None, 'airplane_list': None, 'mission_list': mission_list, 'flight_list': trip_list, 'region': a, 'o': a, 'adate': adate, 'bdate': bdate, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def region_month(request, slug, yeara, moa, ):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    adate = datetime.datetime(int(yeara), int(moa), 1, 0, 0)
    mission_list = Mission.objects.filter(trip_mission__frombase__region__iexact=slug).filter(Q(startdate__year=yeara) & Q(startdate__month=moa)).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a = Stine()
    a.slug = slug
    a.total_cost = a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/mission_list.html', { 'u': u, 'airbase_list': None, 'airplane_list': None, 'mission_list': mission_list, 'flight_list': trip_list, 'region': a, 'o': a, 'adate': adate, 'mo': moa, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def region_year(request, slug, yeara, ):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    adate = datetime.datetime(int(yeara), 1, 1, 0, 0)
    mission_list = Mission.objects.filter(trip_mission__frombase__region__iexact=slug).filter(startdate__year=yeara).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a = Stine()
    a.slug = slug
    a.total_cost = a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()    
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/mission_list.html', { 'u': u, 'airbase_list': None, 'airplane_list': None, 'mission_list': mission_list, 'flight_list': trip_list, 'region': a, 'o': a, 'adate': adate, 'year': yeara, 'entmap': entmap, }, context_instance=RequestContext(request))

# Mission Date

@login_required
@permission_required('flight.add_airbase')
def mission_date(request, yeara, moa, daa):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    mission_list = Mission.objects.filter(startdate=adate).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a = Stine()
    a.total_cost = a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/mission_list.html', { 'u': u, 'airbase_list': None, 'airplane_list': None, 'mission_list': mission_list, 'flight_list': trip_list, 'o': a, 'adate': adate, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def mission_date_to_date(request, yeara, moa, daa, yearb, mob, dab):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    adate = datetime.datetime(int(yeara), int(moa), int(daa), 0, 0)
    bdate = datetime.datetime(int(yearb), int(mob), int(dab), 0, 0)
    mission_list = Mission.objects.filter(startdate__range=(adate, bdate)).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a = Stine()
    a.total_cost = a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/mission_list.html', { 'u': u, 'airbase_list': None, 'airplane_list': None, 'mission_list': mission_list, 'flight_list': trip_list, 'o': a, 'adate': adate, 'bdate': bdate, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def mission_month(request, yeara, moa, ):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    adate = datetime.datetime(int(yeara), int(moa), 1, 0, 0)
    mission_list = Mission.objects.filter(Q(startdate__year=yeara) & Q(startdate__month=moa)).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a = Stine()
    a.total_cost = a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/mission_list.html', { 'u': u, 'airbase_list': None, 'airplane_list': None, 'mission_list': mission_list, 'flight_list': trip_list, 'o': a, 'adate': adate, 'mo': moa, 'entmap': entmap, }, context_instance=RequestContext(request))

@login_required
@permission_required('flight.add_airbase')
def mission_year(request, yeara, ):
    u = User.objects.get(id=request.user.id)
    usermenu(u)
    adate = datetime.datetime(int(yeara), 1, 1, 0, 0)
    mission_list = Mission.objects.filter(startdate__year=yeara).annotate(trip_count=Count('trip_mission'),retardant_sum=Sum('trip_mission__retardantgal'))
    trip_list = Trip.objects.filter(mission__in=mission_list)
    a = Stine()
    a.total_cost = a.acost = a.ecost = a.fcount = a.ftime = a.fcost = a.mtime = a.ntime = a.ncost = a.lcost = a.rgal = a.rcost = a.ocost = a.moves = a.mcost = a.tcost = a.tfs = a.tbs = a.tms = a.tns = 0
    a.mission_count = mission_list.count()
    for m in mission_list:
        m.trip_list = trip_list.filter(mission_id=m.id)
        t2m(m,m.trip_list)
        am(a,m)
    a2(a)
    #mapents(trip_list)
    entmap = None
    return render_to_response('flight/mission_list.html', { 'u': u, 'airbase_list': None, 'airplane_list': None, 'mission_list': mission_list, 'flight_list': trip_list, 'o': a, 'adate': adate, 'year': yeara, 'entmap': entmap, }, context_instance=RequestContext(request))