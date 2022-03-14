# Acoustic Pipeline

This pipeline runs several acoustic analysis programs and outputs a tab-separated file with summarized measures (mean, median, standard deviation, and inter-qualtile range (75th - 25th)) for all acoustic features. This pipeline is checked in the Audiopipe1 server at LDC, and should work in Audiopipe1-deployed machines, but I haven't tested it yet. Version 1.0.1 includes 5 programs: Speech quality checking, in-house Speech Activity Detector, openSMILE (https://www.audeering.com/research/opensmile/), covarep (https://github.com/covarep/covarep), and Penn Phonetics forced aligner (https://asa.scitation.org/doi/10.1121/1.2935783). All programs can be optionally run except the speech quality checking, which will run even when the other programs were `False`. To run the pipeline, download the program and enter a command like the following, for example:

`python3 acoustic_pipeline.py -output_file output.tsv -input_folder /your_audio_folder -openSMILE True` 

## Prerequisites
- openSMILE (https://www.audeering.com/research/opensmile/)
- covarep (https://github.com/covarep/covarep)
- Penn Phonetics forced aligner (https://web.sas.upenn.edu/phonetics-lab/facilities/)
- Speech Activity Detector

All of these programs will be installed in audiopipe1-deployed machines. If users are not using audiopipe1-deployed machines, please install all of the programs separately and replace the locations in the pipeline with new locations (see [Notes](#notes) below). 

## Arguments and options

* `-output_file`: This is an obligatory argument for the output file name. Note that the output file will be tab-separated. 

* `-input_folder`: This is also an obligatory argument. Enter the full path of a folder with audio files to be processed. (If not a full path, MATLAB is likely to raise an error message.)

* `-trans_folder`: Optional (type: string). Enter the location of a folder with corresponding transcript files. If not specified, the program looks for transcript files in the `input_folder`. 

* `-audio_type`: Optional (type: string). If specified, only audio files in the specified format will be processed. All audio types that are supported by Sox (http://sox.sourceforge.net/) are supported. If not specified, the default file type is `wav`. 

* `-openSMILE`: Optional (type: boolean). If `True`, openSMILE will run and calculate low-level descriptor features of the configuration file selected. The location of openSMILE in Audiopipe1 is `/usr/local/src/opensmile`.
 
* `-openSMILE_config`: Optional (type: string). If you want to run openSMILE with a specific configuration file that openSMILE provides, please specify the location of the config file with this option. E.g., `-openSMILE_config /usr/local/src/opensmile/config/is09-13/IS13_ComParE.conf`. If not specified, the interspeech 2013 version (IS13_ComParE.conf) will be used by default. 

* `-SAD`: Optional (type: boolean). If `True`, duration-related measures will be calculated. If transcript files are provided, duration-related measures will be calculated from transcripts, assuming that those transcript files were created with WebTrans, which already has a built-in SAD function. If transcripts are not found, the SAD program runs and duration-related measures will be calculated from SAD outputs.  

* `-covarep`: Optional (type: boolean). If `True`, the covarep program will run. MATLAB with valid license is required to run this program. I am planning to slowly migrate this program from MATLAB to Octave or Python, but this will take some time...  

* `-forced_alignment`: Optional (type: boolean). If `True`, a revised version of the Penn Phonetics forced aligner will run. This program is the only language-specific program out of all, and for now only the English forced aligner is included. 

*  `-turn_level`: Optional (type: boolean). If `True`, all acoustic measures will be summarized by turns (not by speaker). This option works with openSMILE and covarep. Duration measures will not be included in the final output file, even if `-SAD True`.

## Brief sketch of the process

For all audio files in the `input_folder`, the following steps will be performed.

1. Checking transcripts: The step checks if transcripts files are in the right format. Transcript files should not have headers and the column order should be filename, start, end, transcript, speaker, task. If the format of the transcript is different, it raises an error message and the program stops. Please revise the transcript format if you encounter this error message. This program does not change the transcript format.

2. Preprocessing audio files: This step determines if the audio file is stereo or mono. If stereo, it further decides if the two channels are identical (or similar enough to be considered as the same recordings). If identical, the two channels are merged. If not, two channels are separated into two mono audio files. During this process, all files are converted to wav files with a sampling rate of 16 KHz, 16 bits and saved in a temporary folder for further processing.

3. Checking speech quality: I included SpeechQuality1.m on harris, after translating it to Python. This function always runs when the acoustic pipeline runs, and prints the signal-to-noise ratio (SNR) in the terminal (for quick checking). The SNR and the number of clipped frames from this function are also included in the output file.

4. Running programs: The programs that are `True` in the command line will run at this step. The output files of the programs are saved in the `input_folder`. The output file of openSMILE is `.csv`, that of covarep is `.dat`, that of SAD is `.lab` (if SAD runs), and that of forced alignment is `.word` (word-level alignment) and `.align` (phone-level alignment). Please note that SAD won't run if a corresponding transcript file is found (assuming that the transcripts were created in WebTrans). 

5. Summarizing measures: Thi step first calculates turn-level features even if `-turn_level` is `False` to identify who is talking in which channel (only when `-openSMILE` or `-covarep` is `True`). If one speaker has too many NaN values in Channel 1 when turn-level features were calculated, that speaker is considered to be speaking in Channel 2 and dropped from the summarized output dataframe of Channel 1. This function generally works okay but it is not perfect, so users will need to check the final output file carefully. After one audio file is processed, the output dataframe is added to the final output file.    

## Notes

1. For now, `-forced_aligner True` runs the forced aligner, but it does not calculate any measures. Users are welcome to use the aligned files to calculate any measures they want, but the pipeline won't measure anything yet. Word duration-related measures might be added in a later version. Also, note that the forced aligner will run on speech segments by temporarily segmenting audio files into smaller chunks for better accuracy. If the input audio file is in stereo, the channels will merge before running the forced-aligner. This behavior is a temporary solution, because it's hard to decide who's speaking in which channel without running other programs. Since timestamps in the transcripts are used for the forced alignment, alignments should be good enough. I will come up with another solution later. 

2. MATLAB crashes quite frequently when running covarep if an audio file is too large. And covarep is very slow to run. If the audio file is over 100 Mb, consider segmenting the file first before running it through the pipeline. 

3. For users who are not using Audiopipe1-deployed machines: This pipeline can be used in personal machines by modifying a few lines in the script. Please change these lines in the `acousticsLib/run_programs.py` by replacing the location of each program with a new location:

- `SAD_location = "/usr/local/src/ldc_sad_hmm-1.0.9/perform_sad.py"`
- `openSMILE_default_config_location = "/usr/local/src/opensmile/config/is09-13/IS13_ComParE.conf"`
- `acoustic_pipeline_location = "./acoustic_pipeline_1.0.1"`
- `forced_alignment_location = "/usr/local/aligner_v02/segment.py"`

4. Multiprocessing is not available now, so processing many files at once might take long time. I will implement this function later.

5. The speech quality checking function outputs a low SNR when a speaker on the channel does not speak much. I will debug this problem later. 

6. F0 is calculated in both openSMILE (in semitone) and covarep (in Hz). The f0 setting for pitch tracking in covarep is 80 Hz to 400 Hz. I didn't change the pitch tracking setting in openSMILE, so the default value will be used. In both programs, pitch values from voiced frames are calculated, so the values will be similar, but not identical. 

7. It is very important to note that transcripts need to be tab-separated files without headers and with the column order of \[filename, start, end, transcript, speaker, task\]. If transcripts are not in this format, please reformat transcripts before running the program.  

