## This script includes functions for data conversion and summarization.

import pandas as pd
import numpy as np
from scipy.io import loadmat
import glob, os.path
from acousticsLib.run_programs import run_SAD


## functions for openSMILE measures
# merge transcript and outputs
def merge_transcript(transcript, df):
    # calculate duration of speech segments in milliseconds
    transcript['dur'] = (transcript['end'] - transcript['start']) / 0.01
    # repeat the row by the duration of speech segments (rounded)
    transcript_new = transcript.loc[transcript.index.repeat(transcript.dur)].reset_index()
    # rename the start time for merging
    transcript_new.rename(columns={'start':'frameTime'}, inplace=True)
    # merge the transcript and openSMILE output file 
    merged_df = pd.merge_asof(df, transcript_new, on='frameTime')
    return merged_df

# calculate global stat values of low-level descriptors
def calculate_statistics(df, features, feature_names, openSMILE=False):
    # initiate a temporary list <- this will be added as a new row in the output dataframe.
    temp = []
    for feature in features:
        if openSMILE:
            # for pitch features, normalize the values
            if feature == "F0final_sma" or feature== "F0final_sma_de":
                # remove all frames when pitch = 0 Hz 
                df = df[df.F0final_sma > 0]
                # remove all frames with low voicing probability
                df = df[df.voicingFinalUnclipped_sma > 0.5]
                ## Normalize pitch values
                df.F0final_sma = np.log2(df.F0final_sma / df.F0final_sma.quantile(0.1))*12
        else:
            df = df[df['VUV'] > 0.5]
    
        ## calculate statistical functionals for each feature
        mean = df[feature].mean()
        sd = df[feature].std()
        median = df[feature].median()
        iqr = df[feature].quantile(0.75) - df[feature].quantile(0.25)
        # add to the temp list
        temp.extend([mean, sd, median, iqr])
    temp = pd.DataFrame([temp], columns=feature_names)
    return temp

# summarize output files 
def summarize_measures(file, transfile, turn_df, speaker_df, args, openSMILE=False):
    if openSMILE:
        # open openSMILE output file as a pd data frame
        df = pd.read_csv(file, sep=";")
        # check the names of features
        features = df.columns 
        features = features[2:]

    else:
        # open covarep output file as a pd data frame
        df = pd.read_csv(file, sep="\t")
        # check the names of features
        features = df.columns 
        df['frameTime'] = df.index * 0.01

    # make a list of feature names with derivative statistics
    feature_names = []
    for feature in features:
        mean_name = feature+'_mean'
        sd_name = feature+'_sd'
        median_name = feature+'_median'
        iqr_name = feature+'_iqr'
        feature_names.extend([mean_name, sd_name, median_name, iqr_name])
    
    # if feature names were not assigned as column names, assign feature names.
    if ('speaker' not in turn_df.columns) and ('speaker' not in speaker_df.columns):
        # assign column names in the turn-level and speaker-level data frames
        turn_df = pd.concat([turn_df, pd.DataFrame(columns=feature_names)])
        speaker_df = pd.concat([speaker_df, pd.DataFrame(columns=feature_names)])
    
        # add more columns
        turn_df = pd.concat([turn_df, pd.DataFrame(columns=['speaker', 'task', 'transcript', 'dur'])])
        speaker_df = pd.concat([speaker_df, pd.DataFrame(columns=['speaker', 'task'])])
    else:
        pass

    # check if a transcript file exists
    if os.path.exists(transfile):
        # open transcript file 
        transcript = pd.read_csv(transfile, sep='\t', names=['file','start','end','transcript','speaker', 'task'])
        # merge it with the openSMILE output file
        merged_df = merge_transcript(transcript, df)
    
    # if transcript does not exist, it assumes there's only one speaker and summarizes the entire file.
    else:
        print("WARNING: There's no matching transcript file. The program assumes that there's one speaker.")
        merged_df = df
        # add NaN values for transcript headers so that the following codes can run
        merged_df['task'] = np.nan
        merged_df['speaker'] = np.nan

    # make the columns as string type so that transcripts can be processed. 
    merged_df['task'] = merged_df['task'].astype(str)
    merged_df['transcript'] = merged_df['transcript'].astype(str)
    merged_df['speaker'] = merged_df['speaker'].astype(str)
    merged_df['filename'] = file.split('.')[0]
    
    # intermediate data frames
    interDf = pd.DataFrame()
    interDf2 = pd.DataFrame()
    # loop through groupby objects for turn-level
    for key, grouped_df in merged_df.groupby(['speaker', 'task', 'transcript', 'dur', 'filename']):
        temp = calculate_statistics(grouped_df, features, feature_names, openSMILE)
        # include information in the key
        temp['speaker'] = key[0] 
        temp['task'] = key[1] 
        temp['transcript'] = key[2] 
        temp['dur'] = key[3] 
        temp['filename'] = key[4]
        
        interDf = pd.concat([interDf, temp], sort=False)
    
    # drop speakers who were not on the channel for stereo files
    include_speaker = []
    for key, grouped_df in interDf.groupby('speaker'):
        # drop the speaker if the values in the first column contains NaN value 50% of the time.
        if grouped_df.iloc[:, 1].isna().sum() > (0.5 * len(grouped_df)):
            pass
        else:
            include_speaker.append(key)
    
    # if turn_level is true, return turn-level summarized df (only for speakers that were on the channel)
    if args.turn_level:
        if include_speaker:
            turn_df = pd.concat([turn_df, interDf[interDf.speaker.isin(include_speaker)]])
        else:
            turn_df = pd.concat([turn_df, interDf])
        return turn_df
        
    # if not, return speaker-level summarized df
    else: 
        # loop through groupby objects.
        for key, grouped_df in merged_df.groupby(['speaker', 'task', 'filename']):
            temp2 = calculate_statistics(grouped_df, features, feature_names, openSMILE)
            temp2['speaker'] = key[0] 
            temp2['task'] = key[1] 
            temp2['filename'] = key[2]
            interDf2 = pd.concat([interDf2, temp2], sort=False)
        
        # return a df for speakers who were on the channel
        if include_speaker:
            speaker_df = pd.concat([speaker_df, interDf2[interDf2.speaker.isin(include_speaker)]])
        else:
            speaker_df = pd.concat([speaker_df, interDf2])
        return speaker_df

