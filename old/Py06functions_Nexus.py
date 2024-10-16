"""
SOME FUNCTIONS WERE EXTRACTED FROM PY16PROGS.PY (DATA ANALYSIS FOR I16) CREATED BY DAN PORTER, MAINLY FUNCTIONS TO READ THE DATA AND METADATA
(SUCH AS READ_DAT_FILE AND READSCAN), AND THE CHECKSCAN FUNCTION WAS MODIFIED ACCORDINGLY TO THE NEEDS OF I06 DATA;

THE OTHER FUNCTIONS WERE CREATED BY LARISSA ISHIBE-VEIGA WITH HELP FROM DIRK BACKES
THE HYSTERESIS FUNCTION WAS CREATED BY DIRK BACKES IN MATLAB AND ADAPTED IN PYTHON BY LARISSA ISHIBE-VEIGA


Version 1.3

Last updated: 23/02/22

Version History:

18/01/2021 v. 1.0 - Py06functions created from previous scripts of Larissa I Veiga
19/01/2021 - 12/03/2021 - v .1.1 - Inclusion and modification of most of the functions (calc_XMCD, calc_XMCD_pairs,calc_XMLD, calc_XMLD_pairs, plotXMCD, plotXAS, plot_XAS_la,). A log of changes performed in the functions was not kept and the changes were done throughout the beamtimes during this period (the scripts were adapted/created in a daily basis dependending on the nature of the measurements); 
15/03/2021 - v 1.2 - inclusion of fieldx and fieldy in checkscans(). Implementation of max_min_energy() to be used as the energy array to interpolate the zacscan signal. 
8/12/2021 - v 1.3 - implement reading Nexus files
16/02/2022 - v. 1.4 - functions from Py06functions all renamed to "previousname_Nexus" and all of them were adapted to read the nexus files accordingly. All functions can know deal with data from Magnet, XABS and DD except 'calc_XMLD_Hxy_Nexus' and 'hysteresis_Nexus' which needs magnetic field and hence only work when using the Magnet endstation.
23/02/2022 - v. 1.5 - 'read_Nexus_file' function adapted to also read other data rather than only zacscans; Py06functions.py changed to Py06functions_Nexus.py.

"""

from __future__ import print_function
import sys, os
import glob  # find files
import re  # regular expressions
import datetime  # Dates and times
from matplotlib import dates
import time  # For timing
import tempfile  # Find system temp directory
import numpy as np
import h5py  # read hdf5 files such as nexus (.nxs)
import matplotlib.pyplot as plt  # Plotting
import matplotlib.ticker as mtick  # formatting of tick labels
from matplotlib.colors import LogNorm  # logarithmic colormaps
from mpl_toolkits.mplot3d import Axes3D  # 3D plotting
from scipy.optimize import curve_fit  # Peak fitting
from scipy.signal import convolve
from itertools import product
from collections import OrderedDict
from lmfit.models import ConstantModel, VoigtModel, Pearson7Model, GaussianModel, LorentzianModel, LinearModel, \
    ExpressionModel, PolynomialModel, ExponentialModel, StepModel, LinearModel, QuadraticModel, DampedOscillatorModel
from scipy.interpolate import interp1d
from numpy import array, linspace, arange, zeros, ceil, amax, amin, argmax, argmin, abs
from numpy.linalg import norm

"-----------------------Default Experiment Directory----------------------"
# Variable filedir is called from the namespace and can be changed at any
# time,even once the module has been imported, if you change it in the current namespace

filedir = '/dls/i06-1/data/2021/cm28167-5/'
savedir = '/home/arb83176/Jupyter_notebooks/2021/'

"-----------------------------Data file format----------------------------"
datfile_format = '%d.dat'
nxsfile_format = 'i06-1-%i.nxs'


def read_Nexus_file(filename):
    """
    Reads #####.nxs files from instrument, returns class instance containing all data
    Input:
      filename = string filename of data file
    Output:
      d = class instance with parameters associated to scanned values in the data file, plus:
         d.metadata - class containing all metadata from datafile
         d.keys() - returns all parameter names
         d.values() - returns all parameter values
         d.items() - returns parameter (name,value) tuples
    """

    hf = h5py.File(filename, 'r')
    # Read metadata
    meta = OrderedDict()
    d1 = hf['entry']['instrument']
    d2 = hf['entry']['diamond_scan']

    meta['command'] = d2['scan_command'][()].decode('UTF-8')
    # meta['cmd']             = d2['scan_command'][()].decode('UTF-8').split()[:2]
    meta['date'] = d2['start_time'][()].decode('UTF-8')
    meta['pola'] = d1['id']['polarisation'][()].decode('UTF-8')
    meta['insertion_device'] = d1['id']['source_mode'][()].decode('UTF-8')
    meta['idutrp'] = d1['id']['idu']['trp'][()]
    meta['idugap'] = d1['id']['idu']['gap'][()]
    meta['idu_la_angle'] = d1['id']['idu']['la_angle'][()]
    meta['iddtrp'] = d1['id']['idd']['trp'][()]
    meta['iddgap'] = d1['id']['idd']['gap'][()]
    meta['idd_la_angle'] = d1['id']['idd']['la_angle'][()]
    meta['endstation'] = d1['name'][()].decode('UTF-8')
    meta['energy'] = d1['pgm']['energy'][()]  # energy metadata added
    meta['current'] = d1['source']['current'][()]  # ringcurrent metadata added
    meta['EC1'] = d1['EC1']['temperature'][()]
    meta['OH1'] = d1['OH1']['temperature'][()]
    meta['xbpm1x'] = d1['xbpm1']['x'][()]
    meta['xbpm1y'] = d1['xbpm1']['y'][()]
    meta['xbpm2x'] = d1['xbpm2']['x'][()]
    meta['xbpm2y'] = d1['xbpm2']['y'][()]
    meta['m7pitch'] = d1['m7']['pitch'][()]
    if meta['endstation'] == 'Magnet':
        meta['magx'] = d1['scm']['field_x'][()]
        meta['magy'] = d1['scm']['field_y'][()]
        meta['magz'] = d1['scm']['field_z'][()]
        meta['scmy'] = d1['scm']['y'][()]
        meta['scmth'] = d1['scm']['theta'][()]
        meta['Tsample_mag'] = d1['scm']['T_sample'][()]
        meta['gain'] = d1['scm']['amp_1_gain'][()]
    if meta['endstation'] == 'XABS':
        meta['gain'] = d1['xabs']['amp_1_gain'][()]
        meta['xabsx'] = d1['xabs']['x'][()]
        meta['xabsy'] = d1['xabs']['y'][()]
        meta['xabstheta'] = d1['xabs']['theta'][()]
    if meta['endstation'] == 'DD':
        meta['gain'] = d1['ddiff']['amp_1_gain'][()]
        meta['ddx'] = d1['ddiff']['x'][()]
        meta['ddy'] = d1['ddiff']['y'][()]
        meta['ddz'] = d1['ddiff']['z'][()]
        meta['ddth'] = d1['ddiff']['theta'][()]
        meta['dd2th'] = d1['ddiff']['2theta'][()]
        meta['dddy'] = d1['ddiff']['dddy'][()]
        meta['ddphi'] = d1['ddiff']['phi'][()]
        meta['ddchi'] = d1['ddiff']['chi'][()]
        meta['dd_T'] = d1['lakeshore336']['sample'][()]
        meta['dd_T_target'] = d1['lakeshore336']['demand'][()]

    #
    # add more metadata here
    #

    main = OrderedDict()
    main_list = list(d1)
    list_all = ['t', 'scmx', 'scmy', 'scmth', 'magx', 'magy', 'magz', 'xabsx', 'xabsy', 'xabstheta', 'ddth', 'dd2th',
                'ddchi', 'ddphi', 'dddy', 'ddx', 'ddy', 'ddz', 'ca61sr', 'ca62sr', 'ca63sr', 'ca64sr', 'ca65sr',
                'ca66sr', 'ca67sr', 'ca68sr', 'ca101', 'ca101sr']
    if 'fastEnergy' in main_list:
        main['fastEnergy'] = d1['fastEnergy']['value'][()]
        names = ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'idio', 'ifio', 'ifiofb', 'ifioft']
        for name in names:
            main[name] = d1['fesData'][name][()]
        names.insert(0, 'fastEnergy')

    ####------------------ Read other data rather than fast energy scans ---------------------####
    elif 'hyst2' in main_list:
        main['hyst2'] = d1['hyst2']['value'][()]
        names = ['denergyA', 'denergyB', 'detector1_A', 'detector1_B', 'detector2_A', 'detector2_B', 'detector3_A',
                 'detector3_B', 'ridio', 'rifio']
        for name in names:
            main[name] = d1['hyst2'][name][()]
        names.insert(0, 'hyst2')

    else:
        names = [element for element in main_list if element in list_all]
        # print(names)
        for name in names:
            main[name] = d1[name]['value'][()]

    # Convert to class instance
    d = dict2obj(main, order=names)
    d.metadata = dict2obj(meta)

    return d


# def read_Nexus_file(filename):
#    hf = h5py.File(filename, 'r')
#    d  = hf['entry']['instrument']
#
#    return(d)   ------> Can be deleted


def readscan_Nexus(num):
    if os.path.isdir(filedir) == False:
        print("I can't find the directory: {}".format(filedir))
        return None

    file = os.path.join(filedir, nxsfile_format % num)

    try:
        d = read_Nexus_file(file)
        # d = dnp.io.load(file,warn=False) # from SciSoftPi
    except:
        print("Scan {} doesn't exist or can't be read".format(num))
        return None
    return (d)


def max_min_energy_Nexus(scanlist):
    max_list = []
    min_list = []

    for scanno in scanlist:

        d = readscan_Nexus(scanno)
        m = d.metadata
        ks = d.keys()
        scan_type = m.command.split()[1]

        if scan_type != 'fastEnergy':
            continue

        energy1 = d.fastEnergy

        min_list.append(energy1.min())
        max_list.append(energy1.max())

    min_list = np.array(min_list)
    max_list = np.array(max_list)

    energy_min = min_list.max()
    energy_max = max_list.min()
    points = len(energy1)

    energy = np.linspace(energy_min, energy_max, points)

    return energy


def checkscan_Nexus(num=None):
    if os.path.isdir(filedir) == False:
        print("I can't find the directory: {}".format(filedir))
        return ''

    if num is None:
        print("Please provide a scan number")
        return

    # turn into array
    num = np.asarray(num).reshape(-1)

    "----------------Single run------------------"
    d = readscan_Nexus(num[0])
    if d is None:
        print("File does not exist!")
        return 'File does not exist!'
    m = d.metadata
    ks = d.keys()

    metakeys = list(m)

    if m.endstation == 'Magnet':
        fieldx = m.magx
        fieldy = m.magy
        fieldz = m.magz
        tmp = m.Tsample_mag
        rot = m.scmth
        y = m.scmy
        pitch = m.m7pitch

    # <---here add metadata for DD and XABS
    if m.endstation == 'XABS':
        fieldx = 0
        fieldy = 0
        fieldz = 0
        tmp = 300
        rot = m.xabstheta

    if m.endstation == 'DD':
        fieldx = 0
        fieldy = 0
        fieldz = 0
        tmp = m.dd_T
        rot = m.ddth

    cmd = m.command
    scan_type = cmd.split()[:2]

    if m.insertion_device == 'idu':
        rowphase = m.idutrp
        undulator = 'idu'
        laa = m.idu_la_angle
    else:
        rowphase = m.iddtrp
        undulator = 'idd'
        laa = m.idd_la_angle

    pola = m.pola

    # if pola not in ['pc','lh','nc','lv']:
    # pola = float(laa)

    if m.endstation == 'Magnet':

        if pola in ['pc', 'lh', 'nc', 'lv']:
            if (fieldx != 0 and fieldy == 0 and fieldz == 0):
                print('#%d, %s %s, %s, T=%5.1f K, rot=%5.2f deg, Hx=%5.1f T, scmy=%2.2f, m7pitch=%d, Taken on: %s ' % (
                num, scan_type[0], scan_type[1], pola, tmp, rot, fieldx, y, pitch, m.date))

            elif (fieldy != 0 and fieldx == 0 and fieldz == 0):
                print('#%d, %s %s, %s, T=%5.1f K, rot=%5.2f deg, Hy=%5.1f T, scmy=%2.2f, m7pitch=%d, Taken on: %s ' % (
                num, scan_type[0], scan_type[1], pola, tmp, rot, fieldy, y, pitch, m.date))

            elif (fieldz != 0 and fieldx == 0 and fieldy == 0):
                print('#%d, %s %s, %s, T=%5.1f K, rot=%5.2f deg, Hz=%5.1f T, scmy=%2.2f, m7pitch=%d, Taken on: %s ' % (
                num, scan_type[0], scan_type[1], pola, tmp, rot, fieldz, y, pitch, m.date))

            elif (fieldz == 0 and fieldx == 0 and fieldy == 0):
                print('#%d, %s %s, %s, T=%5.1f K, rot=%5.2f deg, Hxyz= 0 T, scmy=%2.2f, m7pitch=%d, Taken on: %s ' % (
                num, scan_type[0], scan_type[1], pola, tmp, rot, y, pitch, m.date))

            else:
                print(
                    '#%d, %s %s, %s, T=%5.1f K, rot=%5.2f deg,Hx=%5.1f T, Hy=%5.1f T, Hz=%5.1f T, scmy=%2.2f, m7pitch=%d, Taken on: %s ' % (
                    num, scan_type[0], scan_type[1], undulator, pola, tmp, rot, fieldx, fieldy, fieldz, y, pitch,
                    m.date))

        else:

            if (fieldx != 0 and fieldy == 0 and fieldz == 0):
                print(
                    '#%d, %s %s, laa=%5.0f, T=%5.1f K, rot=%5.2f deg, Hx=%5.1f T, scmy=%2.2f, m7pitch=%d, Taken on: %s ' % (
                    num, scan_type[0], scan_type[1], laa, tmp, rot, fieldx, y, pitch, m.date))

            elif (fieldy != 0 and fieldx == 0 and fieldz == 0):
                print(
                    '#%d, %s %s, laa=%5.0f, T=%5.1f K, rot=%5.2f deg, Hy=%5.1f T, scmy=%2.2f, m7pitch=%d, Taken on: %s ' % (
                    num, scan_type[0], scan_type[1], laa, tmp, rot, fieldy, y, pitch, m.date))

            elif (fieldz != 0 and fieldx == 0 and fieldy == 0):
                print(
                    '#%d, %s %s, laa=%5.0f, T=%5.1f K, rot=%5.2f deg, Hz=%5.1f T, scmy=%2.2f, m7pitch=%d, Taken on: %s ' % (
                    num, scan_type[0], scan_type[1], laa, tmp, rot, fieldz, y, pitch, m.date))

            elif (fieldz == 0 and fieldx == 0 and fieldy == 0):
                print(
                    '#%d, %s %s, laa=%5.0f, T=%5.1f K, rot=%5.2f deg, Hxyz= 0 T, scmy=%2.2f, m7pitch=%d, Taken on: %s ' % (
                    num, scan_type[0], scan_type[1], laa, tmp, rot, y, pitch, m.date))

            else:
                print(
                    '#%d, %s %s, laa=%5.0f, T=%5.1f K, rot=%5.2f deg,Hx=%5.1f T, Hy=%5.1f T, Hz=%5.1f T, scmy=%2.2f, m7pitch=%d, Taken on: %s ' % (
                    num, scan_type[0], scan_type[1], laa, tmp, rot, fieldx, fieldy, fieldz, y, pitch, m.date))

    if m.endstation in ['XABS', 'DD']:
        if pola in ['pc', 'lh', 'nc', 'lv']:
            print('#%d, %s %s, %s, pol=%s, T=%5.1f K, rot=%5.2f deg, H = 0 T, Taken on: %s ' % (
            num, scan_type[0], scan_type[1], undulator, pola, tmp, rot, m.date))
        else:
            print('#%d, %s %s, %s, laa=%s, T=%5.1f K, rot=%5.2f deg, H = 0 T, Taken on: %s ' % (
            num, scan_type[0], scan_type[1], undulator, laa, tmp, rot, m.date))


def checkscans_Nexus(numlist):
    """
    Get run number information of the numlist,  returns a string
    """
    for num in numlist:
        checkscan_Nexus(num)


class dict2obj(OrderedDict):
    "Convert dictionary object to class instance"

    def __init__(self, dictvals, order=None):
        # Initialise OrderedDict (not sure which of these is correct)
        super(dict2obj, self).__init__()
        # OrderedDict.__init__(self)

        if order is None:
            order = dictvals.keys()

        for name in order:
            setattr(self, name, dictvals[name])
            self.update({name: dictvals[name]})


