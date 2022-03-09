# this script includes functions for transcripts
import pandas as pd
import sys

def get_transcripts_only(transfile, args):
	outfile = args.input_folder+'/temp/temp.txt'
	start = []
	end = []

	with open(transfile, 'r') as infile, open(outfile, 'w') as outFile:
		for line in infile:		
			data = line.rstrip('\n').split('\t')
			
			outFile.writelines(data[3]+'\n')
			start.append(float(data[1]))
			end.append(float(data[2]))
	if len(start) != 0:
		return min(start), max(end) 
	else:
		pass

# check if the transcript is in the right format
def transcript_check(transfile):
	print("The corresponding transcript file is ", transfile)
	df = pd.read_csv(transfile, sep='\t', header=None)
	if len(df.columns) > 6:
		sys.exit("The number of columns in the transcript file is more than 6. Please clean the transcripts and try again.")
	elif (df.iloc[0, 0] =="Audio") or (df.iloc[0, 0] =="File"):
		sys.exit("Transcript file has a header. Please remove the header and try again.")
	else:
		pass
