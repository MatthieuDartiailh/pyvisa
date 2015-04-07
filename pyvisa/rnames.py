# -*- coding: utf-8 -*-
"""
    pyvisa.rnames
    ~~~~~~~~~~~~~~~~~

    Parsing and assembling ressource names.

    :copyright: 2014 by PyVISA Authors, see AUTHORS for more details.
    :license: MIT, see LICENSE for more details.
"""

from __future__ import division, unicode_literals, print_function, absolute_import

from pyvisa import constants


class InvalidResourceName(ValueError):
    pass


_INTERFACE_TYPES = {'ASRL': constants.InterfaceType.asrl,
                    'GPIB': constants.InterfaceType.gpib,
                    'PXI': constants.InterfaceType.pxi,
                    'TCPIP': constants.InterfaceType.tcpip,
                    'USB': constants.InterfaceType.usb,
                    'VXI': constants.InterfaceType.vxi}

_RESOURCE_CLASSES = ('INSTR', 'INTFC', 'BACKPLANE', 'MEMACC', 'SOCKET', 'RAW',
                     'SERVANT')


# :type: (str, str) -> (str, *str) -> {}
_SUBPARSER = {}


def register_subparser(interface_type, resource_class):
    """Register a subparser for a given interface type and resource class.

    :type interface_type: str
    :type resource_class: str
    :return: a decorator
    """
    def deco(cls):
        _SUBPARSER[(interface_type, resource_class)] = cls()
        return cls

    return deco


def call_subparser(interface_type_part, resource_class, *parts):
    """Call a subparser based on the interface_type and resource_class.

    :type interface_type_part: str
    :type resource_class: str
    :return: dict mapping resource part to value.
    :rtype: dict

    :raises ValueError: if the interface is unknown.
    """
    for interface_type, const in _INTERFACE_TYPES.items():
        if not interface_type_part.upper().startswith(interface_type):
            continue

        first_part = interface_type_part.lstrip(interface_type)
        out = _SUBPARSER[(interface_type, resource_class)].parse(first_part, *parts)
        out.update(interface_type=const, resource_class=resource_class)
        out['canonical_resource_name'] = out['canonical_resource_name'] % out
        return out

    raise ValueError('Unknown interface type %s' % interface_type_part)


def parse_resource_name(resource_name):
    """Parse a resource name and return a dict mapping resource part to value.

    :type resource_name: str
    :rtype: dict

    :raises InvalidResourceName: if the resource name is invalid.
    """
    # TODO Remote VISA

    parts = resource_name.strip().split('::')
    interface_type, parts = parts[0], parts[1:]

    if len(parts) == 0:
        resource_class = 'INSTR'
    elif parts[-1] in _RESOURCE_CLASSES:
        parts, resource_class = parts[:-1], parts[-1]
    else:
        resource_class = 'INSTR'

    try:
        out = call_subparser(interface_type, resource_class, *parts)
        out['resource_name'] = resource_name
        return out
    except KeyError:
        raise InvalidResourceName('Invalid resource name: %s\n'
                                  'Could find subparser for %s and %s' % (resource_name, interface_type, resource_class))
    except InvalidResourceName as e:
        raise InvalidResourceName('Invalid resource name: %s\n'
                                  'The syntax is %s' % (resource_name, str(e)))


def assemble_ressource_name(ressource_parts):
    """Build a ressource name from a dict mapping ressource part to value.

    """
    pass


def to_canonical_name(resource_name):
    """Parse a resource name and return the canonical version.

    :type resource_name: str
    :rtype: str
    """
    return parse_resource_name(resource_name)['canonical_resource_name']


class _BaseParserAssembler(object):
    """Base class for ressource name parser/assembler.

    """
    canonical_resource_name = ''

    defaults = {}

    def assemble(self, parts):
        """Assemble a ressource name from parts filling missing values with
        defaults.

        """
        p = self.defaults.copy()
        p.update(parts)
        return self.canonical_resource_name % p

    def parse(self, board, *parts):
        """Parse a ressource name.

        """
        raise NotImplementedError