def plotXAS_Nexus(scanlist, sample_name, mode='TEY', bkg_type='', post_edge_norm=False, save=False):
    """Plot XAS scans for different selection of pre-edge and post-edge analysis - it calls the max_min_energy function which defines the range of energy where all the zacscans will be interpolated ;

    Parameters
    ------------
    scanlist: list with scan numbers of zacscans (pc/nc/lh/lv)

    sample_name: add the name of the sample as string; e.g. 'Sample 1'

    mode: 'C1': drain current of TEY (without normalisation by I0)
          'C2': I0
          'C3': fluorescence yield without normalisation by I0 (front diode)
          'C4': fluorescence yield without normalisation by I0 (90 deg. diode)
          'C5': fluorescence yield without normalisation by I0 (front diode)
          'TEY': total electon yield (C1/C2, if not specified, this is the default)
          'TFY_f1': fluorescence yield (C3/C2, front diode)
          'TFY_90': fluorescence yield (C4/C2, 90 deg. diode)
          'TFY_f2': fluorescence yield (C5/C2, front diode)

    bkg_type: 'flat': subtracts a constant;
              'norm': normalises pre-edge to 1;
              'linear': fits the pre-edge by a linear curve and subtract it

    post-edge_norm: if True, normalises the post-edge to 1


    save: if True, saves the plot

    Returns
    --------
    Plot of XAS against energy
    """

    jump_list = []

    "Determining the energy range to be used as interpolation"

    energy = max_min_energy_Nexus(scanlist)

    "If using a LinearModel (lmfit) for background subtraction"
    background = LinearModel(prefix='back_')

    plt.figure()
    for scanno in scanlist:
        d = readscan_Nexus(scanno)
        m = d.metadata
        ks = d.keys()
        "Skip the scan that is not fastEnergy"

        scan_type = m.command.split()[1]

        if scan_type != 'fastEnergy':
            continue

        if m.insertion_device == 'idu':
            rowphase = m.idutrp
        else:
            rowphase = m.iddtrp

        if m.endstation == 'Magnet':
            fieldx = m.magx
            fieldy = m.magy
            fieldz = m.magz
            tmp = m.Tsample_mag
            rot = m.scmth
            pol = m.pola
        # <---here add metadata for DD and XABS
        if m.endstation == 'XABS':
            fieldx = 0
            fieldy = 0
            fieldz = 0
            tmp = 300
            rot = m.xabstheta
            pol = m.pola
        if m.endstation == 'DD':
            fieldx = 0
            fieldy = 0
            fieldz = 0
            tmp = m.dd_T
            rot = m.ddth
            pol = m.pola

        energy1 = d.fastEnergy

        if mode == 'C1':
            y = d.C1
            ylabel = 'C1 (arb. units)'

        elif mode == 'C2':
            y = d.C2
            ylabel = 'C2 (arb. units)'

        elif mode == 'C3':
            y = d.C3
            ylabel = 'C3 (arb. units)'

        elif mode == 'C4':
            y = d.C4
            ylabel = 'C4 (arb. units)'

        elif mode == 'C5':
            y = d.C5
            ylabel = 'C5 (arb. units)'

        elif mode == 'TEY':
            y = d.C1 / d.C2  # TEY data normalised by i0

        elif mode == 'TFY_f1':
            y = d.C3 / d.C2  # front diode data normalised by i0

        elif mode == 'TFY_f2':
            y = d.C4 / d.C2  # front diode data normalised by i0

        elif mode == 'TFY_90':
            y = d.C5 / d.C2

        else:
            y = d.C1 / d.C2

        ### interpolate ####
        f = interp1d(energy1, y, kind='linear')

        y = f(energy)

        # background type#

        if bkg_type == 'flat':
            "Subtracting the background by a constant"
            y -= y[energy < energy[0] + 5].mean()
            jump = y[energy > energy[-1] - 5].mean() - y[energy < energy[0] + 5].mean()
            jump_list.append(jump)

        if bkg_type == 'norm':
            "Simple normalisation of background to 1"
            y /= y[energy < energy[0] + 5].mean()  # nomalise by the average of a range of energy
            jump = y[energy > energy[-1] - 5].mean() - y[energy < energy[0] + 5].mean()
            jump_list.append(jump)

        if bkg_type == 'linear':
            "Subtracting the background by a linear curve fit "
            energy_back = energy[np.logical_and(energy > energy[0], energy < energy[0] + 5)]
            XAS_back = y[np.logical_and(energy > energy[0], energy < energy[0] + 5)]
            pars_back = background.guess(XAS_back, x=energy_back)

            out_back = background.fit(XAS_back, pars_back, x=energy_back)

            background_fit = background.eval(slope=out_back.params['back_slope'].value,
                                             intercept=out_back.params['back_intercept'].value, x=energy)

            y = y - background_fit
            jump = y[energy > energy[-1] - 5].mean()
            jump_list.append(jump)

        if bkg_type == None:
            y = y

        if post_edge_norm:
            if bkg_type == 'norm':
                y -= y[energy < energy[0] + 5].mean()
                jump = y[energy > energy[-1] - 5].mean()
                y /= jump
            else:

                y /= jump

        if pol == 'lh':
            plt.plot(energy, y, label='%d,%s' % (scanno, pol))

        if pol == 'nc':
            plt.plot(energy, y, label='%d,%s' % (scanno, pol))

        if pol == 'lv':
            plt.plot(energy, y, label='%d,%s' % (scanno, pol))

        if pol == 'pc':
            plt.plot(energy, y, label='%d,%s' % (scanno, pol))

    plt.legend(loc=0, frameon=False)
    plt.xlabel('Energy (eV)', fontsize=12)
    plt.tick_params(direction='in', labelsize=12)
    if mode in ['C1', 'C2', 'C3', 'C4', 'C5']:
        plt.ylabel(ylabel, fontsize=12)
        plt.ticklabel_format(axis='y', style='sci', scilimits=(0, 0))
        plt.suptitle(
            '#%d-#%d, %s, T=%5.2f K,\n'r'H$_x$=%5.1f T, H$_y$=%5.1f T, H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
            scanlist[0], scanlist[-1], sample_name, tmp, fieldx, fieldy, fieldz, rot), fontsize=12)
    else:
        plt.ylabel('XAS (arb. units)', fontsize=12)
        plt.suptitle(
            '#%d-#%d, %s, %s, T=%5.2f K,\n'r'H$_x$=%5.1f T, H$_y$=%5.1f T, H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
            scanlist[0], scanlist[-1], sample_name, mode, tmp, fieldx, fieldy, fieldz, rot), fontsize=12)

    if save:
        plt.savefig(savedir + 'figures/' + '%d-%d_%s_XAS.png' % (scanlist[0], scanlist[-1], sample_name))

    return energy, y


def calc_XMCD_Nexus(scanlist, sample_name, mode='TEY', bkg_type='', post_edge_norm=False, xmcd_norm=None, save=False):
    '''
    Basic XMCD data analysis -  it calls the max_min_energy function which defines the range of energy where all the pc and nc scans will be interpolated

    Parameters
    ------------
    scanlist: list with scan numbers (pc and nc scans)

    sample_name: add the name of the sample as string; e.g. 'Sample 1'

    mode: 'TEY': total electon yield (if not specified, this is the default)
          'TFY_f1': fluorescence yield (front diode)
          'TFY_90': fluorescence yield (90 deg. diode)
          'TFY_f2': fluorescence yield (front diode)

    bck_type: 'flat': subtracts a constant;
              'norm': normalises pre-edge to 1;
              'linear': fits the pre-edge by a linear curve and subtract it

    post-edge_norm: if True, normalises the post-edge to 1

    xmcd_norm: 'jump': divide the XMCD signal by the jump=post_edge-pre-edge value (XMCD plot will be showed in %)
               'peak': divide the XMCD by the max value of XAS(pc)+XAS(nc)/2; usually it's the L3 peak (XMCD plot will be showed in %)
                None : the XMCD will be displayed without any division (XMCD will be showed in arb. units)

    save: if True, saves the 2 plots and the .dat file with the calculated xas and xmcd (you need to save in order to use the function plot_XMCD)

    Returns
    --------
    en_final: averaged energy array
    xmcd: array with the XMCD spectra
    xmcd_std: array with XMCD propagated error

    Plots:
    1st Plot: left panel: normalised XAS spectra for pc polarisation
              right panel: normalised XAS spectra for nc polarisation

    2nd Plot: Upper panel: averaged XAS for pc/nc polarisation
              Lower panel: reulting XMCD spectra and its standard deviation

    '''

    y_pos = []
    y_neg = []
    pc_scans = []
    nc_scans = []
    jump_list = []

    "Determining the energy range to be used as interpolation"

    energy = max_min_energy_Nexus(scanlist)

    # print(energy)

    "If using a LinearModel (lmfit) for background subtraction"
    background = LinearModel(prefix='back_')

    ## getting initial information ##
    d = readscan_Nexus(scanlist[0])
    m = d.metadata
    ks = d.keys()

    if m.endstation == 'Magnet':
        tmp = m.Tsample_mag
        rot = m.scmth
        field = m.magz
    if m.endstation == 'XABS':
        tmp = 300
        rot = m.xabstheta
        field = 0

    if m.endstation == 'DD':
        tmp = m.dd_T
        rot = m.ddth
        field = 0

    plt.figure(figsize=(10, 5))
    plt.suptitle(r'#%d-#%d, %s, %s, T=%5.2f K, H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
    scanlist[0], scanlist[-1], sample_name, mode, tmp, field, rot), fontsize=14)
    ax0 = plt.subplot(1, 2, 1)
    ax1 = plt.subplot(1, 2, 2)

    for scanno in scanlist:

        d = readscan_Nexus(scanno)
        m = d.metadata
        ks = d.keys()

        "Skip the scan that is not fastEnergy"

        scan_type = m.command.split()[1]

        if scan_type != 'fastEnergy':
            continue

        if m.iddgap == 100:
            rowphase = m.idutrp
        else:
            rowphase = m.iddtrp

        if m.endstation == 'Magnet':
            field = m.magz
            tmp = m.Tsample_mag
            rot = m.scmth
            pol = m.pola

        # <---here add metadata for DD and XABS
        if m.endstation == 'XABS':
            field = 0
            tmp = 300
            rot = m.xabstheta
            pol = m.pola
        if m.endstation == 'DD':
            field = 0
            tmp = m.dd_T
            rot = m.ddth
            pol = m.pola

        energy1 = d.fastEnergy

        if mode == 'C1':
            y = d.C1

        elif mode == 'TEY':

            y = d.C1 / d.C2  # TEY data normalised by i0

        elif mode == 'TFY_f1':

            y = d.C3 / d.C2

        elif mode == 'TFY_f2':

            y = d.C4 / d.C2

        elif mode == 'TFY_90':

            y = d.C5 / d.C2

        else:
            # if mode is not specified, then it uses TEY

            mode == 'TEY'

            y = d.C1 / d.C2

        ### interpolate ####

        f = interp1d(energy1, y, kind='linear')

        y = f(energy)

        # background type#

        if bkg_type == 'flat':
            "Subtracting the background by a constant"

            y -= y[energy < energy[0] + 5].mean()
            jump = y[energy > energy[-1] - 5].mean() - y[energy < energy[0] + 5].mean()
            jump_list.append(jump)

        if bkg_type == 'norm':
            "Simple normalisation of background to 1"
            y /= y[energy < energy[0] + 5].mean()  # nomalise by the average of a range of energy
            jump = y[energy > energy[-1] - 5].mean() - y[energy < energy[0] + 5].mean()
            jump_list.append(jump)

        if bkg_type == 'linear':
            "Subtracting the background by a linear curve fit "
            energy_back = energy[np.logical_and(energy > energy[0], energy < energy[0] + 5)]
            XAS_back = y[np.logical_and(energy > energy[0], energy < energy[0] + 5)]
            pars_back = background.guess(XAS_back, x=energy_back)

            out_back = background.fit(XAS_back, pars_back, x=energy_back)

            background_fit = background.eval(slope=out_back.params['back_slope'].value,
                                             intercept=out_back.params['back_intercept'].value, x=energy)

            y = y - background_fit
            jump = y[energy > energy[-1] - 5].mean()
            jump_list.append(jump)

        if bkg_type == None:
            y = y

        if post_edge_norm:
            if bkg_type == 'norm':
                y -= y[energy < energy[0] + 5].mean()
                jump = y[energy > energy[-1] - 5].mean()
                y /= jump
            else:

                y /= jump

        if pol == 'pc':
            y_pos.append(y)
            pc_scans.append(scanno)

            "plotting positive polarisation"
            ax0.plot(energy, y, label='%d' % scanno)
            # ax0.plot(energy,y-background_fit,label='%d'%scanno)
            ax0.legend(loc=0, frameon=False)
            ax0.set_title('pol=%s' % (pol), fontsize=14)

        if pol == 'nc':
            y_neg.append(y)
            nc_scans.append(scanno)

            "plotting positive polarisation"
            ax1.plot(energy, y, label='%d' % scanno)
            # ax1.plot(energy,y-background_fit,label='%d'%scanno)
            # ax1.plot(energy,background_fit,'--',color='black')
            ax1.legend(loc=0, frameon=False)
            ax1.set_title('pol=%s' % (pol), fontsize=14)

    ax0.set_xlabel('Energy (eV)', fontsize=14)
    ax0.set_ylabel('XAS (arb. units)', fontsize=14)
    ax0.tick_params(direction='in', labelsize=14)

    ax1.set_xlabel('Energy (eV)', fontsize=14)
    ax1.set_ylabel('XAS (arb. units)', fontsize=14)
    ax1.tick_params(direction='in', labelsize=14)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    if save:
        plt.savefig(savedir + 'figures/' + '%d-%d_%s_XAS.png' % (scanlist[0], scanlist[-1], mode))

    pos_y_std = np.std(y_pos, axis=0)
    pos_y = np.mean(y_pos, axis=0)

    neg_y_std = np.std(y_neg, axis=0)
    neg_y = np.mean(y_neg, axis=0)

    y_mean = np.mean([pos_y, neg_y], axis=0)
    y_mean_std = np.std([pos_y, neg_y], axis=0)
    # print(jump_list)
    jump_final = np.mean(jump_list)
    # print(jump_final)
    # print(TEY_mean[energy>energy[-1]-5].mean()-TEY_mean[energy<energy[0]+5].mean())

    if xmcd_norm == 'jump':

        xmcd = 100 * (1 / jump_final) * (-pos_y + neg_y)
        xmcd_std = 100 * (1 / jump_final) * np.sqrt(neg_y_std ** 2 + pos_y_std ** 2)

    elif xmcd_norm == 'peak':
        if (bkg_type == 'norm' or bkg_type == None):
            peak = y_mean.max() - y_mean[energy < energy[0] + 5].mean()

        else:
            peak = y_mean.max()

        xmcd = 100 * (-pos_y + neg_y) / peak
        xmcd_std = 100 * (1 / peak) * np.sqrt(neg_y_std ** 2 + pos_y_std ** 2)


    else:
        xmcd = -pos_y + neg_y
        xmcd_std = np.sqrt(neg_y_std ** 2 + pos_y_std ** 2)

    plt.figure()
    ax = plt.subplot(2, 1, 1)
    ax.plot(energy, pos_y, label='pc')
    ax.plot(energy, neg_y, label='nc')
    ax.legend(loc=0, frameon=False, fontsize=14)
    ax.set_ylabel('XAS (arb. units)', fontsize=14)
    ax.tick_params(direction='in', labelbottom=False, right=True, labelsize=14)
    ax.set_title(r'#%d-#%d, %s, XMCD, %s, T=%5.2f K, H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
    scanlist[0], scanlist[-1], sample_name, mode, tmp, field, rot), fontsize=10)

    ax_1 = plt.subplot(2, 1, 2)
    ax_1.errorbar(energy, xmcd, xmcd_std, alpha=0.1)
    ax_1.errorbar(energy, xmcd, lw=3, color='C0', label='nc-pc')
    ax_1.set_xlabel('Energy (eV)', fontsize=14)
    if xmcd_norm is None:
        ax_1.set_ylabel('XMCD (arb. units)', fontsize=14)
    else:
        ax_1.set_ylabel('XMCD (%)', fontsize=14)
    ax_1.legend(loc=0, frameon=False, fontsize=14)

    ax_1.tick_params(direction='in', top=True, right=True, labelsize=14)

    plt.tight_layout()

    if save:
        plt.savefig(savedir + 'figures/' + '%d-%d_%s_XMCD.png' % (scanlist[0], scanlist[-1], mode))

        txt = savedir + 'data/' + '%d-%d_%s_XMCD_results.dat' % (scanlist[0], scanlist[-1], mode)
        f = open(txt, 'w')
        f.write('# Processing parameters:\n')
        f.write('# pc scans = %s\n' % (pc_scans))
        f.write('# nc scans = %s\n' % (nc_scans))
        f.write(
            '# mode = %s; background type = %s, post-edge normalisation to 1 = %s, xmcd signal normalisation = %s  \n' % (
            mode, bkg_type, post_edge_norm, xmcd_norm))

        f.write('Energy[eV]   XAS_pc  XAS_pc_std XAS_nc  XAS_nc_std  XAS_avg   XAS_avg_std  XMCD  XMCD_std\n')
        for m in range(len(energy)):
            help = '{:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f}\n'
            f.write(help.format(energy[m], pos_y[m], pos_y_std[m], neg_y[m], neg_y_std[m], y_mean[m], y_mean_std[m],
                                xmcd[m], xmcd_std[m]))
        f.close()

    return energy, xmcd, xmcd_std


def calc_XMCD_pairs_Nexus(scanlist, sample_name, mode='TEY', bkg_type='', post_edge_norm=False, xmcd_norm=None,
                          save=False):
    '''
    Basic XMCD data analysis of consecute pc/nc pairs - it calls the max_min_energy function which defines the range of energy where all the pc and nc scans will be interpolated

    Parameters
    ------------
    scanlist: list with scan numbers (pc and nc scans)

    sample_name: add the name of the sample as string; e.g. 'Sample 1'

    mode: 'TEY': total electon yield (if not specified, this is the default)
          'TFY_f1': fluorescence yield (front diode)
          'TFY_90': fluorescence yield (90 deg. diode)
          'TFY_f2': fluorescence yield (front diode)

    bck_type: 'flat': subtracts a constant;
              'norm': normalises pre-edge to 1;
              'linear': fits the pre-edge by a linear curve and subtract it

    post-edge_norm: if True, normalises the post-edge to 1


    save: if True, saves the 2 plots and the .dat file with the calculated xas and xmcd (you need to save in order to use the function plot_XMCD)

    Returns
    --------
    en_final: averaged energy array
    xmcd: array with the XMCD spectra
    xmcd_std: array with XMCD propagated error

    Plots:
    1st Plot: left panel: normalised XAS spectra for pc polarisation
              right panel: normalised XAS spectra for nc polarisation

    2nd Plot: Upper panel: averaged XAS for pc/nc polarisation
              Lower panel: reulting XMCD spectra and its standard deviation

    '''

    y_pos = []
    y_neg = []
    jump_list = []
    scans_pos = []
    scans_neg = []

    "Determining the energy range to be used as interpolation"

    energy = max_min_energy_Nexus(scanlist)

    "If using a LinearModel (lmfit) for background subtraction"
    background = LinearModel(prefix='back_')

    ## getting initial information ##
    d = readscan_Nexus(scanlist[0])
    m = d.metadata
    ks = d.keys()

    if mode is None:
        mode = 'TEY'

    for scanno in scanlist:

        d = readscan_Nexus(scanno)
        m = d.metadata
        ks = d.keys()
        if m.iddgap == 100:
            rowphase = m.idutrp
        else:
            rowphase = m.iddtrp

        "Skip the scan that is not fastEnergy"

        scan_type = m.command.split()[1]

        if scan_type != 'fastEnergy':
            continue

        if m.endstation == 'Magnet':
            field = m.magz
            tmp = m.Tsample_mag
            rot = m.scmth
            pol = m.pola

        # <---here add metadata for DD and XABS
        if m.endstation == 'XABS':
            field = 0
            tmp = 300
            rot = m.xabstheta
            pol = m.pola
        if m.endstation == 'DD':
            field = 0
            tmp = m.dd_T
            rot = m.ddth
            pol = m.pola

        energy1 = d.fastEnergy

        if mode == 'TEY':

            y = d.C1 / d.C2  # TEY data normalised by i0

        elif mode == 'TFY_f1':

            y = d.C3 / d.C2

        elif mode == 'TFY_f2':

            y = d.C4 / d.C2

        elif mode == 'TFY_90':

            y = d.C5 / d.C2

        else:

            y = d.C1 / d.C2

        ### interpolate ####
        f = interp1d(energy1, y, kind='linear')

        y = f(energy)

        # background type#

        if bkg_type == 'flat':
            "Subtracting the background by a constant"

            y -= y[energy < energy[0] + 5].mean()
            jump = y[energy > energy[-1] - 5].mean() - y[energy < energy[0] + 5].mean()
            jump_list.append(jump)

        if bkg_type == 'norm':
            "Simple normalisation of background to 1"
            y /= y[energy < energy[0] + 5].mean()  # nomalise by the average of a range of energy
            jump = y[energy > energy[-1] - 5].mean() - y[energy < energy[0] + 5].mean()
            jump_list.append(jump)

        if bkg_type == 'linear':
            "Subtracting the background by a linear curve fit "
            energy_back = energy[np.logical_and(energy > energy[0], energy < energy[0] + 5)]
            XAS_back = y[np.logical_and(energy > energy[0], energy < energy[0] + 5)]
            pars_back = background.guess(XAS_back, x=energy_back)

            out_back = background.fit(XAS_back, pars_back, x=energy_back)

            background_fit = background.eval(slope=out_back.params['back_slope'].value,
                                             intercept=out_back.params['back_intercept'].value, x=energy)

            y = y - background_fit
            jump = y[energy > energy[-1] - 5].mean()
            jump_list.append(jump)

        if bkg_type == None:
            y = y

        if post_edge_norm:
            if bkg_type == 'norm':
                y -= y[energy < energy[0] + 5].mean()
                jump = y[energy > energy[-1] - 5].mean()
                y /= jump
            else:

                y /= jump

        if pol == 'pc':
            y_pos.append(y)
            # en_pos.append(energy)
            scans_pos.append(scanno)

        if pol == 'nc':
            y_neg.append(y)
            # en_neg.append(energy)
            scans_neg.append(scanno)

    print('pos_scans = ' + str(scans_pos))
    print('neg_scans = ' + str(scans_neg))
    pos_y = np.array(y_pos)
    # pos_en = np.array(en_pos)

    neg_y = np.array(y_neg)
    # neg_en = np.array(en_neg)

    xmcd_list = []
    xmcd_std_list = []
    en_final_list = []

    for i, j in zip(range(len(pos_y)), range(len(neg_y))):
        plt.figure()
        ax = plt.subplot(2, 1, 1)
        ax.plot(energy, pos_y[i], label='%d - pc' % scans_pos[i])
        ax.plot(energy, neg_y[j], label='%d - nc' % scans_neg[i])
        ax.legend(loc=0, frameon=False, fontsize=14)
        ax.set_ylabel('XAS (arb. units)', fontsize=14)
        ax.tick_params(direction='in', labelbottom=False, right=True, labelsize=14)
        ax.set_title(r'#%d-#%d, %s, XMCD, %s, T=%5.2f K, H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
        scans_pos[i], scans_neg[j], sample_name, mode, tmp, field, rot), fontsize=12)

        # en_final = np.mean([pos_en[i],neg_en[j]],axis=0)
        # en_final_list.append(en_final)
        y_mean = np.mean([pos_y[i], neg_y[j]], axis=0)
        y_mean_std = np.std([pos_y[i], neg_y[j]], axis=0)

        if xmcd_norm == 'jump':
            jump_final = y_mean[energy > energy[-1] - 5].mean() - y_mean[energy < energy[0] + 5].mean()
            xmcd = 100 * (1 / jump_final) * (-pos_y[i] + neg_y[j])
            xmcd_std = 100 * (1 / jump_final) * np.std([pos_y[i], neg_y[j]], axis=0)
            xmcd_list.append(xmcd)
            xmcd_std_list.append(xmcd_std)

        elif xmcd_norm == 'peak':
            if bkg_type == 'norm':
                peak = y_mean.max() - y_mean[energy < energy[0] + 5].mean()

            else:
                peak = y_mean.max()

            xmcd = 100 * (-pos_y[i] + neg_y[j]) / peak
            xmcd_std = 100 * (1 / peak) * np.std([pos_y[i], neg_y[j]], axis=0)
            xmcd_list.append(xmcd)
            xmcd_std_list.append(xmcd_std)

        else:
            xmcd = -pos_y[i] + neg_y[j]
            xmcd_std = np.std([pos_y[i], neg_y[j]], axis=0)
            xmcd_list.append(xmcd)
            xmcd_std_list.append(xmcd_std)

        ax_1 = plt.subplot(2, 1, 2)
        ax_1.errorbar(energy, xmcd, xmcd_std, alpha=0.3)
        ax_1.errorbar(energy, xmcd, lw=3, color='C0', label='nc-pc')
        ax_1.set_xlabel('Energy (eV)', fontsize=14)
        ax_1.set_ylabel('XMCD (arb. units)', fontsize=14)
        ax_1.legend(loc=0, frameon=False, fontsize=14)

        ax_1.tick_params(direction='in', top=True, right=True, labelsize=14)

        plt.tight_layout()

        if save:
            # plt.savefig(savedir+'figures/'+'%d-%d_%s_XMCD.png'%(scanlist[0],scanlist[-1],mode))

            txt = savedir + 'data/' + '%d-%d_%s_XMCD_results_pairs.dat' % (scans_pos[i], scans_neg[j], mode)
            f = open(txt, 'w')
            f.write('# Processing parameters:\n')
            f.write('# pc scans = %s\n' % (pc_scans))
            f.write('# nc scans = %s\n' % (nc_scans))
            f.write(
                '# mode = %s; background type = %s, post-edge normalisation to 1 = %s, xmcd signal normalisation = %s  \n' % (
                mode, bkg_type, post_edge_norm, xmcd_norm))
            f.write('Energy[eV]   XAS_pc  XAS_nc   XAS_avg  XAS_avg_std  XMCD  XMCD_std\n')
            for m in range(len(energy)):
                help = '{:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f}\n'
                f.write(
                    help.format(energy[m], pos_y[i][m], neg_y[j][m], y_mean[m], y_mean_std[m], xmcd[m], xmcd_std[m]))
            f.close()

    return energy, xmcd_list, scans_pos, scans_neg


