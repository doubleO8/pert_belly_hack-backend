# -*- coding: utf-8 -*-

##############################################################################
#                        2011 E2OpenPlugins                                  #
#                                                                            #
#  This file is open source software; you can redistribute it and/or modify  #
#     it under the terms of the GNU General Public License version 2 as      #
#               published by the Free Software Foundation.                   #
#                                                                            #
##############################################################################
import os
import logging

from enigma import eServiceReference, iServiceInformation, eServiceCenter
from ServiceReference import ServiceReference
from Tools.FuzzyDate import FuzzyTime
from Components.config import config
from Components.MovieList import MovieList
from Screens import MovieSelection
from ..i18n import _

from model_utilities import mangle_epg_text

MOVIETAGFILE = "/etc/enigma2/movietags"
TRASHDIRNAME = "movie_trash"

#: servicereference prefix for movie itmes
MOVIE_LIST_SREF_ROOT = '2:0:1:0:0:0:0:0:0:0:'

#: fallback value for 'movie list root'
MOVIE_LIST_ROOT_FALLBACK = '/media'

MLOG = logging.getLogger("movies")


def getPosition(cutfile, movie_len):
    """
    Retrieve 'last watched' position.

    .. deprecated:: 0.86

    Args:
        cutfile (basestring): movie's cutfile path
        movie_len(int): movie length in minutes
    Returns:
        dict: movie items
    """
    cut_list = []
    if movie_len is not None and os.path.isfile(cutfile):
        try:
            import struct
            with open(cutfile) as f:
                data = f.read()
            while len(data) > 0:
                packedCue = data[:12]
                data = data[12:]
                cue = struct.unpack('>QI', packedCue)
                cut_list.append(cue)
        except Exception:
            return 0
    else:
        return 0
    last_end_point = None
    if len(cut_list):
        for (pts, what) in cut_list:
            if what == 3:
                last_end_point = pts / 90000  # in seconds
    else:
        return 0
    try:
        movie_len = int(movie_len)
    except ValueError:
        return 0
    if movie_len > 0 and last_end_point is not None:
        play_progress = (last_end_point * 100) / movie_len
        if play_progress > 100:
            play_progress = 100
    else:
        play_progress = 0
    return play_progress


