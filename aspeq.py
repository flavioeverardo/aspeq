"""
ASPEQ: Automatic Equalizer using ASP with clingo 5 and Python. 
Extract audio features to build ERB bands per project and equalize them according to the masking between them.
"""

# Imports
import sys
import clingo
import argparse
import textwrap
import random
import datetime
import os
import wave
import contextlib
from classes import erb
from classes import audio_features as af
from classes import csd
from classes.count_propagator import Propagator

""" 
Parse Arguments 
"""
def parse_params():
    parser = argparse.ArgumentParser(prog='aspeq.py',
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     description=textwrap.dedent('''\
An automatic multitrack equalization tool using Answer Set Programming.
Default command-line: python aspeq.py --mixes=1 --project="demo" --masking-factor=0.5 --samples=32768 --erb=40 --essential-threshold=0.8 --analyze --verbose=1
                                     '''),

                                     epilog=textwrap.dedent('''\
aspeq is part of Potassco Labs: https://potassco.org/labs/
Get help/report bugs via : flavio.everardo@cs.uni-potsdam.de
                                     '''),)

    ## Input related to uniform solving and sampling
    basic_args = parser.add_argument_group("Basic Options")

    parser.add_argument("--benchmarks", action='store_true',
                        help="Generate benchmarks only, no grounding or solving calls.")
    parser.add_argument("--analyze", action='store_true',
                        help="Extract audio features. If false, aspeq uses the already calculated instances.")
    parser.add_argument("--mixes", type=int, default=1,
                        help="Number of desired answers/mixes. Default=1")
    parser.add_argument("--masking-factor", type=float, default=0.5,
                        help="Define the masking factor (0-1). Default: 0.5.")
    parser.add_argument("--project", type=str, default="demo",
                        help="Name of the project where all the stems are stored.")
    parser.add_argument("--samples", type=int, default=32768,
                        help="FFT size or number of samples (1000-32768). Default: 32768.")
    parser.add_argument("--erb", type=int, default=40,
                        help="Number of ERB bands (10-100). Default: 40.")
    parser.add_argument("--essential-threshold", type=float, default=0.8,
                        help="Define the threshold for essential ERB bands (0-1). Default: 0.8.")
    #parser.add_argument("--normalize", action='store_true',
    #                    help="Normalize the mixdowns")
    parser.add_argument("--s", type=int, default=-1,
                        help="Number of XOR constraints. Default: -1 = sampling off")
    parser.add_argument("--q", type=float, default=0.5,
                        help="Density of XOR constraints. Default: 0.5")
    parser.add_argument("--verbose", type=int, default=1, choices=[0,1,2],
                        help='''\
Set verbosity level:
0: Print tracks progress
1: Default basic information printing
2: Print EQ configuration''')

    return parser.parse_args()


"""
Checks consistency wrt. related command line args.
"""
def check_input(arguments):
    
    ## Check for errors
    if arguments.mixes < 0:
        raise ValueError("""Number of mixes requested cannot be negative""")
    if arguments.masking_factor <= 0 or arguments.masking_factor >= 1.0:
        raise ValueError("""Masking factor out of bounds (0-1)""")
    if arguments.essential_threshold <= 0 or arguments.essential_threshold >= 1.0:
        raise ValueError("""Essential Threshold out of bounds (0-1)""")
    if arguments.project == "":
        raise ValueError("""A project name must be given.""")
    if arguments.samples < 1000 or arguments.samples > 32768:
        raise ValueError("""Number of samples requested is out of bounds""")
    if arguments.erb < 10 or arguments.erb > 100:
        raise ValueError("""Number of erb bands requested is out of bounds""")
    
    