def calc_XMLD_Nexus(scanlist, sample_name, mode='TEY', bkg_type='', post_edge_norm=False, xmld_norm=None, save=False):
    '''
    Basic XMLD data analysis for LH and LV (not for an arbitrary linear polarisation) - it calls the max_min_energy function which defines the range of energy where all the lh and lv scans will be interpolated

    Parameters
    ------------
    scanlist: list with scan numbers (pc and nc scans)

    sample_name: add the name of the sample as string; e.g. 'Sample 1'

    mode: 'TEY': total electon yield (if not specified, this is the default)
          'TFY_f1': fluorescence yield (front diode)
          'TFY_90': fluorescence yield (90 deg. diode)
          'TFY_f2': fluorescence yield (front diode)

    bck_type: 'flat': subtracts a constant;
              'norm': normalises pre-edge to 1;
              'linear': fits the pre-edge by a linear curve and subtract it

    post-edge_norm: if True, normalises the post-edge to 1

    xmld_norm: 'jump': divide the XMLD signal by the jump=post_edge-pre-edge value (XMLD plot will be showed in %)
               'peak': divide the XMLD by the max value of XAS(lh)+XAS(lv)/2; usually it's the L3 peak (XMLD plot will be showed in %)
                None : the XMLD will be displayed without any division (XMLD will be showed in arb. units)

    save: if True, saves the 2 plots and the .dat file with the calculated xas and xmcd (you need to save in order to use the function plot_XMLD)

    Returns
    --------
    en_final: averaged energy array
    xmcd: array with the XMLD spectra
    xmcd_std: array with XMLD propagated error

    Plots:
    1st Plot: left panel: normalised XAS spectra for pc polarisation
              right panel: normalised XAS spectra for nc polarisation

    2nd Plot: Upper panel: averaged XAS for pc/nc polarisation
              Lower panel: reulting XMLD spectra and its standard deviation

    '''

    y_lh = []
    y_lv = []
    lh_scans = []
    lv_scans = []
    jump_list = []

    "Determining the energy range to be used as interpolation"

    energy = max_min_energy_Nexus(scanlist)

    "If using a LinearModel (lmfit) for background subtraction"
    background = LinearModel(prefix='back_')

    ## getting initial information ##
    d = readscan_Nexus(scanlist[0])
    m = d.metadata
    ks = d.keys()

    plt.figure(figsize=(10, 5))

    if m.endstation == 'Magnet':
        tmp = m.Tsample_mag
        rot = m.scmth
        fieldz = m.magz
        fieldx = m.magx
        fieldy = m.magy

        if (fieldx != 0 and fieldy == 0):
            plt.suptitle(r'#%d-#%d, %s, %s, T=%5.2f K, H$_x$=%5.1f T, H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
            scanlist[0], scanlist[-1], sample_name, mode, tmp, fieldx, fieldz, rot), fontsize=14)
        elif (fieldx == 0 and fieldy != 0):
            plt.suptitle(r'#%d-#%d, %s, %s, T=%5.2f K, H$_y$=%5.1f T, H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
            scanlist[0], scanlist[-1], sample_name, mode, tmp, fieldy, fieldz, rot), fontsize=14)
        elif (fieldx == 0 and fieldy == 0):
            plt.suptitle(r'#%d-#%d, %s, %s, T=%5.2f K, H$_{xy}$=%5.1f T, H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
            scanlist[0], scanlist[-1], sample_name, mode, tmp, fieldx, fieldz, rot), fontsize=14)
        else:
            plt.suptitle(
                r'#%d-#%d, %s, %s, T=%5.2f K, H$_x$=%5.1f T, H$_y$=%5.1f T, H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
                scanlist[0], scanlist[-1], sample_name, mode, tmp, fieldx, fieldy, fieldz, rot), fontsize=14)

    if m.endstation == 'XABS':
        tmp = 300
        rot = m.xabstheta
        field = 0

        plt.suptitle(r'#%d-#%d, %s, %s, T=%5.2f K, H = 0 T, $\theta=%5.1f^{\circ}$' % (
        scanlist[0], scanlist[-1], sample_name, mode, tmp, rot), fontsize=14)

    if m.endstation == 'DD':
        tmp = m.dd_T
        rot = m.ddth
        field = 0

        plt.suptitle(r'#%d-#%d, %s, %s, T=%5.2f K, H = 0 T, $\theta=%5.1f^{\circ}$' % (
        scanlist[0], scanlist[-1], sample_name, mode, tmp, rot), fontsize=14)

    if mode is None:
        mode = 'TEY'

    ax0 = plt.subplot(1, 2, 1)
    ax1 = plt.subplot(1, 2, 2)

    for scanno in scanlist:

        d = readscan_Nexus(scanno)
        m = d.metadata
        ks = d.keys()

        if m.iddgap == 100:
            rowphase = m.idutrp
        else:
            rowphase = m.iddtrp

        "Skip the scan that is not fastEnergy"

        scan_type = m.command.split()[1]

        if scan_type != 'fastEnergy':
            continue

        if m.endstation == 'Magnet':
            tmp = m.Tsample_mag
            rot = m.scmth
            fieldz = m.magz
            fieldx = m.magx
            fieldy = m.magy
            pol = m.pola

        if m.endstation == 'XABS':
            tmp = 300
            rot = m.xabstheta
            field = 0
            pol = m.pola

        if m.endstation == 'DD':
            tmp = m.dd_T
            rot = m.ddth
            field = 0
            pol = m.pola

        energy1 = d.fastEnergy

        if mode == 'TEY':

            y = d.C1 / d.C2  # TEY data normalised by i0

        elif mode == 'TFY_f1':

            y = d.C3 / d.C2

        elif mode == 'TFY_f2':

            y = d.C4 / d.C2

        elif mode == 'TFY_90':

            y = d.C5 / d.C2

        elif mode == 'TFY_f3':

            y = d.C6 / d.C2

        else:

            y = d.C1 / d.C2

        ### interpolate ####
        f = interp1d(energy1, y, kind='linear')

        y = f(energy)

        # background type#

        if bkg_type == 'flat':
            "Subtracting the background by a constant"

            y -= y[energy < energy[0] + 5].mean()
            jump = y[energy > energy[-1] - 5].mean() - y[energy < energy[0] + 5].mean()
            jump_list.append(jump)

        if bkg_type == 'norm':
            "Simple normalisation of background to 1"
            y /= y[energy < energy[0] + 5].mean()  # nomalise by the average of a range of energy
            jump = y[energy > energy[-1] - 5].mean() - y[energy < energy[0] + 5].mean()
            jump_list.append(jump)

        if bkg_type == 'linear':
            "Subtracting the background by a linear curve fit "
            energy_back = energy[np.logical_and(energy > energy[0], energy < energy[0] + 5)]
            XAS_back = y[np.logical_and(energy > energy[0], energy < energy[0] + 5)]
            pars_back = background.guess(XAS_back, x=energy_back)

            out_back = background.fit(XAS_back, pars_back, x=energy_back)

            background_fit = background.eval(slope=out_back.params['back_slope'].value,
                                             intercept=out_back.params['back_intercept'].value, x=energy)

            y = y - background_fit
            jump = y[energy > energy[-1] - 5].mean()
            jump_list.append(jump)

        if bkg_type == None:
            y = y

        if post_edge_norm:
            if bkg_type == 'norm':
                y -= y[energy < energy[0] + 5].mean()
                jump = y[energy > energy[-1] - 5].mean()
                # print(jump)

                y /= jump
            else:
                # print(jump)
                y /= jump

        if pol == 'lh':
            y_lh.append(y)
            lh_scans.append(scanno)

            "plotting positive polarisation"
            ax0.plot(energy, y, label='%d' % scanno)
            # ax0.plot(energy,y-background_fit,label='%d'%scanno)
            ax0.legend(loc=0, frameon=False)
            ax0.set_title('pol=%s' % (pol), fontsize=14)

        if pol == 'lv':
            y_lv.append(y)
            lv_scans.append(scanno)

            "plotting positive polarisation"
            ax1.plot(energy, y, label='%d' % scanno)
            # ax1.plot(energy,y-background_fit,label='%d'%scanno)
            # ax1.plot(energy,background_fit,'--',color='black')
            ax1.legend(loc=0, frameon=False)
            ax1.set_title('pol=%s' % (pol), fontsize=14)

    ax0.set_xlabel('Energy (eV)', fontsize=14)
    ax0.set_ylabel('XAS (arb. units)', fontsize=14)
    ax0.tick_params(direction='in', labelsize=14)

    ax1.set_xlabel('Energy (eV)', fontsize=14)
    ax1.set_ylabel('XAS (arb. units)', fontsize=14)
    ax1.tick_params(direction='in', labelsize=14)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    if save:
        plt.savefig(savedir + 'figures/' + '%d-%d_%s_XAS.png' % (scanlist[0], scanlist[-1], mode))

    lh_y_std = np.std(y_lh, axis=0)
    lh_y = np.mean(y_lh, axis=0)

    lv_y_std = np.std(y_lv, axis=0)
    lv_y = np.mean(y_lv, axis=0)

    y_mean = np.mean([lh_y, lv_y], axis=0)
    y_mean_std = np.std([lh_y, lv_y], axis=0)
    # print(jump_list)
    jump_final = np.mean(jump_list)
    # print(jump_final)
    # print(TEY_mean[energy>energy[-1]-5].mean()-TEY_mean[energy<energy[0]+5].mean())

    if xmld_norm == 'jump':

        xmld = 100 * (1 / jump_final) * (-lh_y + lv_y)
        xmld_std = 100 * (1 / jump_final) * np.sqrt(lv_y_std ** 2 + lh_y_std ** 2)

    elif xmld_norm == 'peak':
        if bkg_type == 'norm':
            peak = y_mean.max() - y_mean[energy < energy[0] + 1].mean()

        else:
            peak = y_mean.max()

        xmld = 100 * (-lh_y + lv_y) / peak
        xmld_std = 100 * (1 / peak) * np.sqrt(lv_y_std ** 2 + lh_y_std ** 2)


    else:
        xmld = -lh_y + lv_y
        xmld_std = np.sqrt(lv_y_std ** 2 + lh_y_std ** 2)

    plt.figure(figsize=(8, 5))
    ax = plt.subplot(2, 1, 1)
    ax.plot(energy, lh_y, label='lh')
    ax.plot(energy, lv_y, label='lv')
    ax.legend(loc=0, frameon=False, fontsize=14)
    ax.set_ylabel('XAS (arb. units)', fontsize=14)
    ax.tick_params(direction='in', labelbottom=False, right=True, labelsize=14)
    if m.endstation == 'Magnet':
        if (fieldx != 0 and fieldy == 0):
            ax.set_title(r'#%d-#%d,%s, XMLD, %s, T=%5.2f K, H$_x$=%5.1f T, H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
            scanlist[0], scanlist[-1], sample_name, mode, tmp, fieldx, fieldz, rot))
        elif (fieldx == 0 and fieldy != 0):
            ax.set_title(r'#%d-#%d,%s, XMLD, %s, T=%5.2f K, H$_y$=%5.1f T, H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
            scanlist[0], scanlist[-1], sample_name, mode, tmp, fieldy, fieldz, rot))
        elif (fieldx == 0 and fieldy == 0):
            ax.set_title(r'#%d-#%d,%s, XMLD, %s, T=%5.2f K, H$_{xy}$=%5.1f T, H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
            scanlist[0], scanlist[-1], sample_name, mode, tmp, fieldx, fieldz, rot))
        else:
            ax.set_title(
                r'#%d-#%d,%s, XMLD, %s, T=%5.2f K, H$_x$=%5.1f T, H$_y$=%5.1f T,H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
                scanlist[0], scanlist[-1], sample_name, mode, tmp, fieldx, fieldy, fieldz, rot))
    if m.endstation in ['XABS', 'DD']:
        ax.set_title(r'#%d-#%d,%s, XMLD, %s, T=%5.2f K, H = 0 T, $\theta=%5.1f^{\circ}$' % (
        scanlist[0], scanlist[-1], sample_name, mode, tmp, rot))

    ax_1 = plt.subplot(2, 1, 2)
    ax_1.errorbar(energy, xmld, xmld_std, alpha=0.3)
    ax_1.errorbar(energy, xmld, lw=3, color='C0', label='lv-lh')
    ax_1.set_xlabel('Energy (eV)', fontsize=14)
    if xmld_norm is None:
        ax_1.set_ylabel('XMLD (arb. units)', fontsize=14)
    else:
        ax_1.set_ylabel('XMLD (%)', fontsize=14)
    ax_1.legend(loc=0, frameon=False, fontsize=14)

    ax_1.tick_params(direction='in', top=True, right=True, labelsize=14)

    plt.tight_layout()

    if save:
        plt.savefig(savedir + 'figures/' + '%d-%d_%s_XMLD.png' % (scanlist[0], scanlist[-1], mode))

        txt = savedir + 'data/' + '%d-%d_%s_XMLD_results.dat' % (scanlist[0], scanlist[-1], mode)
        f = open(txt, 'w')
        f.write('# Processing parameters:\n')
        f.write('# lh scans = %s\n' % (lh_scans))
        f.write('# lv scans = %s\n' % (lv_scans))
        f.write(
            '# mode = %s; background type = %s, post-edge normalisation to 1 = %s, xmld signal normalisation = %s  \n' % (
            mode, bkg_type, post_edge_norm, xmld_norm))
        f.write('Energy[eV]   XAS_lh  XAS_lh_std XAS_lv  XAS_lv_std  XAS_avg   XAS_avg_std  XMLD  XMLD_std\n')
        for m in range(len(energy)):
            help = '{:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f}\n'
            f.write(
                help.format(energy[m], lh_y[m], lh_y_std[m], lv_y[m], lv_y_std[m], y_mean[m], y_mean_std[m], xmld[m],
                            xmld_std[m]))
        f.close()

    return energy, xmld, xmld_std


