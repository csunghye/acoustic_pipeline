# acoustic_pipeline

This program runs several acoustic analysis programs and outputs a tab-separated file with summarized measures (mean, median, standard deviation, and inter-qualtile range (75th - 25th)) for all acoustic features. This program is checked in the Audiopipe1 server at LDC, and should work in Audiopipe1-deployed machines, but I haven't tested it yet. Version 1.0.1 includes 5 programs: Speech quality checking, in-house Speech Activity Detector, openSMILE (https://www.audeering.com/research/opensmile/), covarep (https://github.com/covarep/covarep), and Penn Phonetics forced aligner (https://asa.scitation.org/doi/10.1121/1.2935783). All programs can be optionally run except the speech quality checking, which will run even when the other programs were `False`. To run the program, download the program and enter a command like the following, for example:

`python3 acoustic_pipeline_1.0.1/acoustic_pipeline.py -output_file output.tsv -input_folder /your_audio_folder -openSMILE True` 

## Prerequisites
- openSMILE
- covarep
- Penn Phonetics forced aligner
- Speech Activity Detector

## Arguments and options

* `-output_file`: This is an obligatory argument for the output file name. Note that the output file will be tab-separated. 

* `-input_folder`: This is also an obligatory argument. Enter the location of a folder with audio files to be processed.

* `-trans_folder`: Optional (type: string). Enter the location of a folder with corresponding transcript files. If not specified, the program looks for transcript files in the `input_folder`. 

* `-audio_type`: Optional (type: string). By specifying the audio type, only audio files in those formats will be processed. All audio types that are supported by Sox (http://sox.sourceforge.net/) are supported. If not specified, the default file type is `wav`. 

* `-openSMILE`: Optional (type: boolean). If `True`, openSMILE will run and calculate low-level descriptor features of the configuration file selected. The location of openSMILE in Audiopipe1 is `/usr/local/src/opensmile`.
 
* `-openSMILE_config`: Optional (type: string). If you want to run openSMILE with a specific configuration file that openSMILE provides, please specify the location of the config file with this option. E.g., `-openSMILE_config /usr/local/src/opensmile/config/is09-13/IS13_ComParE.conf`. If not specified, the interspeech 2013 version (IS13_ComParE.conf) will be used by default. 

* `-SAD`: Optional (type: boolean). If `True`, duration-related measures will be calculated. If transcript files are provided, duration-related measures will be calculated from transcripts, assuming that those transcript files were created with WebTrans, which already has a built-in SAD function. If transcripts are not found, the SAD program runs and duration-related measures will be calculated from SAD outputs.  

* `-covarep`: Optional (type: boolean). If `True`, the covarep program will run. MATLAB with valid license is required to run this program. I am planning to slowly migrate this program from MATLAB to Octave or Python, but this will take some time...  

* `-forced_alignment`: Optional (type: boolean). If `True`, the Penn Phonetics forced aligner will run. This program is the only language-specific program out of all, and for now only the English forced aligner is included. 

*  `-turn_level`: Optional (type: boolean). If `True`, all acoustic measures will be summarized by turns (not by speaker). This option works with openSMILE and covarep. Duration measures will not be included in the final output file, even if `-SAD True`.

## Brief sketch of the process

For all audio files in the `input_folder`, the following steps will be performed.

1. Audio preprocessing: The program first determines if the audio file is stereo or mono. If stereo, the program further decides if the two channels are identical (or similar enough to be considered as the same recordings). If identical, the two channels are merged. If not, two channels are separated into two mono audio files. During this process, all files are converted to wav files with a sampling rate of 16 KHz, 16 bits and saved in a temporary folder.

2. Checking speech quality: I included SpeechQuality1.m on harris, after translating it to Python. This function always runs when the acoustic pipeline runs, and prints the signal-to-noise ratio (SNR) in the terminal (for quick checking). The SNR and the number of clipped frames from this function are also included in the output file.

3. 

## NOTE

