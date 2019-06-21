import os
import numpy as np
from datetime import datetime, timedelta

def calwts(Tc, S):
    """
     This routine computes a set of convolution-type filter weights
     using the procedure described in Bloomfield's book. The half
     amplitude point of the filter is Tc and the total span of the
     filter is S. The span, S, must be odd or a fatal error occurs.
    Parameters:
    -----------
    Tc: The period where the filter will have 50%
        amplitude response. The units must be in
        terms of the time step. For example, using
        Tc=10 with an hourly time step gives half
        amplitude response at a period of 10 hours.
        However, if the time step is 5 days, then
        using Tc=10 puts the 50% point at 50 days.

    S:  The total span of the filter in units of
        time step (see above under Tc). N.B., this
        includes the central weights and BOTH sides
        of the filter. This number is therefore
        odd for a proper filter.

    Returns:
    --------
     wts -  The computed weights. This is a vector
            of length S that has been normalized to
            unit sum.
    --------------------------------------------------------------------
    NOTES  :  1. The routine CALRSP can be used to check the response
              function in frequency space for the filter.


    HISTORY:  1. Original version written 15 March 1989 by Gary Mitchum.
    """

    # Check that the span of the filter is odd. Stop if not.
    if S%2 == 0:
        print('Number of filter weights is not odd. Execution terminated.')
        raise
    s = int((S-1)/2)
    t = np.arange(1,s+1,1)

    wt = np.sin(2*np.pi*t/Tc)*np.sin(2*np.pi*t/S)/(4*np.pi**2*t**2/(Tc*S))

    facnrm=1+2*sum(wt)
    wts= np.append(np.flip(wt,0), np.append(1,wt))/facnrm

    return wts

def smooth_gap1(u, wt, ngap=0.8):

    # zero out gaps
    k = np.argwhere(np.isnan(u))

    u[k] = 0

    # add zeros to front and end of time series
    n = len(u)
    nwt = len(wt)
    nwt2 = int(np.floor(nwt/2))
    uu = np.append(np.full(nwt2,0),np.append(u,np.full(nwt2,0)))

    # apply convolution
    ua = np.convolve(uu,wt,'same')

    # binary vector, 1 if data, 0 no data
    xx = np.full(len(uu),1)
    xx[uu==0]=0
    nu = np.convolve(xx,wt,'same')

    # NaN out data if nu < .8
    ua = ua/nu
    kn = np.argwhere(nu/sum(wt)<ngap)
    ua[kn] = np.nan

    # trim off wts at beginning and end of time series
    ua = ua[nwt2:nwt2+n]

    return ua

def datenum(d):
    """
    Python equivalent of the Matlab datenum function.

    Parameters:
    -----------
    d: datetime object (e.g. datetime(yr,mon,day,hr,min,sec))

    Returns:
    --------
    float: datetime object converted to Matlab epoch

    """
    return 366 + d.toordinal() + (d - datetime.fromordinal(d.toordinal())).total_seconds()/(24*60*60)

# TO make it work numpy datetime
def datenum2(date):
    obj = []
    for d in date:
        obj.append(366 + d.astype(datetime).toordinal() + (d.astype(datetime) - datetime.fromordinal(d.astype(datetime).toordinal())).total_seconds()/(24*60*60))
    return obj

def matlab2datetime(matlab_datenum):
    day = datetime.fromordinal(int(matlab_datenum))
    dayfrac = timedelta(days=matlab_datenum%1) - timedelta(days = 366)
    return day + dayfrac + +timedelta(microseconds = 3)

