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
from copy import deepcopy
from server.entity.entity import Entity


class Character(Entity):
    def __init__(self, character_name):
        super().__init__()
        character_detail = deepcopy(all_usable_character[character_name])
        self._hp = character_detail["hp"]
        self.max_hp = character_detail["hp"]
        self.max_energy = character_detail["energy"]
        self.name = character_name
        self.skills: dict = character_detail["skills"]
        self.element = character_detail["element"]
        self.nation = character_detail["nation"]
        self.weapon = character_detail["weapon"]
        self.counter_name = character_detail["counter_name"] if "counter_name" in character_detail else ""
        self.alive = True
        self._energy = 0
        self.modifies = []
        self.application: list[str] = []  # 元素附着
        self.equipment = {"weapon": None, "artifact": None, "talent": None}  # 武器, 圣遗物, 天赋
        self._saturation = 0
        self.is_active = False
        self.state = {} # 只有冻结，准备，附魔这些改变游戏机制的效果写进状态

    def change_hp(self, value):
        self._hp = min(self._hp + value, self.max_hp)
        if self._hp <= 0:
            if "UNYIELDING" in self.state:
                self._hp = 1
            else:
                self.alive = False
                self._hp = 0
                return "die"

    def get_hp(self):
        return self._hp

    def check_need_heal(self):  # 满血时有些卡牌不用触发治疗
        if self._hp == self.max_hp:
            return False
        else:
            return True

    def get_hurt(self):
        return self.max_hp - self._hp

    def get_skills_name(self) -> list:
        skill_names = []
        for key, value in self.skills.items():
            if value["show"]:
                skill_names.append(key)
        return skill_names

    def get_skill_name_and_cost(self) -> tuple[list, list]:
        skill_names = []
        skill_cost = []
        for key, value in self.skills.items():
            if value["show"]:
                skill_names.append(key)
                skill_cost.append(value["cost"])
        return skill_names, skill_cost

    def get_skills_type(self) -> list:
        skill_type = []
        for key, value in self.skills.items():
            if value["show"]:
                if "Normal Attack" in value["tag"]:
                    skill_type.append("Normal Attack")
                elif "Elemental Skill" in value["tag"]:
                    skill_type.append("Elemental Skill")
                elif "Elemental Burst" in value["tag"]:
                    skill_type.append("Elemental Burst")
        return skill_type

    def get_passive_skill(self):
        passive_skill = []
        for key, value in self.skills.items():
            if "Passive Skill" in value["tag"]:
                passive_skill.append(key)
        return passive_skill

    def get_skills_cost(self, skill_name):
        return self.skills[skill_name]["cost"]

    def get_skill_detail(self, skill_name):
        return self.skills[skill_name]

    def get_energy(self):
        return self._energy

    def change_energy(self, value):
        if self._energy + value < 0:
            return False
        else:
            self._energy += value
            self._energy = min(self._energy, self.max_energy)
            return True

    def set_energy(self, value):
        self._energy = value

    def get_saturation(self):
        return self._saturation

    def change_saturation(self, value):
        self._saturation += value

    def cleat_saturation(self):
        self._saturation = 0

def load_character_config(character_pack):
    for character_package, character in character_info.items():
        if character_package in character_pack:
            all_usable_character.update(character)
    print(all_usable_character)

character_info = read_json("./entity/config/character.json")
all_usable_character = {}