def calc_XMLD_pairs_Nexus(scanlist, sample_name, mode='TEY', bkg_type='', post_edge_norm=False, xmld_norm=None,
                          save=False):
    """
    Basic XMLD data analysis of consecute lh/lv pairs - it calls the max_min_energy function which defines the range of energy where all the lh and lv scans will be interpolated

    Parameters
    ------------
    scanlist: list with scan numbers (lh and lv scans)

    sample_name: add the name of the sample as string; e.g. 'Sample 1'

    mode: 'TEY': total electon yield (if not specified, this is the default)
          'TFY_f1': fluorescence yield (front diode)
          'TFY_90': fluorescence yield (90 deg. diode)
          'TFY_f2': fluorescence yield (front diode)

    bck_type: 'flat': subtracts a constant;
              'norm': normalises pre-edge to 1;
              'linear': fits the pre-edge by a linear curve and subtract it

    post-edge_norm: if True, normalises the post-edge to 1


    save: if True, saves the 2 plots and the .dat file with the calculated xas and xmld

    Returns
    --------
    en_final: averaged energy array
    xmld: array with the XMLD spectra
    xmld_std: array with XMLD propagated error

    Plots:
    1st Plot: left panel: normalised XAS spectra for pc polarisation
              right panel: normalised XAS spectra for nc polarisation

    2nd Plot: Upper panel: averaged XAS for pc/nc polarisation
              Lower panel: reulting XMLD spectra and its standard deviation

    """

    y_lh = []
    y_lv = []
    en_lh = []
    en_lv = []
    jump_list = []
    lh_scans = []
    lv_scans = []

    "Determining the energy range to be used as interpolation"

    energy = max_min_energy_Nexus(scanlist)

    "If using a LinearModel (lmfit) for background subtraction"
    background = LinearModel(prefix='back_')

    """
    ## getting initial information ##
    d=readscan(scanlist[0])
    m = d.metadata
    ks = d.keys()
    
    tmp=m.Tsample_mag
    rot = m.scmth
    fieldz = m.magz
    fieldx = m.magx
    fieldy = m.magy
    """

    if mode is None:
        mode = 'TEY'

    for scanno in scanlist:

        d = readscan_Nexus(scanno)
        m = d.metadata
        ks = d.keys()
        if m.iddgap == 100:
            rowphase = m.idutrp
        else:
            rowphase = m.iddtrp

        "Skip the scan that is not fastEnergy"

        scan_type = m.command.split()[1]

        if scan_type != 'fastEnergy':
            continue

        if m.endstation == 'Magnet':
            tmp = m.Tsample_mag
            rot = m.scmth
            fieldz = m.magz
            fieldx = m.magx
            fieldy = m.magy
            pol = m.pola

        if m.endstation == 'XABS':
            tmp = 300
            rot = m.xabstheta
            field = 0
            pol = m.pola

        if m.endstation == 'DD':
            tmp = m.dd_T
            rot = m.ddth
            field = 0
            pol = m.pola

        energy1 = d.fastEnergy

        if mode == 'TEY':

            y = d.C1 / d.C2  # TEY data normalised by i0

        elif mode == 'TFY_f1':

            y = d.C3 / d.C2

        elif mode == 'TFY_f2':

            y = d.C4 / d.C2

        elif mode == 'TFY_90':

            y = d.C5 / d.C2

        else:

            y = d.C1 / d.C2

        ### interpolate ####
        f = interp1d(energy1, y, kind='linear')

        y = f(energy)

        # background type#

        if bkg_type == 'flat':
            "Subtracting the background by a constant"

            y -= y[energy < energy[0] + 5].mean()
            jump = y[energy > energy[-1] - 5].mean() - y[energy < energy[0] + 5].mean()
            jump_list.append(jump)

        if bkg_type == 'norm':
            "Simple normalisation of background to 1"
            y /= y[energy < energy[0] + 5].mean()  # nomalise by the average of a range of energy
            jump = y[energy > energy[-1] - 5].mean() - y[energy < energy[0] + 5].mean()
            jump_list.append(jump)

        if bkg_type == 'linear':
            "Subtracting the background by a linear curve fit "
            energy_back = energy[np.logical_and(energy > energy[0], energy < energy[0] + 5)]
            XAS_back = y[np.logical_and(energy > energy[0], energy < energy[0] + 5)]
            pars_back = background.guess(XAS_back, x=energy_back)

            out_back = background.fit(XAS_back, pars_back, x=energy_back)

            background_fit = background.eval(slope=out_back.params['back_slope'].value,
                                             intercept=out_back.params['back_intercept'].value, x=energy)

            y = y - background_fit
            jump = y[energy > energy[-1] - 5].mean()
            jump_list.append(jump)

        if bkg_type == None:
            y = y

        if post_edge_norm:
            if bkg_type == 'norm':
                y -= y[energy < energy[0] + 5].mean()
                jump = y[energy > energy[-1] - 5].mean()
                # print(jump)

                y /= jump
            else:
                # print(jump)
                y /= jump

        if int(rowphase) == 0:
            pol = 'lh'
            y_lh.append(y)
            lh_scans.append(scanno)




        else:
            pol = 'lv'
            y_lv.append(y)
            lv_scans.append(scanno)

    print(lh_scans)
    print(lv_scans)
    lh_y = np.array(y_lh)

    lv_y = np.array(y_lv)

    for i, j in zip(range(len(y_lh)), range(len(y_lv))):
        plt.figure(figsize=(8, 5))
        ax = plt.subplot(2, 1, 1)
        ax.plot(energy, lh_y[i], label='%d - lh' % (lh_scans[i]))
        ax.plot(energy, lv_y[j], label='%d - lv' % (lv_scans[j]))
        ax.legend(loc=0, frameon=False, fontsize=14)
        ax.set_ylabel('XAS (arb. units)', fontsize=14)
        ax.tick_params(direction='in', labelbottom=False, right=True, labelsize=14)
        if m.endstation == 'Magnet':
            if (fieldx != 0 and fieldy == 0):
                ax.set_title(
                    r'#%d-#%d,%s, XMLD, %s, T=%5.2f K, H$_x$=%5.1f T, H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
                    lh_scans[i], lv_scans[j], sample_name, mode, tmp, fieldx, fieldz, rot))
            elif (fieldx == 0 and fieldy != 0):
                ax.set_title(
                    r'#%d-#%d,%s, XMLD, %s, T=%5.2f K, H$_y$=%5.1f T, H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
                    lh_scans[i], lv_scans[j], sample_name, mode, tmp, fieldy, fieldz, rot))
            elif (fieldx == 0 and fieldy == 0):
                ax.set_title(
                    r'#%d-#%d,%s, XMLD, %s, T=%5.2f K, H$_{xy}$=%5.1f T, H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
                    lh_scans[i], lv_scans[j], sample_name, mode, tmp, fieldx, fieldz, rot))
            else:
                ax.set_title(
                    r'#%d-#%d,%s, XMLD, %s, T=%5.2f K, H$_x$=%5.1f T, H$_y$=%5.1f T,H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
                    lh_scans[i], lv_scans[j], sample_name, mode, tmp, fieldx, fieldy, fieldz, rot))
        if m.endstation in ['XABS', 'DD']:
            ax.set_title(r'#%d-#%d,%s, XMLD, %s, T=%5.2f K, H = 0 T, $\theta=%5.1f^{\circ}$' % (
            lh_scans[i], lv_scans[j], sample_name, mode, tmp, rot))

        y_mean = np.mean([lh_y[i], lv_y[j]], axis=0)
        y_mean_std = np.std([lh_y[i], lv_y[j]], axis=0)

        if xmld_norm == 'jump':
            jump_final = y_mean[energy > energy[-1] - 5].mean() - y_mean[energy < energy[0] + 5].mean()
            xmld = 100 * (1 / jump_final) * (-lh_y[i] + lv_y[j])
            xmld_std = 100 * (1 / jump_final) * np.std([lh_y[i], lv_y[j]], axis=0)

        elif xmld_norm == 'peak':
            if bkg_type == 'norm':
                peak = y_mean.max() - y_mean[energy < energy[0] + 5].mean()

            else:
                peak = y_mean.max()

            xmld = 100 * (-lh_y[i] + lv_y[j]) / peak
            xmld_std = 100 * (1 / peak) * np.std([lh_y[i], lv_y[j]], axis=0)


        else:
            xmld = -lh_y[i] + lv_y[j]
            xmld_std = np.std([lh_y[i], lv_y[j]], axis=0)

        ax_1 = plt.subplot(2, 1, 2)
        ax_1.errorbar(energy, xmld, xmld_std, alpha=0.3)
        ax_1.errorbar(energy, xmld, lw=3, color='C0', label='lv-lh')
        ax_1.set_xlabel('Energy (eV)', fontsize=14)
        if xmld_norm is None:
            ax_1.set_ylabel('XMLD (arb. units)', fontsize=14)
        else:
            ax_1.set_ylabel('XMLD (%)', fontsize=14)
        ax_1.legend(loc=0, frameon=False, fontsize=14)

        ax_1.tick_params(direction='in', top=True, right=True, labelsize=14)

        plt.tight_layout()

        if save:
            # plt.savefig(savedir+'figures/'+'%d-%d_%s_XMLD.png'%(scanlist[0],scanlist[-1],mode))

            txt = savedir + 'data/' + '%d-%d_%s_XMLD_results.dat' % (lh_scans[i], lv_scans[j], mode)
            f = open(txt, 'w')
            f.write('# Processing parameters:\n')
            f.write('# lh scans = %s\n' % (lh_scans[i]))
            f.write('# lv scans = %s\n' % (lv_scans[j]))
            f.write(
                '# mode = %s; background type = %s, post-edge normalisation to 1 = %s, xmld signal normalisation = %s  \n' % (
                mode, bkg_type, post_edge_norm, xmld_norm))
            f.write('Energy[eV]   XAS_lh   XAS_lv   XAS_avg   XAS_avg_std  XMLD  XMLD_std\n')
            for m in range(len(energy)):
                help = '{:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f}\n'
                f.write(help.format(energy[m], lh_y[i][m], lv_y[j][m], y_mean[m], y_mean_std[m], xmld[m], xmld_std[m]))
            f.close()


def calc_XMLD_arbitrary_Nexus(scanlist1, scanlist2, sample_name, mode='TEY', bkg_type='', post_edge_norm=False,
                              xmld_norm=None, save=False):
    '''
    Basic XMLD data analysis for arbitrary linear polarisation - it calls the max_min_energy function which defines the range of energy where all the lh and lv scans will be interpolated

    Parameters
    ------------
    scanlist1: list of scans with one arbitrary polarisation (laa1)
    scanlist2: list of scans with another arbitrary polarisation (laa2)

    sample_name: add the name of the sample as string; e.g. 'Sample 1'

    mode: 'TEY': total electon yield (if not specified, this is the default)
          'TFY_f1': fluorescence yield (front diode)
          'TFY_90': fluorescence yield (90 deg. diode)
          'TFY_f2': fluorescence yield (front diode)

    bck_type: 'flat': subtracts a constant;
              'norm': normalises pre-edge to 1;
              'linear': fits the pre-edge by a linear curve and subtract it

    post-edge_norm: if True, normalises the post-edge to 1

    xmld_norm: 'jump': divide the XMLD signal by the jump=post_edge-pre-edge value (XMLD plot will be showed in %)
               'peak': divide the XMLD by the max value of XAS(laa1)+XAS(laa2)/2; usually it's the L3 peak (XMLD plot will be showed in %)
                None : the XMLD will be displayed without any division (XMLD will be showed in arb. units)

    save: if True, saves the 2 plots and the .dat file with the calculated xas and xmcd (you need to save in order to use the function plot_XMLD)

    Returns
    --------
    energy: energy array
    xmcd: array with the XMLD spectra
    xmcd_std: array with XMLD propagated error

    Plots:
    1st Plot: left panel: normalised XAS spectra for pc polarisation
              right panel: normalised XAS spectra for nc polarisation

    2nd Plot: Upper panel: averaged XAS for pc/nc polarisation
              Lower panel: reulting XMLD spectra and its standard deviation

    '''

    y_1 = []
    y_2 = []
    jump_list = []

    "Determining the energy range to be used as interpolation"
    scanlist = np.concatenate((scanlist1, scanlist2))
    energy = max_min_energy_Nexus(scanlist)

    "If using a LinearModel (lmfit) for background subtraction"
    background = LinearModel(prefix='back_')

    ## getting initial information ##
    d = readscan_Nexus(scanlist[0])
    m = d.metadata
    ks = d.keys()

    plt.figure(figsize=(10, 5))

    if m.endstation == 'Magnet':
        tmp = m.Tsample_mag
        rot = m.scmth
        fieldz = m.magz
        fieldx = m.magx
        fieldy = m.magy

        if (fieldx != 0 and fieldy == 0):
            plt.suptitle(r'#%d-#%d, %s, %s, T=%5.2f K, H$_x$=%5.1f T, H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
            scanlist[0], scanlist[-1], sample_name, mode, tmp, fieldx, fieldz, rot), fontsize=14)
        elif (fieldx == 0 and fieldy != 0):
            plt.suptitle(r'#%d-#%d, %s, %s, T=%5.2f K, H$_y$=%5.1f T, H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
            scanlist[0], scanlist[-1], sample_name, mode, tmp, fieldy, fieldz, rot), fontsize=14)
        elif (fieldx == 0 and fieldy == 0):
            plt.suptitle(r'#%d-#%d, %s, %s, T=%5.2f K, H$_{xy}$=%5.1f T, H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
            scanlist[0], scanlist[-1], sample_name, mode, tmp, fieldx, fieldz, rot), fontsize=14)
        else:
            plt.suptitle(
                r'#%d-#%d, %s, %s, T=%5.2f K, H$_x$=%5.1f T, H$_y$=%5.1f T, H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
                scanlist[0], scanlist[-1], sample_name, mode, tmp, fieldx, fieldy, fieldz, rot), fontsize=14)

    if m.endstation == 'XABS':
        tmp = 300
        rot = m.xabstheta
        field = 0

        plt.suptitle(r'#%d-#%d, %s, %s, T=%5.2f K, H = 0 T, $\theta=%5.1f^{\circ}$' % (
        scanlist[0], scanlist[-1], sample_name, mode, tmp, rot), fontsize=14)

    if m.endstation == 'DD':
        tmp = m.dd_T
        rot = m.ddth
        field = 0

        plt.suptitle(r'#%d-#%d, %s, %s, T=%5.2f K, H = 0 T, $\theta=%5.1f^{\circ}$' % (
        scanlist[0], scanlist[-1], sample_name, mode, tmp, rot), fontsize=14)

    if mode is None:
        mode = 'TEY'

    ax0 = plt.subplot(1, 2, 1)
    ax1 = plt.subplot(1, 2, 2)

    for scanno in scanlist1:

        d = readscan_Nexus(scanno)
        m = d.metadata
        ks = d.keys()
        if m.iddgap == 100:
            rowphase1 = m.idutrp
            undulator = 'idu'
            laa1 = m.idu_la_angle
        else:
            rowphase1 = m.iddtrp
            undulator = 'idd'
            laa1 = m.idd_la_angle

        "Skip the scan that is not fastEnergy"

        scan_type = m.command.split()[1]

        if scan_type != 'fastEnergy':
            continue

        if m.endstation == 'Magnet':
            tmp = m.Tsample_mag
            rot = m.scmth
            fieldz = m.magz
            fieldx = m.magx
            fieldy = m.magy

        if m.endstation == 'XABS':
            tmp = 300
            rot = m.xabstheta
            field = 0

        if m.endstation == 'DD':
            tmp = m.dd_T
            rot = m.ddth
            field = 0

        energy1 = d.fastEnergy

        if mode == 'TEY':

            y = d.C1 / d.C2  # TEY data normalised by i0

        elif mode == 'TFY_f1':

            y = d.C3 / d.C2

        elif mode == 'TFY_f2':

            y = d.C4 / d.C2

        elif mode == 'TFY_90':

            y = d.C5 / d.C2

        else:

            y = d.C1 / d.C2

        ### interpolate ####
        f = interp1d(energy1, y, kind='linear')

        y = f(energy)

        # background type#

        if bkg_type == 'flat':
            "Subtracting the background by a constant"

            y -= y[energy < energy[0] + 5].mean()
            jump = y[energy > energy[-1] - 5].mean() - y[energy < energy[0] + 1].mean()
            jump_list.append(jump)

        if bkg_type == 'norm':
            "Simple normalisation of background to 1"
            y /= y[energy < energy[0] + 5].mean()  # nomalise by the average of a range of energy
            jump = y[energy > energy[-1] - 5].mean() - y[energy < energy[0] + 1].mean()
            jump_list.append(jump)

        if bkg_type == 'linear':
            "Subtracting the background by a linear curve fit "
            energy_back = energy[np.logical_and(energy > energy[0], energy < energy[0] + 1)]
            XAS_back = y[np.logical_and(energy > energy[0], energy < energy[0] + 1)]
            pars_back = background.guess(XAS_back, x=energy_back)

            out_back = background.fit(XAS_back, pars_back, x=energy_back)

            background_fit = background.eval(slope=out_back.params['back_slope'].value,
                                             intercept=out_back.params['back_intercept'].value, x=energy)

            y = y - background_fit
            jump = y[energy > energy[-1] - 5].mean()
            jump_list.append(jump)

        if bkg_type == None:
            y = y

        if post_edge_norm:
            if bkg_type == 'norm':
                y -= y[energy < energy[0] + 5].mean()
                jump = y[energy > energy[-1] - 5].mean()
                # print(jump)

                y /= jump
            else:
                # print(jump)
                y /= jump

        y_1.append(y)

        "plotting positive polarisation"
        ax0.plot(energy, y, label='%d' % scanno)
        # ax0.plot(energy,y-background_fit,label='%d'%scanno)
        ax0.legend(loc=0, frameon=False)
        ax0.set_title('rowphase1=%5.3f' % (rowphase1))

    for scanno in scanlist2:
        d = readscan_Nexus(scanno)
        m = d.metadata
        ks = d.keys()
        if m.iddgap == 100:
            rowphase2 = m.idutrp
            undulator = 'idu'
            laa2 = m.idu_la_angle
        else:
            rowphase2 = m.iddtrp
            undulator = 'idd'
            laa2 = m.idd_la_angle

        if m.endstation == 'Magnet':
            tmp = m.Tsample_mag
            rot = m.scmth
            fieldz = m.magz
            fieldx = m.magx
            fieldy = m.magy

        if m.endstation == 'XABS':
            tmp = 300
            rot = m.xabstheta
            field = 0

        if m.endstation == 'DD':
            tmp = m.dd_T
            rot = m.ddth
            field = 0

        energy1 = d.fastEnergy

        if mode == 'TEY':
            y = d.C1 / d.C2  # TEY data normalised by i0

        elif mode == 'TFY_f1':
            y = d.C3 / d.C2

        elif mode == 'TFY_f2':
            y = d.C4 / d.C2

        elif mode == 'TFY_90':
            y = d.C5 / d.C2

        else:
            y = d.C1 / d.C2

        ### interpolate ####
        f = interp1d(energy1, y, kind='linear')

        y = f(energy)

        # background type#

        if bkg_type == 'flat':
            "Subtracting the background by a constant"

            y -= y[energy < energy[0] + 5].mean()
            jump = y[energy > energy[-1] - 5].mean() - y[energy < energy[0] + 1].mean()
            jump_list.append(jump)

        if bkg_type == 'norm':
            "Simple normalisation of background to 1"
            y /= y[energy < energy[0] + 5].mean()  # nomalise by the average of a range of energy
            jump = y[energy > energy[-1] - 5].mean() - y[energy < energy[0] + 1].mean()
            jump_list.append(jump)

        if bkg_type == 'linear':
            "Subtracting the background by a linear curve fit "
            energy_back = energy[np.logical_and(energy > energy[0], energy < energy[0] + 1)]
            XAS_back = y[np.logical_and(energy > energy[0], energy < energy[0] + 1)]
            pars_back = background.guess(XAS_back, x=energy_back)

            out_back = background.fit(XAS_back, pars_back, x=energy_back)

            background_fit = background.eval(slope=out_back.params['back_slope'].value,
                                             intercept=out_back.params['back_intercept'].value, x=energy)

            y = y - background_fit
            jump = y[energy > energy[-1] - 5].mean()
            jump_list.append(jump)

        if bkg_type == None:
            y = y

        if post_edge_norm:
            if bkg_type == 'norm':
                y -= y[energy < energy[0] + 5].mean()
                jump = y[energy > energy[-1] - 5].mean()
                # print(jump)

                y /= jump
            else:
                # print(jump)
                y /= jump

        y_2.append(y)

        "plotting positive polarisation"
        ax1.plot(energy, y, label='%d' % scanno)
        # ax1.plot(energy,y-background_fit,label='%d'%scanno)
        # ax1.plot(energy,background_fit,'--',color='black')
        ax1.legend(loc=0, frameon=False)
        ax1.set_title('rowphase2=%5.3f' % (rowphase2))

    ax0.set_xlabel('Energy (eV)', fontsize=14)
    ax0.set_ylabel('XAS (arb. units)', fontsize=14)
    ax0.tick_params(direction='in', labelsize=14)

    ax1.set_xlabel('Energy (eV)', fontsize=14)
    ax1.set_ylabel('XAS (arb. units)', fontsize=14)
    ax1.tick_params(direction='in', labelsize=14)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    if save:
        plt.savefig(savedir + 'figures/' + '%d-%d_%s_XAS.png' % (scanlist[0], scanlist[-1], mode))

    pol1_y_std = np.std(y_1, axis=0)
    pol1_y = np.mean(y_1, axis=0)

    pol2_y_std = np.std(y_2, axis=0)
    pol2_y = np.mean(y_2, axis=0)

    y_mean = np.mean([pol1_y, pol2_y], axis=0)
    y_mean_std = np.std([pol1_y, pol2_y], axis=0)
    # print(jump_list)
    jump_final = np.mean(jump_list)
    # print(jump_final)
    # print(TEY_mean[energy>energy[-1]-5].mean()-TEY_mean[energy<energy[0]+5].mean())

    if xmld_norm == 'jump':

        xmld = 100 * (1 / jump_final) * (-pol1_y + pol2_y)
        xmld_std = 100 * (1 / jump_final) * np.sqrt(pol2_y_std ** 2 + pol1_y_std ** 2)

    elif xmld_norm == 'peak':
        if bkg_type == 'norm':
            peak = y_mean.max() - y_mean[energy < energy[0] + 5].mean()

        else:
            peak = y_mean.max()

        xmld = 100 * (-pol1_y + pol2_y) / peak
        xmld_std = 100 * (1 / peak) * np.sqrt(pol2_y_std ** 2 + pol1_y_std ** 2)


    else:
        xmld = -pol1_y + pol2_y
        xmld_std = np.sqrt(pol2_y_std ** 2 + pol1_y_std ** 2)

    plt.figure()
    ax = plt.subplot(2, 1, 1)
    ax.plot(energy, pol1_y, label='laa1=%5.3f' % laa1)
    ax.plot(energy, pol2_y, label='laa2=%5.3f' % laa2)
    ax.legend(loc=0, frameon=False)
    ax.set_ylabel('XAS (arb. units)', fontsize=14)
    ax.tick_params(direction='in', labelbottom=False, right=True, labelsize=14)
    if m.endstation == 'Magnet':
        if (fieldx != 0 and fieldy == 0):
            ax.set_title(
                '#%d-#%d,%s, XMLD, %s, T=%5.2f K,\n' r'H$_x$=%5.1f T, H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
                scanlist[0], scanlist[-1], sample_name, mode, tmp, fieldx, fieldz, rot))
        elif (fieldx == 0 and fieldy != 0):
            ax.set_title(
                '#%d-#%d,%s, XMLD, %s, T=%5.2f K,\n' r'H$_y$=%5.1f T, H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
                scanlist[0], scanlist[-1], sample_name, mode, tmp, fieldy, fieldz, rot))
        elif (fieldx == 0 and fieldy == 0):
            ax.set_title(
                '#%d-#%d,%s, XMLD, %s, T=%5.2f K,\n' r'H$_{xy}$=%5.1f T, H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
                scanlist[0], scanlist[-1], sample_name, mode, tmp, fieldx, fieldz, rot))
        else:
            ax.set_title(
                '#%d-#%d,%s, XMLD, %s, T=%5.2f K,\n' r'H$_x$=%5.1f T, H$_y$=%5.1f T,H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
                scanlist[0], scanlist[-1], sample_name, mode, tmp, fieldx, fieldy, fieldz, rot))
    if m.endstation in ['XABS', 'DD']:
        ax.set_title(r'#%d-#%d,%s, XMLD, %s, T=%5.2f K, H = 0 T, $\theta=%5.1f^{\circ}$' % (
        scanlist[0], scanlist[-1], sample_name, mode, tmp, rot))

    ax_1 = plt.subplot(2, 1, 2)
    ax_1.errorbar(energy, xmld, xmld_std, alpha=0.3)
    ax_1.errorbar(energy, xmld, lw=3, color='C0', label='laa2-laa1')
    ax_1.set_xlabel('Energy (eV)', fontsize=14)
    if xmld_norm is None:
        ax_1.set_ylabel('XMLD (arb. units)', fontsize=14)
    else:
        ax_1.set_ylabel('XMLD (%)', fontsize=14)
    ax_1.legend(loc=0, frameon=False)

    ax_1.tick_params(direction='in', top=True, right=True, labelsize=14)

    plt.tight_layout()

    if save:
        plt.savefig(savedir + 'figures/' + '%d-%d_%s_XMLD.png' % (scanlist[0], scanlist[-1], mode))

        txt = savedir + 'data/' + '%d-%d_%s_XMLD_results.dat' % (scanlist[0], scanlist[-1], mode)
        f = open(txt, 'w')
        f.write('# Processing parameters:\n')
        f.write('# laa1 = %5.3f scans = %s\n' % (laa1, scanlist1))
        f.write('# laa2 = %5.3f scans = %s\n' % (laa2, scanlist2))
        f.write(
            '# mode = %s; background type = %s, post-edge normalisation to 1 = %s, xmld signal normalisation = %s  \n' % (
            mode, bkg_type, post_edge_norm, xmld_norm))
        f.write('Energy[eV]   XAS_laa1  XAS_laa1_std XAS_laa2  XAS_laa2_std  XAS_avg   XAS_avg_std  XMLD  XMLD_std\n')
        for m in range(len(energy)):
            help = '{:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f}\n'
            f.write(help.format(energy[m], pol1_y[m], pol1_y_std[m], pol2_y[m], pol2_y_std[m], y_mean[m], y_mean_std[m],
                                xmld[m], xmld_std[m]))
        f.close()

    return energy, xmld, xmld_std


