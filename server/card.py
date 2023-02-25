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

from utils import read_json
from copy import deepcopy

class Card:
    def __init__(self, name, card_pack):
        self._name = name
        all_usable_card = {}
        for card_package, card in card_dict.items():
            if card_package in card_pack:
                all_usable_card.update(card)
        self.card_info = deepcopy(all_usable_card[name])
        self._cost = self.card_info["cost"]
        self.tag = self.card_info["tag"]
        self.effect_obj = self.card_info["effect_obj"]
        self.combat_limit = {}
        if "combat_limit" in self.card_info:
            self.combat_limit = self.card_info["combat_limit"]
        self.modifies = []
        self.use_skill = ""
        if "use_skill" in self.card_info:
            self.use_skill = self.card_info["use_skill"]
        self.counter = {}
        if "counter" in self.card_info:
            self.counter = {counter: 0 for counter in self.card_info["counter"]}

    def get_name(self):
        return self._name

    def get_cost(self):
        return self._cost

    def init_modify(self):
        if "modify" in self.card_info:
            modifies = self.card_info["modify"]
            team_modify = []
            for modify in modifies:
                if modify["store"] == "self":
                    self.modifies += modify
                else:
                    team_modify += modify
            if team_modify:
                return team_modify



card_dict = read_json("card.json")