def getMovieList(rargs=None, locations=None):
    """
    Generate a `dict` containing movie items information.

    .. deprecated:: 0.86

    Args:
        rargs (dict): request object's args
        locations(list): paths where recordings might be stored
    Returns:
        dict: movie items
    """
    movieliste = []
    tag = None
    directory = None
    fields = None
    bookmarklist = []

    if rargs and "tag" in rargs.keys():
        tag = rargs["tag"][0]

    if rargs and "dirname" in rargs.keys():
        directory = rargs["dirname"][0]

    if rargs and "fields" in rargs.keys():
        fields = rargs["fields"][0]

    if directory is None:
        directory = MovieSelection.defaultMoviePath()
    else:
        try:
            directory.decode('utf-8')
        except UnicodeDecodeError:
            try:
                directory = directory.decode("cp1252").encode("utf-8")
            except UnicodeDecodeError:
                directory = directory.decode("iso-8859-1").encode("utf-8")

    if not directory:
        directory = MOVIE_LIST_ROOT_FALLBACK

    if directory[-1] != "/":
        directory += "/"

    if not os.path.isdir(directory):
        return {
            "movies": [],
            "locations": [],
            "bookmarks": [],
            "directory": [],
        }

    root = eServiceReference(MOVIE_LIST_SREF_ROOT + directory)

    for item in sorted(os.listdir(directory)):
        abs_p = os.path.join(directory, item)
        if os.path.isdir(abs_p):
            bookmarklist.append(item)

    folders = [root]
    if rargs and "recursive" in rargs.keys():
        for f in bookmarklist:
            if f[-1] != "/":
                f += "/"
            ff = eServiceReference(MOVIE_LIST_SREF_ROOT + directory + f)
            folders.append(ff)

    # get all locations
    if locations is not None:
        folders = []

        for f in locations:
            if f[-1] != "/":
                f += "/"
            ff = eServiceReference(MOVIE_LIST_SREF_ROOT + f)
            folders.append(ff)

    for root in folders:
        movielist = MovieList(None)
        movielist.load(root, None)

        if tag is not None:
            movielist.reload(root=root, filter_tags=[tag])

        for (serviceref, info, begin, unknown) in movielist.list:
            if serviceref.flags & eServiceReference.mustDescent:
                continue

            length_minutes = 0
            txtdesc = ""
            filename = '/'.join(serviceref.toString().split("/")[1:])
            filename = '/' + filename
            name, ext = os.path.splitext(filename)

            sourceRef = ServiceReference(
                info.getInfoString(
                    serviceref, iServiceInformation.sServiceref))
            rtime = info.getInfo(
                serviceref, iServiceInformation.sTimeCreate)

            movie = {
                'filename': filename,
                'filename_stripped': filename.split("/")[-1],
                'serviceref': serviceref.toString(),
                'length': "?:??",
                'lastseen': 0,
                'filesize_readable': '',
                'recordingtime': rtime,
                'begintime': 'undefined',
                'eventname': mangle_epg_text(
                    ServiceReference(serviceref).getServiceName()),
                'servicename': mangle_epg_text(sourceRef.getServiceName()),
                'tags': info.getInfoString(serviceref,
                                           iServiceInformation.sTags),
                'fullname': serviceref.toString(),
            }

            if rtime > 0:
                fuzzy_rtime = FuzzyTime(rtime)
                movie['begintime'] = fuzzy_rtime[0] + ", " + fuzzy_rtime[1]

            try:
                length_minutes = info.getLength(serviceref)
            except BaseException:
                pass

            if length_minutes:
                movie['length'] = "%d:%02d" % (
                    length_minutes / 60, length_minutes % 60)
                if fields is None or 'pos' in fields:
                    movie['lastseen'] = getPosition(
                        filename + '.cuts', length_minutes)

            if fields is None or 'desc' in fields:
                txtfile = name + '.txt'
                if ext.lower() != '.ts' and os.path.isfile(txtfile):
                    with open(txtfile, "rb") as handle:
                        txtdesc = ''.join(handle.readlines())

                event = info.getEvent(serviceref)
                extended_description = event and event.getExtendedDescription() or ""  # NOQA
                if extended_description == '' and txtdesc != '':
                    extended_description = txtdesc
                movie['descriptionExtended'] = unicode(
                    extended_description, 'utf_8', errors='ignore').encode(
                    'utf_8', 'ignore')

                desc = info.getInfoString(
                    serviceref, iServiceInformation.sDescription)
                movie['description'] = unicode(
                    desc, 'utf_8', errors='ignore').encode(
                    'utf_8', 'ignore')

            if fields is None or 'size' in fields:
                size = 0
                sz = ''

                try:
                    size = os.stat(filename).st_size
                    if size > 1073741824:
                        sz = "%.2f %s" % ((size / 1073741824.), _("GB"))
                    elif size > 1048576:
                        sz = "%.2f %s" % ((size / 1048576.), _("MB"))
                    elif size > 1024:
                        sz = "%.2f %s" % ((size / 1024.), _("kB"))
                except BaseException:
                    pass

                movie['filesize'] = size
                movie['filesize_readable'] = sz

            movieliste.append(movie)

    if locations is None:
        return {
            "movies": movieliste,
            "bookmarks": bookmarklist,
            "directory": directory
        }

    return {
        "movies": movieliste,
        "locations": locations
    }


def getAllMovies():
    locations = config.movielist.videodirs.value[:] or []
    return getMovieList(locations=locations)


