# -*- coding: utf-8 -*-

##############################################################################
#                        2011 E2OpenPlugins                                  #
#                                                                            #
#  This file is open source software; you can redistribute it and/or modify  #
#     it under the terms of the GNU General Public License version 2 as      #
#               published by the Free Software Foundation.                   #
#                                                                            #
##############################################################################
import logging
from enigma import eConsoleAppContainer
from twisted.web import resource, server

GLOG = logging.getLogger("grab")
GRAB_PATH = '/usr/bin/grab'


class GrabRequest(object):
    def __init__(self, request, session):
        self.request = request

        graboptions = [GRAB_PATH, '-q', '-s']

        if "format" in request.args:
            fileformat = request.args["format"][0]
        else:
            fileformat = "jpg"
        if fileformat == "jpg":
            graboptions.append("-j")
            graboptions.append("95")
        elif fileformat == "png":
            graboptions.append("-p")
        elif fileformat != "bmp":
            fileformat = "bmp"

        if "r" in request.args:
            size = request.args["r"][0]
            graboptions.append("-r")
            graboptions.append("%d" % int(size))

        if "mode" in request.args:
            mode = request.args["mode"][0]
            if mode == "osd":
                graboptions.append("-o")
            elif mode == "video":
                graboptions.append("-v")
        self.container = eConsoleAppContainer()
        self.container.appClosed.append(self.grabFinished)
        self.container.stdoutAvail.append(request.write)
        self.container.setBufferSize(32768)
        self.container.execute(GRAB_PATH, *graboptions)
        try:
            ref = session.nav.getCurrentlyPlayingServiceReference().toString()
            sref = '_'.join(ref.split(':', 10)[:10])
        except BaseException:
            sref = 'screenshot'
        request.notifyFinish().addErrback(self.requestAborted)
        request.setHeader(
            'Content-Disposition', 'inline; filename=%s.%s;' %
            (sref, fileformat))
        request.setHeader(
            'Content-Type',
            'image/%s' %
            fileformat.replace(
                "jpg",
                "jpeg"))
        request.setHeader('Expires', 'Sat, 26 Jul 1997 05:00:00 GMT')
        request.setHeader(
            'Cache-Control',
            'no-store, no-cache, must-revalidate, post-check=0, pre-check=0')
        request.setHeader('Pragma', 'no-cache')

    def requestAborted(self, err):
        # Called when client disconnected early, abort the process and
        # don't call request.finish()
        del self.container.appClosed[:]
        self.container.kill()
        del self.request
        del self.container

    def grabFinished(self, retval=None):
        try:
            self.request.finish()
        except RuntimeError as error:
            GLOG.warning("grabFinished error: {!r}".format(error))
        # Break the chain of ownership
        del self.request


class grabScreenshot(resource.Resource):
    def __init__(self, session, path=None):
        resource.Resource.__init__(self)
        self.session = session

    def render(self, request):
        # Add a reference to the grabber to the Request object. This keeps
        # the object alive at least until the request finishes
        request.grab_in_progress = GrabRequest(request, self.session)
        return server.NOT_DONE_YET
