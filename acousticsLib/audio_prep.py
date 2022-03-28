### This script includes functions for audio preprocessing.
import sox

# checking if an audio file is stero or mono
def check_channel(audio_file):
    ch = sox.file_info.channels(audio_file)
    return ch


# split stereo channels into two mono wav files if the two channels are different
# this will merge the channels (by remixing) if the channels are similar or identical
def process_stereo(audio_file):
    # check sampling rate and number of frames 
    sp = sox.file_info.sample_rate(input_filepath=audio_file)
    n_frame = sox.file_info.num_samples(input_filepath=audio_file)
        
    # initiate a sox transformer class
    tfm = sox.Transformer()
        
    # read audio as arrays
    array_out = tfm.build_array(input_filepath=audio_file)
        
    # compare the two channels -- this line calculates absolute differences between the signals and normalized the diff by the number of frames
    first_ch = array_out[:, 0]
    second_ch = array_out[:, 1]
    result = abs(sum(first_ch - second_ch)/n_frame)
    
    # set the output format in advance (16KHz, 16 bits, mono, pcm)
    tfm.set_output_format(file_type='wav', rate=16000, bits=16, channels=1, encoding='signed-integer')

    # if the two channels are different, split the channels and save them separately.
    if result > 0.13: ## check out the threshold value (0.13) and modify it if necessary.
        # split channels' names will be audio_file +'_firstCH.wav' or '_secondCH.wav'
        filename = audio_file.split('.')[0]
        # save each channel separately
        tfm.build_file(input_array=array_out[:, 0], output_filepath=filename+'_firstCH.wav', sample_rate_in=sp)
        tfm.build_file(input_array=array_out[:, 1], output_filepath=filename+'_secondCH.wav', sample_rate_in=sp)
        # Return a value for further analysis
        return 'processed_stereo'
    # if the two channels are similar or identical, merge them and convert to mono (pcm)
    else:
        # The new file name will be audio_file+'_mono.wav'
        filename = audio_file.split('.')[0]
        # remix the channels into one
        tfm.remix(remix_dictionary={1:[1,2]})
        tfm.build_file(input_array=array_out, output_filepath=filename+'_mono.wav', sample_rate_in=sp)
        # Return a value for further analysis
        return 'merged_stereo'

# process single channel files
def process_mono(audio_file):
    # check sampling rate and number of frames 
    sp = sox.file_info.sample_rate(input_filepath=audio_file)
    n_frame = sox.file_info.num_samples(input_filepath=audio_file)
    
    # check the encoding of the audio file
    file_type_dict = sox.file_info.info(audio_file)

    # if the file is not in pcm, conver to pcm for acoustic measurements (some programs do not run on non-linear wav files...)
    if file_type_dict['encoding'] != 'Signed Integer PCM':
        # initiate a sox transformer class
        tfm = sox.Transformer()
        # set output format
        tfm.set_output_format(file_type='wav', rate=16000, bits=16, channels=1, encoding='signed-integer')
        # The new file name will be audio_file+'_pcm.wav'
        filename = audio_file.split('.')[0]
        # save as a pcm wav file
        tfm.build_file(input_filepath=audio_file, output_filepath=filename+'_mono.wav', sample_rate_in=sp)

        # Return a value for further analysis
        return 'processed_mono'
    else:
        return 'mono'

# combine stereo files for forced-alignment
def combine_channel(audio_file, args):
    # check sampling rate and number of frames 
    sp = sox.file_info.sample_rate(input_filepath=audio_file)
    # initiate a sox transformer class
    tfm = sox.Transformer()
    # read audio as arrays
    array_out = tfm.build_array(input_filepath=audio_file) 

    # set the output format in advance (16KHz, 16 bits, mono, pcm)
    tfm.set_output_format(file_type='wav', rate=16000, bits=16, channels=1, encoding='signed-integer')

    # The new file name will be audio_file+'_mono.wav'
    filename = audio_file.split('/')[-1].split('.')[0]
    # remix the channels into one
    tfm.remix(remix_dictionary={1:[1, 2]})
    tfm.build_file(input_array=array_out, output_filepath=args.input_folder+'/temp/'+filename+'_mono.wav', sample_rate_in=sp)
    