def hr_calwts_filt(tin,xin):

    """
    Uses calwts.m to compute
    filter weights for Bloomfield's convolution filter.  Assumes constant sample period
    for input time series (i.e., no discontinuities).

    Parameters:
    -----------
    tin: A time vector as an array same length as xin
    xin: An array of date points at tin

    Returns:
    --------

    [tout, xout]: An array of timeseries centered on hour
    """

    # filter cutoff period = 90 minutes
    # filter length = 180 minutes

    # filter performance
    # 99.43% power at 6 hour period
    # 89.22% power at 3 hour period
    # 59.8% power at 2 hour period
    # 0.21% power at 1 hour period

    # compute weights depending on sample period
    dt = np.nanmedian(np.diff(tin))*24*60
    Tc = round(90/dt)
    S = round(180/dt)

    # ensure odd length filter
    if S%2 == 0:
        S+=1

    # filter weights
    wts = calwts(Tc,S)

    # find timing discontinuities greater than 15 minutes and correct in data by
    # inserting NaNs

    # input sample period
    dt = np.nanmedian(np.diff(tin))
    t = np.arange(tin[0],tin[-1],dt)

    # find gaps > 16 minutes
    k = np.where(np.diff(tin)>16.0/60/24)[0]
    if len(k)==0:
        print("ZERO")
        x = np.interp(t,tin,xin)
        # This checks
        same = np.where(t == tin)[0]
        not_same = np.where(xin[same] != x[same])[0]
        x[not_same] = xin[not_same]
        # np.where(t == tin,xin,np.interp(t,tin,xin))
    else:
        x=np.full(len(t), np.nan)
        for jj in range(len(k)+1):
            if jj == 0:
                j1 = 0
                j2 = k[jj]
            elif jj == len(k):
                print('jedan')
                j1 = k[jj-1]
                j2 = len(tin)-1
            else:
                print('dva')
                j1 = k[jj-1]
                j2 = k[jj]
            kk = np.where(np.logical_and(t>=tin[j1],t <= tin[j2] ))[0]
            if len(kk)>1:
                x[kk] = np.interp(t[kk],tin[j1:j2+1],xin[j1:j2+1])

    # convolution allowing for gaps
    xs = smooth_gap1( x,wts,.8 )

    yr_ar=[]
    mon_ar=[]
    day_ar=[]
    hr_ar=[]

    # convert the Matlab epoch to Python datetime
    for d in t:
        _date = datetime.fromordinal(int(d)) + timedelta(days=d%1) - timedelta(days = 366)
        yr_ar.append(_date.year)
        mon_ar .append( _date.month)
        day_ar .append( _date.day)
        hr_ar .append( _date.hour)

    yr = np.asarray(yr_ar)
    mon = np.asarray(mon_ar)
    day = np.asarray(day_ar)
    hr = np.asarray(hr_ar)

    # get first hour
    # t1 = datetime.toordinal(datetime(yr[0],mon[0],day[0],hr[0],0,0)+timedelta(days = 366))
    t1 = datenum(datetime(yr[0],mon[0],day[0],hr[0],0,0))
    if t1 < t[0]:
        # t1 = datetime.toordinal(datetime(yr[0],mon[0],day[0],hr[0],0,0)+timedelta(days = 366)+timedelta(hours=1))
        t1 = datenum(datetime(yr[0],mon[0],day[0],hr[0],0,0)+timedelta(hours=1))

    # total number of hours
    nhrs = int(np.floor((t[-1]-t1)*24)+1)

    tout = []

    for j in range(nhrs):
        # tout.append(datetime.toordinal(datetime(yr[0],mon[0],day[0],hr[0],0,0)+timedelta(days = 366)+timedelta(hours=j)))
        tout.append(datenum(datetime(yr[0],mon[0],day[0],hr[0],0,0)+timedelta(hours=j)))

    tout = np.asarray(tout)

    if tout[-1]>t[-1]:
        tout = tout[0:-1]

    xout = np.interp(tout, t, xs)

    return [tout, xout]


def hr_process_2(_data, yr1, yr2):
    """
    Parameters:
    -----------
    _data: a dictionary of sealevel data for a station split by channel name (created using upload(path) method).
    yr1,yr2: Integers, representing years between which to limit data

    Returns:
    --------

    dictionary: hourly averages for each channel and tide

    """
    hr_data={}
    for key in _data.keys():
        if key != 'prd':
            # compute hourly average
            [th,xh] = hr_calwts_filt(_data[key]['time'],_data[key]['sealevel'])

            # if key == 'rad':
            #     print("test", np.nanmean(xh))

            # limit data between yr1 and yr2
            ky = np.argwhere(np.logical_and(th >= datenum(yr1), th < datenum(yr2)))
            if len(ky) == 0:
                continue
            th = th[ky]
            xh = xh[ky]

            # interpolate predicted tide to hourly time stamp from 15min
            pr = np.interp (th, _data['prd']['time'], _data['prd']['sealevel'])
            hr_data[key] = {'time':th, 'sealevel':xh, 'tide':pr,'station':_data[key]['station']}
    return hr_data

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def zero_division(n, d):
    return n / d if d else np.nan
