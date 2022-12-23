
# Executes the multi-step preprocessing / encoding steps for the unencoded data sources

# exit on error
set -e


cd ..
rm -rf encoded_data_sources
mkdir encoded_data_sources


cd scripts
conda run -n mtg-ai-main python -Wignore encode.py --json_path ../raw_data_sources/AllPrintings.json --out_path ../encoded_data_sources --extra_names ../raw_data_sources/names.yaml --extra_flavor ../raw_data_sources/flavor.yaml


cd ../torch-rnn
echo "main_text:"
conda run -n torch-rnn-python python scripts/preprocess.py --input_txt ../encoded_data_sources/main_text.txt --output_h5 ../encoded_data_sources/main_text.h5 --output_json ../encoded_data_sources/main_text.json --val_frac 0.005 --test_frac 0 --chunk_delimiter $'\n\n'
echo "names:"
conda run -n torch-rnn-python python scripts/preprocess.py --input_txt ../encoded_data_sources/names.txt --output_h5 ../encoded_data_sources/names.h5 --output_json ../encoded_data_sources/names.json --val_frac 0.005 --test_frac 0
echo "flavor:"
conda run -n torch-rnn-python python scripts/preprocess.py --input_txt ../encoded_data_sources/flavor.txt --output_h5 ../encoded_data_sources/flavor.h5 --output_json ../encoded_data_sources/flavor.json --val_frac 0.006 --test_frac 0

