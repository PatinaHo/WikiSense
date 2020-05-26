import pandas as pd
import numpy as np
import json
import random
from tqdm import tqdm

from torchtext.data import Field
from torchtext.data import TabularDataset
from torchtext.data import Iterator, BucketIterator

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.autograd import Variable

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
HIDDEN_DIM = 500


def custom_tokenizer(string):
    return string.split(', ')


class BatchWrapper:
    def __init__(self, dl, x_var1, x_var2, y_vars):
        self.dl, self.x_var1, self.x_var2, self.y_vars = dl, x_var1, x_var2, y_vars # we pass in the list of attributes for x and y
    
    def __iter__(self):
        for batch in self.dl:
            x1 = getattr(batch, self.x_var1) # we assume two inputs in this wrapper
            x2 = getattr(batch, self.x_var2)
            
            if self.y_vars is not None: # we will concatenate y into a single tensor
                y = torch.cat([getattr(batch, feat).unsqueeze(1) for feat in self.y_vars], dim=1).float()
            else:
                y = torch.zeros((1))

            yield (x1, x2, y)
    
    def __len__(self):
        return len(self.dl)


class InnerproductBaseline(nn.Module):
    def __init__(self, hidden_dim, emb_dim=300, num_linear=1):
        super().__init__()
        self.sigmoid = nn.Sigmoid()
        self.wn_embedding = nn.Embedding(len(WN_TEXT.vocab), emb_dim, padding_idx=1)
        self.wd_embedding = nn.Embedding(len(WD_TEXT.vocab), emb_dim, padding_idx=1)

    def forward(self, wn_path, wd_path):
        wn_emb  = self.wn_embedding(wn_path) # (16,64,300)
        wd_emb  = self.wd_embedding(wd_path) # (175,64,300)
        wn_layer1 = torch.sum(wn_emb, dim=0) # (64, 300)
        wd_layer1 = torch.sum(wd_emb, dim=0) # (64, 300)
        
        product = torch.bmm(wn_layer1[:, None,:], wd_layer1[:,:, None])  # (64, )
        sigmoid_product = self.sigmoid(product)
        
        return sigmoid_product


if __name__ == "__main__":
    
    #############################
    #######  讀檔, 轉type  #######
    #############################

    df = pd.read_csv('/home/nlplab/patina/WikiSense/data/train_align_gt.csv', delimiter='\t', header=0, engine='python', comment='#')
    for col in df.columns[:-1]:
        df[col] = df[col].fillna(np.NaN).astype(str)
    df['alignment'] = df['alignment'].fillna(0.0).astype(int)

    with open('stop_pages.json', 'r') as f:
        stop_pages = json.load(f)


    #############################################
    ##  Use torchtext to generate data vector  ##
    #############################################

    WD_TEXT = Field(sequential=True, tokenize=custom_tokenizer, lower=True, stop_words=stop_pages)
    WN_TEXT = Field(sequential=True, tokenize=custom_tokenizer, lower=True)
    LABEL = Field(sequential=False, use_vocab=False)

    tv_datafields = [("id", LABEL), ("wikiTitle", None), ("wnSyn", None), ("wdId", None),
                    ("wn_path", WN_TEXT), ("wd_path", WD_TEXT), ("alignment", LABEL)]
    trn, vld = TabularDataset.splits(
                path="/home/nlplab/patina/WikiSense/jupyter_nb/pathClassifier_experiment",
                train='train.tsv', validation="val.tsv",
                format='tsv',
                skip_header=True,
                fields=tv_datafields)

    tst_datafields = [("wikiTitle", None), ("wnSyn", None), ("wdId", None),
                    ("wn_path", WN_TEXT), ("wd_path", WD_TEXT), ("alignment", None)]
    tst = TabularDataset.splits(
                path="/home/nlplab/patina/WikiSense/jupyter_nb/pathClassifier_experiment/test.tsv",
                format='tsv',
                skip_header=True,
                fields=tst_datafields)

    WN_TEXT.build_vocab(trn, max_size=3000)
    WD_TEXT.build_vocab(trn, max_size=3000)

    # split into batches
    train_iter, val_iter = BucketIterator.splits(
        (trn, vld),
        batch_sizes=(64, 64),
        device=device,
        sort_key=lambda x: len(x.wd_path),
        sort_within_batch=False,
        repeat=False
    )
    test_iter = Iterator(tst, batch_size=64, device=device, sort_key=False, sort_within_batch=False, repeat=False)

    # wrap the batchIterator so iterate over data is easier
    train_dl = BatchWrapper(train_iter, "wn_path", "wd_path", ['alignment'])
    valid_dl = BatchWrapper(val_iter, "wn_path", "wd_path", ['alignment'])
    test_dl = BatchWrapper(test_iter, "wn_path", "wd_path", None)


    ##################################
    ####  Model setup & training  ####
    ##################################

    model = InnerproductBaseline(HIDDEN_DIM, emb_dim=300).to(device)
    opt = optim.Adam(model.parameters(), lr=1e-2)
    loss_func = nn.BCELoss()

    epochs = 50

    for epoch in range(1, epochs + 1):
        running_loss = 0.0
        running_corrects = 0
        model.train() # turn on training mode
        for x1, x2, y in train_dl:
            opt.zero_grad()
            
            preds = model(x1.to(device), x2.to(device))
            loss = loss_func(preds, y.to(device))
            loss.backward()
            opt.step()

            running_loss += loss.data * x1.size(1)

        epoch_loss = running_loss / len(trn)

        # calculate the validation loss for this epoch
        val_loss = 0.0
        model.eval() # turn on evaluation mode
        for x1, x2, y in valid_dl:
            preds = model(x1.to(device), x2.to(device))
            loss = loss_func(preds, y.to(device))
            val_loss += loss.data * x1.size(1)

        val_loss /= len(vld)
        print('Epoch: {}, Training Loss: {:.4f}, Validation Loss: {:.4f}'.format(epoch, epoch_loss, val_loss))