
# Executes the multi-step preprocessing / encoding steps for the unencoded data sources

# exit on error
set -e


cd ..
rm -rf encoded_data_sources
mkdir encoded_data_sources


cd mtgencode
conda run -n mtgencode python encode.py -s -e named ../raw_data_sources/AllPrintings.json ../encoded_data_sources/main_text.txt
conda run -n mtgencode python encode_2.py ../raw_data_sources/AllPrintings.json -s --extra_names ../raw_data_sources/names.yaml --extra_flavor ../raw_data_sources/flavor.yaml --outfile_names ../encoded_data_sources/names.txt --outfile_flavor ../encoded_data_sources/flavor.txt --outfile_artists ../encoded_data_sources/artists_stats.txt


cd ../torch-rnn
echo "main_text:"
conda run -n torch-rnn-python python scripts/preprocess.py --input_txt ../encoded_data_sources/main_text.txt --output_h5 ../encoded_data_sources/main_text.h5 --output_json ../encoded_data_sources/main_text.json --val_frac 0.005 --test_frac 0 --chunk_delimiter $'\n\n'
echo "names:"
conda run -n torch-rnn-python python scripts/preprocess.py --input_txt ../encoded_data_sources/names.txt --output_h5 ../encoded_data_sources/names.h5 --output_json ../encoded_data_sources/names.json --val_frac 0.005 --test_frac 0
echo "flavor:"
conda run -n torch-rnn-python python scripts/preprocess.py --input_txt ../encoded_data_sources/flavor.txt --output_h5 ../encoded_data_sources/flavor.h5 --output_json ../encoded_data_sources/flavor.json --val_frac 0.006 --test_frac 0

