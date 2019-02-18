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
TMC is a Titan Micro Electronics communication protocol for driving chips based
on bidirectional two or three wire serial bus using 2 or 3 signals
(CLK = serial clock, DIO = data input/output, STB = strobe). Those chips drive
7-segment digital tubes with simple keyboards.
This protocole decoder is suitable for the chips TM1636, TMP1637, TMP1638, etc.
- TM1636 is compatible with TM1637 as for driving 7-segment digital tu. It
  drives up to 4 digital tubes and has no support for keyboard scanning.
- TM1637 drives up to 6 digital tubes and has support for keyboards, but they
  are practically not used on breaboards.
- TMP1638 drives up to 8 LED digital tubes, upt to 8 two-color LEDs (logically
  10 segment tubes), and has support for keyboard scanning. Those chips are
  usually used on breakout boards with full set of digital tubes, full set of
  LED at least unicolor, and with 8 key or 24 keys keyboards.

NOTE:
The TMC two-wire bus is not I²C (Inter-Integrated Circuit) bus because there
is no slave address and in contrast data bytes are transmitted with least
significant bit first.

"""

from .pd import Decoder
