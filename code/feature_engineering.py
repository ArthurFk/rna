import numpy as np
from sklearn.preprocessing import LabelEncoder, OneHotEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import *
import re
import time

protein_list = ['AGO1', 'AGO2', 'AGO3', 'ALKBH5', 'AUF1', 'C17ORF85', 'C22ORF28', 'CAPRIN1', 'DGCR8', 'EIF4A3', 'EWSR1',
                'FMRP', 'FOX2', 'FUS', 'FXR1', 'FXR2', 'HNRNPC', 'HUR', 'IGF2BP1', 'IGF2BP2', 'IGF2BP3', 'LIN28A',
                'LIN28B',
                'METTL3', 'MOV10', 'PTB', 'PUM2', 'QKI', 'SFRS1', 'TAF15', 'TDP43', 'TIA1', 'TIAL1', 'TNRC6', 'U2AF65',
                'WTAP', 'ZC3H7B']

number_of_protein = len(protein_list)


def get_data(data_path="../dataset/trainset/", positive=1, negative=0, unwatched=-1):
    """
    Get data from dataset
    Input:
        data_path: The path of dataset
        positive: The expectation label of positive labels
        negative: The expectation label of negative labels
        unwatched: The expectation label of unwatched labels

    Output:
        all_rna: A list which contains all rna sequences.
        labels: A numpy array with shape [len(all_rna), number_of_protein]
    """
    rna_dic = {}
    all_rna = []
    labels = []

    for iter_protein in range(number_of_protein):
        fin = open(data_path + protein_list[iter_protein], 'r')
        for line in fin.readlines():
            try:
                rna, label = line.split('\t')
            except:
                print("ERROR")
                break

            if rna not in rna_dic:
                rna_dic[rna] = len(all_rna)
                all_rna.append(rna)
                labels.append(np.ones([number_of_protein]) * unwatched)

            label = int(label)
            labels[rna_dic[rna]][iter_protein] = positive if label == 1 else negative
    labels = np.array(labels)
    assert labels.shape == (len(all_rna), number_of_protein)
    return all_rna, labels


def get_data_sep(data_path="dataset/trainset/", positive=1, negative=0):
    """
    rarely same as above
    """
    rnas = []
    labels = []
    encoder = {'A': 0, 'G': 1, 'C': 2, 'T': 3}
    for pot in protein_list:
        replicate = set()
        fin = open(data_path + pot)
        X = []
        y = []
        for line in fin.readlines():
            rna, label = line.split('\t')
            if rna in replicate:
                continue
            else:
                replicate.add(rna)
            label = positive if int(label) == 1 else negative
            try:
                rna = list(map(lambda x: encoder[x], rna))
            except:
                continue
            X.append(rna)
            y.append(label)
        enc = OneHotEncoder(n_values=4)
        X = enc.fit_transform(X).toarray()
        y = np.array(y)
        rnas.append(X)
        labels.append(y)
    return rnas, labels


def get_data_2(data_path="../dataset/RNA_trainset2/", positive=1, negative=0, unwatched=-1):
    """
    Get data from dataset.
    Input:
        data_path: The path of dataset
        positive: The expectation label of positive labels
        negative: The expectation label of negative labels
        unwatched: The expectation label of unwatched labels

    Output:
        all_rna: A list which contains all rna sequences.
        labels: A numpy array with shape [len(all_rna), number_of_protein]
    """
    rna_dic = {}
    all_rna = []
    labels = []
    all_seq = []
    energies = []

    for iter_protein in range(number_of_protein):
        fin = open(data_path + protein_list[iter_protein] + '/train', 'r')
        fin_2nd = open(data_path + protein_list[iter_protein] + '/train_2nd', 'r')
        fin_lines = fin.readlines()
        fin_2nd_lines = fin_2nd.readlines()
        length = len(fin_lines)
        line2 = None
        for i in range(length):
            try:
                line = fin_lines[i]
                line2 = fin_2nd_lines[2 * i]
                label2 = fin_2nd_lines[2 * i + 1]

                rna, label = line.split('\t')

                line2 = line2.replace("\n", "")
                line2 = line2.split(' ')
                line2 = [i for i in line2 if i != "" and i != "(" and i != ")"]
                seq, energy = line2
                energy = energy.replace('(', "")
                energy = energy.replace(')', "")
                energy = float(energy)

                label = int(label)
                label2 = int(label2)

                assert label == label2
            except Exception as e:
                print(line2)
                print(e)
                break

            if rna not in rna_dic:
                rna_dic[rna] = len(all_rna)
                all_rna.append(rna)
                all_seq.append(seq)
                energies.append(energy)
                labels.append(np.ones([number_of_protein]) * unwatched)

            label = int(label)
            labels[rna_dic[rna]][iter_protein] = positive if label == 1 else negative
    labels = np.array(labels)
    assert labels.shape == (len(all_rna), number_of_protein)
    return all_rna, all_seq, labels, energies


