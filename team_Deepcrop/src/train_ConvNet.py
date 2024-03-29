import os

import numpy as np
from yaml import load, dump, Loader, Dumper
from tqdm import tqdm
import torch
from tabulate import tabulate
import wandb
from torch import nn
import argparse
import time

from competition_toolkit.dataloader import create_dataloader
# from data.dataloader_building import create_dataloader
from utils import create_run_dir, store_model_weights, record_scores

from competition_toolkit.eval_functions import calculate_score

# from semseg.losses import *
# from models.geoseg.datasets.uavid_dataset import *
# from models.geoseg.models.UNetFormer import UNetFormer
# from semseg.models.backbones.convnext import ConvNeXt
from semseg.models.heads import *

from semseg.models import *

import ipdb

def cal_metrics(output, label, use_aux_loss):
    # use_aux_loss = True

    if use_aux_loss:
        output = nn.Softmax(dim=1)(output[0])
    else:
        output = nn.Softmax(dim=1)(output)
    output = output.argmax(dim=1)
    if device != "cpu":
        # print("using cpu")
        metrics = calculate_score(output.detach().cpu().numpy().astype(np.uint8),
                                       label.detach().cpu().numpy().astype(np.uint8))
    else:
        print("using cpu")
        metrics = calculate_score(output.detach().numpy().astype(np.uint8),
                                       label.detach().numpy().astype(np.uint8))
    return metrics

def test(opts, dataloader, model, lossfn):
    model.eval()

    device = opts["device"]

    losstotal = np.zeros((len(dataloader)), dtype=float)
    ioutotal = np.zeros((len(dataloader)), dtype=float)
    bioutotal = np.zeros((len(dataloader)), dtype=float)
    scoretotal = np.zeros((len(dataloader)), dtype=float)

    for idx, batch in tqdm(enumerate(dataloader), leave=False, total=len(dataloader), desc="Test"):
        image, label, filename = batch
        image = image.to(device)
        label = label.to(device)

        # output = model(image)["out"]
        output = model(image)
        # ipdb.set_trace()

        loss = lossfn(output, label).item()
        use_aux_loss = False
        metrics = cal_metrics(output, label, use_aux_loss)

        losstotal[idx] = loss
        ioutotal[idx] = metrics["iou"]
        bioutotal[idx] = metrics["biou"]
        scoretotal[idx] = metrics["score"]

    loss = round(losstotal.mean(), 4)
    iou = round(ioutotal.mean(), 4)
    biou = round(bioutotal.mean(), 4)
    score = round(scoretotal.mean(), 4)

    return loss, iou, biou, score


