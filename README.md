## run the codes


Download the data:

[NORA_MapAI](https://huggingface.co/datasets/sjyhne/mapai_training_data) 

```angular2html

ln -s data NORA_MapAI 
conda activate points_pt

cd team_Deepcrop/scr

sbatch slurm.sh
```


For data details and evaluation:

[README_config.md](https://github.com/llei66/BuildSeg/blob/master/README_config.md)