def calc_XMLD_Hxy_Nexus(scanlist, sample_name, mode='TEY', bkg_type='', post_edge_norm=False, xmld_norm=None,
                        save=False):
    """
    Basic XMLD data analysis for a single linear polarisation (LH or LV) and changing the direction of the magnetic field (Hx or Hy) - it calls the max_min_energy function which defines the range of energy where all the lh and lv scans will be interpolated

    Parameters
    ------------
    scanlist: list of all scans


    sample_name: add the name of the sample as string; e.g. 'Sample 1'

    mode: 'TEY': total electon yield (if not specified, this is the default)
          'TFY_f1': fluorescence yield (front diode)
          'TFY_90': fluorescence yield (90 deg. diode)
          'TFY_f2': fluorescence yield (front diode)

    bck_type: 'flat': subtracts a constant;
              'norm': normalises pre-edge to 1;
              'linear': fits the pre-edge by a linear curve and subtract it

    post-edge_norm: if True, normalises the post-edge to 1

    xmld_norm: 'jump': divide the XMLD signal by the jump=post_edge-pre-edge value (XMLD plot will be showed in %)
               'peak': divide the XMLD by the max value of XAS(laa1)+XAS(laa2)/2; usually it's the L3 peak (XMLD plot will be showed in %)
                None : the XMLD will be displayed without any division (XMLD will be showed in arb. units)

    save: if True, saves the 2 plots and the .dat file with the calculated xas and xmcd (you need to save in order to use the function plot_XMLD)

    Returns
    --------
    energy: energy array
    xmcd: array with the XMLD spectra
    xmcd_std: array with XMLD propagated error

    Plots:
    1st Plot: left panel: normalised XAS spectra for pc polarisation
              right panel: normalised XAS spectra for nc polarisation

    2nd Plot: Upper panel: averaged XAS for pc/nc polarisation
              Lower panel: reulting XMLD spectra and its standard deviation

    """

    y_hx = []
    y_hy = []
    hx_scans = []
    hy_scans = []

    jump_list = []

    "Determining the energy range to be used as interpolation"
    energy = max_min_energy_Nexus(scanlist)

    "If using a LinearModel (lmfit) for background subtraction"
    background = LinearModel(prefix='back_')

    ## getting initial information ##
    d = readscan_Nexus(scanlist[0])
    m = d.metadata
    ks = d.keys()

    if m.endstation == 'Magnet':
        tmp = m.Tsample_mag
        rot = m.scmth
        fieldz = m.magz
        fieldx = m.magx
        fieldy = m.magy
    else:
        print('Error!!!This script just works when using magnet endstation')
        return

    if mode is None:
        mode = 'TEY'

    plt.figure(figsize=(10, 5))
    plt.suptitle(r'#%d-#%d, %s, %s, T=%5.2f K, $\theta=%5.1f^{\circ}$' % (
    scanlist[0], scanlist[-1], sample_name, mode, tmp, rot), fontsize=14)
    ax0 = plt.subplot(1, 2, 1)
    ax1 = plt.subplot(1, 2, 2)

    for scanno in scanlist:

        d = readscan_Nexus(scanno)
        m = d.metadata
        ks = d.keys()

        if m.iddgap == 100:
            rowphase = m.idutrp
            undulator = 'idu'
        else:
            rowphase = m.iddtrp
            undulator = 'idd'

        "Skip the scan that is not fastEnergy"

        scan_type = m.command.split()[1]

        if scan_type != 'fastEnergy':
            continue

        tmp = m.Tsample_mag
        rot = m.scmth

        energy1 = d.fastEnergy

        if mode == 'TEY':

            y = d.idio

        elif mode == 'TFY_f1':

            y = d.C3 / d.C2

        elif mode == 'TFY_f2':

            y = d.C4 / d.C2

        elif mode == 'TFY_90':

            y = d.C5 / d.C2

        else:

            y = d.idio

        ### interpolate ####
        f = interp1d(energy1, y, kind='linear')

        y = f(energy)

        # background type#

        if bkg_type == 'flat':
            "Subtracting the background by a constant"

            y -= y[energy < energy[0] + 5].mean()
            jump = y[energy > energy[-1] - 5].mean() - y[energy < energy[0] + 1].mean()
            jump_list.append(jump)

        if bkg_type == 'norm':
            "Simple normalisation of background to 1"
            y /= y[energy < energy[0] + 5].mean()  # nomalise by the average of a range of energy
            jump = y[energy > energy[-1] - 5].mean() - y[energy < energy[0] + 1].mean()
            jump_list.append(jump)

        if bkg_type == 'linear':
            "Subtracting the background by a linear curve fit "
            energy_back = energy[np.logical_and(energy > energy[0], energy < energy[0] + 1)]
            XAS_back = y[np.logical_and(energy > energy[0], energy < energy[0] + 1)]
            pars_back = background.guess(XAS_back, x=energy_back)

            out_back = background.fit(XAS_back, pars_back, x=energy_back)

            background_fit = background.eval(slope=out_back.params['back_slope'].value,
                                             intercept=out_back.params['back_intercept'].value, x=energy)

            y = y - background_fit
            jump = y[energy > energy[-1] - 5].mean()
            jump_list.append(jump)

        if bkg_type == None:
            y = y

        if post_edge_norm:
            if bkg_type == 'norm':
                y -= y[energy < energy[0] + 5].mean()
                jump = y[energy > energy[-1] - 5].mean()
                # print(jump)

                y /= jump
            else:
                # print(jump)
                y /= jump

        if int(m.magx) != 0:
            field = 'Hx'
            y_hx.append(y)
            hx_scans.append(scanno)

            "plotting positive polarisation"
            ax0.plot(energy, y, label='%d' % scanno)
            # ax0.plot(energy,y-background_fit,label='%d'%scanno)
            ax0.legend(loc=0, frameon=False)
            ax0.set_title('field=%s' % (field), fontsize=14)

        if int(m.magy) != 0:
            field = 'Hy'
            y_hy.append(y)
            hy_scans.append(scanno)

            "plotting positive polarisation"
            ax1.plot(energy, y, label='%d' % scanno)
            # ax1.plot(energy,y-background_fit,label='%d'%scanno)
            # ax1.plot(energy,background_fit,'--',color='black')
            ax1.legend(loc=0, frameon=False)
            ax1.set_title('field=%s' % (field), fontsize=14)

    ax0.set_xlabel('Energy (eV)', fontsize=14)
    ax0.set_ylabel('XAS (arb. units)', fontsize=14)
    ax0.tick_params(direction='in', labelsize=14)

    ax1.set_xlabel('Energy (eV)', fontsize=14)
    ax1.set_ylabel('XAS (arb. units)', fontsize=14)
    ax1.tick_params(direction='in', labelsize=14)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    hx_y_std = np.std(y_hx, axis=0)
    hx_y = np.mean(y_hx, axis=0)

    hy_y_std = np.std(y_hy, axis=0)
    hy_y = np.mean(y_hy, axis=0)

    y_mean = np.mean([hx_y, hy_y], axis=0)
    y_mean_std = np.std([hx_y, hy_y], axis=0)
    # print(jump_list)
    jump_final = np.mean(jump_list)
    # print(jump_final)
    # print(TEY_mean[energy>energy[-1]-5].mean()-TEY_mean[energy<energy[0]+5].mean())

    if xmld_norm == 'jump':

        xmld = 100 * (1 / jump_final) * (-hx_y + hy_y)
        xmld_std = 100 * (1 / jump_final) * np.sqrt(hy_y_std ** 2 + hx_y_std ** 2)

    elif xmld_norm == 'peak':
        if bkg_type == 'norm':
            peak = y_mean.max() - y_mean[energy < energy[0] + 1].mean()

        else:
            peak = y_mean.max()

        xmld = 100 * (-hx_y + hy_y) / peak
        xmld_std = 100 * (1 / peak) * np.sqrt(hy_y_std ** 2 + hx_y_std ** 2)


    else:
        xmld = -hx_y + hy_y
        xmld_std = np.sqrt(hy_y_std ** 2 + hx_y_std ** 2)

    plt.figure()
    ax = plt.subplot(2, 1, 1)
    ax.plot(energy, hx_y, label='Hx')
    ax.plot(energy, hy_y, label='Hy')
    ax.legend(loc=0, frameon=False, fontsize=14)
    ax.set_ylabel('XAS (arb. units)', fontsize=14)
    ax.tick_params(direction='in', labelbottom=False, right=True, labelsize=14)
    ax.set_title(r'#%d-#%d,%s, XMLD, %s, T=%5.2f K, H$_x$=%5.1f T,H$_y$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
    scanlist[0], scanlist[-1], sample_name, mode, tmp, m.magx, m.magy, rot), fontsize=12)

    ax_1 = plt.subplot(2, 1, 2)
    ax_1.errorbar(energy, xmld, xmld_std, alpha=0.3)
    ax_1.errorbar(energy, xmld, lw=3, color='C0', label='Hy-Hx')
    ax_1.set_xlabel('Energy (eV)', fontsize=14)
    if xmld_norm is None:
        ax_1.set_ylabel('XMLD (arb. units)', fontsize=14)
    else:
        ax_1.set_ylabel('XMLD (%)', fontsize=14)
    ax_1.legend(loc=0, frameon=False, fontsize=14)

    ax_1.tick_params(direction='in', top=True, right=True, labelsize=14)

    plt.tight_layout()

    if save:
        plt.savefig(savedir + 'figures/' + '%d-%d_%s_XMLD.png' % (scanlist[0], scanlist[-1], mode))

        txt = savedir + 'data/' + '%d-%d_%s_XMLD_results.dat' % (scanlist[0], scanlist[-1], mode)
        f = open(txt, 'w')
        f.write('# Processing parameters:\n')
        f.write('# Hx scans = %s\n' % (hx_scans))
        f.write('# Hy scans = %s\n' % (hy_scans))
        f.write(
            '# mode = %s; background type = %s, post-edge normalisation to 1 = %s, xmld signal normalisation = %s  \n' % (
            mode, bkg_type, post_edge_norm, xmld_norm))
        f.write('Energy[eV]   XAS_hx  XAS_hx_std XAS_hy  XAS_hy_std  XAS_avg   XAS_avg_std  XMLD  XMLD_std\n')
        for m in range(len(energy)):
            help = '{:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f} {:10.6f}\n'
            f.write(
                help.format(energy[m], hx_y[m], hx_y_std[m], hy_y[m], hy_y_std[m], y_mean[m], y_mean_std[m], xmld[m],
                            xmld_std[m]))
        f.close()

    return energy, hx_y, hy_y, xmld, xmld_std


def plot_XMCD_Nexus(scanlist_list, sample_name, depvar='', mode='TEY', xmcd_amp=None, save=False):
    """
    Plot XMCD spectra as a function of depvar

        Parameters
        ---------------------------
        scanlist_list: list of scan lists e.g., [np.range(),np.range()] (note that the range should be the same as specified in                        the calc_XMCD function)
        sample_name: name of the sample as string e.g., 'sample 1'
        depvar: list with dependent variable; eg: 'temp' uses the magnet sample temperature; 'field' uses the magz field; 'rot'                 uses the sample rotation;
        mode: Needs to specify the same one used for calc_XMCD

        Returns
        ----------------------------
        plot1: XMCD vs energy as a function of dpvar;
        plot 2: XMCD amplitude or area
    """
    dep_list = []
    # dep_mag_list = []
    # dep_rot_list = []
    min_list = []
    min_list_std = []
    max_list = []
    max_list_std = []
    xmcd_int = []

    if depvar not in ['temp', 'field', 'rot']:

        if len(depvar) != len(scanlist_list):
            print('### Error: length of depvar should be the same as the scanlist_list ###')

            return

    plt.figure()

    for i, scanlist in enumerate(scanlist_list):
        dep_temp = []
        dep_mag = []
        dep_rot = []

        'Getting the average temperature, field and rot angle from the scans of scanlist'

        for scanno in scanlist:
            d = readscan_Nexus(scanno)
            dep_temp.append(float(d.metadata.Tsample_mag))
            dep_mag.append(float(d.metadata.magz))
            dep_rot.append(float(d.metadata.scmth))

        dep_temp = np.mean(dep_temp)

        dep_mag = np.mean(dep_mag)
        # print(dep_mag)

        dep_rot = np.mean(dep_rot)

        'Loading the XMCD data saved from calc_XMCD'

        txt = savedir + 'data/' + '%d-%d_%s_XMCD_results.dat' % (scanlist[0], scanlist[-1], mode)
        en, xas_pc, xas_pc_std, xas_nc, xas_nc_std, xas_avg, xas_avg_std, xmcd, xmcd_std = np.loadtxt(txt, skiprows=5,
                                                                                                      unpack=True)

        if depvar == 'temp':
            xlabel = 'Temperature (K)'
            ttl1 = r'%s, H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (sample_name, dep_mag, dep_rot)
            namefile = '%s_Tdep_H=%5.1fT_rot=%5.1fdeg' % (sample_name, dep_mag, dep_rot)
            plt.plot(en, xmcd, label='T=%5.2f K' % (dep_temp))
            dep_list.append(dep_temp)


        elif depvar == 'field':
            # print('it is here')
            xlabel = 'Magnetic Field (T)'
            # print(xlabel)
            ttl1 = r'%s, T=%5.2f, $\theta=%5.1f^{\circ}$' % (sample_name, dep_temp, dep_rot)
            # print(ttl1)
            namefile = '%s_Hdep_T=%5.2fK_rot=%5.1fdeg' % (sample_name, dep_temp, dep_rot)
            # print(namefile)
            plt.plot(en, xmcd, label='H=%5.1f T' % (dep_mag))
            dep_list.append(dep_mag)


        elif depvar == 'rot':
            xlabel = r'$\theta$ ($^{\circ}$)'
            ttl1 = r'%s, T=%5.2f, H$_z$=%5.1f T' % (sample_name, dep_temp, dep_mag)
            namefile = '%s_rotdep_T=%5.2fK_H=%5.1fT' % (sample_name, dep_temp, dep_mag)
            plt.plot(en, xmcd, label='$\theta$=%5.1f^{\circ}' % (dep_rot))
            dep_list.append(dep_rot)


        else:
            if type(depvar) == list:
                xlabel = 'Custom'
                ttl1 = r'T=%5.2f = H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (dep_temp, dep_mag, dep_rot)
                namefile = '%s_customdep_T=%5.2fK_H=%5.1fT_rot=%5.1fdeg' % (sample_name, dep_temp, dep_mag, dep_rot)
                plt.plot(en, xmcd, label='%s' % (depvar[i]))
                dep_list.append(depvar[i])

            else:

                print('### Error: depvar should be a list!!! ###')

        if xmcd_amp == 'min_value':
            index = np.argwhere(xmcd == xmcd.min())
            print('min value found at position %d' % index[0][0])
            min_list.append(xmcd.min())
            min_list_std.append(xmcd_std[index[0][0]])
            ttl2 = 'XMCD min Value vs '

        if xmcd_amp == 'max_value':
            index = np.argwhere(xmcd == xmcd.max())
            print('max value found at position %d' % index[0][0])
            max_list.append(xmcd.max())
            max_list_std.append(xmcd_std[index[0][0]])
            ttl2 = 'XMCD max Value vs '

        if xmcd_amp == 'area':
            integral = integrate.cumtrapz(xmcd, en, initial=0)
            plt.plot(en, integral, '--', color='black')
            xmcd_int.append(integral[-1])
            ttl2 = 'XMCD Area vs '

        if xmcd_amp == 'area_L3':
            end = (en.min() + en.max()) / 2
            en_L3 = en[np.logical_and(en > en.min(), en < end)]
            xmcd_L3 = xmcd[np.logical_and(en > en.min(), en < end)]

            integral = integrate.cumtrapz(xmcd_L3, en_L3, initial=0)

            # plt.plot(en_L3,integral,'--',color='black')

            xmcd_int.append(integral[-1])

            ttl2 = r'XMCD Area L$_3$ vs'

        if xmcd_amp == 'area_L2':
            init = (en.min() + en.max()) / 2
            en_L2 = en[np.logical_and(en > init, en < en.max())]
            xmcd_L2 = xmcd[np.logical_and(en > init, en < en.max())]

            integral = integrate.cumtrapz(xmcd_L2, en_L2, initial=0)

            # plt.plot(en_L2,integral,'--',color='black')

            xmcd_int.append(integral[-1])

            ttl2 = r'XMCD Area L$_2$ vs'

    plt.suptitle(ttl1, fontsize=14)
    plt.legend(loc=0, frameon=False, fontsize=12)
    plt.axhline(y=0, ls='--', color='black')
    plt.ylabel('XMCD (arb. units)', fontsize=14)
    plt.xlabel('Energy (eV)', fontsize=14)
    plt.tick_params(direction='in', labelsize=14)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    if save:
        plt.savefig(savedir + 'figures/' + namefile + '_%s.png' % mode)

    if xmcd_amp in ['area', 'area_L3', 'area_L2']:
        plt.figure()
        if depvar not in ['temp', 'field', 'rot']:
            dummy = np.array([i for i in range(len(dep_list))])
            plt.plot(dummy, xmcd_int, '-o')
            plt.xticks(dummy, depvar, fontsize=14)
            # plt.xticks(dummy)
            # plt.xticklabels(depvar,rotation='vertical',fontsize=14)
        else:
            plt.plot(dep_list, xmcd_int, '-o')
        plt.ylabel('Integrated XMCD (arb. units)', fontsize=14)
    if xmcd_amp in ['min_value']:
        plt.figure()
        min_list = np.array(min_list)
        min_list_std = np.array(min_list_std)
        if depvar not in ['temp', 'field', 'rot']:
            dummy = np.array([i for i in range(len(dep_list))])
            plt.errorbar(dummy, abs(min_list), min_list_std, fmt='-o')
            plt.xticks(dummy, depvar, fontsize=14)
            # plt.xticks(dummy)
            # plt.xticklabels(depvar,rotation='vertical',fontsize=14)
        else:
            dep_list = np.array(dep_list)

            plt.errorbar(dep_list, abs(min_list), min_list_std, fmt='-o')
        plt.ylabel('XMCD (x-1)', fontsize=14)
        # plt.ylim([min_list.max(),min_list.min()])
    if xmcd_amp in ['max_value']:
        max_list = np.array(max_list)
        max_list_std = np.array(max_list_std)

        plt.figure()
        if depvar not in ['temp', 'field', 'rot']:
            dummy = np.array([i for i in range(len(dep_list))])
            plt.errorbar(dummy, max_list, max_list_std, fmt='-o')
            plt.xticks(dummy, depvar, fontsize=14)

        else:
            dep_list = np.array(dep_list)
            plt.errorbar(dep_list, max_list, max_list_std, fmt='-o')
        plt.ylabel('XMCD', fontsize=14)
        # plt.ylim([min_list.max(),min_list.min()])

    plt.xlabel(xlabel, fontsize=14)
    plt.tick_params(direction='in', labelsize=14)
    plt.suptitle(ttl2 + xlabel + ', ' + ttl1, fontsize=12)

    if save:
        plt.savefig(savedir + 'figures/' + '%s_%s_dep_%s.png' % (sample_name, xmcd_amp, mode))


