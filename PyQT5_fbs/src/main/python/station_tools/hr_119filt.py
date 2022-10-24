import numpy as np
import scipy.io
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# mat = scipy.io.loadmat('t0072017rad.mat')
# t = mat['t0072017rad'][:,0]
# x = mat['t0072017rad'][:,1]

def my_filter(tin, xin):
    filt_wts = []
    with open("filt_wts.txt", "r") as file:
        for line in file:
            filt_wts.append(float(line))
    
    filt_wts = np.asarray(filt_wts)
    wts = np.concatenate((np.flip(filt_wts[-59:],0), filt_wts), axis=0)
    
    # tin = np.array([1,2, 3, 4 ,5])
    # xin = np.array([345, 450, 400, 300, 320])
    t = np.arange(tin[0],tin[-1],2.5/60/24)
    # t = np.append(t,tin[-1])
    
    k = np.where(np.diff(tin)>16.0/60/24)
    print("length", k)
    if(len(k[0])==0):
        x = np.interp(t,tin,xin)
    # This conditional below is questionable and might not work
    # It hasn't been tested because the file that I am loading does not satisfy
    # the conditiond
    
    #Tested the above and it seems to be working ok
    else:
        x=np.full(len(t), np.nan)
        for jj in range(len(k[0])):
            if(jj == 0):
                j1 = 0
                j2 = k[0][jj]
            elif(jj == len(k)):
                j1 = k[0][jj-1]
                j2 = len(tin)
            else:
                j1 = k[0][jj-1]
                j2 = k[0][jj]
            # kk = np.where((t>=tin[j1]) & (t <= tin[j2]))
            kk = np.where(np.logical_and(t>=tin[j1],t <= tin[j2] ))
            if(len(kk[0])>1):
                x[kk[0]] = np.interp(t[kk[0]],tin[j1:j2],xin[j1:j2])
    
    my_ts = t[0] 
    # tot_seconds = (float(my_ts)-int(my_ts))*1440*60
    # day = tot_seconds // (24 * 3600)
    # tot_seconds = tot_seconds % (24 * 3600)
    # my_hours = tot_seconds // 3600
    # tot_seconds %= 3600
    # my_minutes = tot_seconds // 60
    # tot_seconds %= 60
    # my_seconds = int(tot_seconds) 
    
    # my_hrs =    (float(my_ts)-int(my_ts))*1440//60                   
    # my_minutes = (float(my_ts)-int(my_ts))*1440*60//60
    # my_seconds = (float(my_ts)-int(my_ts))*1440*60%60
    _date = datetime.fromordinal(int(my_ts)) + timedelta(days=my_ts%1) - timedelta(days = 366)#+timedelta(hours=my_hours) +timedelta(minutes=my_minutes)+timedelta(seconds=my_seconds)
    yr = _date.year
    mon = _date.month
    day = _date.day
    hr = _date.hour
    mint = _date.minute
    sec = _date.second
    
    if(mint==0 and sec == 0):
        t1 = t[0];
    else:
        t1 = datetime.toordinal(datetime(yr,mon,day,hr,0,0)+timedelta(days = 366)+timedelta(hours=1))
        # t1 = float(datetime.toordinal(datetime(yr,mon,day,hr,0,0))+366)
    
    tt = np.arange(t1,t[-1],2.5/60/24)
    xx = np.interp(tt,t,x)
    t = tt
    x = xx
    
    
    
    tt = np.ndarray(0)
    xx = np.ndarray(0)
    
    yr_ar=[]
    mon_ar=[]
    day_ar=[]
    hr_ar=[]
    mint_ar=[]
    sec_ar = []
    for d in t:
        _date = datetime.fromordinal(int(d)) + timedelta(days=d%1) - timedelta(days = 366)
        yr_ar.append(_date.year)
        mon_ar .append( _date.month)
        day_ar .append( _date.day)
        hr_ar .append( _date.hour)
        mint_ar .append( _date.minute)
        sec_ar .append( _date.second)
    
    yr_ar = np.asarray(yr_ar)
    mon_ar = np.asarray(mon_ar)
    day_ar = np.asarray(day_ar)
    hr_ar = np.asarray(hr_ar)
    mint_ar = np.asarray(mint_ar)
    sec_ar = np.asarray(sec_ar)
    
    k = np.where(mint_ar==0)
    
    ks = k[0]-59;
    ke = k[0]+59;
    
    kk = np.where(ks<0)
    ks[kk[0]] = 1
    
    kk = np.where(ke > len(x))
    ke[kk[0]] = len(x)
    
    nhr = len(k[0]);
    tout = []
    
    for t in k[0]:
        tout.append(float(datetime.toordinal(datetime(yr_ar[t],mon_ar[t],day_ar[t],hr_ar[t],mint_ar[t],0)+timedelta(days = 366))+hr_ar[t]/24.0+mint_ar[t]/1440.0))
    nhr = len(k[0])
    tout = np.asarray(tout)
    xout = np.full(nhr,np.nan)
    
    for j in range(nhr):
    
        xx = np.full(119, np.nan)
        ww = np.full(119, np.nan)
        xx[ks[j]-k[0][j]+60:ke[j]-k[0][j]+60] = x[ks[j]:ke[j]]
        ww[ks[j]-k[0][j]+60:ke[j]-k[0][j]+60] = wts[ks[j]-k[0][j]+60:ke[j]-k[0][j]+60]
        kg = np.argwhere(~np.isnan(xx))
        if(sum(ww[kg])==0):
            xout[j] = np.nan
        else:        
            xout[j] = sum(xx[kg]*ww[kg])/sum(ww[kg])
    
        kb = np.argwhere(np.isnan(xx))
        if(len(kb)>0):
            if(sum(abs(ww[kb]))>0.25):
                xout[j] = np.nan
                
    return(tout,xout)
    # 
    # plt.plot(tin,xin)
    # plt.show()
    
# my_filter(t,x)