def train(opts):
    device = opts["device"]
    print(device)
    # The current model should be swapped with a different one of your choice
    # model = torchvision.models.segmentation.fcn_resnet50(pretrained=False, num_classes=opts["num_classes"])
    # model = torchvision.models.segmentation.fcn_resnet101(pretrained=False, num_classes=opts["num_classes"], pretrained_backbone=True)
    # ipdb.set_trace()
    # model = torchvision.models.segmentationß.deeplabv3_resnet50(pretrained=False, num_classes=opts["num_classes"], pretrained_backbone=True)

    # model = unet_resnet18.ResNetUNet(n_class=2)
    # model = eval('SegFormer')(backbone='MiT-B3',num_classes=2)
    model = eval('SegFormer')(backbone='ConvNeXt-T',num_classes=2)

    # model = eval()

    if opts["task"] == 2:
        print("process for the task 2")
        new_conv1 = torch.nn.Conv2d(4, 64, kernel_size=(7, 7), stride=(2, 2), padding=(3, 3), bias=False)
        model.backbone.conv1 = new_conv1

    model.to(device)
    model = model.float()

    optimizer = torch.optim.Adam(model.parameters(), lr=opts["lr"])
    lossfn = torch.nn.CrossEntropyLoss()
    # lossfn = UnetFormerLoss()


    epochs = opts["epochs"]

    trainloader = create_dataloader(opts, "train")
    valloader = create_dataloader(opts, "validation")

    bestscore = 0
    bestiou = 0

    for e in range(epochs):

        model.train()

        losstotal = np.zeros((len(trainloader)), dtype=float)
        scoretotal = np.zeros((len(trainloader)), dtype=float)
        ioutotal = np.zeros((len(trainloader)), dtype=float)
        bioutotal = np.zeros((len(trainloader)), dtype=float)

        stime = time.time()

        for idx, batch in tqdm(enumerate(trainloader), leave=True, total=len(trainloader), desc="Train", position=0):
            image, label, filename = batch
            image = image.to(device)
            label = label.to(device)

            # import ipdb; ipdb.set_trace()
            # output = model(image)["out"]
            output = model(image)


            loss = lossfn(output, label)
            wandb.log({"loss":loss})

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            lossitem = loss.item()
            # output = torch.argmax(torch.softmax(output, dim=1), dim=1)
            use_aux_loss = False

            trainmetrics = cal_metrics(output, label, use_aux_loss )

            losstotal[idx] = lossitem
            ioutotal[idx] = trainmetrics["iou"]
            bioutotal[idx] = trainmetrics["biou"]
            scoretotal[idx] = trainmetrics["score"]

        testloss, testiou, testbiou, testscore = test(opts, valloader, model, lossfn)
        trainloss = round(losstotal.mean(), 4)
        trainiou = round(ioutotal.mean(), 4)
        trainbiou = round(bioutotal.mean(), 4)
        trainscore = round(scoretotal.mean(), 4)



        if testscore > bestscore:
            bestscore = testscore
            print("new best score:", bestscore, "- saving model weights")
            store_model_weights(opts, model, f"best", epoch=e)
        else:
            store_model_weights(opts, model, f"last", epoch=e)

        ## save the IOU best model

        if testiou > bestiou:
            bestiou = testiou
            print("new best iou:", bestiou, "- saving model weights")
            store_model_weights(opts, model, f"best_iou", epoch=e)
        else:
            store_model_weights(opts, model, f"last_iou", epoch=e)

        wandb.log({"loss":loss, "testloss": testloss, "trainloss": trainloss, "testiou": testiou, "testbiou": testbiou,"trainbiou":trainbiou, "trainiou": trainiou, "trainscore": trainscore})
        wandb.log({"bestscore" : bestscore, "bestiou": bestiou})
        wandb.watch(model)
        print(tabulate(
             [["train", trainloss, trainiou, trainbiou, trainscore]],
             headers=["Type", "Loss", "IoU", "BIoU", "Score"]))

        print(tabulate(
            [["test", testloss, testiou, testbiou, testscore, bestscore, bestiou]],
            headers=["Type", "Loss", "IoU", "BIoU", "Score", "BestScore", "Bestiou"]))

        scoredict = {
            "epoch": e,
            "trainloss": trainloss,
            "testloss": testloss,
            "trainiou": trainiou,
            "testiou": testiou,
            "trainbiou": trainbiou,
            "testbiou": testbiou,
            "trainscore": trainscore,
            "testscore": testscore
        }

        record_scores(opts, scoredict)


if __name__ == "__main__":

    parser = argparse.ArgumentParser("Training a segmentation model")

    parser.add_argument("--epochs", type=int, default=80, help="Number of epochs for training")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate used during training")
    parser.add_argument("--config", type=str, default="config/data.yaml", help="Configuration file to be used")
    # parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument("--task", type=int, default=1)
    parser.add_argument("--data_ratio", type=float, default=1.0,
                        help="Percentage of the whole dataset that is used")
    parser.add_argument("--name", type=str, default="run_seg")

    args = parser.parse_args()
    wandb.init(
        # mode="disabled",
                project="BuildingSeg",
               entity="lennylei",
               config={
                   "epochs": args.epochs,
                   "lr":args.lr
               }
               )


    wandb.run.name = args.name

    # Import config
    opts = load(open(args.config, "r"), Loader)

    # Combine args and opts in single dict
    try:
        opts = opts | vars(args)
    except Exception as e:
        opts = {**opts, **vars(args)}
    print(torch.cuda.is_available())
    print(torch.cuda.device_count())
    device = torch.device('cuda' if torch.cuda.is_available else 'cpu')
    opts["device"] = device
    print("Opts:", opts)

    rundir = create_run_dir(opts)
    opts["rundir"] = rundir
    dump(opts, open(os.path.join(rundir, "opts.yaml"), "w"), Dumper)

    train(opts)
    wandb.finish()
