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

from server.entity.entity import Entity
from server.entity.utils import read_json
from copy import deepcopy

class State(Entity):
    def __init__(self, state_name):
        super().__init__()
        self.state_info = deepcopy(all_usable_state[state_name])
        self.name = self.state_info["name"]
        self.modifies = self.state_info["modify"] if "modify" in self.state_info else []
        self.counter_name = self.state_info["counter_name"] if "counter_name" in self.state_info else ""
        self.count = self.state_info["count"] if "count" in self.state_info else 0
        self._usage = self.state_info["usage"] if "usage" in self.state_info else 1
        self.stack = self.state_info["state"] if "state" in self.state_info else 0
        
    def get_show(self):
        return self.state_info["show"]

    def get_icon(self):
        if "icon" in self.state_info:
            return self.state_info["icon"]
        return None
    
    def get_store(self):
        return self.state_info["store"]

    def get_special_const(self):
        if "special_const" in self.state_info:
            return self.state_info["special_const"]
        return {}

def load_state_config(state_pack):
    for state_package, state in state_dict.items():
        if state_package in state_pack:
            all_usable_state.update(state)

state_dict = read_json("./entity/config/state.json")
all_usable_state = {}