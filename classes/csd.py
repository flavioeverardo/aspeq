import os

def create_filters(csd_file, filters):
    f_count = 0
    for filter in filters:
        f_count +=1
        if f_count == 1:
            csd_file.write("aL%s    pareq   aL, %s, ampdb(%s), %s ; Parametric equalization\n"%(f_count, filter[1], filter[2], filter[3]))
            csd_file.write("aR%s    pareq   aR, %s, ampdb(%s), %s ; Parametric equalization\n"%(f_count, filter[1], filter[2], filter[3]))
        else:
            csd_file.write("aL%s    pareq   aL%s, %s, ampdb(%s), %s ; Parametric equalization\n"%(f_count, f_count-1, filter[1], filter[2], filter[3]))
            csd_file.write("aR%s    pareq   aR%s, %s, ampdb(%s), %s ; Parametric equalization\n"%(f_count, f_count-1, filter[1], filter[2], filter[3]))

    csd_file.write("outs aL%s, aR%s\n"%(f_count, f_count))


"""
Build Csound files including header, instruments with eq and without eq and score
"""
def create_header(csd_file, destiny_dir, csdfile):

    wav_filename = "%s%s.wav"%(destiny_dir, csdfile)
    print "create csd file: %s"%csdfile

    csd_file.write("<CsoundSynthesizer>\n")
    csd_file.write("<CsOptions>\n")
    csd_file.write(" -W -o %s  \n"%wav_filename)
    csd_file.write("</CsOptions>\n")
    csd_file.write("<CsInstruments>\n")
    csd_file.write("\n")
    csd_file.write("sr     = 44100\n")
    csd_file.write("kr     = 4410\n")
    csd_file.write("ksmps  = 10\n")
    csd_file.write("nchnls = 2\n")
    csd_file.write("0dbfs  = 1\n")
    csd_file.write("\n")

def create_instrument(csd_file, track_number, operation):

    csd_file.write("\n")
    csd_file.write("instr %s\n"%track_number)
    csd_file.write("ichn filenchnls  p4	;check number of channels\n")
    csd_file.write("\n")
    csd_file.write("if ichn == 1 then\n")
    csd_file.write("aL   soundin p4	;mono signal\n")
    csd_file.write("outs    aL, aL\n")
    csd_file.write("else		;stereo signal\n")
    csd_file.write("aL, aR soundin p4\n")
    csd_file.write("endif\n")
    csd_file.write("\n")

    if operation is None:
        csd_file.write("outs aL, aR\n") # If no eq
    else:
        create_filters(csd_file, operation) # If eq

    csd_file.write("\n")
    csd_file.write("endin\n")
    csd_file.write("\n")

def create_bridge(csd_file):
    csd_file.write("\n")
    csd_file.write("</CsInstruments>\n")
    csd_file.write("<CsScore>\n")

def create_orchestra(csd_file, i, track, duration):
    csd_file.write("i %s 0 %s \"../%s.wav\"\n"%(i, duration, track))

def create_footer(csd_file):
    csd_file.write("\n")
    csd_file.write("</CsScore>\n")
    csd_file.write("</CsoundSynthesizer>\n")

def render(path, csound_file):
    print "render csound file to wav"
    command = "csound %s/%s -O null"%(path,csound_file)
    os.system(command)

