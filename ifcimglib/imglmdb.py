# AUTOGENERATED! DO NOT EDIT! File to edit: notebooks/imglmdb.ipynb (unless otherwise specified).

__all__ = ['imglmdb', 'multidbwrapper']

# Cell
import lmdb
import os.path
import pickle
import numpy
import logging

# Cell
class imglmdb:

    def __init__(self, db_path, endianess="big"):
        self.db_path = db_path
        self.env = lmdb.open(db_path, subdir=os.path.isdir(db_path),
            readonly=True, lock=False,readahead=False, meminit=False)
        self.endianess = endianess
        self.logger = logging.getLogger(__name__)
        self.dropped = set()

        with self.get_read_txn() as txn:
            self.length = int.from_bytes(txn.get(b"__len__"), endianess)
            self.names = txn.get(b'__names__').decode("utf-8").split(' ')
            self.channels_of_interest = [i for i in range(len(self.names))]

            self.targets = txn.get(b'__targets__', default=None)
            if self.targets is not None:
                self.targets = pickle.loads(targets)
        self.idx_byte_length = int(numpy.ceil(numpy.floor(numpy.log2(self.length))/8.))

        self.logger.info("Initialized db (%s) with length %d, and channel names %s" % (self.db_path, self.length, " ".join(self.names)))

    def set_channels_of_interest(self, arr):
        self.channels_of_interest = arr
        self.logger.info("Channels of interest set to %s" % " ".join([self.names[i] for i in arr]))

    def get_read_txn(self):
        return self.env.begin(write=False)

    def get_write_txn(self):
        return self.env.begin(write=True)

    def get_masked_image(self, idx, only_coi = False, txn = None):
        ret = self.get_image(idx, only_coi, txn)

        if len(ret) > 2:
            return numpy.multiply(ret[0], ret[1]), ret[2]
        else:
            return numpy.multiply(ret[0], ret[1])

    def get_image(self, idx, only_coi = False, txn = None):

        if idx in self.dropped:
            raise ValueError("Index is dropped. Call `reset` to reset dropped elements.")

        if txn is None:
            with self.get_read_txn() as txn:
                i, m = pickle.loads(txn.get(int(idx).to_bytes(self.idx_byte_length, "big")))
        else:
            i, m = pickle.loads(txn.get(int(idx).to_bytes(self.idx_byte_length, "big")))

        if only_coi:
            i = i[self.channels_of_interest]
            m = m[self.channels_of_interest]

        if self.targets is None:
            return numpy.array(i), numpy.array(m)

        return numpy.array(i), numpy.array(m), self.targets[idx]

    def get_images(self, idx, only_coi = False, only_image=False, masked=False):
        func = self.get_masked_image if masked else self.get_image

        with self.get_read_txn() as txn:
            ret = []
            if only_image:
                for i in idx:
                    try:
                        ret.append(func(i, only_coi, txn)[0])
                    except ValueError:
                        pass
            else:
                for i in idx:
                    try:
                        ret.append(func(i, only_coi, txn))
                    except ValueError:
                        pass

            return ret


    def __iter__(self):
        self.pointer = 0
        return self

    def __next__(self):
        if self.pointer < self.length:
            while self.pointer in self.dropped: # skip virtually dropped instances
                self.pointer += 1
            self.pointer += 1
            return self.get_image(self.pointer-1)
        else:
            raise StopIteration()

    def drop(self, idx):
        self.dropped.update(idx)

    def drop_commit(self):
        with self.get_write_txn() as txn:
            for idx in self.dropped:
                txn.delete(
                    int(idx).to_bytes(self.idx_byte_length, "big")
                )

    def reset(self):
        self.dropped = set()

    def __del__(self):
        self.env.close()

    def __len__(self):
        return self.length - len(self.dropped)

    def __repr__(self):
        return "db %s, length %d, channels %s" % (self.db_path.split("/")[-1], self.length, " ".join(self.names))

# Cell

class multidbwrapper:

    def __init__(self, db_paths, channels=[]):
        self.db_paths = db_paths
        self.dbs = []
        self.db_start_index = []

        self.length = 0
        tmp_channels = []
        self.__targets = []
        for db_path in self.db_paths:
            db = imglmdb(db_path)
            self.length += len(db)
            tmp_channels.append(db.names)
            self.__targets.extend(db.targets)

        self.__targets = numpy.array(self.__targets)
        self.__label_offset = self.__targets.min()
        self.__targets -= self.__label_offset
        self.__classes = numpy.unique(self.__targets)

        if all(len(i) == len(tmp_channels[0]) for i in tmp_channels):
            if len(channels) > 0:
                self.__channels_of_interest = channels
            else:
                self.__channels_of_interest = [i for i in range(len(tmp_channels[0]))]
        else:
            raise ValueError("Not all DBs contain the same amount of channels.")

    @property
    def targets(self):
        return self.__targets
    @property
    def classes(self):
        return self.__classes
    @property
    def dtype(self):
        return numpy.float32
    @property
    def channels_of_interest(self):
        return self.__channels_of_interest
    @property
    def label_offset(self):
        return self.__label_offset
    def __len__(self):
        return self.length
    def __str__(self):
        return f"{self.length} instances from {len(self.dbs)} databases."

    def _setup(self):
        """Private function used to setup databases. Required for multiprocessing.
        """
        i = 0
        for db_path in self.db_paths:
            db = imglmdb(db_path)
            db.set_channels_of_interest(self.channels_of_interest)

            self.dbs.append(db)
            self.db_start_index.append(i)

            i += len(db)

        self.db_start_index = numpy.array(self.db_start_index)

    def get_image(self, index, only_coi=True):
        """Fetches instance from database based on index.

        Arguments:
            index {int} -- Index of instance to be fetched

        Returns:
            tuple -- image [, label]
        """
        if len(self.dbs) == 0:
            self._setup()

        db_idx = sum(self.db_start_index - index <= 0)-1
        db = self.dbs[db_idx]
        start_idx = self.db_start_index[db_idx]

        image, mask, label = db.get_image(index-start_idx, only_coi=only_coi)

        return image, mask, label-self.label_offset