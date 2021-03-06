"""sys.argv[1]: epoch
   sys.argv[2]: train_batch_size
   sys.argv[3]: test_batch_size
"""
import sys

sys.path.insert(0, "../../../")
import tensorflow as tf
import numpy as np
import os

from sklearn.preprocessing import OneHotEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import *
from code.feature_engineering import get_data

data, label = get_data(data_path="../../../dataset/RNA_trainset/")
print(len(label))

rnas = []
for rna in data:
    encoder = {'A': 0, 'G': 1, 'C': 2, 'T': 3}
    rna = list(map(lambda x: encoder[x], rna))
    rnas.append(rna)
enc = OneHotEncoder()
rnas = enc.fit_transform(rnas).toarray()
X_train, X_test, y_train, y_test = train_test_split(rnas, label, test_size=0.2, random_state=42)
trainset = list(zip(X_train, y_train))
testset = list(zip(X_test, y_test))
print("Load dataset finished!")


def cal_accuracy(label, pred, thethold=0.5):
    total = 0.
    match = 0.
    for i in range(len(label)):
        for j in range(len(label[i])):
            if label[i][j] != -1:
                total += 1
                if label[i][j] == 0 and pred[i][j] < thethold or label[i][j] == 1 and pred[i][j] >= thethold:
                    match += 1
    return match / total


def ave_auc(label, pred):
    auc = []
    l = []
    p = []
    for i in range(37):
        l.append([])
        p.append([])
    for i in range(len(label)):
        for j in range(len(label[i])):
            if label[i][j] != -1:
                l[j].append(label[i][j])
                p[j].append(pred[i][j])
    for i in range(37):
        auc.append(roc_auc_score(l[i], p[i]))
    return np.mean(auc)


