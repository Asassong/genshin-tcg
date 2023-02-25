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
import time
from player import Player
from character import Character
from card import Card
from summon import Summon
from enums import ElementType, PlayerAction, GameStage
from utils import read_json
from typing import Union
# from modify_manager import add_modify, invoke_modify, remove_modify, consume_modify_usage
import socket
import threading
import asyncio
from copy import deepcopy


class Game:
    def __init__(self, mode, player_socket: list, client_deck: dict):
        config = read_json("config.json")
        game_config = config["Game"][mode]
        now_time = time.time()
        self.record = open("./record/%s.txt" % time.strftime("%Y%m%d%H%M%S"), "w", encoding="utf-8")
        random.seed(now_time)
        self.record.write("seed: %s\n" % now_time)
        self.record.flush()
        self.socket = self.create_socket()
        self.client_socket = player_socket
        self.round = 0
        self.players: list[Player] = self.init_player(client_deck, game_config["enable_deck"], game_config["enable_character"], game_config["Player"])
        self.first_player: int = -1
        self.init_card_num = game_config["init_card_num"]
        self.switch_hand_times = game_config["switch_hand_times"]
        self.switch_dice_times = game_config["switch_dice_times"]
        self.max_round = game_config["max_round"]
        self.draw_card_num = game_config["draw_card_num"]
        self.stage = GameStage.NONE
        self.state_dict = read_json("state.json")
        self.now_player = None
        self.broadcast_condition = []
        self.lock = threading.Lock()
        self.special_event = {player: [] for player in self.players}

    @staticmethod
    def create_socket():
        svr_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        svr_sock.bind(("127.0.0.1", 0))
        return svr_sock

    def send(self, data: dict, client):
        self.socket.sendto(str(data).encode(), client)

    def recv(self):
        while True:
            data, remote_addr = self.socket.recvfrom(1024)
            if data:
                data = eval(data)
                message = data["message"]
                client_index = self.client_socket.index(remote_addr)
                # if message == "init_finish":
                #     self.broadcast_condition.append(message)
                if message == "selected_card":
                    card_index = data["index"]
                    player = self.players[client_index]
                    self.record.write("player%s's redraw index: %s" % (client_index, str(card_index)))
                    player.redraw(card_index)
                    self.broadcast_condition.append({message: client_index})
                elif message == "selected_character":
                    character_index = data["character_index"]
                    player = self.players[client_index]
                    state = player.choose_character(character_index)
                    if state:
                        self.broadcast_condition.append({message: client_index})
                elif message == "need_reroll":
                    dices = data["dice_index"]
                    player = self.players[client_index]
                    self.record.write("player%s's reroll index: %s" % (client_index, str(dices)))
                    player.reroll(dices)
                    dices = self.get_player_dice_info(player)
                    self.record.write("player%s's dices: %s" % (client_index, str(dices)))
                    clear_dice_message = {"message": "clear_dice"}
                    self.send(clear_dice_message, remote_addr)
                    dice_message = {"message": "add_dice", "dices": dices}
                    self.send(dice_message, remote_addr)
                    self.record.flush()
                    self.broadcast_condition.append({message: client_index})
                elif message == "commit_cost":
                    player = self.players[client_index]
                    player.use_dices(data["cost"])
                    consume_message = {"message": "remove_dice", "dices": data["cost"]}
                    self.send(consume_message, self.client_socket[client_index])
                    dices = self.get_player_dice_info(player)
                    dice_num_message = {"message": "show_dice_num", "num": len(dices)}
                    self.send(dice_num_message, self.client_socket[client_index])
                    dice_num_message = {"message": "show_oppose_dice_num", "num": len(dices)}
                    for client in self.get_oppose_client(client_index):
                        self.send(dice_num_message, client)
                    self.broadcast_condition.append({message: client_index})
                elif message == "check_cost":
                    self.broadcast_condition.append({message: client_index, "cost": data["cost"]})
                elif data["message"] == "cancel":
                    self.broadcast_condition.append({message: client_index})
                elif data["message"].startswith("chose_target"):
                    self.broadcast_condition.append({message: client_index, "index": data["index"]})

    @staticmethod
    def skip_list_index(target_list: list, index:int):
        return target_list[:index] + target_list[index+1:]

    def init_player(self, player_deck, card_pack, char_pack, player_config):
        players = []
        for index, ip in enumerate(self.client_socket):
            players.append(Player(player_config, card_pack, char_pack, player_deck[ip]))
        return players

    def ask_client_init_character(self):
        for index, player in enumerate(self.players):
            characters = player.characters
            self.record.write("player%d's characters: %s\n" % (index, str(characters)))
            for char_index, character in enumerate(characters):
                init_message = {"message": "init_character", "position": char_index, "character_name": character.name,
                                "hp": character.get_hp(), "energy": (character.get_energy(), character.max_energy)}
                self.send(init_message, self.client_socket[index])
                init_message = {"message": "init_oppo_character", "position": char_index,
                                "character_name": character.name,
                                "hp": character.get_hp(), "energy": (character.get_energy(), character.max_energy)}
                for client_socket in self.skip_list_index(self.client_socket, index):
                    self.send(init_message, client_socket)
        self.record.flush()

    def start_game(self):
        for client in self.client_socket:
            self.send({"message":"game start"}, client)
        enable_receive = threading.Thread(target=self.recv)
        enable_receive.start()
        self.broadcast_condition.clear()
        self.ask_client_init_character()
        # while True:
        #     if self.broadcast_condition.count("init_finish") == len(self.client_socket):
        #         get = False
        #         try:
        #             get = self.lock.acquire()
        #             self.broadcast_condition.clear()
        #         finally:
        #             if get:
        #                 self.lock.release()
        #         if get:
        #             break
        self.stage = GameStage.GAME_START
        asyncio.run(self.init_draw())
        self.invoke_passive_skill()
        asyncio.run(self.init_choose_active())
        self.first_player = random.randint(0, len(self.players) - 1)
        self.record.write("player%d first\n" % self.first_player)
        self.record.flush()
        self.start()

    async def init_draw(self):
        for index, player in enumerate(self.players):
            player.draw(self.init_card_num)
            card_info = self.get_player_hand_card_info(player)
            self.record.write("player%d's hand cards: %s\n" % (index, str(card_info)))
        self.record.flush()
        tasks = []
        for index, player in enumerate(self.players):
            tasks.append(asyncio.create_task(self.ask_client_redraw(index, player)))
        await asyncio.gather(*tasks)
        for index, player in enumerate(self.players):
            cards = self.get_player_hand_card_info(player)
            self.record.write("player%d's hand cards: %s\n" % (index, str(cards)))
            for client in self.get_oppose_client(index):
                oppo_card_num_message = {"message": "oppose_card_num", "num": len(cards)}
                self.send(oppo_card_num_message, client)
        self.record.flush()

    async def ask_client_redraw(self, index, player):
        await asyncio.sleep(0)
        for _ in range(self.switch_hand_times):
            await self.ask_player_redraw_card(index, player)
            await asyncio.sleep(0)
        cards = self.get_player_hand_card_info(player)
        add_card_message = {"message": "add_card", "cards": cards}
        self.send(add_card_message, self.client_socket[index])

    async def init_choose_active(self):
        tasks = []
        for player in self.players:
            tasks.append(asyncio.create_task(self.ask_player_choose_character(player)))
        await asyncio.gather(*tasks)
        for index, player in enumerate(self.players):
            character_index = player.current_character
            choose_message = {"message": "player_change_active", "change_from": None, "change_to": character_index}
            self.send(choose_message, self.client_socket[index])
            for client in self.get_oppose_client(index):
                choose_message = {"message": "oppose_change_active", "change_from": None,
                                  "change_to": character_index}
                self.send(choose_message, client)
            active = player.get_active_character_obj()
            self.record.write("player%d choose active character %s\n" % (index, active.get_name()))
            skill = active.get_skills_type()
            init_skill_message = {"message": "init_skill", "skills": skill}
            self.send(init_skill_message, self.client_socket[index])
            self.invoke_modify("change_to", player, active, change_action="fast")
        self.record.flush()

    def invoke_passive_skill(self):
        for player in self.players:
            self.now_player = self.players.index(player)
            characters = player.get_character()
            for character in characters:
                passive_skills = character.get_passive_skill()
                for passive in passive_skills:
                    self.handle_skill(player, character, passive, have_been_cost=True)

    def start(self):
        while True:
            self.round += 1
            self.record.write("round%d start\n" % self.round)
            self.record.flush()
            # if not self.round % 2:
            #     hide_oppose_message = {"message": "hide_oppose"}
            #     for client in self.client_socket:
            #         self.socket.sendto(str(hide_oppose_message).encode(), client)
            # else:
            #     show_oppose_message = {"message": "show_oppose"}
            #     for client in self.client_socket:
            #         self.socket.sendto(str(show_oppose_message).encode(), client)
            self.stage = GameStage.ROUND_START
            self.start_stage()
            self.stage = GameStage.ROLL
            asyncio.run(self.roll_stage())
            self.stage = GameStage.ACTION
            self.action_stage()
            self.stage = GameStage.ROUND_END
            self.end_stage()

    def start_stage(self):
        self.now_player = self.first_player
        for _ in range(len(self.players)):
            player = self.players[self.now_player]
            active = player.get_active_character_obj()
            self.invoke_modify("start", player, active, only_invoker=True)
            standby = player.get_standby_obj()
            for each in standby:
                self.invoke_modify("start", player, each, only_invoker=True)
            self.invoke_modify("start", player, None, only_invoker=True)
            for summon in player.summons:
                self.invoke_modify("start", player, summon, only_invoker=True)
            for support in player.supports:
                self.invoke_modify("start", player, support, only_invoker=True)

    async def roll_stage(self):
        tasks = []
        for index, player in enumerate(self.players):
            tasks.append(asyncio.create_task(self.roll_and_reroll(index, player)))
        await asyncio.gather(*tasks)

    async def roll_and_reroll(self, index, player):
        roll_effect = self.invoke_modify("roll", player, None, only_invoker=True)
        if "FIXED_DICE" in roll_effect:
            player.roll(fixed_dice=roll_effect["FIXED_DICE"])
            roll_effect.pop("FIXED_DICE")
        else:
            player.roll()
        dices = self.get_player_dice_info(player)
        self.record.write("player%s's dices: %s" % (index, str(dices)))
        extra_switch_times = 0
        if "REROLL" in roll_effect:
            if isinstance(roll_effect["REROLL"], str):
                extra_switch_times += eval(roll_effect["REROLL"])
                roll_effect.pop("REROLL")
        await asyncio.sleep(0)
        for _ in range(self.switch_dice_times + extra_switch_times):
            await self.ask_player_reroll_dice(player)
            await asyncio.sleep(0)
        dices = self.get_player_dice_info(player)
        card_num_message = {"message": "show_dice_num", "num": len(dices)}
        self.send(card_num_message, self.client_socket[index])
        card_num_message = {"message": "show_oppose_dice_num", "num": len(dices)}
        for client in self.get_oppose_client(index):
            self.send(card_num_message, client)

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
                # for modify_name, modify in active.modifies.copy().items():
                #     consume_state = consume_modify_usage(modify, "act")
                #     if consume_state == "remove":
                #         remove_modify(active.modifies, modify_name)
                self.invoke_modify("action", now_player, active)
                action, extra = self.ask_player_action(now_player)
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
                    self.element_tuning(now_player, extra)
                elif PlayerAction(action) == PlayerAction.CHANGE_CHARACTER:
                    change_state = self.player_change_avatar(now_player, extra)
                    change_from = now_player.current_character
                    if not change_state:
                        continue
                    elif change_state == "fast":
                        action_type = "fast"
                    now_player.choose_character(extra)
                    self.send_effect_message("change_active", now_player, None, change_from=change_from, change_to=extra)
                elif PlayerAction(action) == PlayerAction.USING_SKILLS:
                    use_state = self.use_skill(now_player, extra)
                    if not use_state:
                        continue
                elif PlayerAction(action) == PlayerAction.PLAY_CARD:
                    self.play_card(now_player, extra)
                if action_type is not None:
                    if action_type == "fast":
                        continue
                    else:
                        action_end_message = {"message": "act_end"}
                        self.send(action_end_message, self.client_socket[self.now_player])
                        self.now_player = (self.now_player + 1) % len(self.players)
                else:
                    judge_action_type = self.judge_action(action)
                    if judge_action_type == "fast":
                        continue
                    else:
                        action_end_message = {"message": "act_end"}
                        self.send(action_end_message, self.client_socket[self.now_player])
                        self.now_player = (self.now_player + 1) % len(self.players)
            else:
                action_end_message = {"message": "act_end"}
                self.send(action_end_message, self.client_socket[self.now_player])
                self.now_player = (self.now_player + 1) % len(self.players)

    def end_stage(self):
        self.now_player = self.first_player
        for _ in range(len(self.players)):
            player = self.players[self.now_player]
            active = player.get_active_character_obj()
            self.invoke_modify("end", player, active, only_invoker=True)
            standby = player.get_standby_obj()
            for each in standby:
                self.invoke_modify("end", player, each, only_invoker=True)
            self.invoke_modify("end", player, None, only_invoker=True)
            need_remove_summon = []
            for summon in player.summons:
                effect = summon.effect
                print("summon_effect", effect)
                for each_effect in effect:
                    if "damage" in each_effect:
                        self.handle_damage(player, summon, "team", each_effect["damage"])
                    elif "heal" in each_effect:
                        if each_effect["effect_obj"] == "ACTIVE":
                            active.change_hp(each_effect["heal"])
                            self.send_effect_message("hp", player, active)
                        elif each_effect["effect_obj"] == "ALL":
                            for character in player.characters:
                                character.change_hp(each_effect["heal"])
                                self.send_effect_message("hp", player, character)
                    elif "application" in each_effect:
                        if each_effect["effect_obj"] == "ACTIVE":
                            self.handle_element_reaction(player, active, each_effect["application"])
                summon_state = player.trigger_summon(summon, 1)
                if summon_state == "remove":
                    need_remove_summon.append(summon)
            for summon in need_remove_summon:
                player.summons.remove(summon)
            for summon in player.summons:
                self.invoke_modify("end", player, summon, only_invoker=True)
            for support in player.supports:
                self.invoke_modify("end", player, support, only_invoker=True)
            player.dices.clear()
            self.send_effect_message("clear_dice", player, None)
            player.draw(2)
            cards = self.get_player_hand_card_info(player)
            self.send_effect_message("add_card", player, None, card_name=cards[-2:], card_num=len(cards))
            player.clear_character_saturation()
            self.now_player = (self.now_player + 1) % len(self.players)
        self.round_end_consume_modify()

    def get_now_player(self):
        return self.players[self.now_player]

    def get_oppose(self, index):
        return self.skip_list_index(self.players, index)

    def get_one_oppose(self, player):
        # TODO 多人
        index = self.players.index(player)
        all_oppose = self.get_oppose(index)
        return all_oppose[0]

    def get_oppose_client(self, index):
        return self.skip_list_index(self.client_socket, index)

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

    async def ask_player_redraw_card(self, index, player: Player):
        card_info = self.get_player_hand_card_info(player)
        redraw_message = {"message": "redraw", "hand": card_info}
        self.send(redraw_message, self.client_socket[index])
        while True:
            for condition_index, each in enumerate(self.broadcast_condition):
                if isinstance(each, dict):
                    if "selected_card" in each:
                        if each["selected_card"] == index:
                            get = False
                            try:
                                get = self.lock.acquire()
                                self.broadcast_condition.pop(condition_index)
                                return
                            finally:
                                if get:
                                    self.lock.release()
            await asyncio.sleep(0.1)

    async def ask_player_choose_character(self, player: Player):
        select_message = {"message": "select_character"}
        index = self.players.index(player)
        self.send(select_message, self.client_socket[index])
        while True:
            for condition_index, each in enumerate(self.broadcast_condition):
                if isinstance(each, dict):
                    if "selected_character" in each:
                        if each["selected_character"] == index:
                            get = False
                            try:
                                get = self.lock.acquire()
                                self.broadcast_condition.pop(condition_index)
                                return
                            finally:
                                if get:
                                    self.lock.release()
            await asyncio.sleep(0.1)

    async def ask_player_reroll_dice(self, player):
        dice_type = self.get_player_dice_info(player)
        reroll_message = {"message": "reroll", "now_dice": dice_type}
        index = self.players.index(player)
        self.send(reroll_message, self.client_socket[index])
        while True:
            for condition_index, each in enumerate(self.broadcast_condition):
                if isinstance(each, dict):
                    if "need_reroll" in each:
                        if each["need_reroll"] == index:
                            get = False
                            try:
                                get = self.lock.acquire()
                                self.broadcast_condition.pop(condition_index)
                                return
                            finally:
                                if get:
                                    self.lock.release()
            await asyncio.sleep(0.1)

    async def ask_player_choose_target(self, player, target_type):
        target = "choose_target_%s" % target_type
        choose_message = {"message": target}
        return_target = target.replace("choose", "chose")
        index = self.players.index(player)
        self.send(choose_message, self.client_socket[index])
        while True:
            for condition_index, each in enumerate(self.broadcast_condition):
                if isinstance(each, dict):
                    if return_target in each:
                        if each[return_target] == index:
                            get = False
                            try:
                                get = self.lock.acquire()
                                self.broadcast_condition.pop(condition_index)
                                return each["index"]
                            finally:
                                if get:
                                    self.lock.release()
            await asyncio.sleep(0.1)

    def ask_player_action(self, player: Player):
        action_message = {"message": "action_phase_start"}
        self.send(action_message, self.client_socket[self.players.index(player)])
        while True:
            data, addr = self.socket.recvfrom(1024)
            if data:
                data = eval(data)
                # 1.使用角色技能2.元素调和3.结束回合4.切换角色5.打出卡牌
                if data["message"] == "selected_character":
                    return 4, data["character"]
                elif data["message"] == "play_card":
                    return 5, data["card_index"]
                elif data["message"] == "element_tuning":
                    return 2, data["card_index"]
                elif data["message"] == "round_end":
                    return 3, None
                # elif data["message"] == "check_skill_cost":
                #     active = player.get_active_character_obj()
                #     skill_names = active.get_skills_name()
                #     skill_name = skill_names[data["skill_index"]]
                #     skill_detail = active.get_skill_detail(skill_name)
                #     skill_cost = skill_detail["cost"].copy()
                #     skill_type = skill_detail["type"]
                #     use_skill_effect = self.invoke_modify("use_skill", player, active, use=False, skill_name=skill_name,
                #                                      skill_type=skill_type, cost=skill_cost)
                #     real_cost = use_skill_effect["cost"]
                #     state = player.check_cost(real_cost)
                #     if state or state == {}:
                #         enable_message = {"message": "enable_commit"}
                #         self.send(enable_message, self.client_socket[self.players.index(player)])
                elif data["message"] == "use_skill":
                    return 1, data["skill_index"]

    def ask_player_remove_summon(self, player: Player):
        summon = player.get_summon_name()
        s_summon = ",".join(summon)
        # # while True:
        # #     print("%s" % player.name)
        # #     print("您的召唤物为 %s" % s_summon)
        # #     index = input("请选择要移除的召唤物(0-%d, 空格隔开):" % (len(summon) - 1))
        # #     valid_index = self.judge_input(index, 0, len(summon) - 1)
        # #     if len(valid_index) == 1:
        # #         break
        # #     else:
        # #         print("输入格式错误，请重输")
        # return valid_index[0]
        return 1

    def ask_player_remove_support(self, player: Player):
        support = player.get_support_name()
        s_support = ",".join(support)
        # while True:
        #     print("%s" % player.name)
        #     print("您的支援卡为 %s" % s_support)
        #     index = input("请选择要移除的支援卡(0-%d, 空格隔开):" % (len(support) - 1))
        #     valid_index = self.judge_input(index, 0, len(support) - 1)
        #     if len(valid_index) == 1:
        #         break
        #     else:
        #         print("输入格式错误，请重输")
        # return valid_index[0]
        return 1

    def element_tuning(self, player: Player, card_index):
        state = asyncio.run(self.action_cost(player, {"ANY": 1}))
        if state:
            element = player.get_active_character_obj().element
            player.append_special_dice(element)
            self.send_effect_message("dice", player, None)
            player.remove_hand_card(card_index)
            self.send_effect_message("remove_card", player, None, card_index=card_index)

    def preview_cost(self, operation, player, invoker: Character|None, normal_cost, **kwargs):

        def preview_change(operation, player, invoker, modify, cost):
            effect = modify["effect"]
            if "CHANGE_COST" in effect:
                if self.modify_satisfy_condition(operation, player, invoker, modify):
                    cost_change = eval(effect["CHANGE_COST"])
                    if "ANY" in cost:
                        if cost["ANY"] > 0 or cost_change > 0:
                            cost["ANY"] += cost_change
            return cost

        def preview_skill(operation, player, invoker, modify, cost, **kwargs):
            effect = modify["effect"]
            if self.modify_satisfy_condition(operation, player, invoker, modify, **kwargs):
                if set(effect.keys()) & {"COST_ANY", "COST_PYRO", "COST_HYDRO", "COST_ELECTRO", "COST_CRYO",
                                         "COST_DENDRO", "COST_ANEMO", "COST_GEO", "COST_ALL", "COST_ELEMENT"}:
                    effect_type = set(effect.keys()) & {"COST_ANY", "COST_PYRO", "COST_HYDRO", "COST_ELECTRO",
                                                        "COST_CRYO",
                                                        "COST_DENDRO", "COST_ANEMO", "COST_GEO", "COST_ALL",
                                                        "COST_ELEMENT"}
                    effect_type = list(effect_type)[0]
                    effect_value = effect[effect_type]
                    element_type = effect_type.replace("COST_", "")
                    if element_type in ElementType.__members__:
                        if element_type in cost:
                            cost[element_type] += eval(effect_value)
                            if cost[element_type] <= 0:
                                cost.pop(element_type)
                    elif element_type == "ANY":
                        if element_type in cost:
                            cost[element_type] += eval(effect_value)
                            if cost[element_type] <= 0:
                                cost.pop(element_type)
                    elif element_type == "ELEMENT":
                        for element in ['CRYO', 'HYDRO', 'PYRO', 'ELECTRO', 'GEO', 'DENDRO', 'ANEMO']:
                            if element in cost:
                                cost[element] += eval(effect_value)
                                if cost[element] <= 0:
                                    cost.pop(element)
                                break
                    elif element_type == "ALL":  # 暂时只写same
                        if "SAME" in cost:
                            cost["SAME"] += eval(effect_value)
                            if cost["SAME"] <= 0:
                                cost.pop("SAME")
            return cost

        cost = normal_cost.copy()
        if operation == "change":
            change_from = kwargs["change_from"]
            change_to = kwargs["change_to"]
            for modify in change_from.modifies:
                cost = preview_change("change_from", player, change_from, modify, cost)
            for modify in player.team_modifier:
                cost = preview_change("change_from", player, change_from, modify, cost)
            for modify in change_to.modifies:
                cost = preview_change("change_to", player, change_to, modify, cost)
        elif operation == "use_skill":
            for modify in invoker.modifies:
                cost = preview_skill("skill_cost", player, invoker, modify, cost, **kwargs)
            for _, state in invoker.state.items():
                for modify in state["modify"]:
                    cost = preview_skill("skill_cost", player, invoker, modify, cost, **kwargs)
            for modify in player.team_modifier:
                cost = preview_skill("skill_cost", player, invoker, modify, cost, **kwargs)
            for _, state in player.team_state:
                for modify in state["modify"]:
                    cost = preview_skill("skill_cost", player, invoker, modify, cost, **kwargs)
        elif operation == "play_card":
            for modify in player.team_modifier:
                cost = preview_skill("card_cost", player, invoker, modify, cost, **kwargs)
        return cost

    def modify_satisfy_condition(self, operation, player, invoker, modify, **kwargs):
        trigger_time = modify["trigger_time"]
        if self.is_trigger_time(operation, trigger_time):
            if "time_limit" in modify:
                time_limit = modify["time_limit"]
                if self.check_condition(player, invoker, modify["condition"], **kwargs):
                    if "ROUND" in time_limit:
                        if time_limit['ROUND'][1] > 0:
                            return True
                        else:
                            return False
                    return True
            else:
                return True
        return False

    async def action_cost(self, player, cost):
        dice_type = self.get_player_dice_info(player)
        cost_state = player.check_cost(cost)
        if cost_state:
            cost_indexes = []
            use_energy = -1
            for key, value in cost_state.items():
                if key == "ENERGY":
                    use_energy = value
                else:
                    start_index = 0
                    for _ in range(value):
                        new_index = dice_type.index(key, start_index)
                        cost_indexes.append(new_index)
                        start_index = new_index + 1
            cost_message = {"message": "highlight_dice", "dice_indexes": cost_indexes}
            player_index = self.players.index(player)
            self.send(cost_message, self.client_socket[player_index])
            while True:
                for condition_index, each in enumerate(self.broadcast_condition):
                    if isinstance(each, dict):
                        if "commit_cost" in each:
                            if each["commit_cost"] == player_index:
                                get = False
                                try:
                                    get = self.lock.acquire()
                                    self.broadcast_condition.pop(condition_index)
                                finally:
                                    if get:
                                        self.lock.release()
                                if get:
                                    if use_energy != -1:
                                        active = player.get_active_character_obj()
                                        active.change_energy(-use_energy)
                                        self.send_effect_message("energy", player, active)
                                    return True
                        elif "check_cost" in each:
                            if each["check_cost"] == player_index:
                                check_result = player.recheck_cost(cost, each["cost"])
                                if check_result:
                                    enable_message = {"message": "enable_commit"}
                                    self.send(enable_message, self.client_socket[player_index])
                                get = False
                                try:
                                    get = self.lock.acquire()
                                    self.broadcast_condition.pop(condition_index)
                                finally:
                                    if get:
                                        self.lock.release()
                        elif "cancel" in each:
                            if each["cancel"] == player_index:
                                get = False
                                try:
                                    get = self.lock.acquire()
                                    self.broadcast_condition.pop(condition_index)
                                finally:
                                    if get:
                                        self.lock.release()
                                if get:
                                    return False
                await asyncio.sleep(0.1)
        elif cost_state == {}:
            return True
        return False

    def player_change_avatar(self, player: Player, character_index):
        normal_cost = {"ANY": 1}
        change_action = "combat"
        active = player.get_active_character_obj()
        new_active = character_index
        if player.check_character_alive(new_active):
            new_active_obj = player.characters[new_active]
            preview_cost = self.preview_cost("change", player, None, normal_cost, change_from=active, change_to=new_active_obj)
            cost_state = asyncio.run(self.action_cost(player, preview_cost))
            if cost_state:
                change_effect = self.invoke_modify("change_from", player, active, change_cost=normal_cost, change_action=change_action)
                change_effect = self.invoke_modify("change_to", player, new_active_obj, change_cost=change_effect["change_cost"],
                                                   change_action=change_effect["change_action"])
                change_action = change_effect["change_action"]
                self.invoke_modify("after_change", player, None, only_invoker=True)
            else:
                return False
        else:
            return False
        return change_action

    def use_skill(self, player: Player, skill_index):
        active = player.get_active_character_obj()
        if "FROZEN" in active.state:
            return False
        skill_names = active.get_skills_name()
        skill_name = skill_names[skill_index]
        use_state = self.handle_skill(player, active, skill_name)
        if use_state:
            return True
        else:
            return False

    def play_card(self, player: Player, card_index):
        card = player.get_card_obj(card_index)
        effect_obj = card.effect_obj
        card_cost = card.get_cost().copy()
        tag = card.tag
        cost = self.preview_cost("play_card", player, None, card_cost, card_tag=tag, cost=card_cost)
        state = player.check_cost(cost)
        if state or state == {}:
            obj = None
            if effect_obj == "select":
                char_index = asyncio.run(self.ask_player_choose_target(player, "character"))
                obj = player.characters[char_index]
            elif effect_obj == "summon":
                summon_index = asyncio.run(self.ask_player_choose_target(player, "summon"))
                obj = player.summons[summon_index]
            elif effect_obj == "oppose":
                oppose = self.get_one_oppose(player)
                char_index = asyncio.run(self.ask_player_choose_target(player, "oppose_character"))
                obj = oppose.characters[char_index]
            elif effect_obj == "oppose_summon":
                oppose = self.get_one_oppose(player)
                summon_index = asyncio.run(self.ask_player_choose_target(player, "oppose_summon"))
                obj = oppose.summons[summon_index]
            elif effect_obj == "all_summon":
                pass
            elif effect_obj == "player":
                pass
            if card.combat_limit:
                pass

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
            cost_state = self.action_cost(player, cost)
            if not cost_state:
                return False
            self.invoke_modify("card_cost", player, card, card_tag=tag, cost=card_cost)
            player.remove_hand_card(card_index)
            self.send_effect_message("remove_card", player, None, card_index=card_index)
            modifies = card.init_modify()
            self.add_modify(player, obj, modifies)
            if "Weapon" in tag or "Artifact" in tag or "Talent" in tag:
                if isinstance(obj, Character):
                    equip = list(set(tag) & {"Weapon", "Artifact", "Talent"})[0].lower()
                    # TODO 移除已有modify
                    # if obj.equipment[equip] is not None:
                    #     remove_modify(obj.modifies, obj.equipment[equip], "main")
                    obj.equipment[equip] = card.get_name()
                    equipment = [type_.lower() for type_, value in obj.equipment.items() if value is not None]
                    self.send_effect_message("equip", player, obj, equip=equipment)
            elif "Location" in tag or "Companion" in tag or "Item" in tag:
                if card.counter:
                    for key, value in card.counter.items():
                        init_support_message = {"message": "init_support", "support_name": card.get_name(), "count": str(value)}
                        self.socket.sendto(str(init_support_message).encode(), self.client_socket[self.now_player])
                        init_support_message = {"message": "init_oppose_support", "support_name": card.get_name(),
                                                "count": str(value)}
                        self.socket.sendto(str(init_support_message).encode(), self.client_socket[~self.now_player])
                else:
                    init_support_message = {"message": "init_support", "support_name": card.get_name(),
                                            "count": ""}
                    self.socket.sendto(str(init_support_message).encode(), self.client_socket[self.now_player])
                    init_support_message = {"message": "init_oppose_support", "support_name": card.get_name(),
                                            "count": ""}
                    self.socket.sendto(str(init_support_message).encode(), self.client_socket[~self.now_player])
            self.invoke_modify("play_card", player, None, only_invoker=True, card_tag=tag)
            if card.use_skill:
                self.handle_skill(player, player.get_active_character_obj(), card.use_skill, have_been_cost=True)
        else:
            return False
        return True

    def handle_skill(self, player, invoker, skill_name, have_been_cost=False):
        skill_detail = invoker.get_skill_detail(skill_name)
        if "modify" in skill_detail:
            self.add_modify(player, invoker, skill_detail["modify"])
        skill_type = skill_detail["type"]
        skill_cost = skill_detail["cost"].copy()
        if not have_been_cost:
            preview_cost = self.preview_cost("use_skill", player, invoker, skill_cost, skill_name=skill_name, skill_type=skill_type)
            state = self.action_cost(player, preview_cost)
            if not state:
                return False
            # TODO 可莉
            self.invoke_modify("skill_cost", player, invoker, skill_name=skill_name,
                               skill_type=skill_type, cost=skill_cost)
        if "Normal Attack" in skill_type or "Elemental Skill" in skill_type:
            add_energy = 1
        else:
            add_energy = 0
        use_skill_effect = self.invoke_modify("use_skill", player, invoker, skill_name=skill_name, skill_type=skill_type, add_energy=add_energy)
        if "add_energy" in use_skill_effect:
            invoker.change_energy(use_skill_effect["add_energy"])
        else:
            invoker.change_energy(add_energy)
        self.send_effect_message("energy", player, invoker)
        if "damage" in skill_detail:
            self.handle_damage(player, invoker, "team", skill_detail["damage"], skill_type=skill_type, skill_name=skill_name)
        if "create" in skill_detail:
            self.handle_state(player, invoker, skill_detail["create"])
        if "summon" in skill_detail:
            self.handle_summon(player, skill_detail["summon"])
        return True

    def handle_damage(self, player: Player, attacker, attackee: Union[str, Character], damage: dict[str, int], **kwargs):
        oppose: Player = self.get_one_oppose(player)
        extra_attack = []
        if attackee == "team":
            oppose_active = oppose.get_active_character_obj()
        else:
            oppose_active = attackee
        for element_type, init_damage in damage.items():
            if element_type in ElementType.__members__:
                reaction_effect = self.handle_element_reaction(oppose, oppose_active, element_type)
                effects = next(reaction_effect)
                reaction = effects["reaction"]
                for key, value in effects.items():
                    if key == element_type:
                        init_damage += eval(effects[key])
                    elif key in ["HYDRO_DMG", "GEO_DMG", "ELECTRO_DMG","DENDRO_DMG", "PYRO_DMG", "PHYSICAL_DMG",
                                "CRYO_DMG", "ANEMO_DMG", "PIERCE_DMG"]:
                        extra_attack.append({key.replace("_DMG", ""): value})
                attack_effect = self.invoke_modify("attack", player, attacker, **kwargs, reaction=reaction, damage=init_damage, element=element_type)
                damage = attack_effect["damage"]
                attackee_effect = self.invoke_modify("defense", oppose, oppose_active, **kwargs, reaction=reaction, hurt=damage,
                                              element=element_type)
                hurt = attackee_effect["hurt"]
                if hurt > 0:
                    if "SHIELD" in oppose_active.state:
                        need_remove_shield = []
                        state_shield: list = oppose_active.state["SHIELD"]
                        for index, shield in enumerate(state_shield):
                            left_shield = shield["shield"]
                            if hurt >= left_shield:
                                hurt -= left_shield
                                need_remove_shield.append(index)
                            else:
                                left_shield -= hurt
                                hurt = 0
                            if hurt == 0:
                                break
                        sort_need_remove = sorted(need_remove_shield, reverse=True)
                        for need_remove in sort_need_remove:
                           state_shield.pop(need_remove)
                if hurt > 0:
                    if "SHIELD" in oppose.team_state:
                        need_remove_shield = []
                        state_shield: list = oppose.team_state["SHIELD"]
                        is_active = oppose_active.is_active
                        for index, shield in enumerate(state_shield):
                            left_shield = shield["shield"]
                            if shield["effect_obj"] == "ACTIVE":
                                if not is_active:
                                    continue
                            if hurt >= left_shield:
                                hurt -= left_shield
                                need_remove_shield.append(index)
                            else:
                                left_shield -= hurt
                                hurt = 0
                            if hurt == 0:
                                break
                        sort_need_remove = sorted(need_remove_shield, reverse=True)
                        for need_remove in sort_need_remove:
                           state_shield.pop(need_remove)
                if hurt > 0:
                    oppose_state = oppose_active.change_hp(-hurt)
                    self.send_effect_message("hp", oppose, oppose_active)
                    if oppose_state == "die":
                        self.handle_oppose_dead(oppose)
                next(reaction_effect)
            elif element_type == "PHYSICAL":
                infusion = None
                if isinstance(attacker, Character):
                    if "INFUSION" in attacker.state:
                        state_infusion = attacker.state["INFUSION"]
                        if state_infusion:
                            infusion = state_infusion[0]["type"]
                    if infusion is None:
                        if "INFUSION" in player.team_state:
                            state_infusion = player.team_state["INFUSION"]
                            if state_infusion:
                                infusion = state_infusion[0]["type"]
                if infusion is not None:
                    self.handle_damage(player, attacker, attackee, {infusion: init_damage}, **kwargs)
                else:
                    attack_effect = self.invoke_modify("attack", player, attacker, **kwargs, reaction=None,
                                                  damage=init_damage, element=element_type)
                    damage = attack_effect["damage"]
                    attackee_effect = self.invoke_modify("defense", oppose, oppose_active, **kwargs, reaction=None,
                                                    hurt=damage, element=element_type)
                    hurt = attackee_effect["hurt"]
                    if hurt > 0:
                        if "SHIELD" in oppose_active.state:
                            need_remove_shield = []
                            state_shield: list = oppose_active.state["SHIELD"]
                            for index, shield in enumerate(state_shield):
                                left_shield = shield["shield"]
                                if hurt >= left_shield:
                                    hurt -= left_shield
                                    need_remove_shield.append(index)
                                else:
                                    left_shield -= hurt
                                    hurt = 0
                                if hurt == 0:
                                    break
                            sort_need_remove = sorted(need_remove_shield, reverse=True)
                            for need_remove in sort_need_remove:
                                state_shield.pop(need_remove)
                    if hurt > 0:
                        if "SHIELD" in oppose.team_state:
                            need_remove_shield = []
                            state_shield: list = oppose.team_state["SHIELD"]
                            is_active = oppose_active.is_active
                            for index, shield in enumerate(state_shield):
                                left_shield = shield["shield"]
                                if shield["effect_obj"] == "ACTIVE":
                                    if not is_active:
                                        continue
                                if hurt >= left_shield:
                                    hurt -= left_shield
                                    need_remove_shield.append(index)
                                else:
                                    left_shield -= hurt
                                    hurt = 0
                                if hurt == 0:
                                    break
                            sort_need_remove = sorted(need_remove_shield, reverse=True)
                            for need_remove in sort_need_remove:
                                state_shield.pop(need_remove)
                    if hurt > 0:
                        oppose_state = oppose_active.change_hp(-hurt)
                        self.send_effect_message("hp", oppose, oppose_active)
                        if oppose_state == "die":
                            self.handle_oppose_dead(oppose)
            elif element_type == "PIERCE":
                if attackee == "team":
                    oppose_standby = oppose.get_standby_obj()
                else:
                    oppose_standby = [attackee]
                # TODO pierce modify
                for obj in oppose_standby:
                    oppose_state = obj.change_hp(-init_damage)
                    self.send_effect_message("hp", oppose, obj)
                    if oppose_state == "die":
                        self.handle_oppose_dead(oppose)
        if extra_attack:
            oppose_other = oppose.get_character().copy()
            oppose_other.remove(oppose_active)
            for damage in extra_attack:
                for standby in oppose_other:
                    self.handle_damage(player, attacker, standby, damage)
        self.invoke_modify("extra_attack", player, attacker)
        self.invoke_modify("after_attack", player, attacker)

    def handle_oppose_dead(self, oppose: Player):
        end = True
        for index in range(len(oppose.get_character())):
            if oppose.check_character_alive(index):
                end = False
                break
        if end:
            self.stage = GameStage.GAME_END
            exit(0)
        else:
            change_from = oppose.get_active_character_obj()
            if not change_from.alive:
                asyncio.run(self.ask_player_choose_character(oppose))
            change_to = oppose.get_active_character_obj()
            if change_from != change_to:
                self.invoke_modify("change_to", oppose, change_to, change_action="fast", change_cost={})
                self.send_effect_message("change_active", oppose, None, change_from=oppose.characters.index(change_from),
                                         change_to=oppose.characters.index(change_to))
            self.special_event[oppose].append({"name": "DIE", "remove": "round_start"})

    def handle_state(self, player, invoker: Character, combat_state):
        # TODO modify修改modify
        for state_name, _ in combat_state.items():
            state_info = deepcopy(self.state_dict[state_name])
            if state_info["store"] == "SELF":
                invoker.state.update({state_name: state_info})
            elif state_info["store"] == "TEAM":
                player.team_state.update({state_name: state_info})

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
                    player.team_modifier += summon_modify

    def handle_element_reaction(self, player, trigger_obj: Character, element):
        trigger_obj.application.append(ElementType[element])
        applied_element = set(trigger_obj.application)
        # 反应顺序还需进一步测试
        if {ElementType.CRYO, ElementType.PYRO}.issubset(applied_element):
            applied_element.remove(ElementType.CRYO)
            applied_element.remove(ElementType.PYRO)
            yield {"CRYO": "+2", "PYRO": "+2", "reaction": "MELT"}
        elif {ElementType.HYDRO, ElementType.PYRO}.issubset(applied_element):
            applied_element.remove(ElementType.PYRO)
            applied_element.remove(ElementType.HYDRO)
            yield {"HYDRO": "+2", "PYRO": "+2", "reaction": "VAPORIZE"}
        elif {ElementType.ELECTRO, ElementType.PYRO}.issubset(applied_element):
            applied_element.remove(ElementType.ELECTRO)
            applied_element.remove(ElementType.PYRO)
            yield {"ELECTRO": "+2", "PYRO": "+2", "reaction": "OVERLOADED"}
            self.add_modify(player, trigger_obj, [{"name": "OVERLOADED_0",
                                                   "trigger_time": "after_attack",
                                                   "condition":["IS_ACTIVE"],
                                                   "effect":{"CHANGE_CHARACTER": -1},
                                                   "effect_obj":"ALL",
                                                   "store": "SELF",
                                                   "time_limit":{"IMMEDIATE": 1}}])
        elif {ElementType.HYDRO, ElementType.CRYO}.issubset(applied_element):
            applied_element.remove(ElementType.HYDRO)
            applied_element.remove(ElementType.CRYO)
            yield {"HYDRO": "+1", "CRYO": "+1", "reaction": "FROZEN"}
            self.add_modify(player, trigger_obj, [{"name": "FROZEN_0",
                                                   "trigger_time": "element_reaction",
                                                   "condition":[],
                                                   "effect":{"FROZEN": {"name": "FROZEN",
                                                                        "time_limit":{"DURATION": 1}}},
                                                   "effect_obj":"SELF",
                                                   "store": "SELF",
                                                   "time_limit":{"IMMEDIATE": 1}},
                                                  {"name": "FROZEN_1",
                                                   "trigger_time": "defense",
                                                   "condition":[[{"logic": "check", "what": "element", "whose": "hurt", "operator": "equal", "condition": "PHYSICAL"},
                                                                 {"logic": "check", "what": "element", "whose": "hurt", "operator": "equal", "condition": "PYRO"}]],
                                                   "effect":{"REMOVE_STATE": "FROZEN", "HURT": "+2"},
                                                   "effect_obj":"SELF",
                                                   "store": "SELF",
                                                   "time_limit":{"DURATION": 1}}])
        elif {ElementType.ELECTRO, ElementType.CRYO}.issubset(applied_element):
            applied_element.remove(ElementType.CRYO)
            applied_element.remove(ElementType.ELECTRO)
            yield {"ELECTRO": "+1", "CRYO": "+1", "PIERCE_DMG": 1, "reaction": "SUPER_CONDUCT"}
        elif {ElementType.ELECTRO, ElementType.HYDRO}.issubset(applied_element):
            applied_element.remove(ElementType.ELECTRO)
            applied_element.remove(ElementType.HYDRO)
            yield {"ELECTRO": "+1", "HYDRO": "+1", "PIERCE_DMG": 1, "reaction": "ELECTRO_CHARGE"}
        elif {ElementType.DENDRO, ElementType.PYRO}.issubset(applied_element):
            applied_element.remove(ElementType.DENDRO)
            applied_element.remove(ElementType.PYRO)
            yield {"DENDRO": "+1", "PYRO": "+1", "reaction": "BURNING"}
            self.handle_summon(player, {"Burning Flame": 1})
        elif {ElementType.DENDRO, ElementType.HYDRO}.issubset(applied_element):
            applied_element.remove(ElementType.DENDRO)
            applied_element.remove(ElementType.HYDRO)
            yield {"DENDRO": "+1", "HYDRO": "+1", "reaction": "BLOOM"}
            self.handle_state(player, player.get_active_character_obj(), {"Dendro Core": 1})
        elif {ElementType.DENDRO, ElementType.ELECTRO}.issubset(applied_element):
            applied_element.remove(ElementType.DENDRO)
            applied_element.remove(ElementType.ELECTRO)
            yield {"DENDRO": "+1", "ELECTRO": "+1", "reaction": "CATALYZE"}
            self.handle_state(player, player.get_active_character_obj(), {"Catalyzing Field": 2})
        elif ElementType.ANEMO in applied_element:
            applied_element.remove(ElementType.ANEMO)
            elements = list(applied_element)
            for element in elements:
                if element != ElementType.DENDRO:
                    applied_element.remove(element)
                    yield {element.name + "_DMG": 1, "reaction": "SWIRL", "swirl_element": element.name}
                    break
        elif ElementType.GEO in applied_element:
            applied_element.remove(ElementType.GEO)
            elements = list(applied_element)
            for element in elements:
                if element != ElementType.DENDRO:
                    applied_element.remove(element)
                    yield {"GEO": "+1", "reaction": "CRYSTALLIZE", "crystallize_element": element.name}
                    self.add_modify(player, trigger_obj, [{"name": "CRYSTALLIZE_0",
                                                           "trigger_time": "element_reaction",
                                                           "condition":[],
                                                           "effect": {"SHIELD": {"name": "CRYSTALLIZE_SHIELD",
                                                                                 "shield": 1,
                                                                                 "effect_obj":"ACTIVE"}},
                                                           "effect_obj": "ACTIVE",
                                                           "store": "TEAM",
                                                           "be_added": [{"stack": 2}],
                                                           "time_limit":{"IMMEDIATE": 1}}])
                    break
        else:
            yield {"reaction": None}
        trigger_obj.application = list(applied_element)
        self.send_effect_message("application", player, trigger_obj)
        self.invoke_modify("element_reaction", player, trigger_obj, only_invoker=True)
        yield

    @staticmethod
    def add_modify(player, invoker: Union[Character, Summon, Card], modifies:list):
        old_team_modifies_name = {}
        team_need_del_index = []
        for index, old_team_modify in enumerate(player.team_modifier):
            old_team_modifies_name.update({old_team_modify["name"]: index})
        old_invoker_modifies_name = {}
        invoker_need_del_index = []
        for index, old_invoker_modify in enumerate(invoker.modifies):
            old_invoker_modifies_name.update({old_invoker_modify["name"]: index})
        for modify in modifies:
            modify_name = modify["name"]
            store = modify["store"]
            if store == "SELF" or store == "select":
                if modify_name in old_invoker_modifies_name:
                    invoker_need_del_index.append(old_invoker_modifies_name[modify_name])
                invoker.modifies.append(modify)
            elif store == "TEAM":
                if modify_name in old_team_modifies_name:
                    team_need_del_index.append(old_team_modifies_name[modify_name])
                player.team_modifier.append(modify)
        sort_team_del_index = sorted(team_need_del_index, reverse=True)
        sort_invoker_del_index = sorted(invoker_need_del_index, reverse=True)
        for index in sort_team_del_index:
            player.team_modifier.pop(index)
        for index in sort_invoker_del_index:
            invoker.modifies.pop(index)

    def invoke_modify(self, operation:str, player, invoker: Union[Character, Card, Summon, None], only_invoker:bool = False, **kwargs):
        is_active = False
        is_character = False
        return_effect = {}
        if isinstance(invoker, Character):
            is_character = True
            if invoker.is_active:
                is_active = True
        if invoker is not None:
            need_remove = []
            for index, modify in enumerate(invoker.modifies):
                trigger_time = modify["trigger_time"]
                time_limit = modify["time_limit"]
                consume = False
                if self.modify_satisfy_condition(operation, player, invoker, modify, **kwargs):
                    effect_obj = modify["effect_obj"]
                    effect = modify["effect"]
                    kwargs, consume = self.handle_effect(player, invoker, effect, effect_obj, return_effect, **kwargs)
                if self.is_trigger_time(operation, trigger_time): # 重复检验了
                    if consume:
                        self.record.write("trigger %s, effect is %s" % (modify["name"], str(modify["effect"])))
                        consume_status = self.consume_modify_usage(modify)
                        if consume_status == "remove":
                            need_remove.append(index)
                    elif "IMMEDIATE" in time_limit:
                        need_remove.append(index)
            self.remove_modify(invoker.modifies, need_remove)
        if is_character:
            for state_name, state in invoker.state.items():
                consume_state = False
                for modify in state["modify"]:
                    if self.modify_satisfy_condition(operation, player, invoker, modify, **kwargs):
                        effect_obj = modify["effect_obj"]
                        effect = modify["effect"]
                        kwargs, consume = self.handle_effect(player, invoker, effect, effect_obj, return_effect,
                                                             **kwargs)
                        if consume:
                            self.record.write("trigger %s, effect is %s" % (modify["name"], str(modify["effect"])))
                            if "time_limit" in modify:
                                self.consume_modify_usage(modify)
                            consume_state = True
                if consume_state:
                    kwargs.setdefault("have_consumed_state", [])
                    if state_name not in kwargs["have_consumed_state"]:
                        # TODO state usage
                        consume_state_status = self.consume_state_usage(state)
                        kwargs["have_consumed_state"].append(state_name)
        if only_invoker and invoker is None:
            need_remove = []
            for index, modify in enumerate(player.team_modifier):
                trigger_time = modify["trigger_time"]
                time_limit = modify["time_limit"]
                consume = False
                if self.modify_satisfy_condition(operation, player, invoker, modify, **kwargs):
                    effect_obj = modify["effect_obj"]
                    effect = modify["effect"]
                    kwargs, consume = self.handle_effect(player, invoker, effect, effect_obj, return_effect, **kwargs)
                if self.is_trigger_time(operation, trigger_time):  # 重复检验了
                    if consume:
                        self.record.write("trigger %s, effect is %s" % (modify["name"], str(modify["effect"])))
                        consume_status = self.consume_modify_usage(modify)
                        if consume_status == "remove":
                            need_remove.append(index)
                    elif "IMMEDIATE" in time_limit:
                        need_remove.append(index)
                self.remove_modify(player.team_modifier, need_remove)
            for state_name, state in player.team_state.items():
                consume_state = False
                for modify in state["modify"]:
                    if self.modify_satisfy_condition(operation, player, invoker, modify, **kwargs):
                        effect_obj = modify["effect_obj"]
                        consume_state = True
                        effect = modify["effect"]
                        kwargs, consume = self.handle_effect(player, invoker, effect, effect_obj, return_effect,
                                                             **kwargs)
                        if consume:
                            self.record.write("trigger %s, effect is %s" % (modify["name"], str(modify["effect"])))
                            if "time_limit" in modify:
                                self.consume_modify_usage(modify)
                            consume_state = True
                if consume_state:
                    kwargs.setdefault("have_consumed_state", [])
                    if state_name not in kwargs["have_consumed_state"]:
                        # TODO state usage
                        consume_state_status = self.consume_state_usage(state)
                        kwargs["have_consumed_state"].append(state_name)
        if not only_invoker:
            if is_active:
                self.invoke_modify(operation, player, None, only_invoker=True, **kwargs)
            for summon in player.summons:
                self.invoke_modify(operation, player, summon, only_invoker=True, **kwargs)
            for support in player.supports:
                self.invoke_modify(operation, player, support, only_invoker=True, **kwargs)
        self.record.flush()
        if "cost" in kwargs:
            return_effect["cost"] = kwargs["cost"]
        if "damage" in kwargs:
            if "damage_multiple" in return_effect:
                kwargs["damage"] = eval(str(kwargs["damage"]) + return_effect["damage_multiple"])
            return_effect["damage"] = -(-kwargs["damage"] // 1)  # ceil
        if "hurt" in kwargs:
            kwargs["hurt"] = max(kwargs["hurt"], 0)
            if "hurt_multiple" in return_effect:
                kwargs["hurt"] = eval(str(kwargs["hurt"]) + return_effect["hurt_multiple"])
            return_effect["hurt"] = -(-kwargs["hurt"] // 1)  # ceil
        if "change_cost" in kwargs:
            return_effect["change_cost"] = kwargs["change_cost"]
        if "change_action" in kwargs:
            return_effect["change_action"] = kwargs["change_action"]
        return return_effect

    def handle_effect(self, player, invoker, effect, effect_obj, return_effect, **kwargs):
        consume = False
        if effect_obj == "COUNTER":
            if isinstance(invoker, Character) or isinstance(invoker, Card):
                for counter_name, counter_change in effect.items():
                    if counter_name in invoker.counter:
                        if isinstance(counter_change, str):
                            invoker.counter[counter_name] += eval(counter_change)
                        else:
                            invoker.counter[counter_name] = counter_change
                        consume |= True
        else:
            if "REROLL" in effect:
                value = effect["REROLL"]
                if isinstance(value, str):
                    return_effect.setdefault("REROLL", 0)
                    return_effect["REROLL"] += eval(value)
                    consume |= True
                elif isinstance(value, int):
                    for _ in range(value):
                        asyncio.run(self.ask_player_reroll_dice(player))
                    consume |= True
            elif "FIXED_DICE" in effect:
                return_effect.setdefault("FIXED_DICE", [])
                return_effect["FIXED_DICE"] += effect["FIXED_DICE"]
                consume |= True
            elif "USE_SKILL" in effect:
                if effect_obj == "SELF" and isinstance(invoker, Character):
                    self.handle_skill(player, invoker, effect["USE_SKILL"], have_been_cost=True)
                    consume |= True
            elif "CHANGE_COST" in effect:
                if "cost" in kwargs:
                    cost = kwargs["cost"]
                    cost_change = eval(effect["CHANGE_COST"])
                    if "ANY" in cost:
                        if cost["ANY"] > 0 or cost_change > 0:
                            cost["ANY"] += cost_change
                            consume |= True
            elif "CHANGE_ACTION" in effect:
                if "change_action" in kwargs:
                    if kwargs["change_action"] != effect["CHANGE_ACTION"]:
                        kwargs["change_action"] = effect["CHANGE_ACTION"]
                        consume |= True
            elif "SKILL_ADD_ENERGY" in effect:
                if "add_energy" in kwargs:
                    kwargs["add_energy"] = kwargs["add_energy"]
                    consume |= True
            elif set(effect.keys()) & {"COST_ANY", "COST_PYRO", "COST_HYDRO", "COST_ELECTRO", "COST_CRYO",
                                              "COST_DENDRO", "COST_ANEMO", "COST_GEO", "COST_ALL", "COST_ELEMENT"}:
                if "cost" in kwargs:
                    cost: dict = kwargs["cost"]
                    effect_type = set(effect.keys()) & {"COST_ANY", "COST_PYRO", "COST_HYDRO", "COST_ELECTRO", "COST_CRYO",
                                              "COST_DENDRO", "COST_ANEMO", "COST_GEO", "COST_ALL", "COST_ELEMENT"}
                    effect_type = list(effect_type)[0]
                    effect_value = effect[effect_type]
                    element_type = effect_type.replace("COST_", "")
                    if element_type in ElementType.__members__:
                        if element_type in cost:
                            cost[element_type] += eval(effect_value)
                            if cost[element_type] <= 0:
                                cost.pop(element_type)
                                consume |= True
                    elif element_type == "ANY":
                        if element_type in cost:
                            cost[element_type] += eval(effect_value)
                            if cost[element_type] <= 0:
                                cost.pop(element_type)
                                consume |= True
                    elif element_type == "ELEMENT":
                        consume |= False
                        for element in ['CRYO', 'HYDRO', 'PYRO', 'ELECTRO', 'GEO', 'DENDRO', 'ANEMO']:
                            if element in cost:
                                cost[element] += eval(effect_value)
                                consume |= True
                                if cost[element] <= 0:
                                    cost.pop(element)
                                break
                    elif element_type == "ALL":  # 暂时只写same
                        if "SAME" in cost:
                            cost["SAME"] += eval(effect_value)
                            if cost["SAME"] <= 0:
                                cost.pop("SAME")
                                consume |= True
            elif "DMG" in effect:
                effect_value = effect["DMG"]
                if "damage" in kwargs:
                    if effect_value.startswith("*") or effect_value.startswith("/"):
                        return_effect["damage_multiple"] = effect_value
                    else:
                        kwargs["damage"] += eval(effect_value)
                    consume |= True
            elif "HURT" in effect:
                effect_value = effect["HURT"]
                if "hurt" in kwargs:
                    if effect_value.startswith("*") or effect_value.startswith("/"):
                        return_effect["hurt_multiple"] = effect_value
                        consume |= True
                    else:
                        hurt_change = eval(effect_value)
                        if kwargs["hurt"] > 0 or hurt_change > 0:
                            kwargs["hurt"] += eval(effect_value)
                            kwargs["hurt"] = max(kwargs["hurt"], 0)
                            consume |= True
            elif "SHIELD" in effect:
                if effect_obj == "SELF":
                    if isinstance(invoker, Character):
                        invoker.state.setdefault("SHIELD", []).append(effect["SHIELD"])
                elif effect_obj == "TEAM" or effect_obj == "ACTIVE":
                    player.team_state.setdefault("SHIELD", []).append(effect["SHIELD"])
                consume |= True
            elif "INFUSION" in effect:
                if effect_obj == "SELF":
                    if isinstance(invoker, Character):
                        invoker.state.setdefault("INFUSION", []).append(effect["INFUSION"])
                elif effect_obj == "TEAM" or effect_obj == "ACTIVE":
                    player.team_state.setdefault("INFUSION", []).append(effect["INFUSION"])
                consume |= True
            elif "ADD_MODIFY" in effect:
                self.add_modify(player, invoker, effect["ADD_MODIFY"])
            elif set(effect.keys()) & {"HYDRO_DMG", "GEO_DMG", "ELECTRO_DMG","DENDRO_DMG", "PYRO_DMG", "PHYSICAL_DMG",
                                    "CRYO_DMG", "ANEMO_DMG", "PIERCE_DMG"}:
                attack_type = set(effect.keys()) & {"HYDRO_DMG", "GEO_DMG", "ELECTRO_DMG","DENDRO_DMG", "PYRO_DMG", "PHYSICAL_DMG",
                                    "CRYO_DMG", "ANEMO_DMG", "PIERCE_DMG"}
                attack_type = list(attack_type)[0]
                element_type = attack_type.replace("_DMG", "")
                if effect_obj == "OPPOSE_ALL":
                    oppose: Player = self.get_one_oppose(player)
                    for character in oppose.characters:
                        self.handle_damage(player, None, character, {element_type: effect[attack_type]})
                elif effect_obj == "OPPOSE":
                    self.handle_damage(player, None, "team", {element_type: effect[attack_type]})
                elif effect_obj == "SELF":
                    # TODO 待确认
                    self.handle_damage(player, None, invoker, {element_type: effect[attack_type]})
            elif "DRAW_CARD" in effect:
                card = effect["DRAW_CARD"]
                if isinstance(card, int):
                    player.draw(card)
                    cards = self.get_player_hand_card_info(player)
                    self.send_effect_message("add_card", player, invoker, card_name=cards[-card:], card_num=len(cards))
                else:
                    if card.startswith("TYPE_"):
                        card_type = card.replace("TYPE_", "")
                        player.draw_type(card_type)
                        cards = self.get_player_hand_card_info(player)
                        self.send_effect_message("add_card", player, invoker, card_name=cards[-1:], card_num=len(cards))
            elif "ADD_CARD" in effect:
                player.append_hand_card(effect["ADD_CARD"])
                cards = self.get_player_hand_card_info(player)
                self.send_effect_message("add_card", player, invoker, card_name=cards[-1:], card_num=len(cards))
            elif "APPEND_DICE" in effect:
                dices = effect["APPEND_DICE"]
                if isinstance(dices, list):
                    for dice in dices:
                        if dice == "RANDOM":
                            player.append_random_dice()
                        elif dice == "BASE":
                            player.append_base_dice()
                        else:
                            player.append_special_dice(dice)
                    self.send_effect_message("dice", player, None)
                else:
                    if dices == "RANDOM":
                        player.append_random_dice()
                    elif dices == "BASE":
                        player.append_base_dice()
                    else:
                        player.append_special_dice(dices)
                    self.send_effect_message("dice", player, None)
            elif "CHANGE_CHARACTER" in effect:
                if effect_obj == "OPPOSE":
                    oppose  = self.get_one_oppose(player)
                    change_from = oppose.get_active_character_obj()
                    oppose.auto_change_active(effect["CHANGE_CHARACTER"])
                    change_to = oppose.get_active_character_obj()
                    if change_from != change_to:
                        self.invoke_modify("change_from", oppose, change_from, change_action="fast", change_cost={})
                        self.invoke_modify("change_to", oppose, change_to, change_action="fast", change_cost={})
                        self.send_effect_message("change_active", oppose, None,
                                                 change_from=oppose.characters.index(change_from),
                                                 change_to=oppose.characters.index(change_to))
                elif effect_obj == "ALL":
                    change_from = player.get_active_character_obj()
                    player.auto_change_active(effect["CHANGE_CHARACTER"])
                    change_to = player.get_active_character_obj()
                    if change_from != change_to:
                        self.invoke_modify("change_from", player, change_from, change_action="fast", change_cost={})
                        self.invoke_modify("change_to", player, change_to, change_action="fast", change_cost={})
                        self.send_effect_message("change_active", player, None,
                                                 change_from=player.characters.index(change_from),
                                                 change_to=player.characters.index(change_to))
            elif "HEAL" in effect:
                heal = effect["HEAL"]
                if effect_obj == "ACTIVE":
                    active = player.get_active_character_obj()
                    active.change_hp(heal)
                    self.send_effect_message("hp", player, active)
                elif effect_obj == "STANDBY":
                    standby = player.get_standby_obj()
                    for obj in standby:
                        obj.change_hp(heal)
                        self.send_effect_message("hp", player, obj)
                elif effect_obj == "SELF":
                    if isinstance(invoker, Character):
                        invoker.change_hp(heal)
                        self.send_effect_message("hp", player, invoker)
                elif isinstance(effect_obj, Character):
                    effect_obj.change_hp(heal)
                    self.send_effect_message("hp", player, effect_obj)
                elif effect_obj == "ALL":
                    characters = player.characters
                    for index, character in enumerate(characters):
                        character.change_hp(heal)
                        self.send_effect_message("hp", player, character)
            elif "APPLICATION" in effect:
                element = effect["APPLICATION"]
                if effect_obj == "ACTIVE":
                    self.handle_element_reaction(player, player.get_active_character_obj(), element)
            elif "CHANGE_ENERGY" in effect:
                if effect_obj == "ACTIVE":
                    active = player.get_active_character_obj()
                    active.change_energy(effect["CHANGE_ENERGY"])
                    self.send_effect_message("energy", player, active)
        return kwargs, consume

    @staticmethod
    def consume_modify_usage(modify, operation="use"):
        time_limit = modify["time_limit"]
        if operation == "use":
            if "USAGE" in time_limit:
                time_limit["USAGE"] -= 1
                if time_limit["USAGE"] <= 0:
                    return "remove"
            if "ROUND" in time_limit:
                time_limit["ROUND"][1] -= 1
            if "IMMEDIATE" in time_limit:
                return "remove"
        elif operation == "end":
            if "ROUND" in time_limit:
                time_limit["ROUND"][1] = time_limit["ROUND"][0]
            if "DURATION" in time_limit:
                time_limit["DURATION"] -= 1
                if time_limit["DURATION"] == 0:
                    return "remove"

    def consume_state_usage(self, state, operation="use"):
        time_limit = state["time_limit"]
        if operation == "use":
            if "USAGE" in time_limit:
                time_limit["USAGE"] -= 1
                if time_limit["USAGE"] <= 0:
                    return "remove"
                return time_limit["USAGE"]
            if "ROUND" in time_limit:
                time_limit["ROUND"][1] -= 1
                if time_limit["ROUND"][1] == 0:
                    return "use_up"
            if "IMMEDIATE" in time_limit:
                return "remove"
        elif operation == "end":
            if "ROUND" in time_limit:
                time_limit["ROUND"][1] = time_limit["ROUND"][0]
                return "activate"
            if "DURATION" in time_limit:
                time_limit["DURATION"] -= 1
                if time_limit["DURATION"] == 0:
                    return "remove"
            for modify in state["modify"]:
                if "time_limit" in modify:
                    self.consume_modify_usage(modify, "end")

    @staticmethod
    def remove_modify(modifies: list, need_remove_indexes: list):
        if need_remove_indexes:
            sort_index = sorted(need_remove_indexes, reverse=True)
            for index in sort_index:
                modifies.pop(index)

    def send_effect_message(self, change_type:str, player, invoker, **kwargs):
        player_index = self.players.index(player)
        if change_type == "hp":
            position = player.characters.index(invoker)
            hp = invoker.get_hp()
            change_hp_message = {"message": "change_hp",
                                 "position": position,
                                 "hp": hp}
            self.send(change_hp_message, self.client_socket[player_index])
            change_hp_message = {"message": "change_oppose_hp",
                                 "position": player.current_character,
                                 "hp": hp}
            for client in self.get_oppose_client(player_index):
                self.send(change_hp_message, client)
        elif change_type == "application":
            position = player.characters.index(invoker)
            application = [elementType.name.lower() for elementType in invoker.application]
            application_message = {"message": "change_application", "position": position,
                                   "application": application}
            self.send(application_message, self.client_socket[player_index])
            application_message = {"message": "oppose_change_application", "position": position,
                                   "application": application}
            for client in self.get_oppose_client(player_index):
                self.send(application_message, client)
        elif change_type == "equip": # kwargs: equip
            position = player.characters.index(invoker)
            equip = kwargs["equip"]
            update_equip_message = {"message": "change_equip", "position": position,
                                    "equip": equip}
            self.send(update_equip_message, self.client_socket[player_index])
            update_equip_message = {"message": "change_oppose_equip", "position": position, "equip": equip}
            for client in self.get_oppose_client(player_index):
                self.send(update_equip_message, client)
        elif change_type == "energy":
            char_index = player.characters.index(invoker)
            energy = (invoker.get_energy(), invoker.max_energy)
            change_energy_message = {"message": "change_energy", "position": char_index,
                                     "energy": energy}
            self.send(change_energy_message, self.client_socket[player_index])
            change_energy_message = {"message": "change_oppose_energy", "position": char_index,
                                     "energy": energy}
            for client in self.get_oppose_client(player_index):
                self.send(change_energy_message, client)
        elif change_type == "state":
            pass
        elif change_type == "infusion":
            pass
        elif change_type == "change_active": # kwargs: change_from, change_to
            from_index = kwargs["change_from"]
            to_index = kwargs["change_to"]
            choose_message = {"message": "oppose_change_active", "from_index": from_index, "to_index": to_index}
            for client in self.get_oppose_client(player_index):
                self.send(choose_message, client)
            choose_message = {"message": "player_change_active", "from_index": from_index, "to_index": to_index}
            self.send(choose_message, self.client_socket[player_index])
            clear_skill_message = {"message": "clear_skill"}
            self.send(clear_skill_message, self.client_socket[player_index])
            active = player.get_active_character_obj()
            skill = active.get_skills_type()
            init_skill_message = {"message": "init_skill", "skills": skill}
            self.send(init_skill_message, self.client_socket[player_index])
        elif change_type == "dice":
            dices = self.get_player_dice_info(player)
            dice_message = {"message": "clear_dice"}
            self.send(dice_message, self.client_socket[player_index])
            dice_message = {"message": "show_dice", "dices": dices}
            self.send(dice_message, self.client_socket[player_index])
            dice_num_message = {"message": "show_dice_num", "num": len(dices)}
            self.send(dice_num_message, self.client_socket[player_index])
            dice_num_message = {"message": "show_oppose_dice_num", "num": len(dices)}
            for client in self.get_oppose_client(player_index):
                self.send(dice_num_message, client)
        elif change_type == "clear_dice":
            dice_message = {"message": "clear_dice"}
            self.send(dice_message, self.client_socket[player_index])
            dice_num_message = {"message": "show_dice_num", "num": ""}
            self.send(dice_num_message, self.client_socket[player_index])
            dice_num_message = {"message": "show_oppose_dice_num", "num": ""}
            for client in self.get_oppose_client(player_index):
                self.send(dice_num_message, client)
        elif change_type == "add_card": # kwargs: card_name, card_num
            add_card_message = {"message": "add_card", "card_name": kwargs["card_name"]}
            self.send(add_card_message, self.client_socket[player_index])
            oppo_card_num_message = {"message": "oppose_card_num", "num": kwargs["card_num"]}
            for client in self.get_oppose_client(player_index):
                self.send(oppo_card_num_message, client)
        elif change_type == "remove_card": # kwargs: card_index
            remove_card_message = {"message": "remove_card", "card_index": kwargs["card_index"]}
            self.send(remove_card_message, self.client_socket[player_index])
            oppo_card_num_message = {"message": "oppose_card_num", "num": len(self.get_player_hand_card_info(player))}
            for client in self.get_oppose_client(player_index):
                self.send(oppo_card_num_message, client)

    @staticmethod
    def is_trigger_time(operation, modify_tag):
        if modify_tag == "any":
            return True
        else:
            if operation == modify_tag:
                return True
            # if operation == "init_draw":
            #     if modify_tag in ["init_draw"]:
            #         return True
            # elif operation == "start":
            #     if modify_tag in ["start"]:
            #         return True
            # elif operation == "roll":
            #     if modify_tag in ["roll"]:
            #         return True
            # elif operation == "action":
            #     if modify_tag in ["action"]:
            #         return True
            # elif operation == "use_skill":
            #     if modify_tag in ["use_skill", "cost"]:
            #         return True
            # elif operation == "change_cost":
            #     if modify_tag in ["change_cost", "cost"]:
            #         return True
            # elif operation == "card_cost":
            #     if modify_tag in ["card_cost", "cost"]:
            #         return True
            # elif operation == "after_using_skill":
            #     if modify_tag in ["after_using_skill"]:
            #         return True
            # elif operation == "attack":
            #     if modify_tag in ["attack", "combat"]:
            #         return True
            # elif operation == "defense":
            #     if modify_tag in ["defense", "combat"]:
            #         return True
            # elif operation == "extra_attack":
            #     if modify_tag in ["extra_attack"]:
            #         return True
            # elif operation == "after_attack":
            #     if modify_tag in ["after_attack"]:
            #         return True
            # elif operation == "play_card":
            #     if modify_tag in ["play_card"]:
            #         return True
            # elif operation == "change_from":
            #     if modify_tag in ["change_from"]:
            #         return True
            # elif operation == "change_to":
            #     if modify_tag in ["change_to"]:
            #         return True
            # elif operation == "after_change":
            #     if modify_tag in ["after_change"]:
            #         return True
            # elif operation == "pierce":
            #     if modify_tag in ["pierce"]:
            #         return True
            # elif operation == "end":
            #     if modify_tag in ["stage", "end"]:
            #         return True
        return False

    def check_condition(self, player, invoker, condition, **kwargs):
        special = []
        if condition:
            for each in condition:
                if isinstance(each, str):
                    if each.startswith("STAGE_"):
                        condition_stage = each.replace("STAGE_", "")
                        if condition_stage == self.stage.name:
                            continue
                        else:
                            return False
                    # elif each == "BE_CHANGED_AS_ACTIVE":
                    #     if "change_to" in kwargs:
                    #         if kwargs["change_to"] == kwargs["invoke"]:
                    #             continue
                    #         else:
                    #             return False
                    #     else:
                    #         return False
                    # elif each == "CHANGE_TO_STANDBY" or each == "CHANGE_AVATAR":
                    #     if "change_from" in kwargs:
                    #         if kwargs["change_from"] == kwargs["invoke"]:
                    #             print(kwargs["change_from"].name, kwargs["invoke"].name)
                    #             continue
                    #         else:
                    #             return False
                    #     else:
                    #         return False
                    elif each == "EXCLUSIVE":
                        if "exclusive" in kwargs:
                            return False
                        else:
                            special.append("EXCLUSIVE")
                            continue
                    elif each == "BEING_HIT":
                        if "hurt" in kwargs:
                            continue
                        else:
                            return False
                    elif each == "SKILL":
                        if "skill_type" in kwargs:
                            continue
                        else:
                            return False
                    elif each == "NORMAL_ATTACK":
                        if "skill_type" in kwargs:
                            if "Normal Attack" in kwargs["skill_type"]:
                                continue
                            else:
                                return False
                        else:
                            return False
                    elif each == "ELEMENTAL_SKILL":
                        if "skill_type" in kwargs:
                            if "Elemental Skill" in kwargs["skill_type"]:
                                continue
                            else:
                                return False
                        else:
                            return False
                    elif each == "ELEMENTAL_BURST":
                        if "skill_type" in kwargs:
                            if "Elemental Burst" in kwargs["skill_type"]:
                                continue
                            else:
                                return False
                        else:
                            return False
                    elif each == "ELEMENT_DMG":
                        if "damage" in kwargs and "element" in kwargs:
                            if kwargs["element"] != "PHYSICAL" and kwargs["element"] != "PIERCE":
                                continue
                            else:
                                return False
                        else:
                            return False
                    elif each == "ELEMENT_HURT":
                        if "hurt" in kwargs and "element" in kwargs:
                            if kwargs["element"] != "PHYSICAL" and kwargs["element"] != "PIERCE":
                                continue
                            else:
                                return False
                        else:
                            return False
                    elif each == "ELEMENT_REACTION":
                        if "reaction" in kwargs:
                            if kwargs["reaction"] is not None:
                                continue
                            else:
                                return False
                        else:
                            return False
                    # elif each == "SELF_HURT":
                    #     special.append("SELF_HURT")
                    elif each == "SWIRL":
                        if "reaction" in kwargs:
                            if kwargs["reaction"] == "SWIRL":
                                continue
                            else:
                                return False
                    elif each == "IS_ACTIVE":
                        if isinstance(invoker, Character):
                            if invoker.is_active:
                                continue
                        return False
                    elif each == "IS_NOT_ACTIVE":
                        if isinstance(invoker, Character):
                            if not invoker.is_active:
                                continue
                        return False
                    elif each == "GET_MOST_HURT":
                        special.append({"OBJ": player.get_most_hurt()})
                    elif each == "PYRO_RELATED":
                        if "reaction" in kwargs:
                            if kwargs["reaction"] in ["MELT", "VAPORIZE", "OVERLOADED", "BURNING"]:
                                continue
                            elif kwargs["reaction"] == "SWIRL":
                                if kwargs["swirl_element"] == "PYRO":
                                    continue
                                else:
                                    return False
                            elif kwargs["reaction"] == "CRYSTALLIZE":
                                if kwargs["crystallize_element"] == "PYRO":
                                    continue
                                else:
                                    return False
                            else:
                                return False
                    elif each == "HYDRO_RELATED":
                        if "reaction" in kwargs:
                            if kwargs["reaction"] in ["VAPORIZE", "FROZEN", "ELECTRO_CHARGE", "BLOOM"]:
                                continue
                            elif kwargs["reaction"] == "SWIRL":
                                if kwargs["swirl_element"] == "HYDRO":
                                    continue
                                else:
                                    return False
                            elif kwargs["reaction"] == "CRYSTALLIZE":
                                if kwargs["crystallize_element"] == "HYDRO":
                                    continue
                                else:
                                    return False
                            else:
                                return False
                    elif each == "ELECTRO_RELATED":
                        if "reaction" in kwargs:
                            if kwargs["reaction"] in ["OVERLOADED", "SUPER_CONDUCT", "ELECTRO_CHARGE", "CATALYZE"]:
                                continue
                            elif kwargs["reaction"] == "SWIRL":
                                if kwargs["swirl_element"] == "ELECTRO":
                                    continue
                                else:
                                    return False
                            elif kwargs["reaction"] == "CRYSTALLIZE":
                                if kwargs["crystallize_element"] == "ELECTRO":
                                    continue
                                else:
                                    return False
                            else:
                                return False
                    elif each == "CRYO_RELATED":
                        if "reaction" in kwargs:
                            if kwargs["reaction"] in ["MELT", "SUPER_CONDUCT", "FROZEN", "SUPER_CONDUCT"]:
                                continue
                            elif kwargs["reaction"] == "SWIRL":
                                if kwargs["swirl_element"] == "CRYO":
                                    continue
                                else:
                                    return False
                            elif kwargs["reaction"] == "CRYSTALLIZE":
                                if kwargs["crystallize_element"] == "CRYO":
                                    continue
                                else:
                                    return False
                            else:
                                return False
                    elif each == "DENDRO_RELATED":
                        if "reaction" in kwargs:
                            if kwargs["reaction"] in ["BURNING", "BLOOM", "CATALYZE"]:
                                continue
                            else:
                                return False
                    elif each == "ANEMO_RELATED":
                        if "reaction" in kwargs:
                            if kwargs["reaction"] == "SWIRL":
                                continue
                            else:
                                return False
                    elif each == "GEO_RELATED":
                        if "reaction" in kwargs:
                            if kwargs["reaction"] == "CRYSTALLIZE":
                                continue
                            else:
                                return False
                    # elif each == "FORCE":
                    #     special.append("FORCE")
                    elif each == "HAVE_SHIELD":
                        if isinstance(invoker, Character):
                            if "SHIELD" in invoker.state:
                                continue
                            elif invoker.is_active:
                                if "SHIELD" in player.team_state:
                                    continue
                        return False
                    # elif each == "REMOVE":
                    #     if "NEED_REMOVE" not in special:
                    #         return False
                    #     else:
                    #         special.append("REMOVE")
                    elif each == "REPLACE":
                        # TODO
                        pass
                    elif each == "DIFFERENCE_FIRST":
                        # TODO
                        pass
                    elif each == "OPPOSE_DIE":
                        pass
                    else:
                        return False
                elif isinstance(each, dict):
                    logic = each["logic"]
                    if logic == "check":
                        check_type = each["what"]
                        if check_type == "counter":
                            if invoker is not None:
                                attribute = each["whose"]
                                if attribute in invoker.counter:
                                    num = invoker.counter[attribute]
                                    require = each["condition"]
                                    # TODO special const
                                    if require.startswith("__"):
                                        pass
                                    if self.compare(each["operator"], num, require):
                                        continue
                        elif check_type == "element":
                            attribute = each["whose"]
                            require = each["condition"]
                            if attribute == "hurt":
                                if "hurt" in kwargs and "element" in kwargs:
                                    if self.compare(each["operator"], kwargs["element"], require):
                                        continue
                            elif attribute == "attack":
                                if "damage" in kwargs and "element" in kwargs:
                                    if self.compare(each["operator"], kwargs["element"], require):
                                        continue
                            elif attribute == "self":
                                if isinstance(invoker, Character):
                                    element = invoker.element
                                    if self.compare(each["operator"], element, require):
                                        continue
                        elif check_type == "weapon":
                            attribute = each["whose"]
                            if attribute == "active":
                                weapon = player.get_active_character_obj().weapon.name
                            else:
                                weapon = "None"
                            require = each["condition"]
                            if self.compare(each["operator"], weapon, require):
                                continue
                        elif check_type == "hurt":
                            if "hurt" in kwargs:
                                hurt = kwargs["hurt"]
                                require = each["condition"]
                                if self.compare(each["operator"], hurt, require):
                                    continue
                        elif check_type == "hp":
                            attribute = each["whose"]
                            require = each["condition"]
                            if attribute == "active":
                                hp = player.get_active_character_obj().get_hp()
                                if self.compare(each["operator"], hp, require):
                                    continue
                            elif attribute == "oppose":
                                hp = self.get_one_oppose(player).get_active_character_obj().get_hp()
                                if self.compare(each["operator"], hp, require):
                                    continue
                        elif check_type == "dice_num":
                            require = each["condition"]
                            dice_num = len(player.dices)
                            if self.compare(each["operator"], dice_num, require):
                                continue
                        elif check_type == "ENERGY":
                            if isinstance(invoker, Character):
                                energy = invoker.get_energy()
                                require = each["condition"]
                                if self.compare(each["operator"], energy, require):
                                    continue
                        return False
                    elif logic == "HAVE_CARD":
                        cards = player.hand_cards
                        if each[1] in cards:
                            continue
                        else:
                            return False
                    elif logic == "DONT_HAVE_CARD":
                        cards = player.hand_cards
                        if each[1] in cards:
                            return False
                        else:
                            continue
                    elif logic == "HAVE_STATE":
                        whose = each["whose"]
                        state_name = each["what"]
                        if whose == "self":
                            if isinstance(invoker, Character):
                                if state_name in invoker.state:
                                    continue
                        elif whose == "team":
                            if state_name in player.team_state:
                                continue
                        return False
                    elif logic == "HAVE_MODIFY":
                        whose = each["whose"]
                        state_name = each["what"]
                        have_modify = False
                        if whose == "self":
                            state_range = invoker.modifies
                        elif whose == "team":
                            state_range = player.team_modifier
                        for modify in state_range:
                            if modify["name"] == state_name:
                                have_modify = True
                                break
                        if have_modify:
                            continue
                        return False
                    elif logic == "HAVE_SUMMON":
                        summons = player.summons
                        summon_name = each["what"]
                        have_summon = False
                        for summon in summons:
                            if summon_name == summon.get_name():
                                have_summon = True
                                break
                        if have_summon:
                            continue
                        return False
                    elif logic == "sum":
                        check_type = each["what"]
                        if check_type == "summon_num":
                            special.append({"NUMBER": len(player.summons)})
                        elif check_type == "counter":
                            attribute = each["whose"]
                            if attribute in invoker.counter:
                                special.append({"NUMBER": invoker.counter[attribute]})
                        elif check_type == "nation":
                            nation = player.get_character_nation()
                            attribute = each["whose"]
                            special.append({"NUMBER": nation.count(attribute)})
                        elif check_type == "card_cost":
                            # TODO
                            card_cost = kwargs["card_cost"]
                            cost = 0
                            for key, value in card_cost.items():
                                cost += value
                            special.append({"NUMBER": cost})
                    elif logic == "GET_ELEMENT":
                        what = each["what"]
                        if what == "swirl":
                            if "swirl_element" in kwargs:
                                special.append({"ELEMENT": kwargs["swirl_element"]})
                        elif what == "active":
                            element = player.get_active_character_obj().element
                            special.append({"ELEMENT": element})
                        elif what == "self":
                            element = invoker.element
                            special.append({"ELEMENT": element})
                        return False
                    elif logic == "EQUIP":
                        if "card_tag" in kwargs:
                            if each["what"] in kwargs["card_tag"]:
                                continue
                            else:
                                return False
                        else:
                            return False
                    elif logic == "PLAY_CARD":
                        if each["what"].startswith("TYPE_"):
                            tag = each["what"].replace("TYPE_", "")
                            if "card_tag" in kwargs:
                                if tag in kwargs["card_tag"]:
                                    continue
                                else:
                                    return False
                            else:
                                return False
                    elif logic == "COMPARE":
                        # TODO
                        two = [each[1], each[3]]
                        two_side = []
                        for each_side in two:
                            type_, attribute = each_side.split("_", 1)
                            if type_ == "SUMMON":
                                if attribute == "NUM":
                                    two_side.append({"NUMBER": len(player.summons)})
                            elif type_ == "COUNTER":
                                if attribute in kwargs["invoke"].counter:
                                    two_side.append({"NUMBER": kwargs["invoke"].counter[attribute]})
                            elif type_ == "NATION":
                                nation = player.get_character_nation()
                                two_side.append({"NUMBER": nation.count(attribute)})
                            elif type_ == "CARD":
                                if attribute == "COST":
                                    card_cost = kwargs["card_cost"]
                                    cost = 0
                                    for key, value in card_cost.items():
                                        cost += value
                                    two_side.append({"NUMBER": cost})
                            if eval(str(two_side[0]) + two[2] + str(two_side[1])):
                                continue
                            else:
                                return False
                    elif logic == "USE_SKILL":
                        if "skill_name" in kwargs:
                            if kwargs["skill_name"] == each["what"]:
                                continue
                            else:
                                return False
                        else:
                            return False
                    # elif each[0] == "NEED_REMOVE":
                    #     condition_state = check_condition([each[1]], game, **kwargs)
                    #     if not condition_state:
                    #         special.append("NEED_REMOVE")
                elif isinstance(each, list):
                    satisfy = False
                    for condition in each:
                        condition_state = self.check_condition(player, invoker, condition, **kwargs)
                        if condition_state:
                            if condition_state[1]:
                                special += condition_state[1]
                            satisfy = True
                            break
                    if not satisfy:
                        return False

        return True, special

    @staticmethod
    def compare(operator, left_value, right_value):
        if operator == "equal":
            if left_value == right_value:
                return True
        elif operator == "less":
            if left_value < right_value:
                return True
        elif operator == "large":
            if left_value > right_value:
                return True
        elif operator == "large_equal":
            if left_value >= right_value:
                return True
        elif operator == "not_equal":
            if left_value != right_value:
                return True
        elif operator == "less_equal":
            if left_value <= right_value:
                return True
        elif operator == "is": # 属于某个类别
            if right_value == "melee":
                if left_value in ["POLEARM", "SWORD", "CLAYMORE"]:
                    return True
            elif right_value == "even":
                if not left_value % 2:
                    return True
            elif right_value == "ELEMENT":
                if left_value in ["HYDRO", "GEO", "ELECTRO","DENDRO", "PYRO", "CRYO", "ANEMO"]:
                    return True
        return False

    def round_end_consume_modify(self):
        for player in self.players:
            for character in player.characters:
                need_remove_modifies = []
                for index, modify in enumerate(character.modifies):
                    consume_state = self.consume_modify_usage(modify, "end")
                    if consume_state == "remove":
                        need_remove_modifies.append(index)
                self.remove_modify(character.modifies, need_remove_modifies)
                for state in character.state:
                    # TODO 完善
                    consume_state = self.consume_state_usage(state, "end")
            need_remove_modifies = []
            for index, modify in enumerate(player.team_modifier):
                consume_state = self.consume_modify_usage(modify, "end")
                if consume_state == "remove":
                    need_remove_modifies.append(index)
            self.remove_modify(player.team_modifier, need_remove_modifies)
            for state in player.team_state:
                # TODO 完善
                consume_state = self.consume_state_usage(state, "end")
            for summon in player.summons:
                need_remove_modifies = []
                for index, modify in enumerate(summon.modifies):
                    consume_state = self.consume_modify_usage(modify, "end")
                    if consume_state == "remove":
                        need_remove_modifies.append(index)
                self.remove_modify(summon.modifies, need_remove_modifies)
            for support in player.supports:
                need_remove_modifies = []
                for index, modify in enumerate(support.modifies):
                    consume_state = self.consume_modify_usage(modify, "end")
                    if consume_state == "remove":
                        need_remove_modifies.append(index)
                self.remove_modify(support.modifies, need_remove_modifies)


# if __name__ == '__main__':
#     mode = "Game1"
#     state = pre_check(mode)
#     if isinstance(state, list):
#         error = " ".join(state)
#         print("以下卡牌不合法：%s" % error)
#     else:
#         game = Game(mode)
#         game.start_game()
