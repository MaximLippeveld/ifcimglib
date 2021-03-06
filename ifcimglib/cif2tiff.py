# AUTOGENERATED! DO NOT EDIT! File to edit: notebooks/cif2tiff.ipynb (unless otherwise specified).

__all__ = ['PIL_logger', 'convert', 'convert_cmd']

# Cell
import math
import javabridge
import bioformats as bf
import numpy as np
import logging
from tqdm import tqdm
from pathlib import Path
import numpy
import click
import flowio
from PIL import Image
from multiprocessing import Pool
import sys
import logging

# disable PIL lowwing
PIL_logger = logging.getLogger('PIL')
PIL_logger.setLevel(logging.ERROR)

import tblib.pickling_support
tblib.pickling_support.install()

# Internal Cell

def _is_image(_series, _r):
    _r.rdr.setSeries(_series)
    return _r.rdr.getPixelType() != 1

# Internal Cell

class ExceptionWrapper(object):

    def __init__(self, ee):
        self.ee = ee
        __, __, self.tb = sys.exc_info()

    def re_raise(self):
        raise self.ee.with_traceback(self.tb)

# Internal Cell

def setup_directory_structure(out, fcs):
    data = flowio.FlowData(fcs)

    label_idx = None
    for k, v in data.channels.items():
        if v["PnN"] == "label":
            label_idx = int(k)

    assert label_idx is not None, "No label column present in fcs file"

    labels = numpy.reshape(data.events, (-1, data.channel_count))[:, label_idx-1].astype(int)

    prefix = Path(out).joinpath(*Path(fcs).parts[-3:-1])
    for label in numpy.unique(labels):
        (prefix / str(label)).mkdir(exist_ok=True, parents=True)

    return labels, prefix

def process_chunk(images, crange):
    try:
        logger = logging.getLogger(__name__)
        logger.debug("[process_chunk] enter")
        upper_bound = images[0].reshape(len(crange), -1).max(axis=1)
        lower_bound = images[0].reshape(len(crange), -1).min(axis=1)

        counter = 1
        for i in images[1:]:
            a = images[counter].reshape(len(crange), -1).min(axis=1)
            b = images[counter].reshape(len(crange), -1).max(axis=1)
            lower_bound = np.where(a < lower_bound, a, lower_bound)
            upper_bound = np.where(b > upper_bound, b, upper_bound)

            counter += 1

        logger.debug("[process_chunk] done")
        return lower_bound, upper_bound
    except Exception as e:
        logger.debug("[process_chunk] error")
        return ExceptionWrapper(e)

def get_min_max_in_file(reader, r_length, crange, nprocs, nchunks):
    logger = logging.getLogger(__name__)
    logger.info(f"[get_min_max_in_file] enter")

    chunks = numpy.array_split(numpy.arange(0, r_length, step=2), nchunks)
    image_chunks = [None]*len(chunks)

    with Pool(processes=nprocs) as pool:
        results = []
        lower_bound, upper_bound = None, None
        for i, chunk in tqdm(enumerate(chunks), position=0, leave=False, total=len(chunks)):

            images = [None]*len(chunk)
            for j, series in tqdm(enumerate(chunk), total=len(chunk), position=1, leave=False, mininterval=10):
                first = reader.read(c=0, series=series)
                im = numpy.empty(shape=(len(crange),) + first.shape, dtype=first.dtype)
                mask = numpy.empty(shape=(len(crange),) + first.shape, dtype=first.dtype)

                im[0] = first
                for c in crange[1:]:
                    im[c] = reader.read(c=c, series=series)
                for c in crange:
                    mask[c] = reader.read(c=c, series=series+1)
                images[j] = im*mask

            image_chunks[i] = images
            results.append(pool.apply_async(process_chunk, args=(image_chunks[i], crange)))
            logger.info(f"[get_min_max_in_file] submitted chunk {i}")

        for i, result in enumerate(results):
            logger.info(f"[get_min_max_in_file] waiting for result {i}")
            r = result.get()

            if isinstance(r, ExceptionWrapper):
                r.re_raise()

            a, b = r

            if lower_bound is None:
                lower_bound = a
            else:
                lower_bound = np.where(a < lower_bound, a, lower_bound)
            if upper_bound is None:
                upper_bound = b
            else:
                upper_bound = np.where(b > upper_bound, b, upper_bound)
        results = []

    logger.info(f"[get_min_max_in_file] done")
    return lower_bound, upper_bound, image_chunks

