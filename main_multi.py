import os
import math
from termcolor import colored
import numpy as np
import matplotlib
matplotlib.use('Agg')

from data_helpers import load_data
from keras import callbacks
from keras.utils.vis_utils import plot_model
from matplotlib import pyplot as plt
from keras import backend as K
from capsule_net import CapsNet


def lambda1(epoch):
    return 0.001 * np.exp(-epoch / 10.)


def lambda2(epoch):
   initial_lrate = 0.1
   k = 0.1
   return k*initial_lrate/np.sqrt(epoch + K.epsilon())


def step_decay(epoch):
    initial_lrate = 0.1
    drop = 0.5
    epochs_drop = 5
    lrate = initial_lrate * math.pow(drop, math.floor((1+epoch)/epochs_drop))
    return lrate


def margin_loss(y_true, y_pred):
    L = y_true * K.square(K.maximum(0., 0.9 - y_pred)) + 0.5 * (1 - y_true) * K.square(K.maximum(0., y_pred - 0.1))
    return K.mean(K.sum(L, 1))


def train(model, train, dev, test, save_directory, optimizer, epoch, batch_size, schedule):
    (X_train, Y_train) = train
    (X_dev, Y_dev) = dev
    (X_test, Y_test) = test

    # Callbacks
    log = callbacks.CSVLogger(filename=save_directory + '/log.csv')

    tb = callbacks.TensorBoard(log_dir=save_directory + '/tensorboard-logs', batch_size=batch_size)

    checkpoint = callbacks.ModelCheckpoint(filepath=save_directory + '/weights-improvement-{epoch:02d}.hdf5',
                                           save_best_only=True,
                                           save_weights_only=True,
                                           verbose=1)

    lr_decay = callbacks.LearningRateScheduler(schedule=schedule, verbose=1)

    # compile the model
    model.compile(optimizer=optimizer,
                  loss=[margin_loss],
                  metrics=['accuracy'])

    history = model.fit(x=X_train,
              y=Y_train,
              validation_data=[X_dev, Y_dev],
              batch_size=batch_size,
              epochs=epoch,
              callbacks=[log, tb, checkpoint, lr_decay],
              shuffle=True,
              verbose=1)

    score = model.evaluate(X_test, Y_test, batch_size=batch_size)

    print colored(save_directory, 'green')
    print colored(score, 'green')
    print(history.history.keys())

    # Summarize history for accuracy
    plt.plot(history.history['acc'])
    plt.plot(history.history['val_acc'])
    plt.title('model accuracy')
    plt.ylabel('accuracy')
    plt.xlabel('epoch')
    plt.legend(['training accuracy', 'testing accuracy'], loc='upper left')
    plt.savefig(save_directory + '/model_accuracy.png')
    plt.close()

    # Summarize history for loss
    plt.plot(history.history['loss'])
    plt.plot(history.history['val_loss'])
    plt.title('model loss')
    plt.ylabel('loss')
    plt.xlabel('epoch')
    plt.legend(['training loss', 'testing loss'], loc='upper left')
    plt.savefig(save_directory + '/model_loss.png')
    plt.close()

    model.save_weights(save_directory + '/trained_model.h5')


if __name__ == "__main__":
    # Databases
    databases = ["MR", "SST-1", "SST-2", "SUBJ", "TREC", "ProcCons", "IMDB"]

    # Hyperparameters
    optimizers = ['adam', 'nadam']
    epochs = [10, 20]
    batch_sizes = [200, 500]
    schedules = [lambda1, lambda2, step_decay]

    save_dir = './multi'
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # Train
    for d in databases:
        print(d)

        (x_train, y_train), (x_dev, y_dev), (x_test, y_test), vocab_size, max_len = load_data(d)

        for o in optimizers:
            for e in epochs:
                for bz in batch_sizes:
                    for s in schedules:

                        model = CapsNet(input_shape=x_train.shape[1:],
                                        n_class=len(np.unique(np.argmax(y_train, 1))),
                                        num_routing=3,
                                        vocab_size=vocab_size,
                                        embed_dim=50,
                                        max_len=max_len
                                        )

                        model.summary()
                        plot_model(model, to_file=save_dir + '/model.png', show_shapes=True)

                        dir = save_dir + '/' + d
                        if not os.path.exists(dir):
                            os.makedirs(dir)

                        folder = dir + "/o=" + o + ",e=" + str(e) + ",bz=" + str(bz) + ",s=" + s.__name__
                        if not os.path.exists(folder):
                            os.makedirs(folder)

                        train(
                            model=model,
                            train=(x_train, y_train),
                            dev=(x_dev, y_dev),
                            test=(x_test, y_test),
                            save_directory=folder,
                            optimizer=o,
                            epoch=e,
                            batch_size=bz,
                            schedule=s
                        )
