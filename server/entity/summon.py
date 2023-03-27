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

from server.entity.utils import read_json
from copy import deepcopy
from server.entity.entity import Entity
import random

class Summon(Entity):
    def __init__(self, summon_name, exist_summon=None):
        super().__init__()
        self.summon_info = deepcopy(all_usable_summon[summon_name])
        self.replace_summon_info_to_special_type(exist_summon)
        self.name = self.summon_info["name"]
        self.modifies = self.summon_info["modify"] if "modify" in self.summon_info else []
        self.counter_name = self.summon_info["counter_name"] if "counter_name" in self.summon_info else ""
        self.count = self.summon_info["count"] if "count" in self.summon_info else 0
        self._usage = self.summon_info["usage"] if "usage" in self.summon_info else 1
        self.stack = self.summon_info["stack"] if "stack" in self.summon_info else 0

    def get_show(self):
        return self.summon_info["show"]

    def replace_summon_info_to_special_type(self, exist_summon):
        if "random_type" in self.summon_info:
            random_summon = random.choice(self.summon_info["type_name"])
            if self.summon_info["random_type"] == "different":
                if random_summon in exist_summon:
                    self.replace_summon_info_to_special_type(exist_summon)
                else:
                    self.summon_info = self.summon_info["type"][random_summon]
            else:
                self.summon_info = self.summon_info["type"][random_summon]

    # def get_icon(self):
    #     if "icon" in self.summon_info:
    #         return self.summon_info["icon"]
    #     return None

    # def get_store(self):
    #     return self.summon_info["store"]
    #
    def get_show_effect(self):
        return self.summon_info["show_effect"]

def load_summon_config(summon_pack):
    for summon_package, summon in summon_dict.items():
        if summon_package in summon_pack:
            all_usable_summon.update(summon)

summon_dict = read_json("./entity/config/summon.json")
all_usable_summon = {}