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

from utils import read_json

class Summon:
    def __init__(self, name):
        self.name = name
        detail = summon_dict[name]
        self.effect = detail["effect"]
        self.usage = detail["effect"]
        self.modifies = []
        if "modify" in detail:
            self.modifies = detail["modify"]
        self.type = {}
        if "type" in detail:
            self.type = detail["type"]
        self.card_type = name
        if "card_type" in detail:
            self.card_type = detail["card_type"]
        self.stack = 1
        if "stack" in detail:
            self.stack = detail["stack"]

    def consume_usage(self, value):
        if isinstance(self.usage, str):
            usage = eval(self.usage)
            if usage <= 0:
                return "remove"
        else:
            self.usage -= value
            if self.usage <= 0:
                return "remove"
        return None

def get_summon_usage(summon_name):
    detail = summon_dict[summon_name]
    usage = detail["usage"]
    return usage

summon_dict = read_json("summon.json")
