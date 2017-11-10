#! /usr/bin/env python
"""
Summarize the taxonomic content of the given signatures, combined.
"""
from __future__ import print_function
import sys
import argparse
import csv
from collections import defaultdict, Counter

import sourmash_lib
from sourmash_lib import sourmash_args
from sourmash_lib.logging import notify, error
from sourmash_lib.lca import lca_utils
from sourmash_lib.lca.lca_utils import debug, set_debug


DEFAULT_THRESHOLD=5


def summarize(hashvals, dblist, threshold):
    """
    Classify 'hashvals' using the given list of databases.

    Insist on at least 'threshold' counts of a given lineage before taking
    it seriously.

    Return (lineage, counts) where 'lineage' is a tuple of LineagePairs.
    """

    # gather assignments from across all the databases
    assignments = defaultdict(set)
    for hashval in hashvals:
        for lca_db in dblist:
            lineages = lca_db.get_lineage_assignments(hashval)
            assignments[hashval].update(lineages)

    # now convert to trees -> do LCA & counts
    counts = Counter()
    for hashval in assignments:

        # for each list of tuple_info [(rank, name), ...] build
        # a tree that lets us discover lowest-common-ancestor.
        tuple_info = assignments[hashval]
        tree = lca_utils.build_tree(tuple_info)

        # now find either a leaf or the first node with multiple
        # children; that's our lowest-common-ancestor node.
        lca, reason = lca_utils.find_lca(tree)
        counts[lca] += 1

    # ok, we now have the LCAs for each hashval, and their number
    # of counts. Now aggregate counts across the tree, going up from
    # the leaves.
    tree = {}

    debug(counts.most_common())

    aggregated_counts = defaultdict(int)
    for lca, count in counts.most_common():
        if count < threshold:
            break

        # climb from the lca to the root.
        while lca:
            aggregated_counts[lca] += count
            lca = lca[:-1]

    debug(aggregated_counts)

    return aggregated_counts


def summarize_main(args):
    """
    main summarization function.
    """
    p = argparse.ArgumentParser()
    p.add_argument('--db', nargs='+', action='append')
    p.add_argument('--query', nargs='+', action='append')
    p.add_argument('--threshold', type=int, default=DEFAULT_THRESHOLD)
    p.add_argument('--traverse-directory', action='store_true',
                        help='load all signatures underneath directories.')
    p.add_argument('-o', '--output', type=argparse.FileType('wt'),
                   help='CSV output')
    p.add_argument('-d', '--debug', action='store_true')
    args = p.parse_args(args)

    if not args.db:
        error('Error! must specify at least one LCA database with --db')
        sys.exit(-1)

    if not args.query:
        error('Error! must specify at least one query signature with --query')
        sys.exit(-1)

    if args.debug:
        set_debug(args.debug)

    # flatten --db and --query
    args.db = [item for sublist in args.db for item in sublist]
    args.query = [item for sublist in args.query for item in sublist]

    # load all the databases
    dblist, ksize, scaled = lca_utils.load_databases(args.db)
    notify('ksize={} scaled={}', ksize, scaled)

    # find all the queries
    notify('finding query signatures...')
    if args.traverse_directory:
        inp_files = list(sourmash_args.traverse_find_sigs(args.query))
    else:
        inp_files = list(args.query)

    # for each query, gather all the hashvals across databases
    total_count = 0
    n = 0
    total_n = len(inp_files)
    hashvals = defaultdict(int)
    for query_filename in inp_files:
        n += 1
        for query_sig in sourmash_lib.load_signatures(query_filename,
                                                      ksize=ksize):
            notify(u'\r\033[K', end=u'')
            notify('... loading {} (file {} of {})', query_sig.name(), n,
                   total_n, end='\r')
            total_count += 1

            mh = query_sig.minhash.downsample_scaled(scaled)
            for hashval in mh.get_mins():
                hashvals[hashval] += 1

    notify(u'\r\033[K', end=u'')
    notify('loaded {} signatures from {} files total.', total_count, n)

    # get the full counted list of lineage counts in this signature
    lineage_counts = summarize(hashvals, dblist, args.threshold)

    # output!
    total = float(len(hashvals))
    for (lineage, count) in lineage_counts.items():
        lineage = ';'.join([ lineage_tup.name for lineage_tup in lineage ])
        p = count / total * 100.
        p = '{:.1f}%'.format(p)

        print('{:5} {:>5}   {}'.format(p, count, lineage))

    # CSV:
    if args.output:
        w = csv.writer(args.output)
        headers = ['count'] + list(lca_utils.taxlist())
        w.writerow(headers)

        for (lineage, count) in lineage_counts.items():
            debug('lineage:', lineage)
            row = [count] + lca_utils.zip_lineage(lineage)
            w.writerow(row)


if __name__ == '__main__':
    sys.exit(summarize_main(sys.argv[1:]))