""" 
Main function
Get ERB bands, build instances, ground, solve and parse answer sets to mix
"""
def main():

    ## Parse input data
    args = parse_params()
    ## Check for input errors
    check_input(args)

    # Input data
    ## STFT parameters
    sr = 44100.0       # Sample Rate
    N  = args.samples  # FFT size or Number of Samples
    M  = N             # Window size 
    H  = int(M/64)     # Hop size
    B  = args.erb      # ERB Bands
    low_lim = 20       # centre freq. of lowest filter
    high_lim = sr / 2  # centre freq. of highest filter
    threshold = args.essential_threshold # Essential bands
    analyze = args.analyze # Extract audio features or use instances in dir
    s = args.s
    q = args.q
    benchmark = args.benchmarks
    solve = not benchmark
    
    ## ASP variables
    project = args.project #project name
    models = [] # answer sets
    tracks = []
    tracks_duration = []

    ## Read wav files from project
    print("Reading tracks...")
    for fl in os.listdir("projects/%s/"%project):
        if fl.endswith(".wav"):
            tracks.append(os.path.splitext(fl)[0])
            if analyze:
                t = "projects/%s/%s.wav"%(project, os.path.splitext(fl)[0])
                with contextlib.closing(wave.open(t,'r')) as f:
                    frames = f.getnframes()
                    rate = f.getframerate()
                    duration = frames / float(rate)
                    tracks_duration.append(duration)

    if analyze:
        duration = int(round(max(tracks_duration)))
        print("Mixdown duration (secs): %s"%duration)

    ## create tracks instance lp
    ## get audio features and create each track_name.lp file
    file_params = "S%s_B%s_ET%s_MF%s"%(N,B,args.essential_threshold,args.masking_factor)

    ## Create clingo object and load instances
    ## Add arguments
    if solve:
        clingo_args = ["--sign-def=rnd",
                       "--sign-fix",
                       "--rand-freq=1",
                       "--seed=%s"%random.randint(0,32767),
                       "--restart-on-model",
                       "--enum-mode=record"]
        control = clingo.Control(clingo_args)
        ## Load eq.lp
        control.load("lp/eq.lp")

    ## for each track
    track_number = 1
    frequencies = []
    spectrums = []
    erbs = []
    filters = []
    for track in tracks:
        if analyze:
            print(" Building instance: %s"%track)
            ## Get spectrum and signal size
            spectrum, len_signal = af.get_spectrum("projects/%s/%s"%(project,track), sr, N, M, H)

            # Equivalent Rectangular Bandwidth
            erb_bands, bandwidths, frequencies, center_fr, filters = af.get_erb_bands(spectrum, len_signal, sr, B, low_lim, high_lim)

            # Save data for plotting
            spectrums.append(spectrum)
            erbs.append(erb_bands)
        
        # ASP instances
        instance = "projects/%s/%s.lp"%(project,track)
        if analyze: ## If not benchmark
            file = open(instance,"w")
            af.build_asp_instance(file, track_number, instance, erb_bands, threshold)
            file.close()

        if solve:
            control.load("projects/%s/%s.lp"%(project,track))
        track_number+=1

    # Build mixdown graphics
    if analyze:
        print("Building graphics...")
        af.build_graphics(frequencies, spectrums, "projects/%s"%(project), project, erbs, B, filters, tracks, False)

    ## Number of mixes
    if solve:
        control.configuration.solve.models = args.mixes

        ## Add masking factor
        control.add("p", [], "#const masking_factor = %s."%int(args.masking_factor*100))
        ## Ground
        print("Grounding...")
        control.ground([("base", [])])
        control.ground([("p", [])])
        ## Solve
        if s >= 0:
            print("Propagator Registered for Sampling")
            control.register_propagator(Propagator(s,q))
        print("Solving...")
        solve_result = control.solve(None, lambda model: models.append(model.symbols(shown=True)))

        if str(solve_result) == "SAT":
            print("%s, Exhausted: %s"%(solve_result,solve_result.exhausted))
            print(models)
            print("")
            results_path = "%s/results/"%("projects/%s"%(project))
            dir = os.path.dirname(results_path)
            if not os.path.exists(dir):
                os.makedirs(dir)

            file = open("%s/plan_%s.txt"%(results_path, file_params),"w")
            for answer in models:
                answer_number = models.index(answer)+1
                print("Answer: %s"%answer_number)

                #Plan
                file.write("Answer: %s \n"%answer_number)
                eqs = af.parse_answer_sets_to_plan(file, tracks, answer, center_fr, bandwidths)
                file.write("\n")

                #Csound
                csound_file = "Answer_%s_mixdown_%s.csd"%(answer_number, file_params)
                file_csd = open("%s/%s"%(results_path, csound_file),"w")
                csd.create_header(file_csd, results_path, csound_file)

                for i in range(len(tracks)):
                    if (i+1) in eqs:
                        ## Create csound instrument with EQs
                        csd.create_instrument(file_csd, i+1, eqs[(i+1)])
                    else:
                        ## Create csound instrument without EQ
                        csd.create_instrument(file_csd, i+1, None)

                # Csound Bridge between Orchestra and Scores
                csd.create_bridge(file_csd)

                # Csound Orchestra
                for i in range(len(tracks)):
                    csd.create_orchestra(file_csd, (i+1), tracks[i], duration)

                # Csound Footer
                csd.create_footer(file_csd)

                # Close file
                file_csd.close()

                # Render csound files
                #if args.normalize:
                #    print("normalize tracks")
                csd.render(results_path, csound_file)

                print("")
            file.close()
        else:
            print("No masking detected for the given values masking-factor and/or essential-threshold")


    if benchmark:
        ## Create a single file instance with the masking factor constant and with all the sub instances of the project
        print("Generating Benchmarks")
        


"""
Main function
"""
if __name__ == '__main__':
    sys.exit(main())					      
