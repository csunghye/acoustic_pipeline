## this script includes functions for running various acoustic programs, 
## including speech activity detector, openSMILE, covarep, speech quality checking, forced-alignment 

import subprocess, os, sys
import numpy as np
from scipy.io import wavfile
from acousticsLib.audio_prep import combine_channel
from acousticsLib.transcript_prep import get_transcripts_only

SAD_location = "/usr/local/src/ldc_sad_hmm-1.0.9/perform_sad.py"
openSMILE_default_config_location = "/usr/local/src/opensmile/config/is09-13/IS13_ComParE.conf"
acoustic_pipeline_location = "./acoustic_pipeline"
forced_alignment_location = "/usr/local/aligner_v02/segment.py"

# run SAD
def run_SAD(audio_file, args):
	subprocess.run(['python3', SAD_location,"--nonspeech","0.15","-L", args.input_folder, audio_file])
    #subprocess.run(['python3',"/Users/csunghye/Documents/ldc_sad_hmm-1.0.9/perform_sad.py","--nonspeech","0.15","-L", args.input_folder, audio_file])
# run openSMILE
def run_openSMILE(audio_file, args):
    # define the name of the output file
    outfilename = audio_file.split('.')[0]+'.csv'
    # if a specific openSMILE config file is listed, run the config file 
    # See the openSMILE doc for various config files
    if args.openSMILE_config:
        subprocess.run(["SMILExtract","-C", args.openSMILE_config, "-I", audio_file, "-D", outfilename, "-instname", audio_file])
    # if not, Interspeech 2013 version will be used 
    else:
        subprocess.run(["SMILExtract","-C", openSMILE_default_config_location,"-I", audio_file, "-D", outfilename, "-instname", audio_file])

# this function calculates a pseudo SNR value and the number of clipped frames
def run_SpeechQuality(file):
    windowT=0.025
    incrT = 0.01
    FS, X = wavfile.read(file)
    windowN = round(windowT*FS)
    incrN = round(incrT*FS)
    
    H = np.hamming(windowN)
    nsamples=len(X)
    lastsamp = nsamples-windowN
    nrms = len(np.arange(0,lastsamp, incrN))
    MS = np.zeros((nrms,1))
    count=0
    for s in np.arange(0,lastsamp, incrN):
        Sig = X[s:(s+windowN)]*H
        MS[count] = (np.conj(Sig)@Sig)/windowN
        count += 1
        
    Q15 = 10*np.log10(np.quantile(MS,0.15))
    Q85 = 10*np.log10(np.quantile(MS,0.85))
    aX = abs(X)
    nclipped = sum(aX== 1)
    return Q85 - Q15, nclipped

# run covarep 
def run_covarep(file):
    cwd = os.getcwd()
    os.chdir(acoustic_pipeline_location)
    ## make a command first for matlab 
    command = 'matlab -nodisplay -nosplash -nodesktop -r "feature_extraction2('+"'"+file+"'"+');exit;"'
    subprocess.run(command, shell=True)
    os.chdir(cwd)

# run forced-alignment (only English version is available for now)
def run_FA(file, transcript_list, transfile, status, args):
    # check if a file is steroe
    if status == "processed_stereo":
        # combine channels for forced alignment
        combine_channel(file, args)
        audio_file = args.input_folder+'/temp/'+file.split('/')[-1].split('.')[0]+'_mono.wav'
    else:
        audio_file = file
    
    if transfile in transcript_list:
        # define the final output file names
        wordfile = file.split('.')[0]+'.word'
        alignfile = file.split('.')[0]+'.align'
        # open transcript and loop through lines
        with open(transfile, 'r') as inFile:
            for line in inFile:
                data = line.rstrip('\n').split('\t')
                start = float(data[1])
                end = data[2]
                dur = float(end) - start

                # define temporary files for turn-level alignments
                temp_text = open(args.input_folder+'/temp/x.txt', 'w')
                temp_text.writelines(data[3]+'\n')
                temp_text.close()

                temp_text = args.input_folder + '/temp/x.txt'
                temp_wav = args.input_folder + '/temp/x.wav'
                temp_word =  args.input_folder + '/temp/x.word'
                temp_align =  args.input_folder + '/temp/x.align'

                # trim the audio file based on timestamps in transcripts
                subprocess.run(['sox', audio_file, temp_wav, 'trim', str(start), str(dur)])
                # run turn-level forced-alignment
                subprocess.run(['python', forced_alignment_location, temp_wav, temp_text, temp_align, temp_word])
        
                #add_start generates correct timestamps in the final output files
                add_start(wordfile, temp_word, start)
                add_start(alignfile, temp_align, start)

    else:
        sys.exit("No transcript file is found. Please check again.")	

# add start time for the alignment files
def add_start(file, tempfile, start):
    # open temp alignment files and final output files
    with open(tempfile, 'r') as inFile, open(file, 'a') as outFile:
        for line in inFile:
            data = line.rstrip('\n').split()
            if len(data) > 2:
                if tempfile.endswith('.word'):
                    outFile.writelines(str(float(data[0])+start)+'\t'+str(float(data[1])+start)+'\t'+data[2]+'\n')
                else:
                    outFile.writelines(str(float(data[0])+(start*10000000))+'\t'+str(float(data[1])+(start*10000000))+'\t')
                    for item in data[2:]:
                        outFile.writelines(item+'\t')
                    outFile.writelines('\n')