class Simple_Deep:
    def __init__(self, path, para, trainset, testset):
        self.graph = tf.Graph()
        self.prediction, self.trainstep, self.loss = None, None, None
        self._path = path
        self._save_path, self._logs_path = None, None
        self.para = para
        self.trainset = trainset
        self.testset = testset
        self.predict_threshold = None
        with self.graph.as_default():
            self._define_inputs()
            self._build_graph()
            self.initializer = tf.global_variables_initializer()
            self.local_initializer = tf.local_variables_initializer()
            self.saver = tf.train.Saver()
        self._initialize_session()

    @property
    def save_path(self):
        if self._save_path is None:
            save_path = '%s/checkpoint' % self._path
            if not os.path.exists(save_path):
                os.makedirs(save_path)
            save_path = os.path.join(save_path, 'model.ckpt')
            self._save_path = save_path
        return self._save_path

    @property
    def logs_path(self):
        if self._logs_path is None:
            logs_path = '%s/logs' % self._path
            if not os.path.exists(logs_path):
                os.makedirs(logs_path)
            self._logs_path = logs_path
        return self._logs_path

    def _initialize_session(self):
        config = tf.ConfigProto()
        config.gpu_options.allow_growth = True
        self.sess = tf.Session(graph=self.graph, config=config)

        self.sess.run(self.initializer)
        self.sess.run(self.local_initializer)

    def _define_inputs(self):
        self.input = tf.placeholder(
            tf.float32,
            shape=[None, self.para['dim']]
        )
        self.labels = tf.placeholder(
            tf.float32,
            shape=[None, self.para['label_dim']]
        )
        self.mask = tf.placeholder(
            tf.float32,
            shape=[None, self.para['label_dim']]
        )
        self.keep_prob = tf.placeholder(tf.float32, shape=[], name='keep_prob')
        self.predict_threshold = tf.placeholder(tf.float32, shape=[], name='threshold')

    def _build_graph(self):
        batchsize = tf.shape(self.input)[0]
        x = tf.reshape(self.input, [batchsize, self.para['len'], 4, 1])
        # x = tf.transpose(x, [0, 2, 1])
        # filter = tf.Variable(tf.random_normal([tf.shape(x)[1], 4, 1, 1]))
        conv = tf.layers.conv2d(x, 16, kernel_size=[4, 4], activation=tf.nn.relu)
        conv = tf.reshape(conv, [batchsize, int(conv.shape[1]), int(conv.shape[3])])
        out = tf.layers.max_pooling1d(conv, 3, strides=3)
        out = tf.nn.dropout(out, self.keep_prob)
        print(out.shape)
        cell_fw = tf.contrib.rnn.BasicLSTMCell(self.para['hidden_size'])
        cell_bw = tf.contrib.rnn.BasicLSTMCell(self.para['hidden_size'])
        cell_fw = tf.contrib.rnn.DropoutWrapper(cell_fw, input_keep_prob=self.keep_prob,
                                                output_keep_prob=self.keep_prob)
        cell_bw = tf.contrib.rnn.DropoutWrapper(cell_bw, input_keep_prob=self.keep_prob,
                                                output_keep_prob=self.keep_prob)
        cell_fw = tf.contrib.rnn.AttentionCellWrapper(cell_fw, attn_length=10)
        cell_bw = tf.contrib.rnn.AttentionCellWrapper(cell_bw, attn_length=10)
        output = tf.concat(tf.nn.bidirectional_dynamic_rnn(cell_fw, cell_bw, out, dtype=tf.float32)[0], 2)
        print(output.shape)
        len = int(output.shape[1]) - 1
        output = tf.slice(output, [0, len, 0], [-1, 1, -1])
        output = tf.reshape(output, [-1, 2 * self.para['hidden_size']])
        print(output.shape)
        output = tf.layers.dense(output, 128)
        output = tf.layers.dense(output, self.para['label_dim'])
        self.prediction = tf.nn.sigmoid(output)
        loss = tf.nn.sigmoid_cross_entropy_with_logits(labels=self.labels, logits=output)
        loss = tf.reduce_sum(tf.multiply(loss, self.mask)) / tf.reduce_sum(self.mask)

        weights = tf.trainable_variables()
        l1_reg = tf.contrib.layers.l1_regularizer(scale=5e-6)
        regularization_penalty = tf.contrib.layers.apply_regularization(l1_reg, weights)
        loss += regularization_penalty

        optimizer = tf.train.AdamOptimizer(self.para['lr'])
        self.trainstep = optimizer.minimize(loss)
        self.loss = loss

        # digit_prediction = tf.cast(tf.sign(tf.add(tf.sign(self.prediction - self.predict_threshold), 1)), tf.int64)
        # weights = tf.sign(tf.add(self.labels, 1))
        # self.labels = tf.cast(self.labels, tf.int64)
        # self.test_accuracy = tf.contrib.metrics.accuracy(labels=self.labels, predictions=digit_prediction,
        #                                               weights=weights)

    def test(self, batch_size):
        batch_per_epoch = int(len(self.testset) / batch_size)

        start_position = 0
        losses = []
        preds = []
        labels = []
        for b in range(batch_per_epoch):
            x, y = zip(*testset[start_position: start_position + batch_size])
            start_position += batch_size
            y = np.array(y)
            mask = y != -1
            mask = mask.astype(np.float32)
            feed_dict = {
                self.input: x,
                self.labels: y,
                self.mask: mask,
                self.keep_prob: 1,
                self.predict_threshold: 0
            }
            fetch = [self.loss, self.prediction]
            loss, pred = self.sess.run(fetch, feed_dict)
            losses.append(loss)
            labels += y.tolist()
            preds += pred.tolist()
            # print("Train epoch {0} batch {1} loss {2}".format(e, b, loss))
        auc = ave_auc(labels, preds)
        print("Test loss {0} accuracy {1} auc {2}".format(np.mean(losses), cal_accuracy(labels, preds),
                                                          auc))
        return auc

    def train(self, batch_size, epoch):
        batch_per_epoch = int(len(self.trainset) / batch_size)
        max_auc = 0
        for e in range(epoch):
            start_position = 0
            losses = []
            preds = []
            labels = []
            for b in range(batch_per_epoch):
                x, y = zip(*trainset[start_position: start_position + batch_size])
                start_position += batch_size
                y = np.array(y)
                mask = y != -1
                mask = mask.astype(np.float32)
                feed_dict = {
                    self.input: x,
                    self.labels: y,
                    self.mask: mask,
                    self.keep_prob: 0.5,
                    self.predict_threshold: 0
                }
                fetch = [self.trainstep, self.loss, self.prediction]
                _, loss, pred = self.sess.run(fetch, feed_dict)
                losses.append(loss)
                labels += y.tolist()
                preds += pred.tolist()
                # print("Train epoch {0} batch {1} loss {2}".format(e, b, loss))


            print(
                "Train epoch {0} loss {1} accuracy {2} auc {3}".format(e, np.mean(losses), cal_accuracy(labels, preds),
                                                                       ave_auc(labels, preds)))
            result = self.test(int(sys.argv[3]))
            if result > max_auc:
                max_auc = result
                self.save_model()


    def load_model(self):
        try:
            self.saver.restore(self.sess, self.save_path)
        except Exception:
            raise IOError('Failed to load model from save path: %s' % self.save_path)
        print('Successfully load model from save path: %s' % self.save_path)

    def save_model(self, global_step=None):
        self.saver.save(self.sess, self.save_path, global_step=global_step)


if __name__ == '__main__':
    para = {'len': 300, 'label_dim': 37, 'dim': 1200, 'hidden_size': 256, 'lr': float(sys.argv[4])}
    model = Simple_Deep('./model_atten_l1_conv2d', para, trainset, testset)
    model.train(batch_size=int(sys.argv[2]), epoch=int(sys.argv[1]))