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

import random

from card import Card
from character import Character
from summon import Summon
from dice import Dice
from enums import ElementType
from utils import update_or_append_dict, read_json
from typing import Optional


class Player:
    def __init__(self, player_info, card_pack, char_pack, deck):
        self.max_summon = player_info["max_summon"]
        self.max_support = player_info["max_support"]
        self.max_hand_card = player_info["max_hand_card"]
        self.dice_num = player_info["dice_num"]
        self.max_dice = player_info["max_dice"]
        self.max_character_saturation = player_info["max_character_saturation"]
        self.summons: list[Summon] = []
        self.supports: list[Card] = []
        self.char_pack = char_pack
        self.card_pack = card_pack
        self.characters: list[Character] = self.init_character(deck[0], char_pack)
        self.dices: list[Dice] = []
        self.cards: list[Card] = self.init_card(deck[1], card_pack)
        self.hand_cards: list[Card] = []
        self.current_character = None
        self.team_modifier = []
        self.team_state = {}
        self.round_has_end = True


    def draw(self, num):
        if len(self.cards) < num:
            num = len(self.cards)
        for i in range(num):
            draw_index = random.randint(0, len(self.cards)-1)
            if len(self.hand_cards) < self.max_hand_card:
                self.hand_cards.append(self.cards[draw_index])
            self.cards.pop(draw_index)

    def redraw(self, cards):
        drop_cards = sorted(cards, reverse=True)
        for i in drop_cards:
            self.cards.append(self.hand_cards[i])
            self.hand_cards.pop(i)
        self.draw(len(drop_cards))

    def draw_type(self, card_type):
        valid_card = []
        for index, card in enumerate(self.cards):
            if card_type in card.tag:
                valid_card.append(index)
        if valid_card:
            draw_index = random.randint(0, len(valid_card) - 1)
            if len(self.hand_cards) < self.max_hand_card:
                self.hand_cards.append(self.cards[valid_card[draw_index]])
            self.cards.pop(valid_card[draw_index])

    @staticmethod
    def init_card(card_list, card_pack):
        cards = []
        for card in card_list:
            cards.append(Card(card, card_pack))
        return cards

    def get_hand(self):
        return self.hand_cards

    @staticmethod
    def init_character(character_list, char_pack):
        char_list = []
        for index, character_name in enumerate(character_list):
            char_list.append(Character(character_name, char_pack))
        return char_list

    def get_character(self):
        return self.characters

    def choose_character(self, character):
        if self.check_character_alive(character):
            self.current_character = character
            self.characters[self.current_character].is_active = True
            return True
        else:
            return False

    def check_character_alive(self, index):
        if self.characters[index].alive:
            return True
        else:
            return False

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
            old_index = self.current_character
            if self.choose_character(new_character_index):
                self.characters[old_index].is_active = False
                return True
            else:
                return False

    def auto_change_active(self, change_direction):
        suppose_index = self.current_character + change_direction
        while True:
            state = self.choose_character(suppose_index % len(self.characters))
            if state:
                break
            else:
                suppose_index += change_direction

    def get_standby_obj(self):
        if self.current_character is not None:
            characters = self.characters[self.current_character+1:] + self.characters[:self.current_character]
            standby = []
            for char in characters:
                if char.alive:
                    standby.append(char)
            return standby

    def get_no_self_obj(self, character: Character):
        if character in self.characters:
            character_index = self.characters.index(character)
            characters = self.characters[character_index + 1:] + self.characters[:character_index]
            other = []
            for char in characters:
                if char.alive:
                    other.append(char)
            return other

    def get_active_first_obj(self):
        if self.current_character is not None:
            characters = self.characters[self.current_character:] + self.characters[:self.current_character]
            alive_char = []
            for char in characters:
                if char.alive:
                    alive_char.append(char)
            return alive_char

    def roll(self, extra_num = 0, fixed_dice = None):
        if fixed_dice is not None:
            fixed_num = len(fixed_dice)
            for dice in fixed_dice:
                self.append_special_dice(dice)
        else:
            fixed_num = 0
        for i in range(self.dice_num + extra_num - fixed_num):
            self.append_random_dice()

    def get_dice(self):
        return self.dices

    def append_random_dice(self):
        self.dices.append(Dice())
        self.dices[-1].roll()

    def append_base_dice(self):
        self.dices.append(Dice())
        self.dices[-1].roll_base()

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

    def append_hand_card(self, card_name):
        self.hand_cards.append(Card(card_name, self.card_pack))

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
        active_energy = active_obj.get_energy()
        active_element = active_obj.element.name
        team_element = []
        for character in self.characters:
            if character.alive:
                team_element.append(character.element.name)
        team_element = list(set(team_element))
        count_dice = {}
        dice_type = []
        for dice in self.dices:
            dice_type.append(ElementType(dice.element).name)
        for dice in set(dice_type):
            count_dice[dice] = dice_type.count(dice)
        count_dice.setdefault("OMNI", 0) # 方便之后的逻辑
        cost = self.sort_cost(cost)
        real_cost = {}
        for cost_type, cost_num in cost.items():
            if cost_type == "ENERGY":
                if active_energy < cost_num:
                    return False
                real_cost.update({"ENERGY": cost_num})
            elif cost_type in ElementType.__members__:
                if cost_type in count_dice:
                    if cost_num <= count_dice[cost_type]:
                        count_dice[cost_type] -= cost_num
                        real_cost.setdefault(cost_type, 0)
                        real_cost[cost_type] += cost_num
                    else:
                        if count_dice["OMNI"] + count_dice[cost_type] >= cost_num:
                            real_cost.setdefault(cost_type, 0)
                            real_cost[cost_type] += count_dice[cost_type]
                            count_dice["OMNI"] -= cost_num - count_dice[cost_type]
                            real_cost.setdefault("OMNI", 0)
                            real_cost["OMNI"] += cost_num - count_dice[cost_type]
                            continue
                        return False
                else:
                    if count_dice["OMNI"] >= cost_num:
                        count_dice["OMNI"] -= cost_num
                        real_cost.setdefault("OMNI", 0)
                        real_cost["OMNI"] += cost_num
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
                        if element == active_element:
                            score += -1
                        elif element in team_element:
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
        if len(self.summons) >= self.max_summon:
            return "remove"
        now_summon_name = self.get_summon_name()
        new_summon = Summon(summon_name)
        if summon_name in now_summon_name:
            index = now_summon_name.index(summon_name)
            summon_obj = self.summons[index]
            if summon_obj.stack > summon_obj.usage:
                if summon_obj.usage <= new_summon.usage:
                    summon_obj.usage = min(summon_obj.usage + new_summon.usage, summon_obj.stack)
                summon_obj.modifies = new_summon.modifies
            else:
                summon_obj.usage = max(summon_obj.usage, new_summon.usage)
        else:
            self.summons.append(new_summon)
        return True

    def remove_summon(self, summon_index):
        self.summons.pop(summon_index)

    def get_summon_name(self):
        summon_name_list = []
        for summon in self.summons:
            summon_name_list.append(summon.get_name())
        return summon_name_list

    def get_summon_by_name(self, summon_name):
        for summon in self.summons:
            if summon_name == summon.get_name():
                return summon

    def trigger_summon(self, summon: Summon, consume_usage):
        summon_state = summon.consume_usage(consume_usage)
        if summon_state == "remove":
            return "remove"

    def get_card_obj(self, index):
        return self.hand_cards[index]

    def add_support(self, card: Card):
        if self.is_support_reach_limit():
            return "remove"
        else:
            self.supports.append(card)
            return True

    def remove_support(self, support_index):
        self.supports.pop(support_index)

    def is_support_reach_limit(self):
        if len(self.supports) >= self.max_support:
            return True
        else:
            return False

    def get_support_name(self):
        name_list = []
        for support in self.supports:
            name_list.append(support.get_name())
        return name_list

    def get_character_nation(self):
        nation_list = []
        for character in self.characters:
            nation_list.append(character.nation)
        return nation_list

    def get_most_hurt_standby(self):
        characters = self.get_standby_obj()
        hp_list = []
        for character in characters:
            hp_list.append(character.get_hurt())
        max_value = max(hp_list)
        if max_value == 0:
            return False
        else:
            return characters[characters.index(max_value)]

    def clear_character_saturation(self):
        for character in self.characters:
            character.cleat_saturation()

player_config = read_json("config.json")["Player"]