@register_subparser('GPIB', 'INSTR')
class _GPIBInstr(_BaseParserAssembler):
    """GPIB Instrument subparser.

    """
    canonical_ressource_name = 'GPIB%(board)s::%(primary_address)s::%(secondary_address)s::INSTR'

    defaults = dict(board='0', secondary_address=constants.VI_NO_SEC_ADDR)

    def parse(self, board, *parts):
        """Parse a GPIB Instrument resource name.

        Format:
            GPIB[board]::primary address[::secondary address][::INSTR]

        :raises InvalidResourceName: if the resource name is invalid.
        """
    if not board:
        board = self.defaults['board']

    if len(parts) == 2:
        primary_address, secondary_address = parts
    elif len(parts) == 1:
        primary_address, secondary_address = parts[0], self.defaults['secondary_address']
    else:
        raise InvalidResourceName('GPIB[board]::primary address[::secondary address][::INSTR]')

    return dict(board=board,
                primary_address=primary_address,
                secondary_address=secondary_address,
                canonical_resource_name=self.canonical_resource_name)


@register_subparser('GPIB', 'INTFC')
class _GPIBIntfc(_BaseParserAssembler):
    """GPIB Interface subparser.

    """
    canonical_name = 'GPIB%(board)s::INTFC'

    defaults = dict(board='0')

    def parse(self, board, *parts):
        """Parse a GPIB Interface resource name.

        Format:
            GPIB[board]::INTFC

        :raises InvalidResourceName: if the resource name is invalid.
        """

    if not board:
        board = self.defaults['board']

    if len(parts) != 0:
        raise InvalidResourceName('GPIB[board]::INTFC')

    return dict(board=board,
                canonical_resource_name=self.canonical_resource_name)


@register_subparser('ASRL', 'INSTR')
class _ASRLInstr(_BaseParserAssembler):
    """ASRL Instrument subparser.

    """
    canonical_resource_name = 'ASRL%(board)s::INSTR'

    defaults = dict(board='0')

    def _asrl_instr(self, board, *parts):
        """Parse a ASRL Instrument resource name.

        Format:
            ASRLboard[::INSTR]

        :raises InvalidResourceName: if the resource name is invalid.
        """

        if not board:
            raise ValueError('ASRL INSTR requires a board.')

        if len(parts) != 0:
            raise InvalidResourceName('ASRLboard[::INSTR]')

        return dict(board=board,
                    canonical_resource_name='ASRL%(board)s::INSTR')


@register_subparser('TCPIP', 'INSTR')
class _TCPIPInstr(_BaseParserAssembler):
    """TCPIP Instrument subparser.

    """
    canonical_resource_name = 'TCPIP%(board)s::%(host_address)s::%(lan_device_name)s::INSTR'

    defaults = dict(board='0', lan_device_name='inst0')

    def parse(self, board, *parts):
        """Parse a TCPIP Instrument resource name.

        Format:
            TCPIP[board]::host address[::LAN device name][::INSTR]

        :raises InvalidResourceName: if the resource name is invalid.
        """

        if not board:
            board = self.defaults['board']

        if len(parts) == 2:
            host_address, lan_device_name = parts
        elif len(parts) == 1:
            host_address, lan_device_name = parts[0], self.defaults['lan_device_name']
        else:
            raise InvalidResourceName('TCPIP[board]::host address[::LAN device name][::INSTR]')

        return dict(board=board,
                    host_address=host_address,
                    lan_device_name=lan_device_name,
                    canonical_resource_name=self.canonical_resource_name)


