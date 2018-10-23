#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Base code implemented by Ajin Tom to read wav files and calculate the average spectrum.
Taken from https://github.com/ajintom/auto-spatial/blob/master/final/my_algo-Ajin%E2%80%99s%20MacBook%20Pro.ipynb

ERB implementation and modification to use with Answer Set Programming (ASP) by Flavio Everardo
flavio.everardo@cs.uni-potsdam.de
"""

## Imports
import numpy as np
from librosa import load, stft, magphase
from classes import erb as erb
from math import ceil, log, sqrt
import os
import matplotlib
from sys import platform
if platform == "linux" or platform == "linux2":
    # Linux
    matplotlib.use('agg')
elif platform == "darwin":
    # OS X
    matplotlib.use('TkAgg')
import matplotlib.pyplot as plt


"""
Load wav file and get spectral information
"""
def get_spectrum(track_name, sr, N, M, H):
    W  = np.hanning(M) # Window Type
    ## Load WAV File
    track,sr = load(track_name+'.wav', sr = sr, mono = 'True')
    ## Perform Short Term Fourier Transform
    stft_ = stft(y = track, n_fft = N,win_length=M, hop_length=H, window = 'hann')
    ## Magnitudes (excluding phase)
    magnitude, _ = magphase(stft_)
    magnitude = magnitude / np.sum(W) #normalising STFT output
    ## Spectrum Average
    spec_avg = np.average(magnitude,axis=1) 
    spec_avg = spec_avg/np.max(spec_avg)
    len_signal = spec_avg.shape[0] # filter bank length

    return spec_avg, len_signal

"""
Build ERB bands wrt the spectral information
"""
def get_erb_bands(spec_avg, len_signal, sr, B, low_lim, high_lim):
    # Equivalent Rectangular Bandwidth
    # Create an instance of the ERB filter bank class
    erb_bank = erb.EquivalentRectangularBandwidth(len_signal, sr, B, low_lim, high_lim)
    
    # Get ERB Bands and convert them to integer
    erb_bands = erb_bank.erb_bands
    erb_bands = list(map(int, erb_bands))

    # Get frequencies indexes
    freqs_index = erb_bank.freq_index
    # Get range of frequencies
    freqs = erb_bank.freqs.tolist()
    # Get frequency bandwidths
    bandwidths = erb_bank.bandwidths
    # Get center frequencies
    center_freqs = erb_bank.center_freqs
    # Get the filters
    filters = erb_bank.filters

    # Get amplitudes wrt the ERB/Center Freq
    erb_amp = []
    for i in range(len(freqs_index)):
        erb_amp.append(spec_avg[freqs_index[i]])

    ## Normalize ERBs amplitude
    max_erb_amp = max(erb_amp)
    erb_amp = erb_amp/max_erb_amp

    return erb_amp, bandwidths, freqs, center_freqs, filters

"""
Plot and save graphics
"""
def build_graphics(freqs, spec_avg, project_path, project_name, erbs, B, filters, tracks, show_plot):
    ## Plot
    plt.figure(figsize=(12,7))
    plt.subplot(311)
    plt.grid(True)
    plt.plot(freqs,filters[:, 1:-1])
    plt.title("%s Auditory filters"%B)
    plt.xlabel('Frequencies (Hz)')
    plt.ylabel('Power Ratio [0-1]')

    plt.subplot(312)
    plt.grid(True)
    for i in range(len(spec_avg)):
        plt.plot(freqs,spec_avg[i], label=tracks[i])
    plt.title(project_name+" Spectrums")
    plt.xlabel('Frequency')
    plt.xlim(xmin=20)
    plt.ylabel('Power Ratio [0-1]')
    plt.xscale('log')
    plt.legend()

    plt.subplot(313)
    plt.grid(True)
    for i in range(len(erbs)):
        erbs[i] = np.insert(erbs[i], 0, 0)
        plt.plot(erbs[i], label=tracks[i])
    plt.title(project_name+" ERB Scale")
    plt.xlabel('ERB Numbers (1-%s)'%B)
    plt.ylabel('Power Ratio [0-1]')
    plt.legend()
    
    plt.tight_layout()

    plt.savefig('%s/%s.png'%(project_path, project_name))
    if show_plot:
        plt.show()

"""
Build ASP Instances wrt the tracks in the project. 
Build atoms erb_band/3 and essential_band/2
"""
def build_asp_instance(file_handle, track_id, instance, erb_bands, threshold):
    file_handle.write("%% Instance: %s\n\n"%(instance))
    file_handle.write("%% erb_band(track id, erb band, amplitude *100).\n")
    file_handle.write("%% essential_erb(track id, erb band).\n")
    for i in range(len(erb_bands)):
        file_handle.write("erb_band(%s,%d,%d).\n"%(track_id, i+1, erb_bands[i]*100 ))
        #Normalize
        if erb_bands[i] >= threshold:
            # Essential frequency band for ASP instance
            file_handle.write("essential_band(%s,%d).\n"%(track_id,i+1))


""" 
dB to amp 
"""
def db2amp(db): # amplitude = 10^(db/20)
    return 10**(db/20)

""" 
amp to dB. amp is a value between 0 and 1 
"""
def amp2db(amp): # dB = 20 * log10(amplitude)
    dB = 20*(log(amp,10))
    return dB


"""
Parse Answer Sets and return information for csound parsing
"""
def parse_answer_sets_to_plan(file, tracks, answers, center_freqs, bandwidths):
    eqs = {}
    for atom in answers:
        if str(atom).startswith("cut(") or str(atom).startswith("boost("):
            track    = int(str(atom.arguments[0]))-1
            index    = int(str(atom.arguments[1]))
            freq     = center_freqs[index-1]
            start_db = amp2db(sqrt(int(str(atom.arguments[2]))/100.0))
            goal_db  = amp2db(sqrt(int(str(atom.arguments[4]))/100.0))
            diff_db  = abs(goal_db - start_db)
            eq_op    = atom.name
            bandw    = bandwidths[index-1]
            q_factor = freq/bandw

            plan_line = "%s:%s %s Hz, %s, %.1f dB  Q %.2f, from: %.1f dB, to: %.1f dB"%(track+1, tracks[track], int(ceil(freq)), eq_op, diff_db, q_factor, start_db, goal_db)
            print(plan_line)
            file.write(plan_line+"\n")

            if str(eq_op) == "cut":
                eqs.setdefault(track+1, []).append([tracks[track], int(ceil(freq)), float("%.1f"%(-diff_db)), float("%.2f"%q_factor)])
            elif str(eq_op) == "boost":
                eqs.setdefault(track+1, []).append([tracks[track], int(ceil(freq)), float("%.1f"%( diff_db)), float("%.2f"%q_factor)])

    return eqs
        
