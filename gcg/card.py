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
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from utils import read_json, DuplicateDict


class Card:
    def __init__(self, name_):
        self._name = name_
        self.card_info = card_dict[name_]
        self._cost = self.card_info["cost"]
        self.tag = self.card_info["tag"]
        self.effect_obj = self.card_info["effect_obj"]
        self.combat_limit = {}
        if "combat_limit" in self.card_info:
            self.combat_limit = self.card_info["combat_limit"]
        self.modifies = DuplicateDict()
        self.use_skill = ""
        if "use_skill" in self.card_info:
            self.use_skill = self.card_info["use_skill"]

    def get_name(self):
        return self._name

    def get_cost(self):
        return self._cost

    def init_modify(self):
        modifies = self.card_info["modify"]
        name = self.get_name()
        return modifies, name




card_dict = read_json("card.json")