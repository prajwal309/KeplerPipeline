'''
% Main pipeline file to generate K2 photometry starting from .fits pixel files downloaded from K2 MAST
% Author Vincent Van Eylen
% Modified by Prajwal Niraula
% Contact vincent@phys.au.dk
% See Van Eylen et al. 2015 (ApJ) for details. Please reference this work if you found this code helpful!
'''
import matplotlib
matplotlib.use('Qt4Agg')

# general python files
import os
import matplotlib.pyplot as pl
import numpy as np
import time

# pipeline files
import pixeltoflux
import centroidfit
import periodfinder
import re
import K2SFF

from ExtractFlux import StandardAperture, ModifiedStandardAperture
def run(filepath,outputpath='',CNum=1,makelightcurve=True, find_transits=True,chunksize=48,cutoff_limit=2., method ='Spitzer'):

  #Initializing the time
  InitialTime = time.time()

  # Takes strings with the EPIC number of the star and input/outputpath. Campaign number is used to complete the correct filename as downloaded from MAST
  starname = re.search('[0-9]{9}',filepath).group(0)


  #handling case for spd vs lpd
  if "spd" in filepath:
    starname = starname+"_spd"


  outputfolder = os.path.join(outputpath,str(starname))

  print "Step 1"
  if makelightcurve:

    # makes raw light curve from pixel file
    if CNum==9 or CNum==10:

        #two filenames present for campaign 9 and campaign 10
        AdditionalFilepath = filepath.replace("1_","2_")

        t1,f_t1,Xc1,Yc1 = StandardAperture(filepath,outputpath=outputpath,plot=False,Campaign=CNum)
        t2,f_t2,Xc2,Yc2 = StandardAperture(AdditionalFilepath,outputpath=outputpath,plot=False,Campaign=CNum)

        T_Raw = np.concatenate(t1,t2)
        Flux_Raw = np.concatenate(f_t1,f_t2)

        t1,f_t1,Xc1,Yc1 = centroidfit.find_thruster_events(t1,f_t1,Xc1,Yc1,starname=starname,outputpath=outputfolder)
        t2,f_t2,Xc2,Yc2 = centroidfit.find_thruster_events(t2,f_t2,Xc2,Yc2,starname=starname,outputpath=outputfolder)

    else:
        ##### Change this later
        t,f_t,Xc,Yc = StandardAperture(filepath,outputpath=outputpath,plot=False,Campaign=CNum)
        T_Raw = t[:]
        Flux_Raw = f_t[:]

        #Remove the thruster events #TODO uncomment this later or implement this in K2SFF
        #t,f_t,Xc,Yc = centroidfit.find_thruster_events(t,f_t,Xc,Yc,starname=starname,outputpath=outputfolder)


    # now fit a polynomial to the data (inspired by Spitzer data reduction), ignore first data points which are not usually very high-quality
    if method == 'Spitzer':
        if CNum==9 or CNum==10:
            [t1,f_t1] = centroidfit.spitzer_fit(t1,f_t1,Xc1,Yc1,starname=starname,outputpath=outputpath,chunksize=chunksize)
            [t2,f_t2] = centroidfit.spitzer_fit(t2,f_t2,Xc2,Yc2,starname=starname,outputpath=outputpath,chunksize=chunksize)
            t = np.append(t1,t2)
            f_t = np.append(f_t1,f_t2)
            del t1, t2, f_t1, f_t2
        #elif CNum==1:
            #[t,f_t] = centroidfit.spitzer_fit(t[90:],f_t[90:],Xc[90:],Yc[90:],starname=starname,outputpath=outputpath,chunksize=chunksize)
        else:
            [t,f_t] = centroidfit.spitzer_fit(t,f_t,Xc,Yc,starname=starname,outputpath=outputpath,chunksize=chunksize)

    elif method == 'SFF':
        if CNum==9 or CNum==10:
            [t1,f_t1] = centroidfit.sff_fit(t1,f_t1,Xc1,Yc1,starname=starname,outputpath=outputpath,chunksize=chunksize)
            [t2,f_t2] = centroidfit.sff_fit(t2,f_t2,Xc2,Yc2,starname=starname,outputpath=outputpath,chunksize=chunksize)
            t = np.append(t1,t2)
            f_t = np.append(f_t1,f_t2)
        #elif CNum==1:
            #[t,f_t] = centroidfit.sff_fit(t[90:],f_t[90:],Xc[90:],Yc[90:],starname=starname,outputpath=outputpath,chunksize=chunksize)
        else:
            [t,f_t] = K2SFF.sff_fit(t,f_t,Xc,Yc,starname=starname,outputpath=outputpath,chunksize=chunksize)
    else:
        raise Exception('No valid method given.')

    T_Detrended = np.copy(t)
    Flux_Detrended = np.copy(f_t)

    np.savetxt(os.path.join(outputfolder, 'CentroidDetrended.txt'),np.transpose([t,f_t]),header='Time, Flux')
    [t,f_t] = centroidfit.clean_data(t,f_t) # do a bit of cleaning
    np.savetxt(os.path.join(outputfolder, 'Cleaned.txt'),np.transpose([t,f_t]),header='Time, Flux')

    T_Cleaned = np.copy(t)
    Flux_Cleaned = np.copy(f_t)

    pl.figure(figsize=(15,10))

    pl.subplot(3,1,1)
    pl.plot(T_Raw, Flux_Raw, "ko", MarkerSize=2)
    pl.ylabel("Flux Counts")
    pl.title("Raw Flux")

    pl.subplot(3,1,2)
    pl.plot(T_Detrended, Flux_Detrended, "ko", MarkerSize=2)
    pl.ylabel("Flux Counts")
    pl.title("Detrended Flux")

    pl.subplot(3,1,3)
    pl.plot(T_Cleaned, Flux_Cleaned, "ko", MarkerSize=2)
    pl.xlabel("Time (days)")
    pl.ylabel("Flux Counts")
    pl.title("Cleaned Flux")

    pl.suptitle(starname)
    pl.savefig(outputfolder+"/DiagnosticPlot.png")
    pl.close()
    del T_Raw, T_Detrended, T_Cleaned, Flux_Raw, Flux_Detrended, Flux_Cleaned
  else:
    [t,f_t] = np.loadtxt(os.path.join(outputfolder, 'CentroidDetrended.txt'),unpack=True,usecols=(0,1))

  if find_transits:
    folded,f_t_folded,period,freqlist,powers = periodfinder.get_period(t,f_t,outputpath=outputpath,starname=starname,get_mandelagolmodel=False)
    np.savetxt(os.path.join(outputfolder, 'PowerSpectrum.txt'),np.transpose([freqlist,powers]),header='Frequencies, Powers')
    periodfinder.make_combo_figure(filepath,t,f_t,period,freqlist,powers,starname=starname,outputpath=outputpath)

  TimeTaken = time.time() - InitialTime
  RecordFile = open(outputpath+"/RunSummary.csv","a")
  TimeTakenStr = "%.2f" %TimeTaken
  print "Time Taken::",TimeTakenStr
  RecordFile.write(TimeTakenStr+',')
  RecordFile.close()
  pl.close('all')
