# exit on error
set -e

repoDir=$HOME"/mtg-ai-card-generator"
torchDir=$HOME"/torch"


echo "eliminating torch repo"
rm -rf $torchDir


echo "acquiring base torch repo"
git clone https://github.com/torch/distro.git $torchDir --recursive
cd $torchDir


echo "patching base torch repo"
cp $repoDir"/torch_patches/base.patch" $torchDir"/."
patch -p1 < base.patch

rm -rf cmake/3.6/Modules/FindCUDA*
./clean.sh


echo "installing base torch repo"
export TORCH_NVCC_FLAGS="-D__CUDA_NO_HALF_OPERATORS__"
export CC=gcc-6
export CXX=g++-6
bash install-deps
./install.sh
source $HOME"/.bashrc"
# ./clean.sh  # TODO, this?


echo "installing torch rocks"
$torchDir"/install/bin/luarocks" install torch
$torchDir"/install/bin/luarocks" install nn
$torchDir"/install/bin/luarocks" install optim
$torchDir"/install/bin/luarocks" install lua-cjson


echo "installing cutorch"
git clone https://github.com/torch/cutorch.git $torchDir"/cutorch"
cp $repoDir"/torch_patches/atomic.patch" $torchDir"/cutorch/."
cp $repoDir"/torch_patches/cutorch_init.patch" $torchDir"/cutorch/."
cd $torchDir"/cutorch"
patch -p1 < atomic.patch
patch -p1 < cutorch_init.patch
$torchDir"/install/bin/luarocks" make rocks/cutorch-scm-1.rockspec


echo "installing cunn"
git clone https://github.com/torch/cunn.git $torchDir"/cunn"
cp $repoDir"/torch_patches/sparselinear.patch" $torchDir"/cunn/."
cp $repoDir"/torch_patches/lookuptable.patch" $torchDir"/cunn/."
cd $torchDir"/cunn"
patch -p1 < sparselinear.patch
patch -p1 < lookuptable.patch
$torchDir"/install/bin/luarocks" make rocks/cunn-scm-1.rockspec


echo "installing torch-hdf5"
git clone https://github.com/deepmind/torch-hdf5 $torchDir"/torch-hdf5"
cd $torchDir"/torch-hdf5"
$torchDir"/install/bin/luarocks" make hdf5-0-0.rockspec


echo "finished"

