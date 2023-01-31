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

import json
from typing import Union, Any, Iterator
from collections.abc import MutableMapping


def read_json(file: str) -> dict[str]:
    with open(file, "r", encoding="utf-8") as f:
        text = json.load(f)
    return text


def pre_check() -> Union[bool, list]:
    # TODO
    config = read_json("config.json")
    character_dict = read_json("character.json")
    card_dict = read_json("card.json")
    return True

def update_or_append_dict(target_dict: dict, element:dict[Any, Union[int, float]]) -> None:
    for key, value in element.items():
        if key in target_dict:
            target_dict[key] += value
        else:
            target_dict.update({key: value})


class DuplicateDict(MutableMapping):
    def __init__(self, init: list[Union[dict, tuple]]=None):
        self._key_value_list = []
        if init is not None:
            for item in init:
                if isinstance(item, dict):
                    for key, value in item.items():
                        self._key_value_list.append((key, value))
                elif isinstance(item, tuple):
                    self._key_value_list.append(item)

    def __setitem__(self, key: Any, value: Any) -> None:
        self._key_value_list.append((key, value))

    def __delitem__(self, key: Any) -> None:
        pop_index = -1
        for index, item in enumerate(self._key_value_list):
            if item[0] == key:
                pop_index = index
                break
        if pop_index != -1: # 有抛异常的必要吗
            self._key_value_list.pop(pop_index)

    def __getitem__(self, key: Any) -> Any:
        for item in self._key_value_list:
            if item[0] == key:
                return item[1]

    def __len__(self) -> int:
        return len(self._key_value_list)

    def __iter__(self) -> Iterator:
        for item in self._key_value_list:
            yield item[0]

    def __contains__(self, key: Any) -> bool:
        if self.__getitem__(key) is not None:
            return True
        else:
            return False

    def index(self, key: Any) -> int:
        key_list = [item[0] for item in self._key_value_list]
        return key_list.index(key)

    def enumerate(self) -> Iterator:
        for index, item in enumerate(self._key_value_list):
            yield index, item[0], item[1]

    def to_list(self):
        return self._key_value_list

