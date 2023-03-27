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

from server.entity.utils import read_json
from server.entity.entity import Entity
from copy import deepcopy

class Card(Entity):
    def __init__(self, name):
        super().__init__()
        self.card_info = deepcopy(all_usable_card[name])
        self.name = self.card_info["name"]
        self._cost = self.card_info["cost"]
        self.tag = self.card_info["tag"]
        self.modifies = self.card_info["modify"] if "modify" in self.card_info else []
        self.counter_name = self.card_info["counter_name"] if "counter_name" in self.card_info else ""
        self.count = self.card_info["count"] if "count" in self.card_info else 0
        self._usage = self.card_info["usage"] if "usage" in self.card_info else 1

    def get_cost(self):
        return self._cost

    def need_fetch(self):
        if "fetch" in self.card_info:
            return self.card_info["fetch"]
        else:
            return False

    def get_store(self):
        return self.card_info["store"]

    def get_combat_limit(self):
        return self.card_info["combat_limit"] if "combat_limit" in self.card_info else []

    def get_show(self):
        return self.card_info["show"]

    def get_icon(self):
        if "icon" in self.card_info:
            return self.card_info["icon"]
        return None

def load_card_config(card_pack):
    for card_package, card in card_dict.items():
        if card_package in card_pack:
            all_usable_card.update(card)

card_dict = read_json("./entity/config/card.json")
all_usable_card = {}