def removeMovie(session, sRef, Force=False):
    service = ServiceReference(sRef)
    result = False
    deleted = False
    message = "service error"

    if service is not None:
        serviceHandler = eServiceCenter.getInstance()
        offline = serviceHandler.offlineOperations(service.ref)
        info = serviceHandler.info(service.ref)
        name = info and info.getName(service.ref) or "this recording"

    if offline is not None:
        if Force is True:
            message = "force delete"
        elif hasattr(config.usage, 'movielist_trashcan'):
            fullpath = service.ref.getPath()
            srcpath = '/'.join(fullpath.split('/')[:-1]) + '/'
            # TODO: check trash
            # TODO: check enable trash default value
            if '.Trash' not in fullpath \
                    and config.usage.movielist_trashcan.value:
                result = False
                message = "trashcan"
                try:
                    import Tools.Trashcan
                    trash = Tools.Trashcan.createTrashFolder(srcpath)
                    MovieSelection.moveServiceFiles(service.ref, trash)
                    result = True
                    message = "The recording '%s' has been successfully moved to trashcan" % name  # NOQA
                except ImportError:
                    message = "trashcan exception"
                    pass
                except Exception as e:
                    MLOG.warning(
                        "Failed to move to .Trash folder: {!r}".format(e))
                    message = "Failed to move to .Trash folder: %s" + str(e)
                deleted = True
        elif hasattr(config.usage, 'movielist_use_trash_dir'):
            fullpath = service.ref.getPath()
            if TRASHDIRNAME not in fullpath \
                    and config.usage.movielist_use_trash_dir.value:
                message = "trashdir"
                try:
                    from Screens.MovieSelection import getTrashDir
                    from Components.FileTransfer import FileTransferJob
                    from Components.Task import job_manager
                    trash_dir = getTrashDir(fullpath)
                    if trash_dir:
                        src_file = str(fullpath)
                        dst_file = trash_dir
                        if dst_file.endswith("/"):
                            dst_file = trash_dir[:-1]
                        text = _("remove")
                        job_manager.AddJob(
                            FileTransferJob(
                                src_file, dst_file, False, False, "%s : %s" %
                                (text, src_file)))
                        # No Result because of async job
                        message = "The recording '%s' has been successfully moved to trashcan" % name  # NOQA
                        result = True
                    else:
                        message = _(
                            "Delete failed, because there is no movie trash "
                            "!\nDisable movie trash in configuration to "
                            "delete this item")
                except ImportError:
                    message = "trashdir exception"
                    pass
                except Exception as e:
                    MLOG.warning(
                        "Failed to move to trashdir: {!r}".format(e))
                    message = "Failed to move to trashdir: %s" + str(e)
                deleted = True
        if not deleted:
            if not offline.deleteFromDisk(0):
                result = True
    else:
        message = "no offline object"

    if result is False:
        return {
            "result": False,
            "message": "Could not delete Movie '%s' / %s" % (name, message)
        }
    else:
        return {
            "result": True,
            "message": "The movie '%s' has been deleted successfully" % name
        }