def plotXAS_la_Nexus(scanlist, sample_name, mode='TEY', bkg_type='flat', reps=1, post_edge_norm=False, peak=False,
                     save=False):
    """Plot XAS scans for different selection of pre-edge and post-edge analysis as a function of the linearly arbitrary polarisation - it calls the max_min_energy function which defines the range of energy where all the zacscans will be interpolated;

    Parameters
    ------------
    scanlist: list with scan numbers - note that if reps>1, one should construct a range such as range(scan1,scan2,reps)


    sample_name: add the name of the sample as string; e.g. 'Sample 1'

    mode: 'TEY': total electon yield (if not specified, this is the default)
          'TFY_f1': fluorescence yield (front diode)
          'TFY_90': fluorescence yield (90 deg. diode)
          'TFY_f2': fluorescence yield (front diode)

    bkg_type: 'flat': subtracts a constant;
              'norm': normalises pre-edge to 1;
              'linear': fits the pre-edge by a linear curve and subtract it

    reps: number of repetition of scans for the same angle; if >1, the final XAS is the average of the repetitions

    post-edge_norm: if True, normalises the post-edge to 1


    save: if True, saves the plot

    Returns
    --------
    Plot of XAS against energy for different angle of linear polarisation
    """

    "If using a LinearModel (lmfit) for background subtraction"

    background = LinearModel(prefix='back_')

    peak_list = []
    jump_list = []
    laa_list = []
    iteration = 0
    plt.figure()
    for scan in scanlist:
        sublist = [scan + i for i in range(reps)]
        # print('sublist = '+str(sublist))

        "Determining the energy range to be used as interpolation"

        energy = max_min_energy_Nexus(sublist)

        d = readscan_Nexus(scan)
        m = d.metadata
        ks = d.keys()

        if m.iddgap == 100:
            rowphase = m.idutrp
            undulator = 'idu'
            laa = m.idu_la_angle

        else:
            rowphase = m.iddtrp
            undulator = 'idd'
            laa = m.idd_la_angle

        laa_list.append(laa)

        energy_list = []
        XAS_list = []

        for scanno in sublist:
            d = readscan_Nexus(scanno)
            m = d.metadata
            ks = d.keys()

            "Skip the scan that is not fastEnergy"

            scan_type = m.command.split()[1]
            if scan_type != 'fastEnergy':
                continue

            if m.endstation == 'Magnet':
                fieldx = m.magx
                fieldy = m.magy
                fieldz = m.magz
                tmp = m.Tsample_mag
                rot = m.scmth

            if m.endstation == 'XABS':
                tmp = 300
                rot = m.xabstheta
                field = 0

            if m.endstation == 'DD':
                tmp = m.dd_T
                rot = m.ddth
                field = 0

            energy1 = d.fastEnergy

            if mode == 'C1':
                y = d.C1
                ylabel = 'C1 (arb. units)'

            elif mode == 'C2':
                y = d.C2
                ylabel = 'C2 (arb. units)'

            elif mode == 'C3':
                y = d.C3
                ylabel = 'C3 (arb. units)'

            elif mode == 'C4':
                y = d.C4
                ylabel = 'C4 (arb. units)'

            elif mode == 'C5':
                y = d.C5
                ylabel = 'C5 (arb. units)'

            elif mode == 'TEY':
                y = d.C1 / d.C2  # TEY data normalised by i0

            elif mode == 'TFY_f1':
                y = d.C3 / d.C2  # front diode data normalised by i0

            elif mode == 'TFY_f2':
                y = d.C4 / d.C2  # front diode data normalised by i0

            elif mode == 'TFY_90':
                y = d.C5 / d.C2

            else:
                y = d.C1 / d.C2

            ### interpolate ####
            f = interp1d(energy1, y, kind='linear')

            y = f(energy)

            # background type#

            if bkg_type == 'flat':
                "Subtracting the background by a constant"

                y -= y[energy < energy[0] + 5].mean()
                jump = y[energy > energy[-1] - 5].mean() - y[energy < energy[0] + 5].mean()
                jump_list.append(jump)

            if bkg_type == 'norm':
                "Simple normalisation of background to 1"
                y /= y[energy < energy[0] + 5].mean()  # nomalise by the average of a range of energy
                jump = y[energy > energy[-1] - 5].mean() - y[energy < energy[0] + 5].mean()
                jump_list.append(jump)

            if bkg_type == 'linear':
                "Subtracting the background by a linear curve fit "
                energy_back = energy[np.logical_and(energy > energy[0], energy < energy[0] + 5)]
                XAS_back = y[np.logical_and(energy > energy[0], energy < energy[0] + 5)]
                pars_back = background.guess(XAS_back, x=energy_back)

                out_back = background.fit(XAS_back, pars_back, x=energy_back)

                background_fit = background.eval(slope=out_back.params['back_slope'].value,
                                                 intercept=out_back.params['back_intercept'].value, x=energy)

                y = y - background_fit
                jump = y[energy > energy[-1] - 5].mean()
                jump_list.append(jump)

            if bkg_type == None:
                y = y

            if post_edge_norm:
                if bkg_type == 'norm':
                    y -= y[energy < energy[0] + 5].mean()
                    jump = y[energy > energy[-1] - 5].mean()
                    y /= jump
                else:

                    y /= jump

            XAS_list.append(y)
            # la_list.append(rowphase)

        # print(la_list)

        XAS = np.mean(np.array(XAS_list), axis=0)
        # laa = np.mean(la_list)
        # print(laa)
        # laalist.append(laa)
        peak_list.append(XAS.max())

        plt.plot(energy, XAS, label='#%d-#%d,laa=%5.3f' % (sublist[0], sublist[-1], laa_list[iteration]))

        # print()

        iteration = iteration + 1

        # print(peak_list)
    laa_list = np.array(laa_list)

    plt.legend(loc=0, frameon=False)
    plt.xlabel('Energy (eV)', fontsize=14)
    plt.ylabel('XAS (arb. units)', fontsize=14)
    plt.tick_params(direction='in', labelsize=14)
    if m.endstation == 'Magnet':
        plt.suptitle(
            '#%d-#%d, %s, %s, T=%5.2f K,\n' r'H$_x$=%5.1f T, H$_y$=%5.1f T, H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
            scanlist[0], sublist[-1], sample_name, mode, tmp, fieldx, fieldy, fieldz, rot))
    if m.endstation in ['XABS', 'DD']:
        plt.suptitle('#%d-#%d, %s, %s, T=%5.2f K, H = 0 T,' r' $\theta=%5.1f^{\circ}$' % (
        scanlist[0], sublist[-1], sample_name, mode, tmp, rot))

    if peak:
        plt.figure()
        if m.endstation == 'Magnet':
            plt.suptitle(
                '#%d-#%d, %s, %s, T=%5.2f K,\n' r'H$_x$=%5.1f T, H$_y$=%5.1f T, H$_z$=%5.1f T, $\theta=%5.1f^{\circ}$' % (
                scanlist[0], sublist[-1], sample_name, mode, tmp, fieldx, fieldy, fieldz, rot))
        if m.endstation in ['XABS', 'DD']:
            plt.suptitle('#%d-#%d, %s, %s, T=%5.2f K, H = 0 T,' r' $\theta=%5.1f^{\circ}$' % (
            scanlist[0], sublist[-1], sample_name, mode, tmp, rot))

        plt.plot(laa_list, peak_list, 'o')
        plt.xlabel(r'laa ($^{\circ}$)', fontsize=14)
        plt.ylabel('XAS peak (arb. units)', fontsize=14)
        plt.tick_params(direction='in', labelsize=14)
        plt.tight_layout(rect=[0, 0.03, 1, 0.93])

    if save:
        plt.savefig(savedir + 'figures/' + '%d-%d_%s_XAS.png' % (scanlist[0], scanlist[-1], sample_name))


def hysteresis1branch_Nexus(scanlist, sample_name, exclude_list=None, save=False):
    """Plot hysteresis with one branch only in TEY and TFY mode;

    Parameters
    ------------
    scanlist: list with scan numbers (pc and nc scans)

    sample_name: add the name of the sample as string; e.g. 'Sample 1'

    exclude_list: list of magnetic fields to be excluded from the analysis

    save: if True, saves the plots and the .dat file with the results

    Returns
    --------
    Plot of hysteresis for each polarisation and ramp up and down
    """

    TEY_pc_up = []
    TEY_pc_down = []
    TEY_nc_up = []
    TEY_nc_down = []

    TFY_pc_up = []
    TFY_pc_down = []
    TFY_nc_up = []
    TFY_nc_down = []

    "Getting information from the first scan"

    d = readscan_Nexus(scanlist[0])

    if d.metadata.endstation == ['XABS', 'DD']:
        print('Error!!! This function just works for the magnet endstation')
        return

    else:
        if 'Tsample_mag' in d.metadata:
            tmp = str(d.metadata.Tsample_mag)
        else:
            tmp = 'n/a'

        if 'scmth' in d.metadata:
            rot = str(int(d.metadata.scmth))
        else:
            rot = 'n/a'

    ttl1 = r'#%d-#%d, %s, T=%s K, $\theta=%s^{\circ}$' % (scanlist[0], scanlist[-1], sample_name, tmp, rot)

    plt.figure(figsize=[9, 6])
    plt.suptitle(ttl1, fontsize=14)
    ax0 = plt.subplot(2, 2, 1)
    ax1 = plt.subplot(2, 2, 2)
    ax2 = plt.subplot(2, 2, 3)
    ax3 = plt.subplot(2, 2, 4)

    for scanno in scanlist:
        field_filtered = []
        index_list = []
        TFY_filtered = []
        TFY_exclude = []
        TEY_filtered = []
        TEY_exclude = []

        d = readscan_Nexus(scanno)
        field = d.hyst2

        TEY = d.ridio
        TFY = d.rifio

        "Removing the region defined in exclude_list"

        if exclude_list is not None:
            if type(exclude_list) != list:
                exclude_list = exclude_list.tolist()
                exclude_list = [round(num, 1) for num in exclude_list]
                # print(exclude_list)

            else:
                exclude_list = exclude_list

            for index, val in enumerate(field):
                if val not in exclude_list:
                    field_filtered.append(val)

                else:
                    index_list.append(index)

            "Removing the region close to magz=0 in the TEY and TFY arrays "

            for item, val in enumerate(TEY):
                if item not in index_list:
                    TEY_filtered.append(val)
                else:
                    TEY_exclude.append(val)

            for item, val in enumerate(TFY):
                if item not in index_list:
                    TFY_filtered.append(val)
                else:
                    TFY_exclude.append(val)

        else:
            field_filtered = field
            TEY_filtered = TEY
            TFY_filtered = TFY

        if d.metadata.iddgap == 100:
            rowphase = d.metadata.idutrp
        else:
            rowphase = d.metadata.iddtrp

        pol = d.metadata.pola

        if pol == 'pc':
            if field_filtered[-1] > field_filtered[1]:
                ax0.plot(field_filtered, TEY_filtered, color='C0', label='pc, up')
                ax1.plot(field_filtered, TFY_filtered, color='C0', label='pc, up')
                TEY_pc_up.append(TEY_filtered)
                TFY_pc_up.append(TFY_filtered)
            else:
                ax0.plot(field_filtered, TEY_filtered, '--', color='C0', label='pc,down')
                ax1.plot(field_filtered, TFY_filtered, '--', color='C0', label='pc,down')
                TEY_filtered = np.flipud(TEY_filtered)
                TFY_filtered = np.flipud(TFY_filtered)

                TEY_pc_down.append(TEY_filtered)
                TFY_pc_down.append(TFY_filtered)

        if pol == 'nc':
            if field_filtered[-1] > field_filtered[1]:
                ax0.plot(field_filtered, TEY_filtered, color='C1', label='nc, up')
                ax1.plot(field_filtered, TFY_filtered, color='C1', label='nc, up')
                TEY_nc_up.append(TEY_filtered)
                TFY_nc_up.append(TFY_filtered)
            else:
                ax0.plot(field_filtered, TEY_filtered, '--', color='C1', label='nc,down')
                ax1.plot(field_filtered, TFY_filtered, '--', color='C1', label='nc,down')
                TEY_filtered = np.flipud(TEY_filtered)
                TFY_filtered = np.flipud(TFY_filtered)

                TEY_nc_down.append(TEY_filtered)
                TFY_nc_down.append(TFY_filtered)

    ax0.legend(loc=0, frameon=False, fontsize=10)
    ax0.set_ylabel('TEY (arb. units)', fontsize=12)
    ax0.tick_params(direction='in', labelbottom=False, labelsize=12)
    ax1.legend(loc=0, frameon=False, fontsize=10)
    ax1.set_ylabel('TFY (arb. units)', fontsize=12)
    ax1.tick_params(direction='in', labelbottom=False, labelsize=12)

    TEY_pc_up = np.array(TEY_pc_up)
    TEY_pc_down = np.array(TEY_pc_down)
    TEY_nc_up = np.array(TEY_nc_up)
    TEY_nc_down = np.array(TEY_nc_down)

    TFY_pc_up = np.array(TFY_pc_up)
    TFY_pc_down = np.array(TFY_pc_down)
    TFY_nc_up = np.array(TFY_nc_up)
    TFY_nc_down = np.array(TFY_nc_down)

    if field_filtered[-1] > field_filtered[1]:
        TEY_xmcd_up = TEY_pc_up - TEY_nc_up
        TFY_xmcd_up = TFY_pc_up - TFY_nc_up
    if field_filtered[-1] < field_filtered[1]:
        TEY_xmcd_down = TEY_pc_down - TEY_nc_down
        TFY_xmcd_down = TFY_pc_down - TFY_nc_down

    "getting field values based on the first scan of a sequence"

    if field_filtered[-1] > field_filtered[1]:
        field_final = field_filtered
        num_TEY = len(TEY_pc_up)
        num_TFY = len(TFY_pc_up)

    else:
        field_final = np.flipud(field_filtered)
        num_TEY = len(TEY_pc_down)
        num_TFY = len(TFY_pc_down)

    for i in range(num_TEY):
        if field_filtered[-1] > field_filtered[1]:
            ax2.plot(field_final, TEY_xmcd_up[i], label='xmcd_up')
        else:
            ax2.plot(field_final, TEY_xmcd_down[i], label='xmcd_down')
            print(TEY_xmcd_down)
    ax2.legend(loc=0, frameon=False, fontsize=12)
    ax2.set_ylabel('TEY XMCD (arb. units)', fontsize=12)
    ax2.set_xlabel('Magnetic Field (T)', fontsize=12)
    ax2.tick_params(direction='in', labelsize=12)

    for i in range(num_TFY):
        if field_filtered[-1] > field_filtered[1]:
            ax3.plot(field_final, TFY_xmcd_up[i], label='xmcd_up')
        else:
            ax3.plot(field_final, TFY_xmcd_down[i], label='xmcd_down')
    ax3.legend(loc=0, frameon=False, fontsize=12)
    ax3.set_ylabel('TFY XMCD (arb. units)', fontsize=12)
    ax3.set_xlabel('Magnetic Field (T)', fontsize=12)
    ax3.tick_params(direction='in', labelsize=12)

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    fig, axs = plt.subplots(1, 2, figsize=(9, 5))
    for i in range(num_TEY):
        if field_filtered[-1] > field_filtered[1]:
            axs[0].plot(field_final, TEY_xmcd_up[i], '-o', color='C2', label='xmcd_up')
        else:
            axs[0].plot(field_final, TEY_xmcd_down[i], '--o', color='C2', label='xmcd_down')
    axs[0].legend(loc=0, frameon=False, fontsize=12)
    axs[0].set_ylabel('TEY XMCD (arb. units)', fontsize=14)
    axs[0].set_xlabel('Magnetic Field (T)', fontsize=14)
    axs[0].tick_params(direction='in', labelsize=14)

    if field_filtered[-1] > field_filtered[1]:
        TEY_xmcd_final = TEY_xmcd_up
        TFY_xmcd_final = TFY_xmcd_up
    else:
        TEY_xmcd_final = TEY_xmcd_down
        TFY_xmcd_final = TFY_xmcd_down

    for i in range(num_TFY):
        if field_filtered[-1] > field_filtered[1]:
            axs[1].plot(field_final, TFY_xmcd_up[i], '-o', color='C3', label='xmcd_up')
        else:
            axs[1].plot(field_final, TFY_xmcd_down[i], '--o', color='C3', label='xmcd_down')
    axs[1].legend(loc=0, frameon=False, fontsize=12)
    axs[1].set_xlabel('Magnetic Field (T)', fontsize=14)
    axs[1].tick_params(direction='in', labelleft=False, labelright=True, right=True, labelsize=14)
    axs[1].set_ylabel('TFY XMCD (arb. units)', fontsize=14)
    axs[1].yaxis.set_label_position("right")
    plt.suptitle(ttl1, fontsize=14)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    if save:
        plt.savefig(savedir + 'figures/' + '%d-%d_%s_hyst.png' % (scanlist[0], scanlist[-1], sample_name))

        for i in range(num_TEY):
            txt = savedir + 'data/' + 'TEY_%d-%d_%s_hyst_%d.dat' % (scanlist[0], scanlist[-1], sample_name, i)
            f = open(txt, 'w')
            f.write('B[T]  pc_up  pc_down nc_up  nc_down   xmcd_up    xmcd_down\n')
            for m in range(len(field_final)):
                help = '{:5.2f}{:10.6f}{:10.6f}{:10.6f}{:10.6f}{:10.6f}{:10.6f}\n'
                f.write(
                    help.format(field_final[m], TEY_pc_up[i][m], TEY_pc_down[i][m], TEY_nc_up[i][m], TEY_nc_down[i][m],
                                TEY_xmcd_up[i][m], TEY_xmcd_down[i][m]))
            f.close()

        for i in range(num_TFY):
            txt = savedir + 'data/' + 'TFY_%d-%d_%s_hyst_%d.dat' % (scanlist[0], scanlist[-1], sample_name, i)
            f = open(txt, 'w')
            f.write('B[T]  pc_up  pc_down nc_up  nc_down   xmcd_up    xmcd_down\n')
            for m in range(len(field_final)):
                help = '{:5.2f}{:10.6f}{:10.6f}{:10.6f}{:10.6f}{:10.6f}{:10.6f}\n'
                f.write(
                    help.format(field_final[m], TFY_pc_up[i][m], TFY_pc_down[i][m], TFY_nc_up[i][m], TFY_nc_down[i][m],
                                TFY_xmcd_up[i][m], TFY_xmcd_down[i][m]))
            f.close()

    return field_final, TEY_xmcd_final, TFY_xmcd_final


