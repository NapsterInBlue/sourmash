"""
Utility functions for lowest-common-ancestor analysis tools.
"""
from __future__ import print_function
import sys
import json
import gzip
from collections import OrderedDict, namedtuple
try:                                      # py2/py3 compat
    from itertools import zip_longest
except ImportError:
    from itertools import izip_longest as zip_longest
import pprint

import sourmash_lib
from sourmash_lib.logging import notify

# type to store an element in a taxonomic lineage
LineagePair = namedtuple('LineagePair', ['rank', 'name'])


# ordered list of taxonomic ranks
def taxlist(include_strain=False):
    for k in ['superkingdom', 'phylum', 'class', 'order', 'family', 'genus',
              'species']:
        yield k
    if include_strain:
        yield 'strain'


# produce an ordered list of tax names from lineage
def zip_lineage(lineage, include_strain=False):
    """@CTB: document and test."""
    row = []
    empty = LineagePair(None, '')
    for taxrank, lineage_tup in zip_longest(taxlist(), lineage,
                                            fillvalue=empty):
        if lineage_tup != empty:
            if lineage_tup.rank != taxrank:
                raise ValueError('incomplete lineage at {}!? {}'.format(lineage_tup.rank, lineage))

        row.append(lineage_tup.name)
    return row


# filter function toreplace blank/na/null with 'unassigned'
filter_null = lambda x: 'unassigned' if x.strip() in \
  ('[Blank]', 'na', 'null', '') else x
null_names = set(['[Blank]', 'na', 'null'])


_print_debug = False
def set_debug(state):
    global _print_debug
    _print_debug = True

def debug(*args):
    if _print_debug:
        pprint.pprint(args)


def build_tree(assignments, initial=None):
    """
    Builds a tree of dictionaries from lists of LineagePair objects
    in 'assignments'.  This tree can then be used to find lowest common
    ancestor agreements/confusion.
    """
    if initial is None:
        tree = {}
    else:
        tree = initial

    for assignment in assignments:
        node = tree

        for lineage_tup in assignment:
            if lineage_tup.name:
                child = node.get(lineage_tup, {})
                node[lineage_tup] = child

                # shift -> down in tree
                node = child

    return tree


def find_lca(tree):
    """
    Given a tree produced by 'find_tree', find the first node with multiple
    children, OR the only leaf in the tree.  Return (lineage_tup, reason),
    where 'reason' is the number of children of the returned node, i.e.e
    0 if it's a leaf and > 1 if it's an internal node.
    """

    node = tree
    lineage = []
    while 1:
        if len(node) == 1:                # descend to only child; track path
            lineage_tup = next(iter(node.keys()))
            lineage.append(lineage_tup)
            node = node[lineage_tup]
        elif len(node) == 0:              # at leaf; end
            return tuple(lineage), 0
        else:                             # len(node) > 1 => confusion!!
            return tuple(lineage), len(node)


