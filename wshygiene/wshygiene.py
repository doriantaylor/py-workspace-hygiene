# -*- coding: utf-8 -*-

from rdflib import ConjunctiveGraph, URIRef, BNode, Literal, RDF, RDFS, OWL, XSD
from rdflib.namespace import Namespace, NamespaceManager
from rdflib.store import Store

import os, urllib, chardet, dateutil.parser

class StorageProxy:
    """Encapsulates data storage."""

    # we want a static NS
    NS = {
        'owl':  'http://www.w3.org/2002/07/owl#',
        'dct':  'http://purl.org/dc/terms/',
        'skos': 'http://www.w3.org/2004/02/skos/core#',
        'sioc': 'http://rdfs.org/sioc/ns#',
        'qb':   'http://purl.org/linked-data/cube#',
        'prov': 'http://www.w3.org/ns/prov#',
        'pav':  'http://purl.org/pav/',
        'bibo': 'http://purl.org/ontology/bibo/',
        'xsd':  'http://www.w3.org/2001/XMLSchema#',
    }
    NS = dict([(x[0], Namespace(x[1])) for x in NS.iteritems()])

    def __init__(self, obj):
        #assert isinstance(obj, Graph)
        if isinstance(obj, str):
            print 'str!'
            if not os.path.isdir(obj): os.makedirs(obj, 0o700)

            self.graph = ConjunctiveGraph('Sleepycat')
            self.graph.open(obj, create = True)
        elif isinstance(obj, Store):
            self.graph = ConjunctiveGraph(obj)
        elif isinstance(obj, Graph):
            self.graph = obj
        else:
            raise 'FAIL'

        nsm = self.graph.namespace_manager
        for k, v in self.NS.iteritems(): nsm.bind(k, v)

        #print [x for x in nsm.namespaces()]

    def add_dir(self, path, mtime=None):
        print "DIR %s" % path

        slug = self.__slug_for(path)

        path = self.__file_uri(path)
        stmts = [(path, RDF.type, self.NS['prov']['Entity']),
                 (path, RDF.type, self.NS['sioc']['Container']),
                 (path, self.NS['dct']['identifier'], slug)]

        if mtime is not None:
            mtime = self.__datetime_literal(mtime)
            stmts.append((path, self.NS['dct']['modified'], mtime))

        for stmt in stmts: self.graph.add(stmt)

    def __file_path(self, uri):
        # early bailout
        if isinstance(uri, str) or isinstance(uri, unicode): return uri

        # otherwise proceed
        assert isinstance(uri, URIRef)
        parsed = urlparse.urlparse(uri)
        
        assert parsed.scheme.lower() == 'file'
        path = urllib.unquote(parsed.path)

    def __slug_for(self, path):
        path = self.__file_path(path)
        bn   = os.path.basename(path)
        if filter(lambda x: ord(x) > 128, bn) != '':
            det = chardet.detect(bn)
            bn  = bn.decode(det['encoding'])

        return Literal(bn, datatype=XSD.string)

    def add_symlink(self, source, target, mtime=None):
        print "LINK %s %s" % (source, target)

        # get this before inputs are coerced
        slug   = self.__slug_for(source)
        # coerce inputs
        source = self.__file_uri(source)
        target = self.__file_uri(target)

        # stmts = [(source, RDF.type, self.NS['prov']['Entity']),
        #          (source, self.NS

        # slug = 

        pass

    def add_symlink_stack(self, stack, mtimes={}):
        assert isinstance(mtimes, dict)

        # this is no symlink
        if len(stack) < 2: return

        # now follow the whole train
        for i in xrange(len(stack) - 1):
            source = self.__file_uri(stack[i])
            target = self.__file_uri(stack[i+1])

            slug = Literal(os.path.basename(stack[i]), datatype=XSD.string)

            # add the symlink data
            self.graph.add((source, RDF.type, self.NS['prov']['Entity']))
            self.graph.add((source, self.NS['dct']['identifier'], slug))
            self.graph.add((source, OWL.sameAs, target))

            # add the mtime
            if mtimes.has_key(source) and mtimes[source] is not None:
                lmt = self.__datetime_literal(mtimes[source])
                self.graph.add((source, self.NS['dct']['modified'], lmt))

    def add_file(self, path, size=None, mtime=None, mimetype=None, digest=None):
        dirname, basename = os.path.split(path)

        s = self.__file_uri(path)

        # prevent a crash from non-ascii filenames 
        if filter(lambda x: ord(x) > 128, basename) != '':
            det = chardet.detect(basename)
            basename = basename.decode(det['encoding'])

        slug = Literal(basename, datatype=XSD.string)

        stmts = [(s, RDF.type, self.NS['prov']['Entity']),
                 (s, RDF.type, self.NS['sioc']['Item']),
                 (s, self.NS['dct']['identifier'], slug)]
        if mtime is not None:
            lmt = self.__datetime_literal(mtime)
            stmts.append((s, self.NS['dct']['modified'], lmt))

        if digest is not None:
            blob = URIRef(digest)
            if mimetype is None: mimetype = 'application/octet-stream'
            ltyp = Literal(mimetype, datatype=XSD.string)
            lsz  = Literal(size, datatype=XSD.integer)
            stmts += [(s, self.NS['pav']['hasCurrentVersion'], blob),
                      (blob, RDF.type, self.NS['prov']['Entity']),
                      (blob, self.NS['dct']['format'], ltyp),
                      (blob, self.NS['dct']['extent'], lsz)]

        for stmt in stmts: self.graph.add(stmt)

        print "FILE %s %d %s %s %s" % (path, size, lmt.value, mimetype, digest)

    def __file_uri(self, path):
        if isinstance(path, URIRef): return path
        return URIRef('file://' + urllib.quote(path))

    # is this what higher-order code looks like?
    def __generate_attach(predicate):
        def f(self, parent, child):
            if not os.path.isabs(child): child = os.path.join(parent, child)
            s = self.__file_uri(parent)
            o = self.__file_uri(child)
            #print repr((s, predicate, o))
            self.graph.add((s, predicate, o))
        return f

    attach_dir  = __generate_attach(NS['sioc']['parent_of'])
    attach_file = __generate_attach(NS['sioc']['container_of'])

    # more higher-order code!
    def __generate_detach(predicate):
        def f(self, parent, children):
            subject = self.__file_uri(parent)

            # retrieve from database
            has = set([x for x in self.graph.objects(subject, predicate)])

            # generate a set of new targets
            new = set()
            for child in children:
                if not os.path.isabs(child):
                    child = os.path.join(parent, child)
                new.add(self.__file_uri(child))

            # now prune the set difference
            for obj in has - new:
                self.graph.remove((subject, predicate, obj))

    detach_dirs  = __generate_detach(NS['sioc']['parent_of'])
    detach_files = __generate_detach(NS['sioc']['container_of'])

    def __datetime_literal(self, dt):
        if not isinstance(dt, datetime):
            dt = datetime.utcfromtimestamp(dt)
        return Literal(dt.isoformat() + 'Z', datatype=XSD.dateTime)

    def __mtime_triple(self, subject, mtime):
        literal = self.__datetime_literal(mtime)

        # aand out
        return subject, Namespace(self.NS['dct'])['modified'], literal

    def get_mtimes(self, path):
        """Get the sorted list of modification times from the given path."""
        # coerce path first
        if not isinstance(path, URIref): path = self.__file_uri(path)
        out = []
        for o in self.graph.objects(path, self.NS['dct']['modified']):
            if o.datatype != XSD.dateTime: continue
            out.append(dateutil.parser.parse(o.value))

        return sorted(out)

    def get_mtime(self, path):
        """Just get the latest modification time from the given path."""
        out = self.get_mtimes(path)

        if len(out) == 0:
            return None
        else:
            return out[-1]

    # we don't actually need to sync
    # def sync(self):
    #     self.graph.store.sync()

