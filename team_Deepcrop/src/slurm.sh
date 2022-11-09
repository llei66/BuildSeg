#!/bin/bash
# normal cpu stuff: allocate cpus, memory
#SBATCH --ntasks=2
#SBATCH --cpus-per-task=4
#SBATCH --job-name="seg"
# we run on the gpu partition and we allocate 1 titanx gpu
#SBATCH -p gpu --gres=gpu:1
#SBATCH --time=4-15:00:00
#SBATCH --mail-type=END,FAIL#SBATCH --mail-user=stefan.oehmcke@di.ku.dku.
#your script, in this case: write the hostname and the ids of the chosen gpus.
hostname
echo $CUDA_VISIBLE_DEVICES
#sh seg_sh/sb_train_Min_denmark_pl_2205_sampling1.sh
#python train.py --task 2 --name combine_lidar
#python train.py --task 1 --name image_resnet101_withweight
#python train.py --task 1 --name  deeplabv3_resnet50_withpreweight
#python train.py --task 2 --name  simple_resNetUnet_task2
#python train_UNetFormer.py --task 1 --name  UNetFormer --data_ratio 0.01
python train_UNetFormer.py --task 1 --name  UNetFormer --data_ratio 1.0