def _moveMovie(session, sRef, destpath=None, newname=None):
    service = ServiceReference(sRef)
    result = True
    errText = 'unknown Error'

    if destpath is not None and not destpath[-1] == '/':
        destpath = destpath + '/'

    if service is not None:
        serviceHandler = eServiceCenter.getInstance()
        info = serviceHandler.info(service.ref)
        name = info and info.getName(service.ref) or "this recording"
        fullpath = service.ref.getPath()
        srcpath = '/'.join(fullpath.split('/')[:-1]) + '/'
        fullfilename = fullpath.split('/')[-1]
        fileName, fileExt = os.path.splitext(fullfilename)
        if newname is not None:
            newfullpath = srcpath + newname + fileExt

        # TODO: check splitted recording
        # TODO: use FileTransferJob
        def domove():
            exists = os.path.exists
            move = os.rename
            errorlist = []
            if fileExt == '.ts':
                suffixes = ".ts.meta", ".ts.cuts", ".ts.ap", ".ts.sc", \
                           ".eit", ".ts", ".jpg", ".ts_mp.jpg"
            else:
                suffixes = "%s.ts.meta" % fileExt, \
                           "%s.cuts" % fileExt, fileExt, '.jpg', '.eit'

            for suffix in suffixes:
                src = srcpath + fileName + suffix
                if exists(src):
                    try:
                        if newname is not None:
                            # rename title in meta file
                            if suffix == '.ts.meta':
                                # todo error handling
                                lines = []
                                with open(src, "r") as fin:
                                    for line in fin:
                                        lines.append(line)
                                lines[1] = newname + '\n'
                                lines[4] = '\n'
                                foutname = srcpath + newname + suffix
                                with open(foutname, 'w') as fout:
                                    fout.write(''.join(lines))
                                os.remove(src)
                            else:
                                move(src, srcpath + newname + suffix)
                        else:
                            move(src, destpath + fileName + suffix)
                    except IOError as e:
                        errorlist.append("I/O error({0})".format(e))
                        break
                    except OSError as ose:
                        errorlist.append(str(ose))
            return errorlist

        # MOVE
        if newname is None:
            if srcpath == destpath:
                result = False
                errText = 'Equal Source and Destination Path'
            elif not os.path.exists(fullpath):
                result = False
                errText = 'File not exist'
            elif not os.path.exists(destpath):
                result = False
                errText = 'Destination Path not exist'
            elif os.path.exists(destpath + fullfilename):
                errText = 'Destination File exist'
                result = False
        # rename
        else:
            if not os.path.exists(fullpath):
                result = False
                errText = 'File not exist'
            elif os.path.exists(newfullpath):
                result = False
                errText = 'New File exist'

        if result:
            errlist = domove()
            if not errlist:
                result = True
            else:
                errText = errlist[0]
                result = False

    etxt = "rename"
    if newname is None:
        etxt = "move"
    if result is False:
        return {
            "result": False,
            "message": "Could not %s recording '%s' Err: '%s'" % (
                etxt, name, errText)}
    else:
        return {
            "result": True,
            "message": "The recording '%s' has been %sd successfully" % (
                name, etxt)}


def moveMovie(session, sRef, destpath):
    return _moveMovie(session, sRef, destpath=destpath)


def renameMovie(session, sRef, newname):
    return _moveMovie(session, sRef, newname=newname)


def getMovieTags(sRef=None, addtag=None, deltag=None):

    if sRef is not None:
        result = False
        service = ServiceReference(sRef)
        if service is not None:
            fullpath = service.ref.getPath()
            filename = '/'.join(fullpath.split("/")[1:])
            metafilename = '/' + filename + '.meta'
            if os.path.isfile(metafilename):
                lines = []
                with open(metafilename, 'r') as f:
                    lines = f.readlines()
                if lines:
                    meta = ["", "", "", "", "", "", ""]
                    lines = [l.strip() for l in lines]
                    le = len(lines)
                    meta[0:le] = lines[0:le]
                    oldtags = meta[4].split(' ')

                    if addtag is not None:
                        addtag = addtag.replace(' ', '_')
                        try:
                            oldtags.index(addtag)
                        except ValueError:
                            oldtags.append(addtag)
                    if deltag is not None:
                        deltag = deltag.replace(' ', '_')
                    else:
                        deltag = 'dummy'
                    newtags = []
                    for tag in oldtags:
                        if tag != deltag:
                            newtags.append(tag)

                    lines[4] = ' '.join(newtags)

                    with open(metafilename, 'w') as f:
                        f.write('\n'.join(lines))

                    result = True
                    return {
                        "result": result,
                        "tags": newtags
                    }

        return {
            "result": result,
            "resulttext": "Recording not found"
        }

    tags = []
    wr = False
    if os.path.isfile(MOVIETAGFILE):
        for tag in open(MOVIETAGFILE).read().split("\n"):
            if len(tag.strip()) > 0:
                if deltag != tag:
                    tags.append(tag.strip())
                if addtag == tag:
                    addtag = None
        if deltag is not None:
            wr = True
    if addtag is not None:
        tags.append(addtag)
        wr = True
    if wr:
        with open(MOVIETAGFILE, 'w') as f:
            f.write("\n".join(tags))
    return {
        "result": True,
        "tags": tags
    }