def hysteresis_Nexus(scanlist, sample_name, exclude_list=None, save=False):
    """Plot hysteresis in TEY and TFY mode;

    Parameters
    ------------
    scanlist: list with scan numbers (pc and nc scans)

    sample_name: add the name of the sample as string; e.g. 'Sample 1'

    exclude_list: list of magnetic fields to be excluded from the analysis

    save: if True, saves the plots and the .dat file with the results

    Returns
    --------
    Plot of hysteresis for each polarisation and ramp up and down
    """

    TEY_pc_up = []
    TEY_pc_down = []
    TEY_nc_up = []
    TEY_nc_down = []

    TFY_pc_up = []
    TFY_pc_down = []
    TFY_nc_up = []
    TFY_nc_down = []

    "Getting information from the first scan"

    d = readscan_Nexus(scanlist[0])

    if d.metadata.endstation == ['XABS', 'DD']:
        print('Error!!! This function just works for the magnet endstation')
        return

    else:
        if 'Tsample_mag' in d.metadata:
            tmp = str(d.metadata.Tsample_mag)
        else:
            tmp = 'n/a'

        if 'scmth' in d.metadata:
            rot = str(int(d.metadata.scmth))
        else:
            rot = 'n/a'

    ttl1 = r'#%d-#%d, %s, T=%s K, $\theta=%s^{\circ}$' % (scanlist[0], scanlist[-1], sample_name, tmp, rot)

    plt.figure(figsize=[9, 6])
    plt.suptitle(ttl1, fontsize=14)
    ax0 = plt.subplot(2, 2, 1)
    ax1 = plt.subplot(2, 2, 2)
    ax2 = plt.subplot(2, 2, 3)
    ax3 = plt.subplot(2, 2, 4)

    for scanno in scanlist:
        field_filtered = []
        index_list = []
        TFY_filtered = []
        TFY_exclude = []
        TEY_filtered = []
        TEY_exclude = []

        d = readscan_Nexus(scanno)
        field = d.hyst2

        TEY = d.ridio
        TFY = d.rifio

        "Removing the region defined in exclude_list"

        if exclude_list is not None:
            if type(exclude_list) != list:
                exclude_list = exclude_list.tolist()
                exclude_list = [round(num, 1) for num in exclude_list]
                # print(exclude_list)

            else:
                exclude_list = exclude_list

            for index, val in enumerate(field):
                if val not in exclude_list:
                    field_filtered.append(val)

                else:
                    index_list.append(index)

            "Removing the region close to mgaz=0 in the TEY and TFY arrays "

            for item, val in enumerate(TEY):
                if item not in index_list:
                    TEY_filtered.append(val)
                else:
                    TEY_exclude.append(val)

            for item, val in enumerate(TFY):
                if item not in index_list:
                    TFY_filtered.append(val)
                else:
                    TFY_exclude.append(val)

        else:
            field_filtered = field
            TEY_filtered = TEY
            TFY_filtered = TFY

        if d.metadata.iddgap == 100:
            rowphase = d.metadata.idutrp
        else:
            rowphase = d.metadata.iddtrp

        pol = d.metadata.pola

        if pol == 'pc':
            if field_filtered[-1] > field_filtered[1]:
                ax0.plot(field_filtered, TEY_filtered, color='C0', label='pc, up')
                ax1.plot(field_filtered, TFY_filtered, color='C0', label='pc, up')
                TEY_pc_up.append(TEY_filtered)
                TFY_pc_up.append(TFY_filtered)
            else:
                ax0.plot(field_filtered, TEY_filtered, '--', color='C0', label='pc,down')
                ax1.plot(field_filtered, TFY_filtered, '--', color='C0', label='pc,down')
                TEY_filtered = np.flipud(TEY_filtered)
                TFY_filtered = np.flipud(TFY_filtered)

                TEY_pc_down.append(TEY_filtered)
                TFY_pc_down.append(TFY_filtered)

        if pol == 'nc':
            if field_filtered[-1] > field_filtered[1]:
                ax0.plot(field_filtered, TEY_filtered, color='C1', label='nc, up')
                ax1.plot(field_filtered, TFY_filtered, color='C1', label='nc, up')
                TEY_nc_up.append(TEY_filtered)
                TFY_nc_up.append(TFY_filtered)
            else:
                ax0.plot(field_filtered, TEY_filtered, '--', color='C1', label='nc,down')
                ax1.plot(field_filtered, TFY_filtered, '--', color='C1', label='nc,down')
                TEY_filtered = np.flipud(TEY_filtered)
                TFY_filtered = np.flipud(TFY_filtered)

                TEY_nc_down.append(TEY_filtered)
                TFY_nc_down.append(TFY_filtered)

    ax0.legend(loc=0, frameon=False, fontsize=10)
    ax0.set_ylabel('TEY (arb. units)', fontsize=12)
    ax0.tick_params(direction='in', labelbottom=False, labelsize=12)
    ax1.legend(loc=0, frameon=False, fontsize=10)
    ax1.set_ylabel('TFY (arb. units)', fontsize=12)
    ax1.tick_params(direction='in', labelbottom=False, labelsize=12)

    TEY_pc_up = np.array(TEY_pc_up)
    TEY_pc_down = np.array(TEY_pc_down)
    TEY_nc_up = np.array(TEY_nc_up)
    TEY_nc_down = np.array(TEY_nc_down)

    TFY_pc_up = np.array(TFY_pc_up)
    TFY_pc_down = np.array(TFY_pc_down)
    TFY_nc_up = np.array(TFY_nc_up)
    TFY_nc_down = np.array(TFY_nc_down)

    TEY_xmcd_up = TEY_pc_up - TEY_nc_up
    TEY_xmcd_down = TEY_pc_down - TEY_nc_down

    TFY_xmcd_up = TFY_pc_up - TFY_nc_up
    TFY_xmcd_down = TFY_pc_down - TFY_nc_down

    "getting field values based on the first scan of a sequence"

    if field_filtered[-1] > field_filtered[1]:
        field_final = field_filtered

    else:
        field_final = np.flipud(field_filtered)

    for i in range(len(TEY_pc_up)):
        ax2.plot(field_final, TEY_xmcd_up[i], label='xmcd_up')
        ax2.plot(field_final, TEY_xmcd_down[i], label='xmcd_down')
    ax2.legend(loc=0, frameon=False, fontsize=12)
    ax2.set_ylabel('TEY XMCD (arb. units)', fontsize=12)
    ax2.set_xlabel('Magnetic Field (T)', fontsize=12)
    ax2.tick_params(direction='in', labelsize=12)

    for i in range(len(TFY_pc_up)):
        ax3.plot(field_final, TFY_xmcd_up[i], label='xmcd_up')
        ax3.plot(field_final, TFY_xmcd_down[i], label='xmcd_down')
    ax3.legend(loc=0, frameon=False, fontsize=12)
    ax3.set_ylabel('TFY XMCD (arb. units)', fontsize=12)
    ax3.set_xlabel('Magnetic Field (T)', fontsize=12)
    ax3.tick_params(direction='in', labelsize=12)

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    fig, axs = plt.subplots(1, 2, figsize=(9, 5))
    for i in range(len(TEY_pc_up)):
        axs[0].plot(field_final, TEY_xmcd_up[i], '-o', color='C2', label='xmcd_up')
        axs[0].plot(field_final, TEY_xmcd_down[i], '--o', color='C2', label='xmcd_down')
    axs[0].legend(loc=0, frameon=False, fontsize=12)
    axs[0].set_ylabel('TEY XMCD (arb. units)', fontsize=14)
    axs[0].set_xlabel('Magnetic Field (T)', fontsize=14)
    axs[0].tick_params(direction='in', labelsize=14)

    for i in range(len(TFY_pc_up)):
        axs[1].plot(field_final, TFY_xmcd_up[i], '-o', color='C3', label='xmcd_up')
        axs[1].plot(field_final, TFY_xmcd_down[i], '--o', color='C3', label='xmcd_down')
    axs[1].legend(loc=0, frameon=False, fontsize=12)
    axs[1].set_xlabel('Magnetic Field (T)', fontsize=14)
    axs[1].tick_params(direction='in', labelleft=False, labelright=True, right=True, labelsize=14)
    axs[1].set_ylabel('TFY XMCD (arb. units)', fontsize=14)
    axs[1].yaxis.set_label_position("right")
    plt.suptitle(ttl1, fontsize=14)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    if save:
        plt.savefig(savedir + 'figures/' + '%d-%d_%s_hyst.png' % (scanlist[0], scanlist[-1], sample_name))

        for i in range(len(TEY_pc_up)):
            txt = savedir + 'data/' + 'TEY_%d-%d_%s_hyst_%d.dat' % (scanlist[0], scanlist[-1], sample_name, i)
            f = open(txt, 'w')
            f.write('B[T]  pc_up  pc_down nc_up  nc_down   xmcd_up    xmcd_down\n')
            for m in range(len(field_final)):
                help = '{:5.2f}{:10.6f}{:10.6f}{:10.6f}{:10.6f}{:10.6f}{:10.6f}\n'
                f.write(
                    help.format(field_final[m], TEY_pc_up[i][m], TEY_pc_down[i][m], TEY_nc_up[i][m], TEY_nc_down[i][m],
                                TEY_xmcd_up[i][m], TEY_xmcd_down[i][m]))
            f.close()

        for i in range(len(TFY_pc_up)):
            txt = savedir + 'data/' + 'TFY_%d-%d_%s_hyst_%d.dat' % (scanlist[0], scanlist[-1], sample_name, i)
            f = open(txt, 'w')
            f.write('B[T]  pc_up  pc_down nc_up  nc_down   xmcd_up    xmcd_down\n')
            for m in range(len(field_final)):
                help = '{:5.2f}{:10.6f}{:10.6f}{:10.6f}{:10.6f}{:10.6f}{:10.6f}\n'
                f.write(
                    help.format(field_final[m], TFY_pc_up[i][m], TFY_pc_down[i][m], TFY_nc_up[i][m], TFY_nc_down[i][m],
                                TFY_xmcd_up[i][m], TFY_xmcd_down[i][m]))
            f.close()

    return field_final, TEY_xmcd_up, TEY_xmcd_down, TFY_xmcd_up, TFY_xmcd_down, field, TEY, TFY


def shirley_calculate(x, y, tol=1e-5, maxit=10):
    """ S = specs.shirley_calculate(x,y, tol=1e-5, maxit=10)
    Calculate the best auto-Shirley background S for a dataset (x,y). Finds the biggest peak
    and then uses the minimum value either side of this peak as the terminal points of the
    Shirley background.
    The tolerance sets the convergence criterion, maxit sets the maximum number
    of iterations.
    """
    DEBUG = False

    # Make sure we've been passed arrays and not lists.
    x = array(x)
    y = array(y)

    # Sanity check: Do we actually have data to process here?
    if not (x.any() and y.any()):
        print("specs.shirley_calculate: One of the arrays x or y is empty. Returning zero background.")
        return zeros(x.shape)

    # Next ensure the energy values are *decreasing* in the array,
    # if not, reverse them.
    if x[0] < x[-1]:
        is_reversed = True
        x = x[::-1]
        y = y[::-1]
    else:
        is_reversed = False

    # Locate the peaks
    maxidx = abs(y - max(y)).argmin()

    # It's possible that maxidx will be 0 or -1. If that is the case,
    # we can't use this algorithm, we return a zero background.
    if maxidx == 0 or maxidx >= len(y) - 1:
        print("specs.shirley_calculate: Boundaries too high for algorithm: returning a zero background.")
        return zeros(x.shape)

    # Locate the minima either side of maxidx.
    lmidx = abs(y[0:maxidx] - min(y[0:maxidx])).argmin()
    rmidx = abs(y[maxidx:] - min(y[maxidx:])).argmin() + maxidx
    xl = x[lmidx]
    yl = y[lmidx]
    xr = x[rmidx]
    yr = y[rmidx]

    # Locate second peak#

    maxidx2 = abs(y[0:lmidx] - max(y[0:lmidx])).argmin()

    # It's possible that maxidx will be 0 or -1. If that is the case,
    # we can't use this algorithm, we return a zero background.
    if (maxidx2 == 0 or maxidx2 >= len(y) - 1):
        print("specs.shirley_calculate: Boundaries too high for algorithm: returning a zero background.")
        return zeros(x.shape)

    # Locate the minima either side of maxidx.
    lmidx2 = abs(y[0:lmidx][0:maxidx2] - min(y[0:lmidx][0:maxidx2])).argmin()
    rmidx2 = abs(y[0:lmidx][maxidx2:] - min(y[0:lmidx][maxidx2:])).argmin() + maxidx2
    xl2 = x[lmidx2]
    yl2 = y[lmidx2]
    xr2 = x[rmidx2]
    yr2 = y[rmidx2]

    # plt.figure()
    # plt.plot(x,y)
    # plt.plot(x[maxidx2],y[maxidx2],'x',color='green')
    # plt.plot(xl2,yl2,'x',color='orange')
    # plt.plot(xr2,yr2,'x',color='black')

    # print(x[lmidx],x[rmidx])

    # Max integration index
    imax = rmidx - 1
    imax2 = rmidx2 - 1

    # Initial value of the background shape B. The total background S = yr + B,
    # and B is equal to (yl - yr) below lmidx and initially zero above.
    B1 = zeros(x.shape)
    B1[:lmidx] = yl - yr
    # print(B1)
    Bnew1 = B1.copy()
    B2 = zeros(x.shape)
    B2[:lmidx2] = yl2 - yr2
    # print(B2)
    Bnew2 = B2.copy()

    it = 0
    while it < maxit:
        if DEBUG:
            print("Shirley iteration: ", it)
        # Calculate new k = (yl - yr) / (int_(xl)^(xr) J(x') - yr - B(x') dx')
        ksum1 = 0.0
        for i in range(lmidx, imax):
            ksum1 += (x[i] - x[i + 1]) * 0.5 * (y[i] + y[i + 1]
                                                - 2 * yr - B1[i] - B1[i + 1])

        k1 = (yl - yr) / ksum1
        # print(k1)

        ksum2 = 0.0

        for i in range(lmidx2, imax2):
            ksum2 += (x[i] - x[i + 1]) * 0.5 * (y[i] + y[i + 1]
                                                - 2 * yr2 - B2[i] - B2[i + 1])

        k2 = (yl2 - yr2) / ksum2

        # Calculate new B
        for i in range(lmidx, rmidx):
            ysum1 = 0.0
            for j in range(i, imax):
                ysum1 += (x[j] - x[j + 1]) * 0.5 * (y[j] +
                                                    y[j + 1] - 2 * yr - B1[j] - B1[j + 1])
            Bnew1[i] = k1 * ysum1
            # print(Bnew[i])
        # If Bnew is close to B, exit.

        if norm(Bnew1 - B1) < tol:
            B1 = Bnew1.copy()
            break
        else:
            B1 = Bnew1.copy()

        for i in range(lmidx2, rmidx2):
            ysum2 = 0.0
            for j in range(i, imax2):
                ysum2 += (x[j] - x[j + 1]) * 0.5 * (y[j] +
                                                    y[j + 1] - 2 * yr2 - B2[j] - B2[j + 1])
            Bnew2[i] = k2 * ysum2
            # print(Bnew[i])
        # If Bnew is close to B, exit.

        if norm(Bnew2 - B2) < tol:
            B2 = Bnew2.copy()
            break
        else:
            B2 = Bnew2.copy()
        it += 1

    if it >= maxit:
        print("specs.shirley_calculate: Max iterations exceeded before convergence.")

    Btotal = zeros(x.shape)

    for i in range(0, rmidx2):
        Btotal[i] = (yr2 + B2)[i]

    for i in range(rmidx2, len(Btotal)):
        Btotal[i] = (yr + B1)[i]
    # print(Btotal)
    if is_reversed:
        return Btotal[::-1]

    else:
        return Btotal


def natural_linewidth(element):
    """
    Returns the value of natural linewidth for the element (at L2 and L3 edges)
    """

    L3_edges = {'Ti': 0.22, 'V': 0.24, 'Cr': 0.27, 'Mn': 0.32, 'Fe': 0.36, 'Co': 0.43, 'Ni': 0.48, 'Cu': 0.56,
                'Zn': 0.65, 'Zr': 1.57, 'Nb': 1.66, 'Mo': 1.78, 'Tc': 1.91, 'Ru': 2.0, 'Rh': 2.13, 'Pd': 2.25,
                'Ag': 2.40, 'Cd': 2.50, 'In': 2.65, 'Hf': 4.80, 'Ta': 4.88, 'W': 4.98, 'Re': 5.04, 'Os': 5.16,
                'Ir': 5.25, 'Pt': 5.31, 'Au': 5.41}
    L2_edges = {'Ti': 0.24, 'V': 0.26, 'Cr': 0.29, 'Mn': 0.34, 'Fe': 0.37, 'Co': 0.43, 'Ni': 0.52, 'Cu': 0.62,
                'Zn': 0.72, 'Zr': 1.78, 'Nb': 1.87, 'Mo': 1.97, 'Tc': 2.08, 'Ru': 2.23, 'Rh': 2.35, 'Pd': 2.43,
                'Ag': 2.57, 'Cd': 2.62, 'In': 2.72, 'Hf': 5.02, 'Ta': 5.15, 'W': 5.33, 'Re': 5.48, 'Os': 5.59,
                'Ir': 5.69, 'Pt': 5.86, 'Au': 6.0}

    return L3_edges[element], L2_edges[element]