def aucs(label, pred):
    aucs = []
    p = []
    l =[]
    for i in range(1):
        p.append([])
        l.append([])
    for i in range(len(label)):
        for j in range(len(label[i])):
            if label[i][j] != -1:
                l[j].append(label[i][j])
                p[j].append(pred[i][j])
    for i in range(1):
        aucs.append(roc_auc_score(l[i], p[i]))
    return aucs

def get_data_sep_2(data_path="../dataset/trainset/", positive=1, negative=0):
    """
    rarely same as above
    """
    rnas = []
    labels = []
    encoder = {'A': 0, 'G': 1, 'C': 2, 'T': 3}
    encoder_sec = {'S': 0, 'M': 1, 'H': 2, 'I': 3, 'T': 4, 'F': 5}
    for pot in protein_list:
        replicate = set()
        fin = open(data_path + pot)
        fin2 = open(data_path + pot + "_2nd")
        X = []
        y = []
        twostrs = []
        j = 0
        lines = fin.readlines()
        line2s = fin2.readlines()
        for i in range(len(lines)):
            line = lines[i]
            rna, label = line.split('\t')
            if 'N' in rna:
                continue
            line2 = line2s[j]
            twostr, label2 = line2.split('\t')

            assert label == label2
            if rna in replicate:
                continue
            else:
                replicate.add(rna)
            label = positive if int(label) == 1 else negative
            try:
                rna = list(map(lambda x: encoder[x], rna))
                twostr = list(map(lambda x: encoder_sec[x], twostr))
            except:
                continue
            X.append(rna)
            twostrs.append(twostr)
            y.append(label)
            j += 1
        enc = OneHotEncoder(n_values=4)
        X = enc.fit_transform(X).toarray()
        enc2 = OneHotEncoder(n_values=6)
        twostrs = enc2.fit_transform(twostrs).toarray()
        y = np.array(y)
        X = list(zip(X, twostrs))
        rnas.append(X)
        labels.append(y)
    return rnas, labels

def get_data_wordseg(data_path="dataset/trainset_wordseg/trainset/", positive=1, negative=0):
    """
    rarely same as above
    """
    rnas = []
    labels = []
    encoder = {'A': 0, 'G': 1, 'C': 2, 'T': 3}
    for pot in protein_list:
        replicate = set()
        fin = open(data_path + pot)
        fin2 = open(data_path + pot + "_wordseg")
        X = []
        y = []
        twostrs = []
        j = 0
        lines = fin.readlines()
        line2s = fin2.readlines()
        for i in range(len(lines)):
            line = lines[i]
            rna, label = line.split('\t')
            if 'N' in rna:
                continue
            line2 = line2s[j]
            twostr, label2 = line2.split('\t')
            twostr = re.split(r'[\s]', twostr)
            twostr = list(map(int, twostr))
            if rna in replicate:
                continue
            else:
                replicate.add(rna)
            label = positive if int(label) == 1 else negative
            try:
                rna = list(map(lambda x: encoder[x], rna))
            except:
                continue
            X.append(rna)

            twostrs.append(twostr)
            y.append(label)
            j += 1
        enc = OneHotEncoder(n_values=4)
        X = enc.fit_transform(X).toarray()
        y = np.array(y)
        X = list(zip(X, twostrs))
        print(len(X[0]))
        rnas.append(X)
        labels.append(y)
    return rnas, labels




if __name__ == '__main__':
    # start = time.time()
    # rnas, all_seq, labels, energies = get_data_2()
    # end = time.time()
    # print(len(rnas[1]), len(labels[1]), end-start, len(all_seq), len(energies), len(rnas))
    rnas, labels = get_data_wordseg()
    print(len(rnas[0]), labels[1].shape)

