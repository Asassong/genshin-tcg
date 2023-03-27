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
from collections import Counter
import re


def read_json(file: str) -> dict[str]:
    with open(file, "r", encoding="utf-8") as f:
        text = json.load(f)
    return text


def pre_check(mode: str, characters:list, cards:list, camp: str) -> Union[bool, list]:
    invalid = []
    config = read_json("config.json")
    character_dict = read_json("./entity/config/character.json")
    card_dict = read_json("./entity/config/card.json")
    game_config = config["Game"][mode]
    char_pack_limit = game_config["enable_character"]
    card_pack_limit = game_config["enable_deck"]
    each_player_config = game_config[camp]
    enable_characters = {}
    for pack_name, pack in character_dict.items():
        if pack_name in char_pack_limit:
            enable_characters.update(pack)
    enable_cards = {}
    for pack_name, pack in card_dict.items():
        if pack_name in card_pack_limit:
            enable_cards.update(pack)
    if len(characters) != each_player_config["character_num"]:
        invalid.append("角色卡数量不符合要求")
    if len(cards) != each_player_config["deck_num"]:
        invalid.append("牌组数量不符合要求")
    if len(set(characters)) != len(characters):
        invalid.append("禁止重复角色")
    character_elements = []
    for character in characters:
        if character in enable_characters:
            character_info = enable_characters[character]
            character_elements.append(character_info["element"])
        else:
            invalid.append("未知角色 %s" % character)
    count_card = dict(Counter(cards))
    for card_name, count in count_card.items():
        if count > 2:
            invalid.append("卡牌 %s 数量过多" % card_name)
        if card_name in enable_cards:
            card_info = enable_cards[card_name]
            if "deck_limit" in card_info:
                deck_limit = card_info["deck_limit"]
                if "character" in deck_limit:
                    if deck_limit["character"] not in characters:
                        invalid.append("卡牌 %s 不合法, 未携带对应角色" % card_name)
                else:
                    for element in ["CRYO", "HYDRO", "PYRO", "ELECTRO", "DENDRO", "ANEMO", "GEO"]:
                        if element in deck_limit:
                            if character_elements.count(element) < deck_limit[element]:
                                invalid.append("卡牌 %s 不合法, 对应元素角色不足" % card_name)
        else:
            invalid.append("未知卡牌 %s" % card_name)
    if invalid:
        return invalid
    return True

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