## summarize SAD outputs
def summarize_SAD(file, transfile, SADdf, args, count):
    # look up where the transcript file is.. 
    if args.trans_folder:
        list_of_trans = glob.glob(args.trans_folder+'/*.txt')
        
    else:
        list_of_trans = glob.glob(args.input_folder+'/*.txt')
       

    if transfile in list_of_trans:
        # do not summarize measures repeatedly for stereo files
        if count < 2:
            # read transcript file
            df = pd.read_csv(transfile, names=['filename', 'start', 'end', 'transcripts','speaker','task'], sep='\t')
            # change the data type of task in case it's NaN
            df['task'] = df['task'].astype(str)
            # calculate speech segment duration
            df['dur'] = df['end'] - df['start']
            # shift the end time of previous speech segment duration to calculate pause duration between two speech segments
            df['pause_end'] = df['end'].shift(1)
            df['prev_pause'] = df['start'] - df['pause_end']
            # in case of overlapping speech (when prev pause duration is negative), assume the pause duration is 0
            df.loc[df.prev_pause < 0,'prev_pause'] = 0
            # get task start and end time for total time
            task_start = df.groupby(by=['task'])['start'].min()
            task_end = df.groupby(by=['task'])['end'].max()
            total_dur = df.groupby(by=['speaker','task'])['prev_pause'].agg([np.sum])+ df.groupby(by=['speaker','task'])['dur'].agg([np.sum])
            # calculate speech segment related measures
            spch = df.groupby(by=['speaker','task'])['dur'].agg([np.sum, np.mean, np.std])
            # calculate pause segment related measures
            nonspch = df.groupby(by=['speaker','task'])['prev_pause'].agg([np.sum, np.mean, np.std])
            # percent_spch = (df.groupby(by=['speaker','task'])['dur'].sum() / total_dur)
		    # get number of pauses and calculate pause rate per minute
            numPause = df.groupby(by=['speaker','task'])['prev_pause'].count()
            # concat all measures 
            temp = pd.concat([total_dur, spch, nonspch, numPause], axis=1)
            # add column names
            temp.columns = ['total_dur', 'totalSpch', 'meanSpch','stdSpch', 'totalPause', 'meanPause','stdPause', 'numPause']
            # calculate other measures
            temp['pause_rate'] = (temp.numPause / temp.total_dur ) *60
            temp['task_start'] = task_start[0]
            temp['task_end'] = task_end[0]
            #temp['filename'] = file.split('/')[-1]
            temp = temp.reset_index()
            
            # concat with the large data frame
            SADdf = pd.concat([SADdf, temp], sort=False)
            
            return SADdf

        # if the second channel of stereo file, just return the existing SADdf
        else:
            return SADdf
    else:
        # if no transcript, run SAD
        run_SAD(file, args)
        # open SAD output file
        SAD_outfile = file.split('.')[0]+'.lab'
        df = pd.read_csv(SAD_outfile, names=['start','end','segment'], sep=" ")
        # measure duration of each segment
        df['dur'] = df['end'] - df['start']
        total_dur = df['end'].max()
        # calculate measures 
        spch = pd.DataFrame(df[df.segment=="speech"]['dur'].agg([np.sum, np.mean, np.std])).T
        nonspch = pd.DataFrame(df[df.segment=="nonspeech"]['dur'].agg([np.sum, np.mean, np.std])).T
        pause_rate = (len(df[df.segment=="nonspeech"]) / total_dur) * 60
        # concat each df and name the columns
        temp = pd.concat([spch, nonspch], axis=1)
        temp.columns = ['totalSpch', 'meanSpch','stdSpch', 'totalPause', 'meanPause','stdPause']
        # add more information
        temp['total_dur'] = total_dur
        temp['pause_rate'] = pause_rate
        temp['filename'] = file.split('/')[-1]
        # include placeholders for the final output file later.
        temp['speaker'] = 'nan'
        temp['task'] = 'nan'
        # concat with the large data frame
        SADdf = pd.concat([SADdf, temp])
        return SADdf

def combine_data(temp, df, args):
    if len(temp) != 0:
        # if turn-level is true, combine data frames by transcript * speaker * task
        if args.turn_level:
            temp = pd.merge(temp, df, how='inner', on=['speaker', 'task', 'transcript', 'filename', 'dur'])
        # if not, combine data frames by speaker * task
        else:
            temp = pd.merge(temp, df, how='inner', on=['speaker', 'task','filename'])
    else:
        temp = df
    return temp