def arctan(x, y, element):
    """
    Actangent background of XAS. Still need to implement conditions where the script won't work

    Input:x: energy
          y: XAS (XAS(pc)+XAS(nc)/2)
          element: absorption edge of interest

    return:xas (with background removed) and arctangent function
    """

    background = ConstantModel(prefix='back_')
    peak1 = StepModel(prefix='peak1_', form='arctan')
    peak2 = StepModel(prefix='peak2_', form='arctan')

    mod = background + peak1 + peak2
    pars = mod.make_params()

    "Defining the parameters"

    maxidx = abs(y - max(y)).argmin()

    # Locate the minima either side of maxidx.
    lmidx = abs(y[0:maxidx] - min(y[0:maxidx])).argmin()
    rmidx = abs(y[maxidx:] - min(y[maxidx:])).argmin() + maxidx
    xl = x[lmidx]
    yl = y[lmidx]
    xr = x[rmidx]
    yr = y[rmidx]

    maxidx2 = abs(y[rmidx:] - max(y[rmidx:])).argmin() + rmidx

    # Locate the minima either side of maxidx.
    rmidx2 = abs(y[maxidx2:] - min(y[maxidx2:])).argmin() + maxidx2
    lmidx2 = abs(y[maxidx:maxidx2] - min(y[maxidx:maxidx2])).argmin() + maxidx
    xl2 = x[lmidx2]
    yl2 = y[lmidx2]
    xr2 = x[rmidx2]
    yr2 = y[rmidx2]

    peak1_amplitude_init = (yr - yl)
    peak1_center_init = x[maxidx]
    peak1_sigma_init = natural_linewidth(element)[0]

    peak2_amplitude_init = (yr2 - yl2)
    peak2_center_init = x[maxidx2]
    peak2_sigma_init = natural_linewidth(element)[1]

    x_back = x[np.logical_and(x > x[0], x < x[0] + 3)]
    y_back = y[np.logical_and(x > x[0], x < x[0] + 3)]
    pars_back = background.guess(y_back, x=x_back)
    out_back = background.fit(y_back, pars_back, x=x_back)
    pars['back_c'].set(out_back.params['back_c'].value, vary=False)

    # Fit #

    pars['peak1_amplitude'].set(peak1_amplitude_init, vary=False)
    pars['peak1_center'].set(peak1_center_init, min=xl, max=xr, vary=False)
    pars['peak1_sigma'].set(peak1_sigma_init, vary=False)  # modified constraint

    pars['peak2_amplitude'].set(peak2_amplitude_init, vary=False)
    pars['peak2_center'].set(peak2_center_init, min=xl2, max=xr2, vary=False)
    pars['peak2_sigma'].set(peak2_sigma_init, vary=False)

    out = mod.fit(y, pars, x=x)

    background_fit = background.eval(c=out.params['back_c'].value, x=x)
    xas = y - background_fit
    arctan = mod.eval(out.params, x=x) - background_fit

    return xas, arctan


def checkdiff_Nexus(scan1, scan2, channel='', bkg_type='', post_edge_norm=False, diff_norm=None, save=False):
    '''
    Check the subraction between scan1 and scan2 -  it calls the max_min_energy function which defines the range of energy where all the zacscans will be interpolated. This function allows for a quick check of the subtraction and gives more options to select the detector.

    Parameters
    ------------
    scan1 and scan2: scan numbers

    sample_name: add the name of the sample as string; e.g. 'Sample 1'

    mode: 'C1': drain current of TEY signal (without normalisation)
          'C2': I0
          'C3': front diode signal
          'C4': 90 deg. diode signal
          'C5': front diode signal
          'idio': C1/C2 - equivalent to TEY mode in calc_XMCD
          'ifio': C3/C2 - fluorescence yield (front diode) (equivalent to TFY_f1 in calc_XMCD)
          'ifioft': C4/C2 - fluorescence yield (90 deg. diode) (equivalent to TFY_90 in calc_XMCD)
          'ifiofb': C5/C2 - fluorescence yield (front diode) (equivalent to TFY_f2 in calc_XMCD)\
          If not specified, it uses idio;

    bck_type: 'flat': subtracts a constant;
              'norm': normalises pre-edge to 1;
              'linear': fits the pre-edge by a linear curve and subtract it

    post-edge_norm: if True, normalises the post-edge to 1

    xmcd_norm: 'jump': divide the diff signal signal by the jump=post_edge-pre-edge value (difference will be showed in %)
               'peak': divide the diff signal by the max value of XAS(scan1)+XAS(scan2)/2; usually it's the L3 peak (difference plot will be showed in %)
                None : the XMCD will be displayed without any division (XMCD will be showed in arb. units)

    save: if True, saves the 2 plots and the .dat file with the calculated xas and diff

    Returns
    --------
    energy: energy array
    diff: array with the difference between scan1 and scan2
    diff_std: array with diff propagated error

    Plots:
    1st Plot: left panel: normalised XAS spectra for scan1
              right panel: normalised XAS spectra for scan2

    2nd Plot: Upper panel: averaged XAS for scan1/scan2 polarisation
              Lower panel: reulting diff spectra and its standard deviation

    '''

    scanlist = [scan1, scan2]

    "Determining the energy range to be used as interpolation"

    energy = max_min_energy_Nexus(scanlist)

    "If using a LinearModel (lmfit) for background subtraction"
    background = LinearModel(prefix='back_')

    y_list = []
    jump_list = []

    for scanno in scanlist:

        d = readscan_Nexus(scanno)

        if d is None:
            print("One of the scans does not exist!")
            return

        m = d.metadata
        ks = d.keys()

        scan_type = m.command.split()[1]

        if scan_type != 'fastEnergy':
            continue

        if m.iddgap == 100:
            rowphase = m.idutrp
            undulator = 'idu'
        else:
            rowphase = m.iddtrp
            undulator = 'idd'

        if m.endstation == 'Magnet':
            fieldx = m.magx
            fieldy = m.magy
            fieldz = m.magz
            tmp = m.Tsample_mag
            rot = m.scmth

        if m.endstation == 'XABS':
            tmp = 300
            rot = m.xabstheta
            field = 0

        if m.endstation == 'DD':
            tmp = m.dd_T
            rot = m.ddth
            field = 0

        energy1 = d.fastEnergy

        if channel == 'C1':
            y = d.C1
            ylabel = 'C1 (arb. units)'

        elif channel == 'C2':
            y = d.C2
            ylabel = 'C2 (arb. units)'

        elif channel == 'C3':
            y = d.C3
            ylabel = 'C3 (arb. units)'

        elif channel == 'C4':
            y = d.C4
            ylabel = 'C4 (arb. units)'

        elif channel == 'C5':
            y = d.C5
            ylabel = 'C5 (arb. units)'

        elif channel == 'C6':
            y = d.C6
            ylabel = 'C6 (arb. units)'

        elif channel == 'idio':
            y = d.idio
            ylabel = 'idio (arb. units)'

        elif channel == 'ifio':
            y = d.ifio
            ylabel = 'ifio (arb. units)'

        elif channel == 'ifioft':
            y = d.ifioft
            ylabel = 'ifioft (arb. units)'

        elif channel == 'ifiofb':
            y = d.ifiofb
            ylabel = 'ifiofb (arb. units)'

        else:
            y = d.idio
            ylabel = 'idio (arb. units)'

        ### interpolate ####

        f = interp1d(energy1, y, kind='linear')

        y = f(energy)

        # background type#

        if bkg_type == 'flat':
            "Subtracting the background by a constant"

            y -= y[energy < energy[0] + 5].mean()
            jump = y[energy > energy[-1] - 5].mean() - y[energy < energy[0] + 5].mean()
            jump_list.append(jump)

        if bkg_type == 'norm':
            "Simple normalisation of background to 1"
            y /= y[energy < energy[0] + 5].mean()  # nomalise by the average of a range of energy
            jump = y[energy > energy[-1] - 5].mean() - y[energy < energy[0] + 5].mean()
            jump_list.append(jump)

        if bkg_type == 'linear':
            "Subtracting the background by a linear curve fit"
            energy_back = energy[np.logical_and(energy > energy[0], energy < energy[0] + 5)]
            XAS_back = y[np.logical_and(energy > energy[0], energy < energy[0] + 5)]
            pars_back = background.guess(XAS_back, x=energy_back)

            out_back = background.fit(XAS_back, pars_back, x=energy_back)

            background_fit = background.eval(slope=out_back.params['back_slope'].value,
                                             intercept=out_back.params['back_intercept'].value, x=energy)

            y = y - background_fit
            jump = y[energy > energy[-1] - 5].mean()
            jump_list.append(jump)

        if bkg_type == None:
            y = y
            jum_list.append(1)

        if post_edge_norm:
            if bkg_type == 'norm':
                y -= y[energy < energy[0] + 5].mean()
                jump = y[energy > energy[-1] - 5].mean()
                y /= jump
            else:

                y /= jump

        y_list.append(y)

    y_list = np.array(y_list)
    y_mean = np.mean(y_list, axis=0)
    y_mean_std = np.std(y_list, axis=0)
    # print(jump_list)
    jump_final = np.mean(jump_list)
    # print(jump_final)
    # print(TEY_mean[energy>energy[-1]-5].mean()-TEY_mean[energy<energy[0]+5].mean())

    if diff_norm == 'jump':

        diff = 100 * (1 / jump_final) * (y_list[0] - y_list[1])


    elif diff_norm == 'peak':
        if bkg_type == 'norm':
            peak = y_mean.max() - y_mean[energy < energy[0] + 5].mean()

        else:
            peak = y_mean.max()

        diff = 100 * (y_list[0] - y_list[1]) / peak



    else:
        diff = y_list[0] - y_list[1]

    plt.figure()
    ax = plt.subplot(2, 1, 1)
    ax.plot(energy, y_list[0], label='%d' % (scanlist[0]))
    ax.plot(energy, y_list[1], label='%d' % (scanlist[1]))
    ax.set_ylabel(ylabel, fontsize=14)
    ax.tick_params(direction='in', labelbottom=False, right=True, labelsize=14)
    ax.legend(loc=0, frameon=False)

    ax1 = plt.subplot(2, 1, 2)
    ax1.plot(energy, diff, label='%d-%d' % (scanlist[0], scanlist[1]))
    ax1.legend(loc=0, frameon=False)

    ax1.set_xlabel('Energy (eV)', fontsize=14)
    if diff_norm is None:
        ax1.set_ylabel('Difference (arb. units)', fontsize=14)
    else:
        ax1.set_ylabel('Difference (%)', fontsize=14)
    ax1.tick_params(direction='in', right=True, labelsize=14)

    plt.tight_layout()

    return energy, diff


def profile_Nexus(scan1, scan2, channel=''):
    """
    Subtraction of the two profile scans (scmy, scmx or m7pitch) on and off the absorption edge. This function helps to find the position of highest contrast.

    Parameters
    -------------
    scan1, scan2: two scans on and off the absorption edge
    channel: C1 (TEY), C3 or C5 (front diodes), C4 (90 deg. diode), idio, ifio, ifioft, ifiofb
    If no channel is specified, then it uses C1;

    Returns
    -------------
    Subtraction of scan(higher energy) with scan(lower energy)
    """

    scanlist = [scan1, scan2]

    y_list = []
    x_list = []
    en_list = []
    cmd_type = []

    for scanno in scanlist:

        d = readscan_Nexus(scanno)

        if d is None:
            print("One of the scans does not exist!")
            return

        m = d.metadata

        cmd = m.command

        en = m.energy

        if m.endstation == 'Magnet':

            if 'scmy' in cmd:
                x = d.scmy
                xlabel = 'scmy (mm)'

            elif 'scmx' in cmd:
                x = d.scmx
                xlabel = 'scmx (mm)'

            elif 'm7pitch' in cmd:
                x = d.m7pitch
                xlabel = r'm7pitch ($\mu$rad)'

            else:
                print('scan %d of wrong type' % scanno)

        if m.endstation == 'XABS':

            if 'xabsx' in cmd:
                x = d.xabsx
                xlabel = 'xabsx (mm)'

            elif 'xabsy' in cmd:
                x = d.xabsy
                xlabel = 'xabsy (mm)'

            elif 'm7pitch' in cmd:
                x = d.m7pitch
                xlabel = r'm7pitch ($\mu$rad)'

            else:
                print('scan %d of wrong type' % scanno)

        if m.endstation == 'DD':

            if 'ddx' in cmd:
                x = d.ddx
                xlabel = 'ddx (mm)'

            elif 'ddy' in cmd:
                x = d.ddy
                xlabel = 'ddy (mm)'

            elif 'ddz' in cmd:
                x = d.ddz
                xlabel = 'ddz (mm)'

            elif 'm7pitch' in cmd:
                x = d.m7pitch
                xlabel = r'm7pitch ($\mu$rad)'

            else:
                print('scan %d of wrong type' % scanno)

        if channel == 'C1':
            y = d.ca61sr
            ylabel = 'ca61sr'


        elif channel == 'C3':
            y = d.ca63sr
            ylabel = 'ca63sr'

        elif channel == 'C4':
            y = d.ca64sr
            ylabel = 'ca64sr'

        elif channel == 'C5':
            y = d.ca65sr
            ylabel = 'ca65sr'

        elif channel == 'idio':
            y = d.idio
            ylabel = 'idio'

        elif channel == 'ifio':
            y = d.ifio
            ylabel = 'ifio'

        elif channel == 'ifioft':
            y = d.ifioft
            ylabel = 'ifioft'

        elif channel == 'ifiofb':
            y = d.ifiofb
            ylabel = 'ifiofb'

        else:
            y = d.ca61sr
            ylabel = 'ca61sr'

        y_list.append(y)
        x_list.append(x)
        en_list.append(en)

        cmd_type.append(cmd.split()[1])

    y_list = np.array(y_list)
    x_list = np.array(x_list)
    en_list = np.array(en_list)
    cmd_type = np.array(cmd_type)

    'Checking if both scans are of same type'
    if cmd_type[0] != cmd_type[1]:
        print("Both scans need to be of the same type")
        return

    'Checking if both scans are of the same length - if not, it interpolates the data with less number of points'

    if len(x_list[0]) > len(x_list[1]):
        x = np.linspace(x_list[0].min(), x_list[0].max(), len(x_list[0]))
        f = interp1d(x_list[1], y_list[1], kind='linear')
        y1 = y_list[0]
        y2 = f(x)

    elif len(x_list[0]) < len(x_list[1]):
        x = np.linspace(x_list[1].min(), x_list[1].max(), len(x_list[1]))
        f = interp1d(x_list[0], y_list[0], kind='linear')

        y1 = f(x)
        y2 = y_list[1]

    else:
        y1 = y_list[0]
        y2 = y_list[1]

    if en_list[0] < en_list[1]:

        contrast = y2 - y1
        ttl = 'E$_2$-E$_1$'

    elif en_list[0] > en_list[1]:

        contrast = y1 - y2
        ttl = 'E$_1$-E$_2$'

    else:
        print("Error, scans need to have different energies")
        return

    plt.figure()
    ax = plt.subplot(2, 1, 1)
    ax.plot(x, y1, label='E$_1$ = %5.2f eV' % (en_list[0]))
    ax.plot(x, y2, label='E$_2$ = %5.2f eV' % (en_list[1]))
    ax.legend(loc=0, frameon=False, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=14)
    ax.tick_params(direction='in', labelbottom=False, right=True, labelsize=14)

    ax_1 = plt.subplot(2, 1, 2)
    ax_1.plot(x, contrast, '--', color='C2', label=ttl)
    ax_1.legend(loc=0, frameon=False, fontsize=12)
    ax_1.set_xlabel(xlabel, fontsize=14)
    ax_1.set_ylabel(ylabel, fontsize=14)
    ax_1.tick_params(direction='in', top=True, right=True, labelsize=14)

    plt.tight_layout()


def convert_zacscan(workdirectory, files):
    '''Example:
    workdirectory = '/dls/i06-1/data/2023/mm33456-2/'
    files = range(313553,313555)
    bl.convert_zacscan(workdirectory, files)'''

    num = len(files)
    for file in files:
        filename = 'i06-1-' + str(file)
        hf = h5py.File(workdirectory + filename + '.nxs', 'r')
        d1 = hf['entry']['instrument']
        fastEnergy = d1['fastEnergy']['value'][()]
        C1 = d1['fesData']['C1'][()]
        C2 = d1['fesData']['C2'][()]
        C3 = d1['fesData']['C3'][()]
        C4 = d1['fesData']['C4'][()]
        C5 = d1['fesData']['C5'][()]
        C6 = d1['fesData']['C6'][()]
        idio = d1['fesData']['idio'][()]
        ifio = d1['fesData']['ifio'][()]
        ifiofb = d1['fesData']['ifiofb'][()]
        ifioft = d1['fesData']['ifioft'][()]
        names = ['fastEnergy', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'idio', 'ifio', 'ifiofb', 'ifioft']
        f = open(workdirectory + 'processing/' + filename + '.txt', "w")
        f.write('E\tC1\tC2\tC3\tC4\tC5\tC6\tidio\tifio\tifiofb\tifioft\n')
        for i in range(len(C1)):
            f.write("%.2f\t%.0f\t%.0f\t%.0f\t%.0f\t%.0f\t%.0f\t%.4f\t%.4f\t%.4f\t%.4f\t\n" \
                    % (fastEnergy[i], C1[i], C2[i], C3[i], C4[i], C5[i], C6[i], idio[i], ifio[i], ifiofb[i], ifioft[i]))
        f.close()


def convert_energy_scan(workdirectory, files):
    '''Example:
    workdirectory = '/dls/i06-1/data/2023/mm33456-2/'
    files = (313365,313366)
    bl.convert_zacscan(workdirectory, files)'''

    num = len(files)
    for file in files:
        filename = 'i06-1-' + str(file)
        hf = h5py.File(workdirectory + filename + '.nxs', 'r')

        d1 = hf['entry']
        try:
            E = d1['ca61sr']['energy'][()]
        except:
            print('No energy!')
        else:
            try:
                C1 = d1['ca61sr']['ca61sr'][()]
            except:
                C1 = np.zeros_like(E)
            try:
                C2 = d1['ca61sr']['ca62sr'][()]
            except:
                C2 = np.zeros_like(E)
            try:
                C3 = d1['ca61sr']['ca63sr'][()]
            except:
                C3 = np.zeros_like(E)
            try:
                C4 = d1['ca61sr']['ca64sr'][()]
            except:
                C4 = np.zeros_like(E)
            try:
                C5 = d1['ca61sr']['ca65sr'][()]
            except:
                C5 = np.zeros_like(E)
            try:
                C6 = d1['ca61sr']['ca66sr'][()]
            except:
                C6 = np.zeros_like(E)
            try:
                idio = C1 / C2
                ifio = C3 / C2
                ifiofb = C4 / C2
                ifioft = C5 / C2
            except:
                print('Check if I0 is zero!')
            f = open(workdirectory + 'processing/' + filename + '.txt', "w")
            f.write('E\tC1\tC2\tC3\tC4\tC5\tC6\tidio\tifio\tifiofb\tifioft\n')
            for i in range(len(C1)):
                f.write("%.2f\t%.0f\t%.0f\t%.0f\t%.0f\t%.0f\t%.0f\t%.4f\t%.4f\t%.4f\t%.4f\t\n" \
                        % (E[i], C1[i], C2[i], C3[i], C4[i], C5[i], C6[i], idio[i], ifio[i], ifiofb[i], ifioft[i]))
            f.close()
