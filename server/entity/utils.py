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
from typing import Union, Any
import re

def read_json(file: str) -> dict[str]:
    with open(file, "r", encoding="utf-8") as f:
        text = json.load(f)
    return text


def update_or_append_dict(target_dict: dict, element:dict[Any, Union[int, float]]) -> None:
    for key, value in element.items():
        if key in target_dict:
            target_dict[key] += value
        else:
            target_dict.update({key: value})

def evaluate_expression(expression: str, constant_values: dict): # 将形如"{__element}"的字符串用constant_values中对应值替换
    special = re.search('\{(__\w+)}', expression)
    if special:
        special_key = special.group(1)
        try:
            if "{%s}" % special_key == expression: # 如果为{__number}执行if, "{__element}_DMG", "+{__number}"执行else
                return constant_values[special_key]
            else:
                return expression.format(**constant_values)
        except KeyError as e:
            print("潜在错误: 未get或fetch的special_const %s" % e)
    return expression

def reverse_delete(target_list: list, index_list: Union[set, list]):
    if index_list:
        for index in sorted(index_list, reverse=True):
            target_list.pop(index)