# Cell

def convert(cif_files, fcs_files, output, channels, nproc=1, nchunks=None, limit=-1, external_jvm_control=False):

    if nchunks is None:
        nchunks = nproc

    output = Path(output)

    logger = logging.getLogger(__name__)

    try:

        if not external_jvm_control:
            logger.debug("[convert] starting Java VM")
            javabridge.start_vm(class_path=bf.JARS, run_headless=True, max_heap_size="12G")
            logger.debug("[convert] started Java VM")

        counter = 0
        for cif, fcs in zip(cif_files, fcs_files):
            logging.info(f"[convert] processing {cif}")

            labels, prefix = setup_directory_structure(output, fcs)

            reader = bf.formatreader.get_image_reader("reader", path=cif)

            r_length = javabridge.call(reader.metadata, "getImageCount", "()I")
            if limit != -1:
                r_length = limit

            num_channels = javabridge.call(reader.metadata, "getChannelCount", "(I)I", 0)

            if len(channels) == 0:
                crange = [i for i in range(num_channels)]
            else:
                crange = np.array(channels)-1

            logging.debug(f"[convert] starting get_min_max for {cif}")
            lower_bound, upper_bound, image_chunks = get_min_max_in_file(reader, r_length, crange, nproc, nchunks)
            logging.debug(f"[convert] get_min_max for {cif} done")
            lower_bound = lower_bound.reshape(len(crange), 1, 1)
            upper_bound = upper_bound.reshape(len(crange), 1, 1)

            label_idx = 0
            logging.debug(f"[convert] writing out images for {cif}")
            for images in tqdm(image_chunks, position=0, leave=False, mininterval=10):
                for im in images:
                    im = (((im - lower_bound) / (upper_bound - lower_bound))*(2**16)).astype(numpy.uint16)
                    pillow_img = Image.fromarray(im[0], mode="I;16")
                    pillow_img.save(
                        prefix / str(labels[label_idx]) / f"{counter}.tiff",
                        append_images = [Image.fromarray(im[i], mode="I;16") for i in range(1, im.shape[0])],
                        save_all = True
                    )
                    counter+=1
                    label_idx+=1

            logging.debug(f"[convert] all images written for {cif}")

    finally:
        if not external_jvm_control:
            logging.debug(f"[convert] killing vm")
            javabridge.kill_vm()

# Cell
@click.command(name="cif2tiff")
@click.argument("cif", type=click.Path(exists=True, file_okay=False))
@click.argument("output", type=click.Path(exists=False, file_okay=False))
@click.option("--channels", multiple=True, type=int, default=[], help="Images from these channels will be extracted. Default is to extract all. 1-based index.")
@click.option("--nproc", type=int, default=-1, help="Amount of processes to use.")
@click.option("--nchunks", type=int, default=-1, help="Amount of chunks to use.")
@click.option("--debug", is_flag=True, flag_value=True, help="Show debugging information.", default=False)
@click.option("--limit", type=int, default=-1, help="Limit images to load from each file.")
def convert_cmd(cif, output, channels, nproc, nchunks, debug, limit):

    if nproc == -1:
        from multiprocessing import cpu_count
        nproc = cpu_count()

    if nchunks == -1:
        nchunks = nproc

    if debug:
        logging.basicConfig(level=logging.DEBUG)

    import glob
    cif_files = glob.glob(str(Path(cif) / "**" / "*.cif"))
    fcs_files = [str(Path(f).with_suffix(".fcs")) for f in cif_files]

    convert(cif_files, fcs_files, output, channels, nproc, nchunks, limit)