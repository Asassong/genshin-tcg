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

import random
from card import Card
from character import Character
from summon import Summon, get_summon_usage
from dice import Dice
from enums import ElementType
from utils import update_or_append_dict
from typing import Optional


class Player:
    def __init__(self):
        self.name = ""
        self.max_summon = 4
        self.max_support = 4
        self.max_card = 30
        self.character_num = 3
        self.max_hand_card = 10
        self.dice_num = 8
        self.summons: list[Summon] = []
        self.supports = []
        self.characters: list[Character] = []
        self.dices: list[Dice] = []
        self.cards: list[Card] = []
        self.hand_cards: list[Card] = []
        self.current_character = None
        self.round_has_end = True
        self.team_modifier = []

    def draw(self, num):
        if len(self.cards) < num:
            num = len(self.cards)
        elif len(self.hand_cards) + num > self.max_hand_card:
            num = self.max_hand_card - len(self.hand_cards)
        for i in range(num):
            draw_index = random.randint(0, len(self.cards)-1)
            self.hand_cards.append(self.cards[draw_index])
            self.cards.pop(draw_index)

    def redraw(self, cards):
        drop_cards = sorted(cards, reverse=True)
        for i in drop_cards:
            self.cards.append(self.hand_cards[i])
            self.hand_cards.pop(i)
        self.draw(len(drop_cards))

    def init_card(self, card_list):
        for card in card_list:
            self.cards.append(Card(card))

    def get_hand(self):
        return self.hand_cards

    def init_character(self, character_list):
        if len(character_list) == self.character_num:
            for character_name in character_list:
                self.characters.append(Character(character_name))

    def get_character(self):
        return self.characters

    def choose_character(self, character):
        if not self.characters[character].alive:
            return False
        self.current_character = character
        return True

    def get_active_character_obj(self) -> Optional[Character]:
        if self.current_character is not None:
            return self.characters[self.current_character]

    def get_active_character_name(self):
        if self.current_character is not None:
            return self.characters[self.current_character].name
        else:
            return None

    def change_active_character(self, new_character_index):
        if self.current_character == new_character_index:
            return False
        else:
            return self.choose_character(new_character_index)

    def get_standby_obj(self):
        if self.current_character is not None:
            standby = []
            for i in range(len(self.characters)):
                if i != self.current_character and self.characters[i].alive:
                    standby.append(self.characters[i])
            return standby

    def roll(self):
        for i in range(self.dice_num):
            self.append_random_dice()

    def get_dice(self):
        return self.dices

    def append_random_dice(self):
        self.dices.append(Dice())
        self.dices[-1].roll()

    def append_special_dice(self, element):
        self.dices.append(Dice())
        if isinstance(element, str):
            index = ElementType[element].value
        elif isinstance(element, ElementType):
            index = element.value
        else:
            return None
        self.dices[-1].set_element_type(index)

    def remove_dice(self, index):
        self.dices.pop(index)

    def use_dices(self, indexes: list[int]):
        indexes = sorted(indexes, reverse=True)
        for index in indexes:
            self.remove_dice(index)

    def remove_hand_card(self, index):
        self.hand_cards.pop(index)

    def reroll(self, indexes):
        indexes = sorted(indexes, reverse=True)
        for index in indexes:
            self.remove_dice(index)
        for i in range(len(indexes)):
            self.append_random_dice()

    @staticmethod
    def sort_cost(cost):
        score_dict = {"ANY": 1, "ENERGY": 4, "SAME": 2}
        return dict(sorted(cost.items(), key=lambda x: score_dict[x[0]] if x[0] in score_dict else 3, reverse=True))

    def check_cost(self, cost):
        active_obj = self.get_active_character_obj()
        active_energy = active_obj.energy
        active_element = active_obj.element
        team_element = []
        for character in self.characters:
            team_element.append(character.element)
        team_element = list(set(team_element))
        count_dice = {}
        dice_type = []
        for dice in self.dices:
            dice_type.append(ElementType(dice.element).name)
        for dice in set(dice_type):
            count_dice[dice] = dice_type.count(dice)
        if "OMNI" not in count_dice:  # 方便之后的逻辑
            count_dice["OMNI"] = 0
        cost = self.sort_cost(cost)
        real_cost = {}
        for cost_type, cost_num in cost.items():
            if cost_type == "ENERGY":
                if active_energy < cost_num:
                    return False
                real_cost.update({"ENERGY": cost_num})
            elif cost_type in ElementType.__members__:
                if cost_type in count_dice:
                    if cost_num < count_dice[cost_type]:
                        count_dice[cost_type] -= cost_num
                        update_or_append_dict(real_cost, {cost_type: cost_num})
                    elif cost_num == count_dice[cost_type]:
                        update_or_append_dict(real_cost, {cost_type: cost_num})
                        del count_dice[cost_type]
                    else:
                        if count_dice["OMNI"] + count_dice[cost_type] >= cost_num:
                            update_or_append_dict(real_cost, {cost_type: count_dice[cost_type]})
                            count_dice["OMNI"] -= cost_num - count_dice[cost_type]
                            update_or_append_dict(real_cost, {"OMNI": cost_num - count_dice[cost_type]})
                            del count_dice[cost_type]
                            continue
                        return False
                else:
                    if count_dice["OMNI"] >= cost_num:
                        count_dice["OMNI"] -= cost_num
                        update_or_append_dict(real_cost, {"OMNI": cost_num})
                        continue
                    return False
            elif cost_type == "SAME":
                valid_list = []
                for key, value in count_dice.items():
                    if key == "OMNI":
                        if value >= cost_num:
                            valid_list.append(["OMNI"] * cost_num)
                    else:
                        if value >= cost_num:
                            valid_list.append([key] * cost_num)
                        elif value + count_dice["OMNI"] >= cost_num:
                            valid_list.append(["OMNI"] * (cost_num - value) + [key] * value)
                history_score = []
                for each in valid_list:
                    score = 0
                    for element in each:
                        if element in active_element:
                            score += -1
                        elif element == team_element:
                            score += 0
                        elif element == "OMNI":
                            score += -5
                        else:
                            score += 10
                    if history_score:
                        if score > history_score[0]:
                            history_score = [score, each]
                    else:
                        history_score = [score, each]
                if history_score:
                    valid_dice = {}
                    for dice in set(history_score[1]):
                        valid_dice[dice] = history_score[1].count(dice)
                    update_or_append_dict(real_cost, valid_dice)
                    for key, value in valid_dice.items():
                        if count_dice[key] > value or key == "OMNI":
                            count_dice[key] -= value
                        else:
                            del count_dice[key]
                else:
                    return False
            elif cost_type == "ANY":
                choose = []
                for _ in range(cost_num):
                    history_score = []
                    if len(count_dice) == 1:
                        if count_dice["OMNI"] == 0:
                            return False
                    for key, value in count_dice.items():
                        score = 0
                        if value == 1:
                            score += 1
                        if key not in team_element:
                            score += 5
                        if key == active_element:
                            score += -1
                        if key == "OMNI":
                            score += -10
                        if history_score:
                            if score > history_score[0]:
                                history_score = [score, key]
                        else:
                            history_score = [score, key]
                    if history_score:
                        if count_dice[history_score[1]] > 1 or history_score[1] == "OMNI":
                            count_dice[history_score[1]] -= 1
                        else:
                            del count_dice[history_score[1]]
                        choose.append(history_score[1])
                    else:
                        return False
                valid_dice = {}
                for dice in set(choose):
                    valid_dice[dice] = choose.count(dice)
                update_or_append_dict(real_cost, valid_dice)
            else:
                return False
        return real_cost

    def recheck_cost(self, cost, input_index):
        input_element = [ElementType(self.dices[i].element).name for i in input_index]
        count_input = {}
        for dice in set(input_element):
            count_input[dice] = input_element.count(dice)
        cost = self.sort_cost(cost)
        for cost_type, cost_num in cost.items():
            if cost_type in ElementType.__members__:
                if cost_type in count_input:
                    if cost_num <= count_input[cost_type]:
                        for _ in range(cost_num):
                            input_element.remove(cost_type)
                            count_input[cost_type] -= 1
                    elif "OMNI" in count_input:
                        if count_input["OMNI"] + count_input[cost_type] >= cost_num:
                            for _ in range(count_input[cost_type]):
                                input_element.remove(cost_type)
                                count_input[cost_type] -= 1
                            for _ in range(cost_num - count_input[cost_type]):
                                input_element.remove("OMNI")
                                count_input["OMNI"] -= 1
                        else:
                            return False
                    else:
                        return False
                elif "OMNI" in count_input:
                    if count_input["OMNI"] >= cost_num:
                        for _ in range(cost_num):
                            input_element.remove("OMNI")
                            count_input["OMNI"] -= 1
                else:
                    return False
            elif cost_type == "SAME":  # 由于same只用于卡牌，费用固定为1项，故简化
                if len(count_input) == 1:
                    for key, value in count_input.items():
                        if value >= cost_num:
                            for _ in range(cost_num):
                                input_element.remove(key)
                                count_input[key] -= 1
                        else:
                            return False
                elif len(count_input) == 2:
                    if len(input_element) == cost_num and "OMNI" in input_element:
                        input_element.clear()
                        count_input.clear()
                    else:
                        return False
                else:
                    return False
            elif cost_type == "ANY":
                if len(input_element) == cost_num:
                    input_element.clear()
                    count_input.clear()
                else:
                    return False
        if len(input_element) == 0:
            return True
        else:
            return False

    def add_summon(self, summon_name):
        now_summon_name = self.get_summon_name()
        if summon_name in now_summon_name:
            index = now_summon_name.index(summon_name)
            summon_obj = self.summons[index]
            # TODO 逻辑还需确认
            if summon_obj.stack <= 1:
                self.remove_summon(index)
            else:
                if summon_obj.stack <= summon_obj.usage:
                    return False  # 无意义，只起跳过作用
                else:
                    usage = get_summon_usage(summon_name)
                    summon_obj.stack = min(summon_obj.usage + usage, summon_obj.stack * usage)
                    return True  # 无意义，只起跳过作用
        else:
            if len(self.summons) >= self.max_summon:
                yield "remove"
        self.summons.append(Summon(summon_name))

    def remove_summon(self, summon_index):
        self.summons.pop(summon_index)

    def get_summon_name(self):
        summon_name_list = []
        for summon in self.summons:
            summon_name_list.append(summon.name)
        return summon_name_list

    def trigger_summon(self):
        for summon in self.summons:
            effect = summon.effect
            for effect_type, effect in effect.items():
                if effect_type == "damage":
                    yield "damage", summon, effect


    def get_card_obj(self, index):
        return self.hand_cards[index]

    def add_support(self, card_name):
        if len(self.supports) >= self.max_support:
            yield "remove"
        self.supports.append(card_name)

    def remove_support(self, support_index):
        self.supports.pop(support_index)

    def get_support_name(self):
        return self.supports

