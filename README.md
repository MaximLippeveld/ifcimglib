# ifcimglib



## Install

Run:

`pip install .`

to install this package.

## How to use

`cif2lmdb` can be used as follows:

```
Usage: cif2lmdb [OPTIONS] CIF

Options:
  --output FILE       Output filename. If not set, cif-filename is taken with
                      lmdb extension.

  --channels INTEGER  Images from these channels will be extracted. Default is
                      to extract all. 1-based index.

  --names TEXT        Names to assign to channels.
  --debug             Show debugging information. Limits output to 100 first
                      cells.

  --overwrite         Overwrite lmdb if it exists.
  --targets-npy FILE  Numpy binary file containing targets.
  --skip-npy FILE     Numpy binary file containing instances to be skipped.
  --help              Show this message and exit.
```

Here is an example command:
```
cif2lmdb --channels 1 --channels 6 --channels 9 --names BF --names SSC --names BF2 --output tmp.lmdb --debug --overwrite input.cif
```
It takes input.cif as input and outputs output.lmdb, an lmdb-file containing 100 (see debug flag) 3-channel images with names BF, SSC and BF2.

Please see the [imglmdb.ipynb](imglmdb.ipynb) notebook for usage examples of the `imglmdb` package.
