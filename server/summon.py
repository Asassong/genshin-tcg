# Genius Invokation TCG, write in python.
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
# GNU General Public License for more self.details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from utils import read_json
from copy import deepcopy

class Summon:
    def __init__(self, name):
        self._name = name
        self.detail = deepcopy(summon_dict[name])
        self.effect: list[dict] = self.detail["effect"]
        self.usage = self.detail["usage"]
        self.modifies = self.detail["modify"]
        self.type = {}
        if "type" in self.detail:
            self.type = self.detail["type"]
        self.card_type = name
        if "card_type" in self.detail:
            self.card_type = self.detail["card_type"]
        self.stack = 1
        if "stack" in self.detail:
            self.stack = self.detail["stack"]
        self.element = None
        if "element" in self.detail:
            self.element = self.detail["element"]
        self.counter = {}
        if "counter" in self.detail:
            self.counter = {i: 0 for i in self.detail["counter"]}

    def consume_usage(self, value):
        if isinstance(value, str):
            if value == "all":
                self.usage = 0
        else:
            self.usage -= value
        if self.usage <= 0:
            return "remove"

    def get_name(self):
        return self._name

summon_dict = read_json("summon.json")