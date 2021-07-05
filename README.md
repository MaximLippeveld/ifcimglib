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

### Docker

![docker badge](https://img.shields.io/docker/pulls/maximlippeveld/ifcimglib?style=flat-square)

[Docker images](https://hub.docker.com/r/maximlippeveld/ifcimglib) are available for cif2lmdb (tag cif2lmdb), the jupyter lab environment (tag jupyter-lab-env), and the notebooks in this repository (tag notebooks).

For using cif2lmdb, run:
```
docker run --rm -v /path/to/data/dir:/data maximlippeveld/ifcimglib:cif2lmdb [OPTIONS] /data/example.cif
```
For using the jupyter environment, run:
```
docker run --it -v /path/to/data/dir:/data -v /path/to/your/code/dir:/app -p [your-port]:8888 maximlippeveld/ifcimglib:jupyter-lab-env
```
Fur using the notebooks in this repository, run:
```
docker run --it -v /path/to/data/dir:/data -p [your-port]:8888 maximlippeveld/ifcimglib:notebooks
```
