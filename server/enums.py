# Genius Invokation TCG, write by python.
# Copyright (C) 2023 Asassong
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from enum import Enum


class ElementType(Enum):
    NONE = -1
    OMNI = 0
    CRYO = 1 # 冰
    HYDRO = 2 # 水
    PYRO = 3 # 火
    ELECTRO = 4 # 雷
    GEO = 5 # 岩
    DENDRO = 6 # 草
    ANEMO = 7 # 风


class GameStage(Enum):
    NONE = 0
    GAME_START = 1
    ROUND_START = 2
    ROLL = 3
    ACTION = 4
    ROUND_END = 5
    GAME_END = 6

    REROLL = 10