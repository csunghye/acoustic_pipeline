## This program runs several acoustic analysis programs, including openSMILE, SAD, forced-alignment, speech quality checking etc. 
## And it generates summarized acoustic values by speaker (and task if any).
## If audio_type is not provided, the program assumes that all files are in .wav
## All audio file format that is supported by Sox will be supported. (--> need to still experiment)
   
## usage: 
## python3 acoustic_pipeline.py -output_file testing.csv -input_folder /home/csunghye/acoustic_testing -openSMILE True -SAD True -covarep True -forced_alignment True -trans_folder /home/csunghye/acoustic_testing -speaker_label 'CAR Staff' 'Child' 'Parent'
## If unspecified, openSMILE IS13 configure file will be used.


import argparse, glob, os, shutil, os.path
import pandas as pd
from acousticsLib.transcript_prep import transcript_check
from acousticsLib.run_programs import run_openSMILE, run_SpeechQuality, run_covarep, run_FA
from acousticsLib.audio_prep import check_channel, process_stereo, process_mono
from acousticsLib.data_summary import summarize_measures, summarize_SAD, combine_data

def main(args):
    
    # make a list of input files if the audio file type is given
    if args.audio_type:
        filelist = glob.glob(args.input_folder+'/*.'+args.audio_type)	
    # If audio_type is null, make a list of wav files in the input oflder
    else:
        filelist = glob.glob(args.input_folder+'/*.wav')

    # define the output file   
    outputname = args.output_file

    # loop through files in the file list
    for file in filelist:
        print(file, " is being processed...")
        filename = file.split('/')[-1]
		
        # make output dataframes for the file being processed
        turn_df = pd.DataFrame()
        SMILEdf = pd.DataFrame()
        covarep_df = pd.DataFrame()
        SADdf = pd.DataFrame(columns=['filename','task_start', 'task_end','total_dur', 'totalSpch', 'meanSpch','stdSpch', 'totalPause', 'meanPause','stdPause','numPause'])
    
        # check if the transcript is in the right format before running any program. 
        # Note: only transcripts without header and 6 columns (filename, start, end, text, speaker, section) will be processed.
        if args.trans_folder:
            transcript_list = glob.glob(args.trans_folder+'/*.txt')
            transfile = args.trans_folder + '/'+filename.split('.')[0]+'.txt'
            if transfile in transcript_list:
                transcript_check(transfile)
        else: 
            transcript_list = glob.glob(args.input_folder+'/*.txt')
            transfile = args.input_folder + '/'+filename.split('.')[0]+'.txt'
            if transfile in transcript_list:
                transcript_check(transfile)
            else:
                print("No corresponding transcript file is found. The program assumes that there's only one speaker.")
		
        # make a temporary folder and copy the audio file that's being processed 
        # this temp folder will be deleted at the end of the loop
        os.mkdir(args.input_folder+"/temp")
        shutil.copy2(file, args.input_folder+'/temp')

        # Check the number of channels in the copied audio file and process the file accordingly
        if check_channel(args.input_folder+'/temp/'+filename) > 1:
            status = process_stereo(args.input_folder+'/temp/'+filename)
        else: 
            status = process_mono(args.input_folder+'/temp/'+filename)

        # Make a new temp file list for processing
        if status == 'processed_stereo':
            newfilelist = [filename.split('.')[0]+'_firstCH.wav', filename.split('.')[0]+'_secondCH.wav']
        elif status == 'merged_stereo' or  status == 'processed_mono':
            newfilelist = [filename.split('.')[0]+'_mono.wav']
        else:
            newfilelist = [filename]
        
        # count number of files in the newfilelist (to prevent summarizing SAD measures in the transcript of stereo files twice)
        count = 0
        # loop through files in the temp folder
        for newfile in newfilelist:
            temp = pd.DataFrame()
            ## check speech quality
            print("Checking the speech quality of "+newfile)
            snr, nclipped = run_SpeechQuality(args.input_folder+'/temp/'+newfile)
            print("SNR: ", snr,"dB")

            ## run openSMILE
            if args.openSMILE:
                run_openSMILE(args.input_folder+'/temp/'+newfile, args)
                # copy the output file of openSMILE to the input folder
                os_outfile = newfile.split('.')[0]+'.csv'
                shutil.copy2(args.input_folder+'/temp/'+os_outfile, args.input_folder)

                # summarize the output data and return a df
                SMILEdf = summarize_measures(args.input_folder+'/temp/'+os_outfile, transfile, turn_df, SMILEdf, args, openSMILE=True)    
                # combine with temp output dataframe
                temp = combine_data(temp, SMILEdf, args)
            
            ## run SAD
            if args.SAD:
                count += 1
                # SAD would not run if there's a transcript file from WebTrans (which already has the SAD function)
				# If no corresponding transcript, SAD will run and output files will be summarized. 
                SADdf = summarize_SAD(newfile, transfile, SADdf, args, count) 
                # if SAD ran, copy the output file to the input folder (before deleting the temp folder)
                list_of_lab = glob.glob(args.input_folder+'/temp/*.lab')
                SADout = newfile.split('.')[0]+'.lab'
                if SADout in list_of_lab:
                    shutil.copy2(args.input_folder+'/temp/'+SADout, args.input_folder)
                
                ## if turn-level measures are calculated, SAD measures won't be added to the temp output dataframe.
                if args.turn_level:
                    pass
                # combine result with temporary output dataframe
                else:
                    if len(temp) !=0:
                        temp = pd.merge(temp, SADdf, how='inner', on=['speaker', 'task'])
                    else:
                        temp = SADdf    
            ## run covarep
            if args.covarep:
                run_covarep(args.input_folder+'/temp/'+newfile)
                # copy output file to the input_folder
                covarep_out = args.input_folder+'/temp/'+newfile.split('/')[-1].split('.')[0]+'.dat'
                shutil.copy2(covarep_out, args.input_folder)
                covarep_df = summarize_measures(covarep_out, transfile, turn_df, covarep_df, args, openSMILE=False)    
                # combine with temp output dataframe
                temp = combine_data(temp, covarep_df, args)
        
            # Add SNR and nclipped in the temp output dataframe
            temp['SNR'] = snr
            temp['nClipped'] = nclipped
            out_file = args.input_folder+'/'+outputname
            # write final results of the file being processed to the output file. 
            if os.path.exists(out_file):
                temp.to_csv(args.input_folder+'/'+outputname, index=None, sep='\t', mode='a', header=False)
            else:
                temp.to_csv(args.input_folder+'/'+outputname, index=None, sep='\t', mode='a')

        # run forced-aligner
        if args.forced_alignment:
            run_FA(file, transcript_list, transfile, status, args)
        
        # delete all contents in the temp folder
        shutil.rmtree(args.input_folder+'/temp')
					

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract acoustic features from audio files.')
    parser.add_argument('-output_file', type=str, required=True, help='Name the output file')
    parser.add_argument('-input_folder', type=str, required=True, help='Folder containing input wav files')
    parser.add_argument('-audio_type', type=str, required=False, help='The audio file type for processing, e.g., wav or flac')
    parser.add_argument('-openSMILE', type=bool, required=False, help='Boolean for running openSMILE')
    parser.add_argument('-openSMILE_config', type=str, required=False, help='Configuration file name for openSMILE')
    parser.add_argument('-SAD', type=bool, required=False, help='Boolean for running the SAD program')
    parser.add_argument('-covarep', type=bool, required=False, help='Boolean for running the covarep program')
    parser.add_argument('-forced_alignment', type=bool, required=False, help='Boolean for running the forced_aligner')
    parser.add_argument('-trans_folder', type=str, required=False, help='Folder with transcripts')
    parser.add_argument('-turn_level', type=bool, required=False, help='Boolean for summarizing measures at the turn level')
    args = parser.parse_args()
    
    main(args)


