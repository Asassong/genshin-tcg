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
        self.combat_limit = self.card_info["combat_limit"] if "combat_limit" in self.card_info else []
        self.modifies = self.card_info["modify"] if "modify" in self.card_info else []
        self.use_skill = self.card_info["use_skill"] if "use_skill" in self.card_info else ""
        self.counter = {}
        if "counter" in self.card_info:
            self.counter = {counter: 0 for counter in self.card_info["counter"]}
        self.usage = self.card_info["usage"] if "usage" in self.card_info else 1

    def get_name(self):
        return self._name

    def get_cost(self):
        return self._cost

    def need_fetch(self):
        if "fetch" in self.card_info:
            return self.card_info["fetch"]
        else:
            return False

    def get_store(self):
        return self.card_info["store"]

    def have_usage(self):
        if "usage" in self.card_info:
            return True
        return False

    def have_counter(self):
        if "counter" in self.card_info:
            return True
        return False

    def get_count(self):
        if self.counter:
            _, num = next(iter(self.counter.items()))
            return num

    def add_counter(self, counter_name):
        self.counter.update({counter_name: 0})

    def clear_counter(self):
        self.counter.clear()

card_dict = read_json("card.json")