#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import logging

from enigma import eServiceCenter, eServiceReference
from Screens.ChannelSelection import service_types_tv, service_types_radio

from utilities import parse_servicereference, mangle_snp, SERVICE_KIND_COMMENT
from utilities import parse_simple_index, mangle_service_type_arg

ROOT_FMT = '{:s} FROM BOUQUET "{:s}" ORDER BY bouquet'
LIST_FMT = "SN"
BLACKLISTED_SERVICE_KIND = (SERVICE_KIND_COMMENT,)

SNP_INDEX = "/etc/enigma2/snp.index"


class ServiceController(object):
    """
    Available services listing and conversions.
    """

    def __init__(self, *args, **kwargs):
        self.log = logging.getLogger(__name__)
        self.esc_instance = eServiceCenter.getInstance()
        self.raise_exceptions = kwargs.get("may_raise", False)
        self.snp_index = None

        if os.path.isfile(SNP_INDEX):
            self.snp_index = parse_simple_index(SNP_INDEX)

    def _mangle_snp(self, service_name):
        snp_name = mangle_snp(service_name)

        if not snp_name:
            return '--------'

        if self.snp_index is not None:
            try:
                return self.snp_index[snp_name]
            except KeyError:
                pass

        return snp_name

    def get_services_set(self, service_types=None, **kwargs):
        """
        Retrieve a set of service names and references available on device.

        Args:
            service_types: Service types to list all(None), tv or radio

        """
        services_set = set()
        bouquet_index = [
            (service_types_tv, 'bouquets.tv'),
            (service_types_radio, 'bouquets.radio'),
        ]
        service_type_whitelist = set()

        if service_types is None:
            pass
        elif isinstance(service_types, (list, set, tuple)):
            for item in service_types:
                service_type_whitelist |= mangle_service_type_arg(item)
        else:
            service_type_whitelist |= mangle_service_type_arg(service_types)

        for service_type_selector, bouquet in bouquet_index:
            root = eServiceReference(
                ROOT_FMT.format(service_type_selector, bouquet))
            slist = self.esc_instance.list(root)

            # list
            for (b_service_reference, b_service_name) in slist.getContent(
                    LIST_FMT, True):
                self.log.debug("BOUQUET : {!r}".format(b_service_name))
                # bouquet root
                b_root = eServiceReference(b_service_reference)
                self.log.debug(b_root)
                # bouquet items list iterator
                b_list = self.esc_instance.list(b_root)
                # bouquet items list
                b_items = b_list.getContent(LIST_FMT, True)
                for (service_reference, service_name) in b_items:
                    x = service_reference, service_name.decode("utf-8")
                    psref = parse_servicereference(service_reference,
                                                   extended=True)
                    if psref['kind'] in BLACKLISTED_SERVICE_KIND:
                        continue
                    if service_type_whitelist:
                        if psref['service_type'] not in service_type_whitelist:
                            continue
                    services_set.add(x)
                    self.log.debug(x)

        for sr, sn in services_set:
            yield sr, sn, self._mangle_snp(sn)
