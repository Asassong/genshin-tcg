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


class Card:
    def __init__(self, name_):
        self.name = name_
        card_info = card_dict[name_]
        self.cost = card_info["cost"]
        self.tag = card_info["tag"]
        self.effect_obj = card_info["effect_obj"]
        self.combat_limit = {}
        if "combat_limit" in card_dict[name_]:
            self.combat_limit = card_dict[name_]["combat_limit"]
        self.modify = card_dict[name_]["modify"]


    def get_name(self):
        return self.name

    def get_cost(self):
        return self.cost

card_dict = read_json("card.json")