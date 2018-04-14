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
import pprint

from twisted.web import static, resource, http

from Components.config import config as comp_config
from utilities import require_valid_file_parameter, build_url
from utilities import mangle_host_header_port
from defaults import FILE_ACCESS_WHITELIST
from recording import RECORDINGS_ROOT_PATH

FLOG = logging.getLogger("filecrap")


class FileController(resource.Resource):
    """
    Filesystem Access Controller.

    Provides file downloading and generates `.m3u` playlists on the fly for
    requested files.

    .. note::

        This implementation

            * does *not* provide directory listing support
            * Limits access to files contained in \
              :py:const:`~controllers.recording.RECORDINGS_ROOT_PATH`
            * Limits access to files contained in \
              :py:const:`~controllers.defaults.FILE_ACCESS_WHITELIST`

    """
    def render(self, request):
        action = "download"
        if "action" in request.args:
            action = request.args["action"][0]

        FLOG.warning("DEPRECATED file.py access:")
        FLOG.warning(pprint.pformat(request.args))

        if "file" in request.args:
            try:
                filename = require_valid_file_parameter(request, "file")
            except ValueError as verr:
                request.setResponseCode(http.BAD_REQUEST)
                FLOG.error(verr)
                return ''
            except IOError as ioerr:
                FLOG.error(ioerr)
                request.setResponseCode(http.NOT_FOUND)
                return ''

            if not filename.startswith(RECORDINGS_ROOT_PATH):
                if filename not in FILE_ACCESS_WHITELIST:
                    FLOG.error("{!r} NOT IN WHITELIST {!r}".format(
                        filename, FILE_ACCESS_WHITELIST))
                    request.setResponseCode(http.FORBIDDEN)
                    return ''

            if action == "stream":
                name = "stream"
                m3u_content = [
                    '#EXTM3U',
                    '#EXTVLCOPT--http-reconnect=true',
                ]

                if "name" in request.args:
                    name = request.args["name"][0]
                    m3u_content.append("#EXTINF:-1,%s" % name)

                mangled = mangle_host_header_port(
                    request.getHeader('host'),
                    fallback_port=comp_config.OpenWebif.port.value)
                args = {
                    "action": "download",
                    "file": filename
                }
                source_url = build_url(hostname=mangled['hostname'],
                                       path="file", args=args,
                                       port=mangled["port"])
                m3u_content.append(source_url)
                request.setHeader(
                    "Content-Disposition",
                    'attachment;filename="%s.m3u"' %
                    name)
                request.setHeader("Content-Type", "application/x-mpegurl")
                return "\n".join(m3u_content)
            elif action == "download":
                request.setHeader(
                    "Content-Disposition",
                    "attachment;filename=\"%s\"" % (filename.split('/')[-1]))
                rfile = static.File(
                    filename, defaultType="application/octet-stream")
                return rfile.render(request)
            else:
                FLOG.warning("Unsupported action: {!r}".format(action))
                request.setResponseCode(http.NOT_IMPLEMENTED)
                return ""

        if "dir" in request.args:
            FLOG.warning("No 'dir' support.")
            request.setResponseCode(http.NOT_IMPLEMENTED)
            return ""
