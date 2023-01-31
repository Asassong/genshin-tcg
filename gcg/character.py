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

from enums import ElementType, Nation, WeaponType
from utils import read_json, DuplicateDict


class Character:
    def __init__(self, character_name):
        self._hp = character_info[character_name]["hp"]
        self.max_hp = character_info[character_name]["hp"]
        self.max_energy = character_info[character_name]["energy"]
        self.name = character_name
        self.skills: dict = character_info[character_name]["skills"]
        self.element = ElementType[character_info[character_name]["element_type"].upper()]
        self.nation = [Nation[i] for i in character_info[character_name]["nation"] if i]
        self.weapon = WeaponType[character_info[character_name]["weapon"].upper()]
        if "counter" in character_info[character_name]:
            self.counter = {i: 0 for i in character_info[character_name]["counter"]}
        else:
            self.counter = {}
        self.alive = True
        self.energy = 0
        self.modifies = DuplicateDict()
        self.application: list[ElementType] = []  # 元素附着
        self.weapon_infusion: ElementType = ElementType.NONE  # 元素附魔
        self.equipment = {"weapon": None, "reliquary": None, "talent": None}  # 武器, 圣遗物, 天赋

    def change_hp(self, value):
        self._hp = min(self._hp + value, self.max_hp)
        if self._hp <= 0:
            self.alive = False
            return "die"

    def get_hp(self):
        return self._hp

    def check_need_heal(self):  # 满血时有些卡牌不用触发治疗
        if self._hp == self.max_hp:
            return False
        else:
            return True

    def get_card_info(self):
        detail = ""
        if self.alive:
            detail += "%s:血量%s 能量%s/%s" % (self.name, self._hp, self.energy, self.max_energy)
            # detail += "技能 " + " ".join(list(self.skills.keys())) + " "
            detail += "附着" + self.application[0].name + " " if self.application else ""
            detail += "附魔" + self.weapon_infusion.name + " " if self.weapon_infusion else ""
            for key, value in self.equipment.items():
                if value is not None:
                    detail += "%s %s " % (key, value)
            detail += "\n"
            return detail
        else:
            return "%s已退场\n" % self.name

    def get_skills_name(self) -> list:
        skill_names = []
        for key, value in self.skills.items():
            if "Passive Skill" not in value["type"]:
                skill_names.append(key)
        return skill_names

    def get_passive_skill(self):
        passive_skill = []
        for key, value in self.skills.items():
            if "Passive Skill" in value["type"]:
                passive_skill.append(key)
        return passive_skill

    def get_skills_cost(self, skill_name):
        return self.skills[skill_name]["cost"]

    def get_skill_detail(self, skill_name):
        return self.skills[skill_name]

    def change_energy(self, value):
        self.energy += value


character_info = read_json("character.json")





