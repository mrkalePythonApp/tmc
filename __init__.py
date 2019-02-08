# -*- coding: utf-8 -*-
u"""This file is part of the libsigrokdecode project.

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

DECODER:
TMC is a Titan Micro Electronics communication protocol for driving LED driver
chips based on bidirectional two-wire serial bus using 2 or 3 signals
(CLK = serial clock, DIO = data input/output, STB = strobe). Those chips driver
7-segment displays with simple keyboards.
This protocole decoder is suitable for the chip TM1636, TMP1637, TMP1638.
Chips TM1636 are compatible with TM1637 chips as for driving 7-segment LEDs.
TM1636 drives 4 LEDs and has no support for keyboards. TM1637 drives 6 LEDs.

NOTE:
The TMC two-wire bus is not I²C (Inter-Integrated Circuit) bus because there
is no slave address and in contrast data bytes are transmitted with least
significant bit first.

"""

from .pd import Decoder