@register_subparser('TCPIP', 'SOCKET')
class _TCPIPSocket(_BaseParserAssembler):
    """TCPIP Socket subparser.

    """
    canonical_resource_name = 'TCPIP%(board)s::%(host_address)s::%(port)s::SOCKET'

    # XXXX this value is weird for port
    defaults = dict(board='0', port='inst0')

    def parse(self, board, *parts):
        """Parse a TCPIP Socket resource name.

        Format:
            TCPIP[board]::host address::port::SOCKET

        :raises InvalidResourceName: if the resource name is invalid.
        """

        if not board:
            board = self.defaults['board']

        if len(parts) == 2:
            host_address, port = parts
        elif len(parts) == 1:
            host_address, port = parts[0], self.defaults['port']
        else:
            raise InvalidResourceName('TCPIP[board]::host address::port::SOCKET')

        return dict(board=board,
                    host_address=host_address,
                    port=port,
                    canonical_resource_name=self.canonical_resource_name)


@register_subparser('USB', 'INSTR')
class _USBInstr(_BaseParserAssembler):
    """USB Instrument subparser.

    """
    canonical_resource_name = 'USB%(board)s::%(manufacturer_id)s::%(model_code)s::%(serial_number)s::%(usb_interface_number)s::INSTR'

    defaults = dict(board='0', usb_interface_number='0')

    def parse(self, board, *parts):
        """Parse a USB Instrument resource name.

        Format:
            USB[board]::manufacturer ID::model code::serial number[::USB interface number][::INSTR]

        :raises InvalidResourceName: if the resource name is invalid.
        """

        if not board:
            board = self.defaults['board']

        if len(parts) == 4:
            manufacturer_id, model_code, serial_number, usb_interface_number = parts
        elif len(parts) == 3:
            manufacturer_id, model_code, serial_number = parts
            usb_interface_number = self.defaults['usb_interface_number']
        else:
            raise InvalidResourceName('USB[board]::manufacturer ID::model code::serial number[::USB interface number][::INSTR]')

        return dict(board=board,
                    manufacturer_id=manufacturer_id,
                    model_code=model_code,
                    serial_number=serial_number,
                    usb_interface_number=usb_interface_number,
                    canonical_resource_name=self.canonical_resource_name)


@register_subparser('USB', 'RAW')
class _USBRaw(_BaseParserAssembler):
    """USB Raw subparser.

    """
    canonical_resource_name = 'USB%(board)s::%(manufacturer_id)s::%(model_code)s::%(serial_number)s::%(usb_interface_number)s::RAW'

    defaults = dict(borad='0', usb_interface_number='0')

    def parse(self, board, *parts):
        """Parse a USB Raw resource name.

        Format:
            USB[board]::manufacturer ID::model code::serial number[::USB interface number]::RAW

        :raises InvalidResourceName: if the resource name is invalid.
        """

        if not board:
            board = '0'

        if len(parts) == 4:
            manufacturer_id, model_code, serial_number, usb_interface_number = parts
        elif len(parts) == 3:
            manufacturer_id, model_code, serial_number = parts
            usb_interface_number = '0'
        else:
            raise InvalidResourceName('USB[board]::manufacturer ID::model code::serial number[::USB interface number][::INSTR]')

        return dict(board=board,
                    manufacturer_id=manufacturer_id,
                    model_code=model_code,
                    serial_number=serial_number,
                    usb_interface_number=usb_interface_number,
                    canonical_resource_name=self.canonical_resource_name)


@register_subparser('PXI', 'INSTR')
class _PXIInstr(_BaseParserAssembler):
    """GPIB Instrument subparser.

    """
    canonical_ressource_name = 'PXI%(board)s::%(primary_address)s::INSTR'

    defaults = dict(board='0')

    def parse(self, board, *parts):
        """Parse a GPIB Instrument resource name.

        Format:
            GPIB[board]::primary address[::secondary address][::INSTR]

        :raises InvalidResourceName: if the resource name is invalid.
        """
    if not board:
        board = self.defaults['board']

    if len(parts) == 1:
        primary_address = parts[0]
    else:
        raise InvalidResourceName('PXI[board]::primary address[::INSTR]')

    return dict(board=board,
                primary_address=primary_address,
                canonical_resource_name=self.canonical_resource_name)
