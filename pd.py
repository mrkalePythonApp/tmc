# -*- coding: utf-8 -*-
"""This file is part of the libsigrokdecode project.

Copyright (C) 2019 Libor Gabaj <libor.gabaj@gmail.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, see <http://www.gnu.org/licenses/>.

"""

import sigrokdecode as srd
import common.srdhelper as hlp


"""
OUTPUT_PYTHON format:

Packet:
[<ptype>, <pdata>]

<ptype>:
 - "START" (START condition)
 - "COMMAND" (Command)
 - "DATA" (Data)
 - "STOP" (STOP condition)
 - "ACK" (ACK bit)
 - "NACK" (NACK bit)
 - "BITS" (<pdata>: list of data bits and their ss/es numbers)

<pdata> is the data byte associated with the "DATA*" command.
For "START", "STOP", "ACK", and "NACK" <pdata> is None.
"""
###############################################################################
# Channels
###############################################################################
CLK = 0     # Serial clock
DIO = 1     # Data input/output
STB = 2     # Strobe line


###############################################################################
# Enumeration classes for device parameters
###############################################################################
class Chip:
    """Enumeration of possible driver chip types."""

    (TM1637, TM1638) = (0, 1)


###############################################################################
# Enumeration classes for annotations
###############################################################################
class AnnProtocol:
    """Enumeration of annotations for protocol states."""

    (START, STOP, ACK, NACK, COMMAND, DATA, BIT) = range(7)


class AnnInfo:
    """Enumeration of annotations for formatted info."""

    (WARN,) = (AnnProtocol.BIT + 1,)


class AnnBinary:
    """Enumeration of annotations for binary info."""

    (DATA,) = (0,)


###############################################################################
# Parameters mapping
###############################################################################
commands = {
    AnnProtocol.START: "START",
    AnnProtocol.STOP: "STOP",
    AnnProtocol.ACK: "ACK",
    AnnProtocol.NACK: "NACK",
    AnnProtocol.COMMAND: "COMMAND",
    AnnProtocol.DATA: "DATA",
    AnnProtocol.BIT: "BITS",
}

chips = {
    Chip.TM1637: "TM1637",
    Chip.TM1638: "TM1638",
}


###############################################################################
# Parameters anotations definitions
###############################################################################
"""
- The last item of an annotation list is used repeatedly without a value.
- The last two items of an annotation list are used repeatedly without a value.
"""
protocol = {
    AnnProtocol.START: ["Start", "S"],
    AnnProtocol.STOP: ["Stop", "P"],
    AnnProtocol.ACK: ["ACK", "A"],
    AnnProtocol.NACK: ["NACK", "N"],
    AnnProtocol.COMMAND: ["Command", "C"],
    AnnProtocol.DATA: ["Data", "D"],
    AnnProtocol.BIT: ["Bit", "B"],
}

info = {
    AnnInfo.WARN: ["Warnings", "Warn", "W"],
}

binary = {
    AnnBinary.DATA: ["Data", "D"],
}


###############################################################################
# Decoder
###############################################################################
class SamplerateError(Exception):
    """Custom exception."""

    pass


class ChannelError(Exception):
    """Custom exception."""

    pass


