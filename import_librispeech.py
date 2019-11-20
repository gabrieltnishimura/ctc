"""
Taken from https://github.com/mozilla/DeepSpeech

mozilla/DeepSpeech is licensed under the
Mozilla Public License 2.0

LibriSpeech
    NAME    : LibriSpeech SLR 12
    URL     : http://www.openslr.org/12/
    HOURS   : 1,000
    TYPE    : Read - English
    AUTHORS : Vassil Panayotov et al
    TYPE    : FREE
    LICENCE : CC BY 4.0

Modified slightly to generate .flac in stead of .wav
"""


from __future__ import absolute_import, division, print_function

import os
# Make sure we can import stuff from util/
# This script needs to be run from the root of the DeepSpeech repository
import sys

sys.path.insert(1, os.path.join(sys.path[0], '..'))

import codecs
import fnmatch
import pandas
import tarfile
import unicodedata
from shutil import copyfile

from tensorflow.contrib.learn.python.learn.datasets import base
from tensorflow.python.platform import gfile


def _download_and_preprocess_data(data_dir):
    # Conditionally download data to data_dir
    print("Downloading Librivox data set (55GB) into {} if not already present...".format(data_dir))

    def filename_of(x): return os.path.split(x)[1]

    TRAIN_CLEAN_100_URL = "http://www.openslr.org/resources/12/dev-other.tar.gz"
    train_clean_100 = base.maybe_download(filename_of(TRAIN_CLEAN_100_URL), data_dir, TRAIN_CLEAN_100_URL)
    print("Extracting librivox data if not already extracted...")
    LIBRIVOX_DIR = "LibriSpeech"
    work_dir = os.path.join(data_dir, LIBRIVOX_DIR)
    _maybe_extract(data_dir, os.path.join(LIBRIVOX_DIR, "dev-other"), train_clean_100)
    print("Moving files and splitting transcriptions...")
    train_100 = _convert_audio_and_split_sentences(work_dir, "dev-other", "dev-other-new")
    train_100.to_csv(os.path.join(data_dir, "librivox-dev-other.csv"), index=False)


def _maybe_extract(data_dir, extracted_data, archive):
    # If data_dir/extracted_data does not exist, extract archive in data_dir
    if not gfile.Exists(os.path.join(data_dir, extracted_data)):
        tar = tarfile.open(archive)
        tar.extractall(data_dir)
        tar.close()


def _convert_audio_and_split_sentences(extracted_dir, data_set, dest_dir):
    source_dir = os.path.join(extracted_dir, data_set)
    target_dir = os.path.join(extracted_dir, dest_dir)

    # print('Source dir: ', source_dir)
    # print('target dir: ', target_dir)

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    # Loop over transcription files and split each one
    #
    # The format for each file 1-2.trans.txt is:
    #  1-2-0 transcription of 1-2-0.flac
    #  1-2-1 transcription of 1-2-1.flac
    #  ...
    #
    # Each file is then split into several files:
    #  1-2-0.txt (contains transcription of 1-2-0.flac)
    #  1-2-1.txt (contains transcription of 1-2-1.flac)
    #  ...
    #
    # We also convert the corresponding FLACs to WAV in the same pass
    files = []
    for root, dirnames, filenames in os.walk(source_dir):
        for filename in fnmatch.filter(filenames, '*.trans.txt'):
            trans_filename = os.path.join(root, filename)
            with codecs.open(trans_filename, "r", "utf-8") as fin:
                for line in fin:
                    # Parse each segment line
                    first_space = line.find(" ")
                    seqid, transcript = line[:first_space], line[first_space+1:]

                    # We need to do the encode-decode dance here because encode
                    # returns a bytes() object on Python 3, and text_to_char_array
                    # expects a string.
                    transcript = unicodedata.normalize("NFKD", transcript)  \
                                            .encode("ascii", "ignore")      \
                                            .decode("ascii", "ignore")

                    transcript = transcript.lower().strip()

                    # Convert corresponding FLAC to a WAV
                    old_file = os.path.join(root, seqid + ".flac")
                    target_file = os.path.join(target_dir, seqid + ".flac")
                    # target_file = os.path.join(target_dir, seqid + ".wav")
                    if not os.path.exists(target_file):
                        copyfile(old_file, target_file)
                        # Transformer().build(old_file, target_file)
                    filesize = os.path.getsize(target_file)
                    target_file_path = os.path.abspath(target_file)
                    files.append((target_file_path, filesize, transcript))

    return pandas.DataFrame(data=files, columns=["filename", "filesize", "transcript"])


if __name__ == "__main__":
    _download_and_preprocess_data(sys.argv[1])