class LCA_Database(object):
    """
    Wrapper class for taxonomic database.

    obj.lineage_dict: key 'lineage_id' => lineage tuple [(name, rank), ...]
    obj.hashval_to_lineage_id: key 'hashval' => 'lineage_id'
    obj.ksize: k-mer size
    obj.scaled: scaled value
    obj.signatures_to_lineage: key 'md5sum' => 'lineage_id'
    """
    def __init__(self):
        self.lineage_dict = None
        self.hashval_to_lineage_id = None
        self.ksize = None
        self.scaled = None
        self.signatures_to_lineage = None

    def load(self, db_name):
        "Load from a JSON file."
        xopen = open
        if db_name.endswith('.gz'):
            xopen = gzip.open

        with xopen(db_name, 'rt') as fp:
            load_d = json.load(fp)
            version = load_d['version']
            assert version == '1.0'

            type = load_d['type']
            assert type == 'sourmash_lca'

            ksize = int(load_d['ksize'])
            scaled = int(load_d['scaled'])

            # convert lineage_dict to proper lineages (tuples of LineagePairs)
            lineage_dict_2 = load_d['lineages']
            lineage_dict = {}
            for k, v in lineage_dict_2.items():
                vv = []
                for rank in taxlist():
                    name = v.get(rank, '')
                    vv.append(LineagePair(rank, name))

                lineage_dict[int(k)] = tuple(vv)

            # convert hashval -> lineage index keys to integers (looks like
            # JSON doesn't have a 64 bit type so stores them as strings)
            hashval_to_lineage_id_2 = load_d['hashval_assignments']
            hashval_to_lineage_id = {}
            for k, v in hashval_to_lineage_id_2.items():
                hashval_to_lineage_id[int(k)] = v

            signatures_to_lineage = load_d['signatures_to_lineage']

        self.lineage_dict = lineage_dict
        self.hashval_to_lineage_id = hashval_to_lineage_id
        self.ksize = ksize
        self.scaled = scaled
        self.signatures_to_lineage = signatures_to_lineage

    def save(self, db_name):
        "Save to a JSON file."
        xopen = open
        if db_name.endswith('.gz'):
            xopen = gzip.open

        with xopen(db_name, 'wt') as fp:
            # use an OrderedDict to preserve output order
            save_d = OrderedDict()
            save_d['version'] = '1.0'
            save_d['type'] = 'sourmash_lca'
            save_d['license'] = 'CC0'
            save_d['ksize'] = self.ksize
            save_d['scaled'] = self.scaled

            # convert lineage internals from tuples to dictionaries
            d = OrderedDict()
            for k, v in self.lineage_dict.items():
                d[k] = dict([ (vv.rank, vv.name) for vv in v ])
            save_d['lineages'] = d

            # convert values from sets to lists, so that JSON knows how to save
            save_d['hashval_assignments'] = \
               dict((k, list(v)) for (k, v) in self.hashval_to_lineage_id.items())
            save_d['signatures_to_lineage'] = self.signatures_to_lineage
            json.dump(save_d, fp)

    def downsample_scaled(self, scaled):
        """
        Downsample to the provided scaled value, i.e. eliminate all hashes
        that don't fall in the required range.
        """
        if scaled == self.scaled:
            return
        elif scaled < self.scaled:
            raise ValueError("cannot decrease scaled from {} to {}".format(self.scaled, scaled))

        max_hash = sourmash_lib.get_max_hash_for_scaled(scaled)
        new_hashvals = {}
        for k, v in self.hashval_to_lineage_id.items():
            if k < max_hash:
                new_hashvals[k] = v
        self.hashval_to_lineage_id = new_hashvals
        self.scaled = scaled

        # CTB: could also clean up lineage_dict and signatures_to_lineage
        # but space savings should be negligible.

    def get_lineage_assignments(self, hashval):
        """
        Get a list of lineages for this hashval.
        """
        x = []

        lineage_id_list = self.hashval_to_lineage_id.get(hashval, [])
        for lineage_id in lineage_id_list:
            lineage = self.lineage_dict[lineage_id]
            x.append(lineage)

        return x


def load_databases(filenames):
    ksize_vals = set()
    scaled_vals = set()
    dblist = []

    # load all the databases
    for db_name in filenames:
        notify(u'\r\033[K', end=u'', file=sys.stderr)
        notify('... loading database {}'.format(db_name), end='\r',
              file=sys.stderr)

        lca_db = LCA_Database()
        lca_db.load(db_name)

        ksize_vals.add(lca_db.ksize)
        if len(ksize_vals) > 1:
            raise Exception('multiple ksizes, quitting')
        scaled_vals.add(lca_db.scaled)
        if len(scaled_vals) > 1:
            raise Exception('multiple scaled vals, quitting')

        dblist.append(lca_db)

    notify(u'\r\033[K', end=u'')
    notify('loaded {} databases.', len(dblist))

    ksize = ksize_vals.pop()
    scaled = scaled_vals.pop()

    return dblist, ksize, scaled