import os, stat, hashlib, base64
from datetime import datetime
from xdg import Mime

# multiprocessing stuff
from multiprocessing import Process, Pipe
from time import sleep

class Scanner:
    """Encapsulates the scanning process."""

    # don't do subversion for now
    IGNORE = set(['.wshygiene', '.svn', 'CVS', '/mnt', '/etc', '/usr'])

    # XXX maybe do these as plugins?
    def __do_git (self, path):
        from git import Repo
        print "GIT " + path
        #pass

    def __do_hg (self, path):
        from mercurial import hg, ui, scmutil, commands
        print "HG " + path
        #pass

    # dispatch table for version control
    VCS = {
        '.git': __do_git,
        '.hg': __do_hg,
    }

    # content-scanning block size (should we make it configurable?)
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

    def __scan_file_prelim(self, dirname, basename=None):
        # normalize path
        fullpath = dirname
        if basename is not None: fullpath = os.path.join(dirname, basename)

        if not os.path.exists(fullpath): return

        st = os.stat(fullpath)
        if not os.path.isfile(fullpath): return

        return fullpath, st.st_size, st.st_mtime # datetime.utcfromtimestamp(st.st_mtime)

    def __scan_fs_entity(self, dirname, basename=None):
        # normalize path
        fullpath = dirname
        if basename is not None: fullpath = os.path.join(dirname, basename)

        # name parent mtime mimetype size

        if not os.path.exists(fullpath): return

        st = os.stat(fullpath)

        if os.path.islink(fullpath):
            target = os.readlink(fullpath)
            # add symlink
            self.store.add_symlink(fullpath, target)
        elif os.path.isdir(fullpath):
            # add directory
            self.store.add_dir(fullpath)
        else:
            size     = st.st_size
            mtime    = datetime.utcfromtimestamp(st.st_mtime)
            mimetype = 'application/octet-stream'
            digest   = None

            # only scan/add the file if the stored mtime is 
            #oldmt = self.store.get_mtime(fullpath)
            #print 'old: %s new %s' % (oldmt, mtime)
            #if oldmt is None or mtime > oldmt:
            if os.access(fullpath, os.R_OK):
                mimetype = Mime.get_type2(fullpath)
                digest   = self.__ni_uri(fullpath)
            
            self.store.add_file(fullpath, size, mtime, mimetype, digest)

    def __deref_symlinks(self, path, seen=set()):
        """recursively construct a chain of symlinks until we hit a real file
        or a cycle"""

        # what it says above ^^^
        if path in seen or not os.path.islink(path): return [path]

        # don't forget our insurance
        seen.add(path)

        # now check 
        dirname = os.path.dirname(path)
        target  = os.path.normpath(os.path.join(dirname, os.readlink(path)))

        # shortcut to dangling symlink
        if not os.path.lexists(target): return [path, target]

        # clean any symlinks out up to the basename
        tdir, tbase = os.path.split(target)
        tdir   = os.path.realpath(tdir)
        target = os.path.join(tdir, tbase)

        # normal recursion
        return [path] + self.__deref_symlinks(target, seen)

    def __symlink_mtimes(self, stack):
        out = {}
        for path in stack:
            try:
                st = os.lstat(path)
                out[path] = datetime.utcfromtimestamp(st.st_mtime)
            except OSError:
                out[path] = None
        return out

    def __path_contains(self, path, contains):
        """Check to see if a path is contained in a set."""
        if os.path.isabs(path):
            p = path
            while p != os.path.dirname(p):
                if p in contains: return True
                p = os.path.dirname(p)
            else:
                return False
        else:
            return p in contains

    # def __attach_dir(self, parent, child):
    #     #s = URIRef(
    #     #self.store.graph.
    #     pass

    # def __attach_file(self, parent, child):
    #     pass

    def __content_scan(self, path):
        mimetype = Mime.get_type2(path)
        digest   = self.__ni_uri(path)

        return str(mimetype), digest

    def __content_scan_loop(self, conn):
        while True:
            if conn.poll():
                # get the message
                msg = conn.recv()

                # not being a tuple is the signal to shut down
                if not isinstance(msg, tuple):
                    # send back an ack and close the connection
                    conn.send(None)
                    conn.close()
                    return

                # tuple is path, size, mtime (or at least it better be)
                path = msg[0]
                try:
                    mimetype, digest  = self.__content_scan(msg[0])
                    #print msg + (mimetype, digest)
                    conn.send(msg + (mimetype, digest))
                except IOError as e:
                    # send the error down the channel
                    conn.send(e)
                except Exception as e:
                    # everything else is bunk
                    print e
                    break
            else:
                sleep(0.1)

    def scan(self, roots=[], ignore=None):
        """Scan a list of roots.

        This is what this bastard looks like scanning half a million
        files on an AFS share:

        real    788m10.824s
        user    214m31.540s
        sys     29m17.144s

        slow right?

        """

        # make sure this is a list as we will be modifying it
        roots = list(roots)

        # our insurance from infinite cycles
        seen = set()

        # subprocess fun times
        pconn, cconn = Pipe()
        cscan = Process(target=self.__content_scan_loop, args=(cconn,))
        cscan.start()

        for root in roots:
            if root in self.IGNORE or os.path.basename(root) in self.IGNORE:
                continue

            for current, dirs, files in os.walk(root):
                # insurance
                if current in seen: continue
                seen.add(current)

                # now add the current dir
                cstat = os.stat(current)
                self.store.add_dir(current, cstat.st_mtime)

                #print current

                # subdirectories will be easer to test as a set
                ds = set(dirs)

                # remove intersection of dirs and ignored
                for skip in self.IGNORE & ds: dirs.remove(skip)

                # process/remove intersection of version control
                for vc in set(self.VCS.keys()) & ds:
                    self.VCS[vc](self, current)
                    dirs.remove(vc)

                # sort these things
                dirs.sort()
                files.sort()

                # now deal with symlinks that are dirs
                for dn in dirs:
                    subdir = os.path.join(current, dn)
                    links  = self.__deref_symlinks(subdir)

                    if len(links) > 1:
                        print 'SYMLINK DIR %s' % repr(links)

                        # add symlinks
                        mtimes = self.__symlink_mtimes(links)
                        self.store.add_symlink_stack(links, mtimes)

                        # follow the (last) symlink
                        if not self.__path_contains(links[-1], self.IGNORE):
                            roots.append(links[-1])

                    self.store.attach_dir(current, dn)

                    # not sure if we have to do this hashtag cargocult
                    if not os.access(subdir, os.R_OK): dirs.remove(dn)

                # scan the dir
                #self.__scan_fs_entity(current)

                # scan the files
                #for fn in files: self.__scan_fs_entity(current, fn)
                fs = set(files)
                for fn in files:
                    absfile = os.path.join(current, fn)

                    # deal with symlinks
                    links   = self.__deref_symlinks(absfile)
                    if len(links) > 1:
                        print 'SYMLINK FILE %s' % repr(links)
                        mtimes = self.__symlink_mtimes(links)
                        self.store.add_symlink_stack(links, mtimes)

                    self.store.attach_file(current, fn)

                    if os.path.isfile(links[-1]):
                        # attach the first one
                        # scan the last one
                        #self.__scan_fs_entity(links[-1])
                        msg = self.__scan_file_prelim(links[-1])
                        if msg is not None:
                            #print "SENDING MESSAGE", msg
                            pconn.send(msg)

                # retrieve stuff but only for so long
                while pconn.poll():
                    try:
                        msg = pconn.recv()
                        if msg is None: break
                        self.store.add_file(*msg)
                        #print msg
                    except EOFError:
                        break

            # sync after every root?
            # actually it syncs by itself
            # self.store.sync()
                    

        #print len(self.store.graph)

        # clean up the stragglers
        print "GOT HERE"
        pconn.send(None)
        while True:
            if pconn.poll():
                try:
                    msg = pconn.recv()
                    #print msg
                    if msg is None: break
                    self.store.add_file(*msg)
                    
                except EOFError:
                    break
            else:
                sleep(0.1)

        # and finally shut down the subprocess
        cscan.join()

from lxml import etree

class Renderer:
    """Encapsulates the business of rendering data."""
    def __init__(self, store):
        pass
