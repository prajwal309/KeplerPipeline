'''
% Main pipeline file to generate K2 photometry starting from .fits pixel files downloaded from K2 MAST
% Author Vincent Van Eylen
% Contact vincent@phys.au.dk
% See Van Eylen et al. 2015 (ApJ) for details. Please reference this work if you found this code helpful!
'''

# general python files
import os
import matplotlib.pyplot as pl
import numpy as np

# pipeline files
import pixeltoflux
import centroidfit
import periodfinder
import re
from ExtractFlux import AdaptiveAperture, StandardAperture
from Detrender import Detrend


def run(filepath='',outputpath='',makelightcurve=True, find_transits=True,campaign=1,chunksize=300,cutoff_limit=2., method = 'Spitzer'):
  # Takes strings with the EPIC number of the star and input/outputpath. Campaign number is used to complete the correct filename as downloaded from MAST
  starname = re.search('[0-9]{9}',filepath).group(0)

  #handling spd vs lpd
  if "spd" in filepath:
      outputfolder = os.path.join(outputpath,str(starname)+"_spd")
  else:
      outputfolder = os.path.join(outputpath,str(starname))

  if makelightcurve:
    # makes raw light curve from pixel file

    #t,f_t,Xc,Yc = pixeltoflux.gotoflux(filepath,outputpath=outputpath,campaign=campaign,cutoff_limit=cutoff_limit)

    t,f_t,Xc,Yc = StandardAperture(filepath,outputpath=outputpath,campaign=campaign,plot=False)
    # removes outlying data points where thrusters are fired
    t,f_t,Xc,Yc = centroidfit.find_thruster_events(t,f_t,Xc,Yc,starname=starname,outputpath=outputfolder)

    # now fit a polynomial to the data (inspired by Spitzer data reduction), ignore first data points which are not usually very high-quality
    if method == 'Spitzer':
        [t,f_t] = centroidfit.spitzer_fit(t[90:],f_t[90:],Xc[90:],Yc[90:],starname=starname,outputpath=outputpath,chunksize=chunksize)
    elif method == 'SFF':
        [t,f_t] = centroidfit.sff_fit(t[90:],f_t[90:],Xc[90:],Yc[90:],starname=starname,outputpath=outputpath,chunksize=chunksize)
    else:
        print 'No valid method given. Using Spitzer Polynomial Correction'
        [t,f_t] = centroidfit.spitzer_fit(t[90:],f_t[90:],Xc[90:],Yc[90:],starname=starname,outputpath=outputpath,chunksize=chunksize)


    [t,f_t] = centroidfit.clean_data(t,f_t) # do a bit of cleaning

    outputlightcurvefolder = os.path.join(outputfolder,'lcs/') # one may want to put the LCs in a different folder e.g. to keep all together
    if not os.path.exists(outputlightcurvefolder):
      os.makedirs(outputlightcurvefolder)
    np.savetxt(os.path.join(outputlightcurvefolder, 'centroiddetrended_lightcurve_' + str(starname) + '.txt'),np.transpose([t,f_t]),header='Time, Flux')
  else:
    outputlightcurvefolder = os.path.join(os.path.join(outputpath,str(starname)),'lcs')
    [t,f_t] = np.loadtxt(os.path.join(outputlightcurvefolder, 'centroiddetrended_lightcurve_' + str(starname) + '.txt'),unpack=True,usecols=(0,1))


  if find_transits:
    folded,f_t_folded,period,freqlist,powers = periodfinder.get_period(t,f_t,outputpath=outputpath,starname=starname,get_mandelagolmodel=False)
    np.savetxt(os.path.join(outputfolder, 'powerspectrum_' + str(starname) + '.txt'),np.transpose([freqlist,powers]),header='Frequencies, Powers')
    periodfinder.make_combo_figure(filepath,t,f_t,period,freqlist,powers,starname=starname,outputpath=outputpath)
  #pl.show() # comment out to keep things running for multiple stars
  pl.close('all')