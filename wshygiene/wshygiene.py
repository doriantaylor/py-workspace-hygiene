# -*- coding: utf-8 -*-

from rdflib import Graph, URIRef, BNode, Literal, Namespace
from rdflib.store import Store

class StorageProxy:
    """Encapsulates data storage."""

    NS = {
        'sioc': 'http://rdfs.org/sioc/ns#',
    }

    def __init__(self, obj):
        #assert isinstance(obj, Graph)
        if isinstance(obj, str):
            print 'str!'
            if not os.path.isdir(obj): os.makedirs(obj, 0o700)

            self.graph = Graph('Sleepycat')
            self.graph.open(obj, create = True)
        elif isinstance(obj, Store):
            self.graph = Graph(obj)
        elif isinstance(obj, Graph):
            self.graph = obj
        else:
            raise 'FAIL'

        nsm = self.graph.namespace_manager
        for k, v in self.NS.iteritems(): nsm.bind(k, Namespace(v))

        print [x for x in nsm.namespaces()]

    def add_dir(self, path):
        # print "DIR %s" % path
        pass

    def add_symlink(self, source, target):
        # print "LINK %s %s" % (source, target)
        pass

    def add_file(self, path, size=None, mtime=None, mimetype=None, digest=None):
        dirname, basename = os.path.split(path)
        # print "FILE %s %d %s %s %s" % (path, size, mtime.isoformat(),
        #                                mimetype, digest)
        pass
        

import os, stat, hashlib, base64
from datetime import datetime
from xdg import Mime

class Scanner:
    """Encapsulates the scanning process."""

    # don't do subversion for now
    IGNORE = set(['.wshygiene', '.svn'])

    # XXX maybe do these as plugins?
    def __do_git (self, path):
        from git import Repo
        print "GIT " + path
        #pass

    def __do_hg (self, path):
        from mercurial import hg, ui, scmutil, commands
        print "HG " + path
        #pass

    VCS = {
        '.git': __do_git,
        '.hg': __do_hg,
    }

    BLOCKSIZE = 65536

    def __init__(self, store):
        self.store = store

    def __ni_uri(self, path):
        sha = hashlib.sha256()
        with open(path, 'rb') as fh:
            buf = fh.read(self.BLOCKSIZE)
            while len(buf) > 0:
                sha.update(buf)
                buf = fh.read(self.BLOCKSIZE)
        return 'ni:///sha-256;' + base64.urlsafe_b64encode(
            sha.digest()).strip('=')
        

    def __scan_fs_entity(self, dirname, basename):
        # name parent mtime mimetype size
        fullpath = os.path.join(dirname, basename)

        if not os.path.exists(fullpath):
            return

        st = os.stat(fullpath)

        if os.path.isdir(fullpath):
            # add directory
            self.store.add_dir(fullpath)
        elif os.path.islink(fullpath):
            target = os.readlink(fullpath)
            # add symlink
            self.store.add_symlink(fullpath, target)
        else:
            size     = st.st_size
            mtime    = datetime.utcfromtimestamp(st.st_mtime)
            mimetype = Mime.get_type2(fullpath)
            digest   = self.__ni_uri(fullpath)
            #digest = None
            
            self.store.add_file(fullpath, size, mtime, mimetype, digest)

    def scan(self, roots=[], ignore=None):
        """Scan a list of roots."""

        def f (arg, dirname, children):
            # prune out child nodes
            for i in xrange(len(children)):
                if len(children) <= i: break

                # give us the full path
                fp = os.path.join(dirname, children[i])

                queue = []
                if children[i] in self.IGNORE:
                    del children[i]
                elif children[i] in self.VCS and os.path.isdir(fp):
                    #print dirname
                    self.VCS[children[i]](self, dirname)
                    del children[i]
                else:
                    self.__scan_fs_entity(dirname, children[i])
                

        for root in roots:
            root = os.path.realpath(root)

            if not os.path.exists(root): continue

            os.path.walk(root, f, None)

from lxml import etree

class Renderer:
    """Encapsulates the business of rendering data."""
    def __init__(self, store):
        pass
