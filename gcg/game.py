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
from player import Player
from character import Character
from enums import ElementType, PlayerAction, GameStage, TimeLimit, EffectObj, EffectType
from utils import read_json, pre_check
from typing import Union


class Game:
    def __init__(self):
        self.round = 0
        self.players: list[Player] = []
        self.first_player: int = -1
        self.game_modifier = {}
        self.init_card_num = 5
        self.switch_hand_times = 1
        self.switch_dice_times = 1
        self.stage = GameStage.NONE
        self.state_dict = read_json("state.json")
        self.now_player = None

    def start_game(self):
        config = read_json("config.json")
        for key, value in config["Player"].items():
            self.players.append(Player())
            self.players[-1].name = key
            self.players[-1].init_card(value["card"])
            self.players[-1].init_character(value["character"])
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
        self.first_player = random.randint(0, len(self.players) - 1)
        self.start()

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
            player.roll()
            for _ in range(self.switch_dice_times):
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
                    if not change_state:
                        continue
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
            for effect, summon_obj, value in player.trigger_summon():
                if effect == "damage":
                    self.handle_damage(summon_obj, "team", value)
            player.dices.clear()
            player.draw(2)
            self.now_player = (self.now_player + 1) % len(self.players)

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
            card_info.append(card.name)
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
        detail = self.get_player_character_detail(player)
        # TODO 不一定只有两个玩家
        oppose = self.players[~self.players.index(player)]
        oppose_dices = len(oppose.get_dice())
        oppose_cards = len(oppose.get_hand())
        oppose_summon = oppose.get_summon_name()
        s_oppose_summon = ",".join(oppose_summon)
        oppose_names, oppose_active = self.get_player_character_info(oppose)
        oppose_detail = self.get_player_character_detail(oppose)
        while True:
            print("%s" % player.name)
            print("您的骰子为 %s" % s_dice_type)
            print("您的手牌为 %s" % s_card_info)
            print("您的角色为 %s, %s 出战" % (s_name, active))
            print("您的召唤物为 %s" % s_summon_name)
            print(detail)
            print("您的对手手牌%d张，骰子%d个，角色为 %s, %s出战" % (oppose_cards, oppose_dices, oppose_names, oppose_active))
            print("您对手的召唤物为 %s" % s_oppose_summon)
            print(oppose_detail)
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
        player = self.players[self.now_player]
        dice_type = self.get_player_dice_info(player)
        s_dice_type = " ".join(dice_type)
        print("%s, 您的骰子为 %s" % (player.name, s_dice_type))
        cost_state = player.check_cost(cost)
        if state:
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
                valid_dice_index = self.judge_input([operation], 0, len(dice_type) - 1)
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
        else:
            print("费用不足")
            return False
        return True

    def player_change_avatar(self, player: Player):
        normal_cost = {"ANY": 1}
        # TODO
        cost_state = self.no_skill_cost(normal_cost)
        if cost_state:
            new_active = self.ask_player_choose_character(player)
            state = player.change_active_character(new_active)
            if not state:
                self.player_change_avatar(player)
        else:
            return False
        return True

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
        skill_cost = active.get_skills_cost(skill_name)
        if self.skill_cost(skill_cost, skill_name):
            return True
        else:
            return False

    def skill_cost(self, skill_cost, skill_name):
        # TODO
        player = self.players[self.now_player]
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
                self.handle_skill(player, skill_name)
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
                        self.handle_skill(player, skill_name)
                    else:
                        print("输入格式错误")
                        return False
                else:
                    print("输入格式错误")
                    return False
        else:
            print("费用不足")
            return False
        return True

    def play_card(self, player: Player):
        index = self.ask_player_choose_card(player)
        card = player.get_card_obj(index)
        effect_obj = card.effect_obj
        card_cost = card.get_cost()
        state = player.check_cost(card_cost)
        if state:
            if effect_obj == "select":
                char_index = self.ask_player_choose_character(player)
                obj = player.characters[char_index]
            elif effect_obj == "summon":
                pass
            elif effect_obj == "oppose":
                pass
            elif effect_obj == "oppose_summon":
                pass
            elif effect_obj == "all_summon":
                pass
            elif effect_obj == "player":
                pass
            elif isinstance(effect_obj, list):
                pass
            tag = card.tag
            if "Location" in tag or "Companion" in tag or "Item" in tag:
                pass
        else:
            print("费用不足")
            return False


    def handle_skill(self, player, skill_name):
        active = player.get_active_character_obj()
        skill_detail = active.get_skill_detail(skill_name)
        if "modify" in skill_detail:
            self.add_modify(active, skill_detail["modify"], skill_name)
        skill_type = skill_detail["type"]
        self.invoke_modify("use_skill_auto_add_energy", active, skill_type=skill_type)
        if "Normal Attack" in skill_type or "Elemental Skill" in skill_type:
            active.change_energy(1)
        if "damage" in skill_detail:
            self.handle_damage(active, "team", skill_detail["damage"], skill_type=skill_type, skill_name=skill_name)
        if "create" in skill_detail:
            self.handle_state(active, skill_detail["create"])
        if "summon" in skill_detail:
            self.handle_summon(player, skill_detail["summon"])

    def handle_damage(self, attacker, attackee: Union[str, Character], damage: dict[str, int], **kwargs):
        player = self.players[self.now_player]
        oppose = self.players[~self.now_player]
        extra_attack = []
        element_reaction_add_modify = []
        for element_type, init_damage in damage.items():
            # TODO 伤害处理
            if element_type in ElementType.__members__:
                if attackee == "team":
                    attackee = oppose.get_active_character_obj()
                effects: list[dict] = self.handle_element_reaction(attackee, element_type)
                reaction = None
                for effect in effects:
                    for key, value in effect.items():
                        if key == element_type:
                            init_damage += eval(effect[key])
                        elif "add_modify" == key:
                            for add in effect["add_modify"]:
                                if "reaction" in effect:
                                    reaction = effect["reaction"]
                                    element_reaction_add_modify.append((attacker, add, effect["reaction"]))
                        elif key in ["HYDRO_DMG", "GEO_DMG", "ELECTRO_DMG","DENDRO_DMG", "PYRO_DMG", "PHYSICAL_DMG",
                                    "CRYO_DMG", "ANEMO_DMG", "PIERCE_DMG"]:
                            extra_attack.append({key: value})
                if reaction is not None:
                    attacker_modify_effect = self.invoke_modify("element_attack", attacker, **kwargs, reaction=reaction, damage=init_damage, element=element_type)
                else:
                    attacker_modify_effect = self.invoke_modify("element_attack", attacker, **kwargs, damage=init_damage, element=element_type)
                oppose_state = attackee.change_hp(-init_damage)
                if oppose_state == "die":
                    self.handle_oppose_dead(oppose)
            elif element_type == "PHYSICAL":
                # TODO
                # effect = self.invoke_modify("infusion", attacker, **kwargs)
                # infusion: ElementType = effect[0]["infusion"]
                infusion = ElementType.NONE
                if infusion != ElementType.NONE:
                    self.handle_damage(attacker, attackee, {infusion.name: init_damage}, **kwargs)
                else:
                    if attackee == "team":
                        attackee = oppose.get_active_character_obj()
                    attacker_modify_effect = self.invoke_modify("element_attack", attacker,  **kwargs, damage=init_damage,
                                                                element=element_type)
                    oppose_state = attackee.change_hp(-init_damage)
                    if oppose_state == "die":
                        self.handle_oppose_dead(oppose)
            elif element_type == "PIERCE":
                if attackee == "team":
                    oppose_standby = oppose.get_standby_obj()
                else:
                    oppose_standby = [attackee]
                for obj in oppose_standby:
                    attacker_modify_effect = self.invoke_modify("pierce", attacker, **kwargs, damage=init_damage)
                    oppose_state = obj.change_hp(-init_damage)
                    if oppose_state == "die":
                        self.handle_oppose_dead(oppose)

    def handle_oppose_dead(self, oppose: Player):
        pass

    def add_modify(self, invoker: Character, modify, modify_name):
        player = self.players[~self.now_player]
        oppose = self.players[~self.now_player]
        for each in modify:
            if "IMMEDIATE" in each["time_limit"]:
                mod = self.append_modify([], (modify_name, each))
                self.invoke_modify("none", invoker, modify=mod)
            else:
                effect_obj = each["effect_obj"]
                if EffectObj[effect_obj] in [EffectObj.SELF]:
                    new_modifies = self.append_modify(invoker.modifies, (modify_name, each))
                    invoker.modifies = new_modifies
                elif EffectObj[effect_obj] in [EffectObj.OPPOSE_SELF]:
                    oppose_active = oppose.get_active_character_obj()
                    new_modifies = self.append_modify(oppose_active.modifies, (modify_name, each))
                    oppose_active.modifies = new_modifies
                else:
                    new_modifies = self.append_modify(player.team_modifier, (modify_name, each))
                    player.team_modifier = new_modifies


    @staticmethod
    def append_modify(old_modify: list, new_modify: tuple[str, dict]):
        new_modifies = old_modify
        need_del = []
        stack_count = []
        modify_name = new_modify[0]
        for index, modify in enumerate(old_modify):
            if modify_name in modify:
                if "stack" in modify[modify_name]:
                    stack_count.append(str(modify[modify_name]))
                else:
                    need_del.append(index)
        set_stack_count = list(set(stack_count))
        for each in set_stack_count:
            num = stack_count.count(each)
            if num >= eval(each)["stack"]:
                need_del.append(stack_count.index(each))
        need_del = sorted(need_del, reverse=True)
        modify = new_modify[1].copy()  # 否则del会改变原modify
        time_limit = modify["time_limit"]
        del modify["time_limit"]
        new_modifies.append({modify_name: modify, "time_limit": time_limit})
        for i in need_del:
            new_modifies.pop(i)
        return new_modifies

    def invoke_modify(self, operation, invoker, **kwargs):
        all_related_modifies = []
        need_remove_modifies = []
        player = self.players[self.now_player]
        oppose = self.players[~self.now_player]
        return_effect = []
        if "modify" in kwargs :
            all_related_modifies.append(kwargs["modify"])
        if operation == "pierce":
            for modify in player.team_modifier:
                for key, value in modify.items():
                    if key != "time_limit":
                        if "PIERCE" in value["effect"]:
                            all_related_modifies.append(modify)
            for modify in invoker.modifies:
                for key, value in modify.items():
                    if key != "time_limit":
                        if "PIERCE" in value["effect"]:
                            all_related_modifies.append(modify)
        elif operation == "element_attack":
            for modify in player.team_modifier:
                for key, value in modify.items():
                    if key != "time_limit":
                        for change in ["DMG", "CRYO", "PYRO", "HYDRO", "ELECTRO", "DENDRO", "ANEMO", "GEO"]:
                            if change in value["effect"]:
                                all_related_modifies.append(modify)
            for modify in invoker.modifies:
                for key, value in modify.items():
                    if key != "time_limit":
                        for change in ["DMG", "CRYO", "PYRO", "HYDRO", "ELECTRO", "DENDRO", "ANEMO", "GEO"]:
                            if change in value["effect"]:
                                all_related_modifies.append(modify)
        for each in all_related_modifies:
            for modify_name, modify in each.items():
                if modify_name != "time_limit":
                    condition = modify["condition"]
                    satisfy_condition = self.check_condition(condition, kwargs["additional"])
                    if satisfy_condition:
                        time_limit = each["time_limit"]
                        for limit_type, limit in time_limit.items():
                            if TimeLimit[limit_type] == TimeLimit.USAGE:
                                time_limit[limit_type] -= 1
                                if time_limit[limit_type] == 0:
                                    need_remove_modifies.append(each)
                            elif TimeLimit[limit_type] == TimeLimit.ROUND:
                                left_usage = time_limit[limit_type][1]
                                if left_usage > 0:
                                    time_limit[limit_type][1] -= 1
                                else:
                                    satisfy_condition = False
                            else:  # 无限不用处理， 立即生效在add_modify时处理, 持续回合在回合结束时处理
                                break
                    if satisfy_condition:
                        effect_obj = modify["effect_obj"]
                        if EffectObj[effect_obj] == EffectObj.COUNTER:
                            for counter_name, counter_change in modify["effect"].items():
                                if isinstance(counter_change, str):
                                    invoker.counter[counter_name] += eval(counter_change)
                                else:
                                    invoker.counter[counter_name] = counter_change
                            print(invoker.counter)
                        else:
                            effect = modify["effect"]
                            return_effect.append(effect)
        return return_effect

    def check_condition(self, condition, *args):
        if condition:
            for each in condition:
                if isinstance(each, str):
                    if each.startswith("STAGE_"):
                        condition_stage = each.replace("STAGE_", "")
                        if condition_stage == self.stage:
                            continue
                        else:
                            return False
                    else:
                        if each not in args:
                            return False
                elif isinstance(each, list):
                    pass
            return True
        else:
            return True

    def handle_state(self, invoker: Character, combat_state):
        # TODO modify修改modify
        for state_name, num in combat_state.items():
            modify = self.state_dict[state_name]["modify"]
            for _ in range(num):
                self.add_modify(invoker, modify, state_name)

    def handle_summon(self, player: Player, summon_dict: dict):
        for summon_name, num in summon_dict.items():
            for _ in range(num):
                for add_state in player.add_summon(summon_name):
                    if add_state == "remove":
                        index = self.ask_player_remove_summon(player)
                        player.remove_summon(index)

    def handle_element_reaction(self, trigger_obj: Character, element):
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
            effect.append({"ELECTRO": "+2", "PYRO": "+2", "add_modify":[{"condition":["IS_ACTIVE"], "effect":{"CHANGE_CHARACTER": "-1"}, "effect_obj":"OPPOSE_ACTIVE", "time_limit":{"IMMEDIATE": 1}}], "reaction": "OVERLOADED"})
        elif {ElementType.HYDRO, ElementType.CRYO}.issubset(applied_element):
            applied_element.remove(ElementType.HYDRO)
            applied_element.remove(ElementType.CRYO)
            effect.append({"HYDRO": "+1", "CRYO": "+1", "reaction": "FROZEN", "add_modify":[{"condition":[], "effect":{"FROZEN": "TRUE"}, "effect_obj":"OPPOSE_SELF", "time_limit":{"DURATION": 1}},
                                                                      {"condition":[["BEING_HIT_BY", "PHYSICAL", "PYRO"]], "effect":{"FROZEN": "FALSE"}, "effect_obj":"OPPOSE_SELF", "time_limit":{"DURATION": 1}}]})
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
            self.handle_summon(self.players[self.now_player], {"Burning Flame": 1})
        elif {ElementType.DENDRO, ElementType.HYDRO}.issubset(applied_element):
            applied_element.remove(ElementType.DENDRO)
            applied_element.remove(ElementType.HYDRO)
            effect.append({"DENDRO": "+1", "HYDRO": "+1", "reaction": "BLOOM"})
            self.handle_state(self.players[self.now_player].get_active_character_obj(), {"Dendro Core": 1})
        elif {ElementType.DENDRO, ElementType.ELECTRO}.issubset(applied_element):
            applied_element.remove(ElementType.DENDRO)
            applied_element.remove(ElementType.ELECTRO)
            effect.append({"DENDRO": "+1", "ELECTRO": "+1", "reaction": "CATALYZE"})
            self.handle_state(self.players[self.now_player].get_active_character_obj(), {"Catalyzing Field": 2})
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
                    effect.append({"GEO": "+1", "add_modify": [{"condition":[], "effect":{"SHIELD": 1}, "effect_obj":"ACTIVE", "time_limit":{"USAGE": 1}, "stack": 2 ,"repeated": "True"}],
                                   "reaction": "CRYSTALLIZE", "crystallize_element": element.name})
                    break
        trigger_obj.application = list(applied_element)
        return effect


if __name__ == '__main__':
    state = pre_check()
    if isinstance(state, list):
        error = " ".join(state)
        print("以下卡牌不合法：%s" % error)
    else:
        game = Game()
        game.start_game()
