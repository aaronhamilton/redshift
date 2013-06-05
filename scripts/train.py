#!/usr/bin/env python
#PBS -l walltime=10:00:00,mem=10gb,nodes=1:ppn=6

import random
import os
import sys
import plac
import time
from pathlib import Path
import pstats
import cProfile

import redshift.parser
import redshift.io_parse

USE_HELD_OUT = False

@plac.annotations(
    train_loc=("Training location", "positional"),
    train_alg=("Learning algorithm [static, online, max, early]", "option", "a", str),
    n_iter=("Number of Perceptron iterations", "option", "i", int),
    label_set=("Name of label set to use.", "option", "l", str),
    add_extra_feats=("Add extra features", "flag", "x", bool),
    feat_thresh=("Feature pruning threshold", "option", "t", int),
    allow_reattach=("Allow left-clobber", "flag", "r", bool),
    allow_reduce=("Allow reduce when no head is set", "flag", "d", bool),
    profile=("Run profiler (slow)", "flag", None, bool),
    debug=("Set debug flag to True.", "flag", None, bool),
    seed=("Set random seed", "option", "s", int),
    beam_width=("Beam width", "option", "k", int),
    movebeam=("Add labels to beams", "flag", "m", bool),
    bigrams=("What bigram to include/exclude, or all", "option", "b", str),
    add_clusters=("Add brown cluster features", "flag", "c", bool),
    n_sents=("Number of sentences to train from", "option", "n", int)
)
def main(train_loc, model_loc, train_alg="online", n_iter=15,
         add_extra_feats=False, label_set="Stanford", feat_thresh=1,
         allow_reattach=False, allow_reduce=False, bigrams='all',
         add_clusters=False, n_sents=0,
         profile=False, debug=False, seed=0, beam_width=1, movebeam=False):
    if bigrams == 'all':
        bigrams = range(45)
    elif bigrams.startswith('ex'):
        excluded = int(bigrams[2:])
        bigrams = range(45)
        bigrams.pop(excluded)
    elif bigrams.startswith('in'):
        bigrams = [int(bigrams[2:])]
    random.seed(seed)
    train_loc = Path(train_loc)
    model_loc = Path(model_loc)
    if label_set == 'None':
        label_set = None
    elif label_set == 'conll':
        label_set = str(train_loc)
    if debug:
        redshift.parser.set_debug(True)
    parser = redshift.parser.Parser(model_loc, clean=True,
                                    train_alg=train_alg, add_extra=add_extra_feats,
                                    label_set=label_set, feat_thresh=feat_thresh,
                                    allow_reattach=allow_reattach, allow_reduce=allow_reduce,
                                    beam_width=beam_width, label_beam=not movebeam,
                                    feat_codes=bigrams,
                                    add_clusters=add_clusters)
    
    train_sent_strs = train_loc.open().read().strip().split('\n\n')
    if n_sents != 0:
        print "Using %d sents for training"
        random.shuffle(train_sent_strs)
        train_sent_strs = train_sent_strs[:n_sents]
    train_str = '\n\n'.join(train_sent_strs)
    train = redshift.io_parse.read_conll(train_str)
    #train.connect_sentences(1000)
    if profile:
        print 'profiling'
        cProfile.runctx("parser.train(train, n_iter=n_iter)", globals(),
                        locals(), "Profile.prof")
        s = pstats.Stats("Profile.prof")
        s.strip_dirs().sort_stats("time").print_stats()
    else:
        parser.train(train, n_iter=n_iter)
    parser.save()


if __name__ == "__main__":
    plac.call(main)