class Decoder(srd.Decoder):
    """Protocol decoder for Titan Micro Circuits."""

    api_version = 3
    id = "tmc"
    name = "TMC"
    longname = "Titan Micro Circuit"
    desc = "Bus for TM1636/37/38 7-segment LED drivers."
    license = "gplv2+"
    inputs = ["logic"]
    outputs = ["tmc"]
    channels = (
        {"id": "clk", "name": "CLK", "desc": "Clock line"},
        {"id": "dio", "name": "DIO", "desc": "Data line"},
    )
    optional_channels = (
        {"id": "stb", "name": "STB", "desc": "Strobe line"},
    )
    options = (
        {"id": "radix", "desc": "Number format", "default": "Hex",
         "values": ("Hex", "Dec", "Oct", "Bin")},
    )
    annotations = hlp.create_annots(
        {
            "prot": protocol,
            "info": info,
         }
    )
    annotation_rows = (
        ("bits", "Bits", (AnnProtocol.BIT,)),
        ("data", "Cmd/Data", tuple(range(
            AnnProtocol.START, AnnProtocol.DATA + 1
            ))),
        ("warnings", "Warnings", (AnnInfo.WARN,)),
    )
    binary = hlp.create_annots({"data": binary})

    def __init__(self):
        """Initialize decoder."""
        self.reset()

    def reset(self):
        """Reset decoder and initialize instance variables."""
        self.ss = self.es = self.ss_byte = self.ss_ack = -1
        self.samplerate = None
        self.pdu_start = None
        self.pdu_bits = 0
        self.chiptype = None
        self.bytecount = 0
        self.clear_data()
        self.state = "FIND START"

    def metadata(self, key, value):
        """Pass metadata about the data stream."""
        if key == srd.SRD_CONF_SAMPLERATE:
            self.samplerate = value

    def start(self):
        """Actions before the beginning of the decoding."""
        self.out_python = self.register(srd.OUTPUT_PYTHON)
        self.out_ann = self.register(srd.OUTPUT_ANN)
        self.out_binary = self.register(srd.OUTPUT_BINARY)
        self.out_bitrate = self.register(
            srd.OUTPUT_META,
            meta=(int, "Bitrate", "Bitrate from Start bit to Stop bit")
        )

    def putx(self, data):
        """Show data to annotation output across bit range."""
        self.put(self.ss, self.es, self.out_ann, data)

    def putp(self, data):
        """Show data to python output across bit range."""
        self.put(self.ss, self.es, self.out_python, data)

    def putb(self, data):
        """Show data to binary output across bit range."""
        self.put(self.ss, self.es, self.out_binary, data)

    def clear_data(self):
        """Clear data cache."""
        self.bitcount = 0
        self.databyte = 0
        self.bits = []

    def handle_bitrate(self):
        """Calculate bitrate."""
        if self.samplerate:
            elapsed = 1 / float(self.samplerate)    # Sample time period
            elapsed *= self.samplenum - self.pdu_start - 1
            bitrate = int(1 / elapsed * self.pdu_bits)
            self.put(self.ss_byte, self.samplenum, self.out_bitrate, bitrate)

    def handle_start(self, pins):
        """Process start condition."""
        self.ss, self.es = self.samplenum, self.samplenum
        self.pdu_start = self.samplenum
        self.pdu_bits = 0
        self.bytecount = 0
        cmd = AnnProtocol.START
        self.putp([commands[cmd], None])
        self.putx([cmd, protocol[cmd]])
        self.clear_data()
        self.state = "FIND DATA"

    def handle_data(self, pins):
        """Create name and call corresponding data handler."""
        self.pdu_bits += 1
        if self.bitcount == 0:
            self.ss_byte = self.samplenum
        fn = getattr(self,
                     "handle_data_{}".format(chips[self.chiptype].lower()))
        fn(pins)

    def handle_stop(self):
        """Create name and call corresponding stop handler."""
        fn = getattr(self,
                     "handle_stop_{}".format(chips[self.chiptype].lower()))
        fn()

    def handle_data_tm1637(self, pins):
        """Process data bits.

        Arguments
        ---------
        pins : tuple
            Tuple of bit values (0 or 1) for each channel from the first one.

        Notes
        -----
        - The method is called at rising edge of each clock pulse regardless of
          its purpose or meaning.
        - For acknowledge clock pulse and start/stop pulse the registration of
          this bit is provided in vain just for simplicity of the method.
        - The method stores individual bits and their start/end sample numbers.
        - In the bit list, index 0 represents the recently processed bit, which
          is finally the MSB (LSB-first transmission).
        - The method displays previous bit because its end sample number is
          known just at processing the current bit.

        """
        clk, dio, stb = pins
        self.bits.insert(0, [dio, self.samplenum, self.samplenum])
        # Register end sample of the previous bit and display it
        if self.bitcount > 0:
            self.bits[1][2] = self.samplenum
            # Previous bit is data one
            if self.bitcount <= 8:
                # Display previous bit
                annots = hlp.compose_annot("", ann_value=self.bits[1][0])
                self.put(self.bits[1][1], self.bits[1][2], self.out_ann,
                         [AnnProtocol.BIT, annots])
        # Include current data bit to data byte (LSB-first transmission)
        self.bitcount += 1
        if self.bitcount <= 8:
            self.databyte >>= 1
            self.databyte |= (dio << 7)
            return
        # Display data byte
        self.ss, self.es = self.ss_byte, self.samplenum
        cmd = AnnProtocol.DATA
        if self.bytecount == 0:
            cmd = AnnProtocol.COMMAND
        self.bits.pop(0)    # Remove ACK bit
        self.bits.reverse()
        self.putp([commands[AnnProtocol.BIT], self.bits])
        self.putp([commands[cmd], self.databyte])
        self.putb([AnnBinary.DATA, bytes([self.databyte])])
        annots = hlp.compose_annot(
            protocol[cmd],
            ann_value=hlp.format_data(self.databyte, self.options["radix"])
        )
        self.putx([cmd, annots])
        self.clear_data()
        self.ss_ack = self.samplenum  # Remember start of ACK bit
        self.bytecount += 1
        self.state = "FIND ACK"

    def handle_ack(self, pins):
        """Process ACK/NACK bit."""
        clk, dio, stb = pins
        self.ss, self.es = self.ss_ack, self.samplenum
        cmd = AnnProtocol.NACK if (dio == 1) else AnnProtocol.ACK
        self.putp([commands[cmd], None])
        self.putx([cmd, protocol[cmd]])
        self.state = "FIND DATA"

    def handle_stop_tm1637(self):
        """Process stop condition for TM1636/37."""
        self.handle_bitrate()
        # Display stop
        cmd = AnnProtocol.STOP
        self.ss, self.es = self.samplenum, self.samplenum
        self.putp([commands[cmd], None])
        self.putx([cmd, protocol[cmd]])
        self.clear_data()
        self.state = "FIND START"

    def handle_byte_tm1638(self):
        """Process data byte after last CLK pulse."""
        # Display all bits
        self.bits[0][2] = self.samplenum    # Update end sample of the last bit
        for bit in self.bits:
            annots = hlp.compose_annot("", ann_value=bit[0])
            self.put(bit[1], bit[2], self.out_ann, [AnnProtocol.BIT, annots])
        # Display data byte
        self.ss, self.es = self.ss_byte, self.samplenum
        cmd = AnnProtocol.DATA
        if self.bytecount == 0:
            cmd = AnnProtocol.COMMAND
        self.bits.reverse()
        self.putp([commands[AnnProtocol.BIT], self.bits])
        self.putp([commands[cmd], self.databyte])
        self.putb([AnnBinary.DATA, bytes([self.databyte])])
        annots = hlp.compose_annot(
            protocol[cmd],
            ann_value=hlp.format_data(self.databyte, self.options["radix"])
        )
        self.putx([cmd, annots])
        self.bytecount += 1

    def handle_data_tm1638(self, pins):
        """Process data bits at CLK rising edge."""
        clk, dio, stb = pins
        if self.bitcount >= 8:
            self.handle_byte_tm1638()
            self.clear_data()
            self.ss_byte = self.samplenum
        self.bits.insert(0, [dio, self.samplenum, self.samplenum])
        self.databyte >>= 1
        self.databyte |= (dio << 7)
        # Register end sample of the previous bit
        if self.bitcount > 0:
            self.bits[1][2] = self.samplenum
        self.bitcount += 1

    def handle_stop_tm1638(self):
        """Process stop condition for TM1638."""
        self.handle_bitrate()
        self.handle_byte_tm1638()
        # Display stop
        cmd = AnnProtocol.STOP
        self.ss, self.es = self.samplenum, self.samplenum
        self.putp([commands[cmd], None])
        self.putx([cmd, protocol[cmd]])
        self.clear_data()
        self.state = "FIND START"

    def decode(self):
        """Decode samples provided by logic analyzer."""
        if not self.samplerate:
            raise SamplerateError("Cannot decode without samplerate.")
        has_pin = [self.has_channel(ch) for ch in (CLK, DIO)]
        if has_pin != [True, True]:
            raise ChannelError("Both CLK and DIO pins required.")
        while True:
            # State machine
            if self.state == "FIND START":
                # Wait for any of the START conditions:
                # TM1636/37: CLK = high, DIO = falling
                # TM1638: CLK = high, STB = falling
                pins = self.wait([{CLK: "h", DIO: "f"},
                                  {CLK: 'h', STB: "f"},
                                  ])
                if self.matched[0]:
                    self.chiptype = Chip.TM1637
                    self.handle_start(pins)
                elif self.matched[1]:
                    self.chiptype = Chip.TM1638
                    self.handle_start(pins)
            elif self.state == "FIND DATA":
                # Wait for any of the following conditions:
                #  Clock pulse: CLK = rising
                #  TM1636/37 STOP condition: CLK = high, DIO = rising
                #  TM1638 STOP condition: STB = rising
                pins = self.wait([{CLK: "r"},
                                  {CLK: "h", DIO: "r"},
                                  {STB: "r"},
                                  ])
                if self.matched[0]:
                    self.handle_data(pins)
                elif self.matched[1] or self.matched[2]:
                    self.handle_stop()
            elif self.state == "FIND ACK":
                # Wait for an ACK bit
                self.handle_ack(self.wait({CLK: "f"}))
            elif self.state == "FIND STOP":
                # Wait for STOP conditions:
                #  TM1636/37 STOP condition: CLK = high, DIO = rising
                #  TM1638 STOP condition: STB = rising
                pins = self.wait([{CLK: "h", DIO: "r"},
                                  {STB: "r"},
                                  ])
                if self.matched[0] or self.matched[1]:
                    self.handle_stop()
