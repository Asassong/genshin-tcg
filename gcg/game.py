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
from player import Player
from character import Character
from enums import ElementType, PlayerAction, GameStage, TimeLimit, EffectObj
from utils import read_json, pre_check, DuplicateDict
from typing import Union
from modify_manager import add_modify, invoke_modify, remove_modify, consume_modify_usage


class Game:
    def __init__(self, mode):
        self.config = read_json("config.json")
        game_config = self.config["Game"][mode]
        self.round = 0
        self.players: list[Player] = self.init_player(game_config["Player"], game_config["enable_deck"], game_config["enable_character"])
        self.first_player: int = -1
        self.init_card_num = game_config["init_card_num"]
        self.switch_hand_times = game_config["switch_hand_times"]
        self.switch_dice_times = game_config["switch_dice_times"]
        self.stage = GameStage.NONE
        self.state_dict = read_json("state.json")
        self.now_player = None
        self.max_round = game_config["max_round"]
        self.dead_info: set = set()

    @staticmethod
    def init_player(player_list, card_pack, char_pack):
        players = []
        for player in player_list:
            players.append(Player(player, card_pack, char_pack))
        return players

    def start_game(self):
        self.stage = GameStage.GAME_START
        for player in self.players:
            player.draw(self.init_card_num)
            for _ in range(self.switch_hand_times):
                drop_cards = self.ask_player_redraw_card(player)
                player.redraw(drop_cards)
                card_info = self.get_player_hand_card_info(player)
                s_card_info = ",".join(card_info)
                print("%s, 您的手牌为 %s" % (player.name, s_card_info))
            while True:
                character_index = self.ask_player_choose_character(player)
                state = player.choose_character(character_index)
                if state:
                    break
                else:
                    print("无法切换目标角色")
        self.invoke_passive_skill()
        self.first_player = random.randint(0, len(self.players) - 1)
        self.start()

    def invoke_passive_skill(self):
        for player in self.players:
            self.now_player = self.players.index(player)
            characters = player.get_character()
            for character in characters:
                passive_skills = character.get_passive_skill()
                for passive in passive_skills:
                    self.handle_skill(character, passive)

    def start(self):
        while True:
            self.round += 1
            self.stage = GameStage.ROUND_START
            self.stage = GameStage.ROLL
            self.roll_stage()
            self.stage = GameStage.ACTION
            self.action_stage()
            self.stage = GameStage.ROUND_END
            self.end_stage()
            if self.stage == GameStage.GAME_END:
                break

    def roll_stage(self):
        for player in self.players:
            self.now_player = self.players.index(player)
            roll_effect = invoke_modify(self, "roll", None)
            if "FIXED_DICE" in roll_effect:
                player.roll(fixed_dice=roll_effect["FIXED_DICE"])
                roll_effect.pop("FIXED_DICE")
            else:
                player.roll()
            extra_switch_times = 0
            if "REROLL" in roll_effect:
                if isinstance(roll_effect["REROLL"], str):
                    extra_switch_times += eval(roll_effect["REROLL"])
                    roll_effect.pop("REROLL")
            for _ in range(self.switch_dice_times + extra_switch_times):
                indexes = self.ask_player_reroll_dice(player)
                player.reroll(indexes)
                dice_type = self.get_player_dice_info(player)
                s_dice_type = " ".join(dice_type)
                print("%s, 您的骰子为 %s" % (player.name, s_dice_type))

    def action_stage(self):
        for player in self.players:
            player.round_has_end = False
        self.now_player = self.first_player
        while True:
            if self.stage == GameStage.GAME_END:
                break
            round_has_end = True
            action_type = None
            for player in self.players:
                if player.round_has_end:
                    continue
                else:
                    round_has_end = False
                    break
            if round_has_end:
                break
            now_player = self.players[self.now_player]
            if not now_player.round_has_end:
                active = now_player.get_active_character_obj()
                for modify_name, modify in active.modifies.copy().items():
                    consume_state = consume_modify_usage(modify, "act")
                    if consume_state == "remove":
                        remove_modify(active.modifies, modify_name)
                action_effect = invoke_modify(self, "action", active)
                if "USE_SKILL" in action_effect:
                    self.handle_skill(active, action_effect["USE_SKILL"])
                    action_effect.pop("USE_SKILL")
                action = self.ask_player_action(now_player)
                if PlayerAction(action) == PlayerAction.END_ROUND:
                    others_had_end = False
                    for player in self.players:
                        if player.round_has_end:
                            others_had_end = True
                            break
                    now_player.round_has_end = True
                    if not others_had_end:
                        self.first_player = self.now_player
                elif PlayerAction(action) == PlayerAction.ELEMENT_TUNING:
                    self.element_tuning(now_player)
                elif PlayerAction(action) == PlayerAction.CHANGE_CHARACTER:
                    change_state = self.player_change_avatar(now_player)
                    print(("change_state", change_state))
                    if not change_state:
                        continue
                    elif change_state == "fast":
                        action_type = "fast"
                elif PlayerAction(action) == PlayerAction.USING_SKILLS:
                    use_state = self.use_skill(now_player)
                    if not use_state:
                        continue
                elif PlayerAction(action) == PlayerAction.PLAY_CARD:
                    self.play_card(now_player)
                if action_type is not None:
                    if action_type == "fast":
                        continue
                    else:
                        self.now_player = (self.now_player + 1) % len(self.players)
                else:
                    judge_action_type = self.judge_action(action)
                    if judge_action_type == "fast":
                        continue
                    else:
                        self.now_player = (self.now_player + 1) % len(self.players)
            else:
                self.now_player = (self.now_player + 1) % len(self.players)

    def end_stage(self):
        self.now_player = self.first_player
        for _ in range(len(self.players)):
            player = self.players[self.now_player]
            end_stage_effect = invoke_modify(self, "end_c", None, player)
            self.handle_extra_effect("end", end_stage_effect)
            for summon in player.summons.copy():
                for effect, value in player.trigger_summon(summon, 1):
                    if effect == "damage":
                        self.handle_damage(summon, "team", value)
            if self.stage == GameStage.GAME_END:
                break
            end_stage_effect = invoke_modify(self, "end_s", player.get_active_character_obj(), player)
            self.handle_extra_effect("end", end_stage_effect)
            player.dices.clear()
            player.draw(2)
            player.clear_character_saturation()
            self.now_player = (self.now_player + 1) % len(self.players)
        self.round_end_consume_modify()

    def get_now_player(self):
        return self.players[self.now_player]

    def get_oppose(self):
        return self.players[~self.now_player]

    @staticmethod
    def judge_input(input_, min_, max_):
        valid = []
        for each in input_:
            if each.isdigit():
                if min_ <= int(each) <= max_:
                    valid.append(int(each))
                else:
                    break
            else:
                break
        if len(list(set(valid))) == len(input_):
            return valid
        elif input_ == [""]:
            return []
        else:
            return False

    @staticmethod
    def judge_action(action_index):
        if action_index in [1, 3, 4]:
            return "combat"
        else:
            return "fast"

    @staticmethod
    def get_player_hand_card_info(player: Player) -> list[str]:
        hand = player.get_hand()
        card_info = []
        for card in hand:
            card_info.append(card.get_name())
        return card_info

    @staticmethod
    def get_player_character_info(player:Player) -> tuple[list[str], str]:
        character = player.get_character()
        names = []
        for c in character:
            names.append(c.name)
        active = player.get_active_character_name()
        return names, active

    @staticmethod
    def get_player_dice_info(player: Player) -> list[str]:
        dices = player.get_dice()
        dice_type = []
        for dice in dices:
            dice_type.append(ElementType(dice.element).name)
        return dice_type

    @staticmethod
    def get_player_character_detail(player: Player) -> str:
        character = player.get_character()
        detail = ""
        for c in character:
            detail += c.get_card_info()
        return detail

    def ask_player_redraw_card(self, player: Player):
        # TODO
        card_info = self.get_player_hand_card_info(player)
        s_card_info = ",".join(card_info)
        while True:
            print("%s, 您的手牌为 %s" % (player.name, s_card_info))
            index = input("请选择要重抽的卡牌(0-%d, 空格隔开):" % (len(card_info) - 1))
            indexes = index.split(" ")
            drop_cards = self.judge_input(indexes, 0, len(card_info) - 1)
            if drop_cards or drop_cards == []:
                break
            else:
                print("输入格式错误，请重输")
        return drop_cards

    def ask_player_choose_card(self, player: Player):
        card_info = self.get_player_hand_card_info(player)
        s_card_info = ",".join(card_info)
        while True:
            print("%s, 您的手牌为 %s" % (player.name, s_card_info))
            index = input("请选择要打出的卡牌(0-%d):" % (len(card_info) - 1))
            card = self.judge_input(index, 0, len(card_info) - 1)
            if len(card) == 1:
                break
            else:
                print("输入格式错误，请重输")
        return card[0]

    def ask_player_choose_character(self, player: Player):
        # TODO
        names, _ = self.get_player_character_info(player)
        s_name = " ".join(names)
        while True:
            print("%s,您的角色为 %s" % (player.name, s_name))
            index = input("请选择一个角色(0-2)：")
            indexes = self.judge_input([index], 0, 2)
            if isinstance(indexes, list):
                if len(indexes) == 1:
                    break
                else:
                    print("输入格式错误，请重输")
            else:
                print("输入格式错误，请重输")
        return int(index)

    def ask_player_reroll_dice(self, player):
        # TODO
        dice_type = self.get_player_dice_info(player)
        s_dice_type = " ".join(dice_type)
        while True:
            print("%s, 您的骰子为 %s" % (player.name, s_dice_type))
            index = input("请选择要更换的骰子(0-%d, 空格隔开):" % (len(dice_type) - 1))
            indexes = index.split(" ")
            valid_index = self.judge_input(indexes, 0, len(dice_type) - 1)
            if valid_index or valid_index == []:
                break
            else:
                print("输入格式错误，请重输")
        return valid_index

    def ask_player_action(self, player: Player):
        # TODO
        dice_type = self.get_player_dice_info(player)
        s_dice_type = " ".join(dice_type)
        card_info = self.get_player_hand_card_info(player)
        s_card_info = ",".join(card_info)
        names, active = self.get_player_character_info(player)
        s_name = " ".join(names)
        summon_name = player.get_summon_name()
        s_summon_name = ",".join(summon_name)
        support = player.get_support_name()
        s_support_name = ",".join(support)
        detail = self.get_player_character_detail(player)
        # TODO 不一定只有两个玩家
        oppose = self.players[~self.players.index(player)]
        oppose_dices = len(oppose.get_dice())
        oppose_cards = len(oppose.get_hand())
        oppose_summon = oppose.get_summon_name()
        s_oppose_summon = ",".join(oppose_summon)
        oppose_support = oppose.get_support_name()
        s_oppose_support = ",".join(oppose_support)
        oppose_names, oppose_active = self.get_player_character_info(oppose)
        oppose_detail = self.get_player_character_detail(oppose)
        while True:
            print("您的对手手牌%d张，骰子%d个，角色为 %s, %s出战" % (oppose_cards, oppose_dices, oppose_names, oppose_active))
            print("您对手的召唤物为 %s" % s_oppose_summon)
            print("您对手的支援卡为 %s" % s_oppose_support)
            print(oppose_detail)
            print("%s" % player.name)
            print("您的骰子为 %s" % s_dice_type)
            print("您的手牌为 %s" % s_card_info)
            print("您的角色为 %s, %s 出战" % (s_name, active))
            print("您的召唤物为 %s" % s_summon_name)
            print("您的支援卡为 %s" % s_support_name)
            print(detail)
            action = input("请选择要进行的操作\n1.使用角色技能2.元素调和3.结束回合4.切换角色5.打出卡牌")
            valid_action = self.judge_input(action, 1, 5)
            if isinstance(valid_action, list):
                if len(valid_action) == 1:
                    break
                else:
                    print("输入格式错误，请重输")
            else:
                print("输入格式错误，请重输")
        return valid_action[0]

    def ask_player_remove_summon(self, player: Player):
        summon = player.get_summon_name()
        s_summon = ",".join(summon)
        while True:
            print("%s" % player.name)
            print("您的召唤物为 %s" % s_summon)
            index = input("请选择要移除的召唤物(0-%d, 空格隔开):" % (len(summon) - 1))
            valid_index = self.judge_input(index, 0, len(summon) - 1)
            if len(valid_index) == 1:
                break
            else:
                print("输入格式错误，请重输")
        return valid_index[0]

    def ask_player_remove_support(self, player: Player):
        support = player.get_support_name()
        s_support = ",".join(support)
        while True:
            print("%s" % player.name)
            print("您的支援卡为 %s" % s_support)
            index = input("请选择要移除的支援卡(0-%d, 空格隔开):" % (len(support) - 1))
            valid_index = self.judge_input(index, 0, len(support) - 1)
            if len(valid_index) == 1:
                break
            else:
                print("输入格式错误，请重输")
        return valid_index[0]

    def element_tuning(self, player: Player):
        card_info = self.get_player_hand_card_info(player)
        s_card_info = ",".join(card_info)
        dice_type = self.get_player_dice_info(player)
        s_dice_type = " ".join(dice_type)
        while True:
            print("您的骰子为 %s" % s_dice_type)
            print("您的手牌为 %s" % s_card_info)
            dice_index = input("请选择要更换的骰子(0-%d):" % (len(dice_type) - 1))
            valid_dice_index = self.judge_input([dice_index], 0, len(dice_type) - 1)
            if isinstance(valid_dice_index, list):
                if len(valid_dice_index) != 1:
                    print("输入格式错误，请重输")
                    continue
            else:
                print("输入格式错误，请重输")
                continue
            card_index = input("请选择要弃置的卡牌(0-%d):" % (len(card_info) - 1))
            drop_card = self.judge_input(card_index, 0, len(card_info) - 1)
            if isinstance(drop_card, list):
                if len(drop_card) == 1:
                    break
                else:
                    print("输入格式错误，请重输")
            else:
                print("输入格式错误，请重输")
        player.remove_dice(valid_dice_index[0])
        element = player.get_active_character_obj().element
        player.append_special_dice(element)
        player.remove_hand_card(drop_card[0])

    def no_skill_cost(self, cost):
        player = self.get_now_player()
        dice_type = self.get_player_dice_info(player)
        s_dice_type = " ".join(dice_type)
        print("%s, 您的骰子为 %s" % (player.name, s_dice_type))
        cost_state = player.check_cost(cost)
        if cost_state:
            cost_indexes = []
            for key, value in cost_state.items():
                start_index = 0
                for _ in range(value):
                    new_index = dice_type.index(key, start_index)
                    cost_indexes.append(new_index)
                    start_index = new_index + 1
            print("将消耗以下编号骰子：%s" % str(cost_indexes))
            operation = input("enter确认，q取消，或输入序号更换")
            if operation == "":
                player.use_dices(cost_indexes)
            elif operation == "q":
                return False
            else:
                indexes = operation.split(" ")
                valid_dice_index = self.judge_input(indexes, 0, len(dice_type) - 1)
                if valid_dice_index:
                    check_result = player.recheck_cost(cost, valid_dice_index)
                    if check_result:
                        player.use_dices(valid_dice_index)
                    else:
                        print("输入格式错误")
                        return False
                else:
                    print("输入格式错误")
                    return False
        elif cost_state == {}:
            pass
        else:
            print("费用不足")
            return False
        return True

    def player_change_avatar(self, player: Player):
        normal_cost = {"ANY": 1}
        change_action = "combat"
        active = player.get_active_character_obj()
        new_active = self.ask_player_choose_character(player)
        if player.check_character_alive(new_active):
            change_cost_effect = invoke_modify(self, "change_cost", active, cost=normal_cost, change_from=active, change_to=player.characters[new_active])
            cost_state = self.no_skill_cost(change_cost_effect["cost"])
            change_cost_effect.pop("cost")
            if cost_state:
                change_action_effect = invoke_modify(self, "change", active, change_from=active, change_to=player.characters[new_active])
                if "change_action" in change_action_effect:
                    change_action = change_action_effect["change_action"]
                player.choose_character(new_active)
            else:
                return False
        else:
            return False
        return change_action

    def use_skill(self, player: Player):
        active = player.get_active_character_obj()
        skill_names = active.get_skills_name()
        s_skill_names = ",".join(skill_names)
        while True:
            print("您的出战角色技能如下：%s" % s_skill_names)
            skill = input("请选择要使用的技能(0-%d):" % (len(skill_names) - 1))
            skill_index = self.judge_input([skill], 0, len(skill_names) - 1)
            if isinstance(skill_index, list):
                if len(skill_index) == 1:
                    break
                else:
                    print("输入格式错误，请重输")
            else:
                print("输入格式错误，请重输")
        skill_name = skill_names[skill_index[0]]
        use_state = self.handle_skill(active, skill_name)
        if use_state:
            return True
        else:
            return False

    def skill_cost(self, skill_cost):
        # TODO
        player = self.get_now_player()
        active = player.get_active_character_obj()
        state = player.check_cost(skill_cost)
        if state:
            dice_type = self.get_player_dice_info(player)
            s_dice_type = " ".join(dice_type)
            print("%s, 您的骰子为 %s" % (player.name, s_dice_type))
            use_energy = -1
            if "ENERGY" in state:
                use_energy = state["ENERGY"]
            cost_indexes = []
            for key, value in state.items():
                if key != "ENERGY":
                    start_index = 0
                    for _ in range(value):
                        new_index = dice_type.index(key, start_index)
                        cost_indexes.append(new_index)
                        start_index = new_index + 1
            print("将消耗以下编号骰子：%s" % str(cost_indexes))
            operation = input("enter确认，q取消，或输入序号更换")
            if operation == "":
                player.use_dices(cost_indexes)
                if use_energy != -1:
                    active.change_energy(-use_energy)
            elif operation == "q":
                return False
            else:
                valid_dice_index = self.judge_input([operation], 0, len(dice_type) - 1)
                if valid_dice_index:
                    check_result = player.recheck_cost(skill_cost, valid_dice_index)
                    if check_result:
                        player.use_dices(valid_dice_index)
                        if use_energy != -1:
                            active.change_energy(-use_energy)
                    else:
                        print("输入格式错误")
                        return False
                else:
                    print("输入格式错误")
                    return False
        elif state == {}:
            pass
        else:
            print("费用不足")
            return False
        return True

    def play_card(self, player: Player):
        index = self.ask_player_choose_card(player)
        card = player.get_card_obj(index)
        effect_obj = card.effect_obj
        card_cost = card.get_cost().copy()
        state = player.check_cost(card_cost)
        if state or state == {}:
            obj = None
            if effect_obj == "select":
                char_index = self.ask_player_choose_character(player)
                obj = player.characters[char_index]
            elif effect_obj == "summon":
                summon_index = self.ask_player_remove_summon(player)
                obj = player.summons[summon_index]
            elif effect_obj == "oppose":
                oppose = self.players[~self.now_player]
                char_index = self.ask_player_choose_character(oppose)
                obj = player.characters[char_index]
            elif effect_obj == "oppose_summon":
                oppose = self.players[~self.now_player]
                summon_index = self.ask_player_remove_summon(oppose)
                obj = player.summons[summon_index]
            elif effect_obj == "all_summon":
                pass
            elif effect_obj == "player":
                pass
            elif isinstance(effect_obj, list):
                pass
            if card.combat_limit:
                pass
            tag = card.tag
            if "Location" in tag or "Companion" in tag or "Item" in tag:
                for add_state in player.add_support(card):
                    if add_state == "remove":
                        index = self.ask_player_remove_support(player)
                        player.remove_support(index)
            elif "Food" in tag:
                if isinstance(obj, Character):
                    if obj.get_saturation() < player.max_character_saturation:
                        obj.change_saturation("+1")
                    else:
                        return False
                else:
                    return False
            elif "Weapon" in tag:
                if isinstance(obj, Character):
                    if obj.weapon not in tag:
                        return False
                else:
                    return False
            if card.use_skill:
                cost_state = self.skill_cost(card_cost)
            else:
                cost_state = self.no_skill_cost(card_cost)
            if not cost_state:
                return False
            player.remove_hand_card(index)
            modifies, modify_name = card.init_modify()
            if "Weapon" in tag or "Artifact" in tag or "Talent" in tag:
                if isinstance(obj, Character):
                    equip = list(set(tag) & {"Weapon", "Artifact", "Talent"})[0].lower()
                    if obj.equipment[equip] is not None:
                        remove_modify(obj.modifies, obj.equipment[equip], "main")
                    obj.equipment[equip] = card.get_name()
                    add_modify(self, obj, modifies, modify_name)
            else:
                add_modify(self, card, modifies, modify_name)
            if card.use_skill:
                self.handle_skill(self.get_now_player().get_active_character_obj(), card.use_skill)
        else:
            print("费用不足")
            return False
        return True


    def handle_skill(self, invoker, skill_name):
        skill_detail = invoker.get_skill_detail(skill_name)
        skill_cost = skill_detail["cost"].copy()
        skill_type = skill_detail["type"]
        if "Normal Attack" in skill_type or "Elemental Skill" in skill_type:
            add_energy = 1
        else:
            add_energy = 0
        use_skill_effect = invoke_modify(self, "use_skill", invoker, skill_name=skill_name, skill_type=skill_type, cost=skill_cost, add_energy=add_energy)
        if "add_energy" in use_skill_effect:
            invoker.change_energy(use_skill_effect["add_energy"])
            use_skill_effect.pop("add_energy")
        else:
            invoker.change_energy(add_energy)
        if "cost" in use_skill_effect:
            real_cost = use_skill_effect["cost"]
            # TODO 万一不用技能了，modify就白调了
            cost_state = self.skill_cost(real_cost)
            use_skill_effect.pop("cost")
        else:
            cost_state = self.skill_cost(skill_cost)
        if not cost_state:
            return False
        left_effect = self.handle_extra_effect("use_skill", use_skill_effect)
        if "modify" in skill_detail:
            add_modify(self, invoker, skill_detail["modify"], skill_name)
        if "damage" in skill_detail:
            self.handle_damage(invoker, "team", skill_detail["damage"], skill_type=skill_type, skill_name=skill_name, left_effect=left_effect)
        if "create" in skill_detail:
            self.handle_state(invoker, skill_detail["create"])
        if "summon" in skill_detail:
            self.handle_summon(self.get_now_player(), skill_detail["summon"])
        return True

    def handle_damage(self, attacker, attackee: Union[str, Character], damage: dict[str, int], **kwargs):
        oppose = self.get_oppose()
        extra_attack = []
        if attackee == "team":
            oppose_active = oppose.get_active_character_obj()
        else:
            oppose_active = attackee
        for element_type, init_damage in damage.items():
            if element_type in ElementType.__members__:
                effects: list[dict] = self.handle_element_reaction(oppose_active, element_type)
                reaction = None
                for effect in effects:
                    for key, value in effect.items():
                        if key == element_type:
                            init_damage += eval(effect[key])
                        elif key in ["HYDRO_DMG", "GEO_DMG", "ELECTRO_DMG","DENDRO_DMG", "PYRO_DMG", "PHYSICAL_DMG",
                                    "CRYO_DMG", "ANEMO_DMG", "PIERCE_DMG"]:
                            extra_attack.append({key.replace("_DMG", ""): value})
                attack_effect = invoke_modify(self, "attack", attacker, **kwargs, reaction=reaction, damage=init_damage, element=element_type)
                damage = attack_effect["damage"]
                attack_effect.pop("damage")
                self.handle_extra_effect("attack", attack_effect)
                attackee_effect = invoke_modify(self, "defense", oppose_active, **kwargs, reaction=reaction, hurt=damage,
                                              element=element_type)
                hurt = attackee_effect["hurt"]
                attackee_effect.pop("hurt")
                self.handle_extra_effect("defense", attackee_effect)
                shield_effect = invoke_modify(self, "shield", oppose_active, **kwargs, hurt=hurt)
                hurt = shield_effect["hurt"]
                oppose_state = oppose_active.change_hp(-hurt)
                if oppose_state == "die":
                    self.handle_oppose_dead(oppose)
            elif element_type == "PHYSICAL":
                infusion_effect = invoke_modify(self, "infusion", attacker, **kwargs)
                if "infusion" in infusion_effect:
                    infusion = infusion_effect["infusion"]
                    infusion_effect.pop("infusion")
                    left_effect = self.handle_extra_effect("infusion", infusion_effect)
                    self.handle_damage(attacker, attackee, {infusion: init_damage}, **kwargs, left_effect=left_effect)
                else:
                    attack_effect = invoke_modify(self, "attack", attacker, **kwargs, reaction=None,
                                                  damage=init_damage, element=element_type)
                    damage = attack_effect["damage"]
                    attack_effect.pop("damage")
                    self.handle_extra_effect("attack", attack_effect)
                    attackee_effect = invoke_modify(self, "defense", oppose_active, **kwargs, reaction=None,
                                                    hurt=damage, element=element_type)
                    hurt = attackee_effect["hurt"]
                    attackee_effect.pop("hurt")
                    self.handle_extra_effect("defense", attackee_effect)
                    shield_effect = invoke_modify(self, "shield", oppose_active, **kwargs, hurt=hurt)
                    hurt = shield_effect["hurt"]
                    oppose_state = oppose_active.change_hp(-hurt)
                    if oppose_state == "die":
                        self.handle_oppose_dead(oppose)
            elif element_type == "PIERCE":
                if attackee == "team":
                    oppose_standby = oppose.get_standby_obj()
                else:
                    oppose_standby = [attackee]
                # TODO 穿透伤害不能改变伤害，但是可能有其他效果
                for obj in oppose_standby:
                    oppose_state = obj.change_hp(-init_damage)
                    if oppose_state == "die":
                        self.handle_oppose_dead(oppose)
        if extra_attack:
            oppose_other = oppose.get_character().copy().remove(attackee)
            for key, value in extra_attack:
                for standby in oppose_other:
                    self.handle_damage(attacker, standby, {key: value})
        extra_effect = invoke_modify(self, "extra", attacker, None)
        if "extra_attack" in extra_effect:
            for element, damage in extra_effect["extra_attack"]:
                self.handle_damage(attacker, "team", {element: damage})


    def handle_oppose_dead(self, oppose: Player):
        end = True
        for index in range(len(oppose.get_character())):
            if oppose.check_character_alive(index):
                end = False
                break
        if end:
            self.stage = GameStage.GAME_END
        else:
            self.ask_player_choose_character(oppose)
            self.dead_info.add(oppose)

    def handle_state(self, invoker: Character, combat_state):
        # TODO modify修改modify
        for state_name, num in combat_state.items():
            modify = self.state_dict[state_name]["modify"]
            for _ in range(num):
                add_modify(self, invoker, modify, state_name)

    def handle_summon(self, player: Player, summon_dict: dict):
        for summon_name, num in summon_dict.items():
            for _ in range(num):
                for add_state in player.add_summon(summon_name):
                    if add_state == "remove":
                        index = self.ask_player_remove_summon(player)
                        player.remove_summon(index)
                summon_obj = player.summons[-1]
                summon_modify = summon_obj.init_modify()
                if summon_modify is not None:
                    modifies, summon = summon_modify
                    add_modify(self, summon_obj, modifies, summon)

    def handle_element_reaction(self, trigger_obj: Character, element, type_="oppose"):
        trigger_obj.application.append(ElementType[element])
        applied_element = set(trigger_obj.application)
        effect = []
        # 反应顺序还需进一步测试
        if {ElementType.CRYO, ElementType.PYRO}.issubset(applied_element):
            applied_element.remove(ElementType.CRYO)
            applied_element.remove(ElementType.PYRO)
            effect.append({"CRYO": "+2", "PYRO": "+2", "reaction": "MELT"})
        elif {ElementType.HYDRO, ElementType.PYRO}.issubset(applied_element):
            applied_element.remove(ElementType.PYRO)
            applied_element.remove(ElementType.HYDRO)
            effect.append({"HYDRO": "+2", "PYRO": "+2", "reaction": "VAPORIZE"})
        elif {ElementType.ELECTRO, ElementType.PYRO}.issubset(applied_element):
            applied_element.remove(ElementType.ELECTRO)
            applied_element.remove(ElementType.PYRO)
            effect.append({"ELECTRO": "+2", "PYRO": "+2", "reaction": "OVERLOADED"})
            if type_ == "oppose":
                add_modify(self, trigger_obj, [{"category": "extra", "condition":["IS_ACTIVE"], "effect":{"CHANGE_CHARACTER": -1}, "effect_obj":"OPPOSE", "time_limit":{"IMMEDIATE": 1}}], "OVERLOADED")
            else:
                add_modify(self, trigger_obj, [
                    {"category": "extra", "condition": ["IS_ACTIVE"], "effect": {"CHANGE_CHARACTER": -1},
                     "effect_obj": "ALL", "time_limit": {"IMMEDIATE": 1}}], "OVERLOADED")
        elif {ElementType.HYDRO, ElementType.CRYO}.issubset(applied_element):
            applied_element.remove(ElementType.HYDRO)
            applied_element.remove(ElementType.CRYO)
            effect.append({"HYDRO": "+1", "CRYO": "+1", "reaction": "FROZEN"})
            if type_ == "oppose":
                add_modify(self, trigger_obj, [{"category": "action", "condition":[], "effect":{"FROZEN": "TRUE"}, "effect_obj":"OPPOSE_SELF", "time_limit":{"DURATION": 1}},
                                               {"category": "defense", "condition":[["BEING_HIT_BY", "PHYSICAL", "PYRO"]], "effect":{"FROZEN": "FALSE", "HURT": "+2"}, "effect_obj":"OPPOSE_SELF", "time_limit":{"DURATION": 1}}], "FROZEN")
            else:
                add_modify(self, trigger_obj, [
                    {"category": "action", "condition": [], "effect": {"FROZEN": "TRUE"}, "effect_obj": "SELF",
                     "time_limit": {"DURATION": 1}},
                    {"category": "defense", "condition": [["BEING_HIT_BY", "PHYSICAL", "PYRO"]],
                     "effect": {"FROZEN": "FALSE", "HURT": "+2"}, "effect_obj": "SELF",
                     "time_limit": {"DURATION": 1}}], "FROZEN")
        elif {ElementType.ELECTRO, ElementType.CRYO}.issubset(applied_element):
            applied_element.remove(ElementType.CRYO)
            applied_element.remove(ElementType.ELECTRO)
            effect.append({"ELECTRO": "+1", "CRYO": "+1", "PIERCE_DMG": 1, "reaction": "SUPER_CONDUCT"})
        elif {ElementType.ELECTRO, ElementType.HYDRO}.issubset(applied_element):
            applied_element.remove(ElementType.ELECTRO)
            applied_element.remove(ElementType.HYDRO)
            effect.append({"ELECTRO": "+1", "HYDRO": "+1", "PIERCE_DMG": 1, "reaction": "ELECTRO_CHARGE"})
        elif {ElementType.DENDRO, ElementType.PYRO}.issubset(applied_element):
            applied_element.remove(ElementType.DENDRO)
            applied_element.remove(ElementType.PYRO)
            effect.append({"DENDRO": "+1", "PYRO": "+1", "reaction": "BURNING"})
            if type_ == "oppose":
                self.handle_summon(self.get_now_player(), {"Burning Flame": 1})
            else:
                self.handle_summon(self.get_oppose(), {"Burning Flame": 1})
        elif {ElementType.DENDRO, ElementType.HYDRO}.issubset(applied_element):
            applied_element.remove(ElementType.DENDRO)
            applied_element.remove(ElementType.HYDRO)
            effect.append({"DENDRO": "+1", "HYDRO": "+1", "reaction": "BLOOM"})
            if type_ == "oppose":
                self.handle_state(self.get_now_player().get_active_character_obj(), {"Dendro Core": 1})
            else:
                self.handle_state(self.get_oppose().get_active_character_obj(), {"Dendro Core": 1})
        elif {ElementType.DENDRO, ElementType.ELECTRO}.issubset(applied_element):
            applied_element.remove(ElementType.DENDRO)
            applied_element.remove(ElementType.ELECTRO)
            effect.append({"DENDRO": "+1", "ELECTRO": "+1", "reaction": "CATALYZE"})
            if type_ == "oppose":
                self.handle_state(self.get_now_player().get_active_character_obj(), {"Catalyzing Field": 2})
            else:
                self.handle_state(self.get_oppose().get_active_character_obj(), {"Catalyzing Field": 2})
        elif ElementType.ANEMO in applied_element:
            applied_element.remove(ElementType.ANEMO)
            elements = list(applied_element)
            for element in elements:
                if element != ElementType.DENDRO:
                    applied_element.remove(element)
                    effect.append({element.name + "_DMG": 1, "reaction": "SWIRL", "swirl_element": element.name})
                    break
        elif ElementType.GEO in applied_element:
            applied_element.remove(ElementType.GEO)
            elements = list(applied_element)
            for element in elements:
                if element != ElementType.DENDRO:
                    applied_element.remove(element)
                    effect.append({"GEO": "+1", "reaction": "CRYSTALLIZE", "crystallize_element": element.name})
                    add_modify(self, trigger_obj, [{"category": "shield", "condition":[], "effect":{"SHIELD": 1}, "effect_obj":"ACTIVE", "time_limit":{"USE_UP": 1}, "stack": 2 ,"repeated": "True"}], "CRYSTALLIZE")
                    break
        trigger_obj.application = list(applied_element)
        return effect

    def handle_extra_effect(self, operation, effect: dict):
        player = self.get_now_player()
        oppose = self.get_oppose()
        left_effect = {}
        for effect_type, effect_value in effect.items():
            if effect_type == "extra_effect":
                for each in effect_value:
                    extra_effect, effect_obj = each
                    if effect_obj == "PLAYER":
                        if "DRAW_CARD" in extra_effect:
                            card = extra_effect["DRAW_CARD"]
                            if isinstance(card, int):
                                player.draw(card)
                            else:
                                if card.startswith("TYPE_"):
                                    card_type = card.replace("TYPE_", "")
                                    player.draw_type(card_type)
                        elif "ADD_CARD" in extra_effect:
                            player.append_hand_card(extra_effect["ADD_CARD"])
                        elif "APPEND_DICE" in extra_effect:
                            dices = extra_effect["APPEND_DICE"]
                            if isinstance(dices, list):
                                for dice in dices:
                                    if dice == "RANDOM":
                                        player.append_random_dice()
                                    elif dice == "BASE":
                                        player.append_base_dice()
                                    else:
                                        player.append_special_dice(dice)
                            else:
                                if dices == "RANDOM":
                                    player.append_random_dice()
                                elif dices == "BASE":
                                    player.append_base_dice()
                                else:
                                    player.append_special_dice(dices)
                    else:
                        if "CHANGE_CHARACTER" in extra_effect:
                            if effect_obj == "OPPOSE":
                                change_from = oppose.get_active_character_obj()
                                oppose.auto_change_active(extra_effect["CHANGE_CHARACTER"])
                                change_to = oppose.get_active_character_obj()
                                if change_from != change_to:
                                    change_action_effect = invoke_modify(self, "change", change_from,
                                                                         change_from=change_from,
                                                                         change_to=change_to, left_effect={"change_action": "fast"})
                                    self.handle_extra_effect("change", change_action_effect)
                            elif effect_obj == "ALL":
                                change_from = player.get_active_character_obj()
                                player.auto_change_active(extra_effect["CHANGE_CHARACTER"])
                                change_to = player.get_active_character_obj()
                                if change_from != change_to:
                                    change_action_effect = invoke_modify(self, "change", change_from,
                                                                         change_from=change_from,
                                                                         change_to=change_to, left_effect={"change_action": "fast"})
                                    self.handle_extra_effect("change", change_action_effect)
                        elif "HEAL" in extra_effect:
                            heal = extra_effect["HEAL"]
                            if effect_obj == "ACTIVE":
                                player.get_active_character_obj().change_hp(heal)
                            elif effect_obj == "STANDBY":
                                standby = player.get_standby_obj()
                                for obj in standby:
                                    obj.change_hp(heal)
                        elif "APPLICATION" in extra_effect:
                            element = extra_effect["APPLICATION"]
                            if effect_obj == "ACTIVE":
                                self.handle_element_reaction(player.get_active_character_obj(), element, "self")
            elif effect_type == "CHANGE_ACTION":
                if operation == "change":
                    left_effect.update({effect_type: effect_value})
            elif effect_type == "DMG":
                if operation == "use_skill" or operation == "infusion":
                    left_effect.update({effect_type: effect_value})
        return left_effect

    def round_end_consume_modify(self):
        for player in self.players:
            for character in player.characters:
                for modify_name, modify in character.modifies.copy().items():
                    consume_state = consume_modify_usage(modify_name, "end")
                    if consume_state == "remove":
                        remove_modify(character.modifies, modify_name)
            for modify_name, modify in player.team_modifier.copy().items():
                consume_state = consume_modify_usage(modify_name, "end")
                if consume_state == "remove":
                    remove_modify(player.team_modifier, modify_name)
            for summon in player.summons:
                for modify_name, modify in summon.modifies.copy().items():
                    consume_state = consume_modify_usage(modify_name, "end")
                    if consume_state == "remove":
                        remove_modify(summon.modifies, modify_name)
            for support in player.supports:
                for modify_name, modify in support.modifies.copy().items():
                    consume_state = consume_modify_usage(modify_name, "end")
                    if consume_state == "remove":
                        remove_modify(support.modifies, modify_name)



if __name__ == '__main__':
    mode = "Game1"
    state = pre_check(mode)
    if isinstance(state, list):
        error = " ".join(state)
        print("以下卡牌不合法：%s" % error)
    else:
        game = Game(mode)
        game.start_game()
