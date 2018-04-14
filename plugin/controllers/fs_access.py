#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import pprint

from twisted.web import static, resource, http

from Components.config import config as comp_config
from utilities import require_valid_file_parameter, build_url
from utilities import mangle_host_header_port
from defaults import FILE_ACCESS_WHITELIST
from recording import RECORDINGS_ROOT_PATH


class RestrictedFilesystemAccessController(resource.Resource):
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

    def __init__(self, *args, **kwargs):
        resource.Resource.__init__(self)
        self.log = logging.getLogger(__name__)

    def render_GET(self, request):
        """
        Request handler for the `file` endpoint.

        Args:
            request (twisted.web.server.Request): HTTP request object
        Returns:
            HTTP response with headers

        .. http:get:: /file

            :query string action: one of `download` [default], `stream`
            :query string name: m3u entry label
            :query string be-lyle: bouquet reference

        """
        action = "download"
        if "action" in request.args:
            action = request.args["action"][0]

        self.log.warning("DEPRECATED file.py access:")
        self.log.warning(pprint.pformat(request.args))

        if "file" in request.args:
            try:
                filename = require_valid_file_parameter(request, "file")
            except ValueError as verr:
                request.setResponseCode(http.BAD_REQUEST)
                self.log.error(verr)
                return ''
            except IOError as ioerr:
                self.log.error(ioerr)
                request.setResponseCode(http.NOT_FOUND)
                return ''

            if not filename.startswith(RECORDINGS_ROOT_PATH):
                if filename not in FILE_ACCESS_WHITELIST:
                    self.log.error("{!r} NOT IN WHITELIST {!r}".format(
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
                self.log.warning("Unsupported action: {!r}".format(action))
                request.setResponseCode(http.NOT_IMPLEMENTED)
                return ""

        if "dir" in request.args:
            self.log.warning("No 'dir' support.")
            request.setResponseCode(http.NOT_IMPLEMENTED)
            return ""
