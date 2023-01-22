"""
(GAME_START)->DRAW->START->ROLL->ACTION->USE_SKILL->ATTACK->DEFENSE->EXTRA->END  ->(GAME_END)
                  ->STAGE               ->COST     ->COMBAT->COMBAT        ->STAGE
(GAME_START)->DRAW->START->ROLL         ->CHANGE_COST->CHANGE->END  ->(GAME_END)
                                        ->COST
(GAME_START)->DRAW->START->ROLL         ->CARD_COST->PLAY_CARD->END  ->(GAME_END)
                                        ->COST
DRAW      DRAW_NUM
          DRAW_TIMES

ROLL      ROLL_TIMES
          FIXED_DICE
          ROLL_NUM

DICE      REMOVE_DICE
          APPEND_DICE

CARD      APPEND_CARD
          DRAW_CARD
          REMOVE_CARD

SUPPORT   ADD_SUPPORT
          REMOVE_SUPPORT

SUMMON    ADD_SUMMON
          REMOVE_SUMMON

CHANGE    CHANGE_ACTION
          CHANGE_TO
          BE_CHANGED_AS
          CHANGE_COST

COST      CHANGE_COST
          SKILL_COST
          CARD_COST

USE_SKILL SKILL_COST
          ADD_ENERGY

COMBAT    ATTACK    DMG
                    CREATE_DMG
                    INFUSION
          DEFENSE   HURT
                    SHIELD
          HEAL
          SKILL
          COUNTER
          TRIGGER_SUMMON
          CONSUME_SUMMON_USAGE
STAGE     END
"""
from player import Player
from character import Character
from enums import EffectObj, TimeLimit, WeaponType
from game import Game


def add_modify(game: Game, invoker: Character, modify: list, modify_name: str, force=False):
    player = game.get_now_player()
    oppose = game.get_oppose()
    for index, each in enumerate(modify):
        if "IMMEDIATE" in each["time_limit"]:
            mod = append_modify([], (modify_name + "_" + str(index), each), force)
            invoke_modify(game, "none", invoker, modify=mod)
        else:
            effect_obj = each["effect_obj"]
            if EffectObj[effect_obj] == EffectObj.SELF:
                new_modifies = append_modify(invoker.modifies, (modify_name + "_" + str(index), each), force)
                invoker.modifies = new_modifies
            elif EffectObj[effect_obj] == EffectObj.NO_SELF:
                others = player.get_no_self_obj(invoker)
                for other in others:
                    new_modifies = append_modify(other.modifies, (modify_name + "_" + str(index), each), force)
                    other.modifies = new_modifies
            elif EffectObj[effect_obj] == EffectObj.OPPOSE_SELF:
                oppose_active = oppose.get_active_character_obj()
                new_modifies = append_modify(oppose_active.modifies, (modify_name + "_" + str(index), each), force)
                oppose_active.modifies = new_modifies
            elif EffectObj[effect_obj] == EffectObj.NO_OPPOSE_SELF:
                others = oppose.get_no_self_obj(invoker)
                for other in others:
                    new_modifies = append_modify(other.modifies, (modify_name + "_" + str(index), each), force)
                    other.modifies = new_modifies
            elif EffectObj[effect_obj] == EffectObj.OPPOSE_ACTIVE:
                new_modifies = append_modify(oppose.team_modifier, (modify_name + "_" + str(index), each), force)
                oppose.team_modifier = new_modifies
            else:
                new_modifies = append_modify(player.team_modifier, (modify_name + "_" + str(index), each), force)
                player.team_modifier = new_modifies


def append_modify(old_modify: list, new_modify: tuple[str, dict], force=False):
    new_modifies = old_modify
    need_del = []
    stack_count = []
    modify_name = new_modify[0]
    for index, modify in enumerate(old_modify):
        if modify_name in modify:
            if not force:
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
    modify = new_modify[1].copy()
    new_modifies.append({modify_name: modify})
    for i in need_del:
        new_modifies.pop(i)
    print(new_modifies)
    return new_modifies


def invoke_modify(game: Game, operation: str, invoker: Character, **kwargs):
    player = game.get_now_player()
    oppose = game.get_oppose()
    all_related_modifies = []
    modify_source = []
    need_remove_modifies = []
    left_effect = []
    if "modify" in kwargs:
        all_related_modifies = kwargs["modify"]
    if operation == "draw": # game -> effect
        for modify in player.team_modifier:
            for key, value in modify.items():
                if value["category"] == "draw" or value["category"] == "any":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "player"))
        for modify in invoker.modifies:
            for key, value in modify.items():
                if value["category"] == "draw" or value["category"] == "any":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "invoker"))
    elif operation == "start":  # game -> effect
        for modify in player.team_modifier:
            for key, value in modify.items():
                if value["category"] == "start" or value["category"] == "any" or value["category"] == "stage":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "player"))
        for modify in invoker.modifies:
            for key, value in modify.items():
                if value["category"] == "roll" or value["category"] == "any":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "invoker"))
    elif operation == "roll":  # game -> FIXED_DICE, REROLL
        for modify in player.team_modifier:
            for key, value in modify.items():
                if value["category"] == "roll" or value["category"] == "any":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "player"))
        for modify in invoker.modifies:
            for key, value in modify.items():
                if value["category"] == "roll" or value["category"] == "any":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "invoker"))
    elif operation == "action": # SKILL_NAME, game -> USE_SKILL, effect
        for modify in player.team_modifier:
            for key, value in modify.items():
                if value["category"] == "action" or value["category"] == "any":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "player"))
        for modify in invoker.modifies:
            for key, value in modify.items():
                if value["category"] == "action" or value["category"] == "any":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "invoker"))
    elif operation == "use_skill":  # SKILL_NAME, SKILL_TYPE, skill_cost, add_energy, game -> skill_cost, add_energy
        for modify in player.team_modifier:
            for key, value in modify.items():
                if value["category"] == "use_skill" or value["category"] == "any" or value["category"] == "cost":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "player"))
        for modify in invoker.modifies:
            for key, value in modify.items():
                if value["category"] == "use_skill" or value["category"] == "any" or value["category"] == "cost":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "invoker"))
    elif operation == "change_cost": # CHANGE_COST, change_from, change_to, game -> CHANGE_COST
        for modify in player.team_modifier:
            for key, value in modify.items():
                if value["category"] == "change_cost" or value["category"] == "any" or value["category"] == "cost":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "player"))
        for modify in invoker.modifies:
            for key, value in modify.items():
                if value["category"] == "change_cost" or value["category"] == "any" or value["category"] == "cost":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "invoker"))
    elif operation == "card_cost":  # card_cost, game -> card_cost
        for modify in player.team_modifier:
            for key, value in modify.items():
                if value["category"] == "card_cost" or value["category"] == "any" or value["category"] == "cost":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "player"))
        for modify in invoker.modifies:
            for key, value in modify.items():
                if value["category"] == "card_cost" or value["category"] == "any" or value["category"] == "cost":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "invoker"))
    elif operation == "attack":  # SKILL_NAME, SKILL_TYPE, damage, element, (reaction), game -> damage
        for modify in player.team_modifier:
            for key, value in modify.items():
                if value["category"] == "attack" or value["category"] == "any" or value["category"] == "combat":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "player"))
        for modify in invoker.modifies:
            for key, value in modify.items():
                if value["category"] == "attack" or value["category"] == "any" or value["category"] == "combat":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "invoker"))
    elif operation == "defense": # SKILL_TYPE, hurt, element, (reaction), game -> hurt
        for modify in oppose.team_modifier:
            for key, value in modify.items():
                if value["category"] == "defense" or value["category"] == "any" or value["category"] == "combat":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "oppose"))
        oppose_active = oppose.get_active_character_obj()
        for modify in oppose_active.modifies:
            for key, value in modify.items():
                if value["category"] == "defense" or value["category"] == "any" or value["category"] == "combat":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "oppose_active"))
    elif operation == "extra":  # game -> effect
        for modify in player.team_modifier:
            for key, value in modify.items():
                if value["category"] == "extra" or value["category"] == "any":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "player"))
        for modify in invoker.modifies:
            for key, value in modify.items():
                if value["category"] == "extra" or value["category"] == "any":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "invoker"))
    elif operation == "play_card":  # CARD_TAG, game -> effect
        for modify in player.team_modifier:
            for key, value in modify.items():
                if value["category"] == "play_card" or value["category"] == "any":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "player"))
        for modify in invoker.modifies:
            for key, value in modify.items():
                if value["category"] == "Play_card" or value["category"] == "any":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "invoker"))
    elif operation == "change":  # game, change_from, change_to -> change_action, change_to, change_cost
        for modify in player.team_modifier:
            for key, value in modify.items():
                if value["category"] == "change" or value["category"] == "any":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "player"))
        for modify in invoker.modifies:
            for key, value in modify.items():
                if value["category"] == "change" or value["category"] == "any":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "invoker"))
    elif operation == "end":  # game -> effect
        for modify in player.team_modifier:
            for key, value in modify.items():
                if value["category"] == "end" or value["category"] == "any" or value["category"] == "stage":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "player"))
        for modify in invoker.modifies:
            for key, value in modify.items():
                if value["category"] == "end" or value["category"] == "any" or value["category"] == "stage":
                    all_related_modifies.append(modify)
                    modify_source.append((key, "invoker"))
    for each in all_related_modifies:
        for modify_name, modify in each:
            condition = modify["condition"]
            satisfy_condition = check_condition(condition, **kwargs, invoke=invoker)
            if satisfy_condition:
                time_limit = modify["time_limit"]
                for limit_type, limit in time_limit.items():
                    if TimeLimit[limit_type] == TimeLimit.ROUND:
                        left_usage = time_limit[limit_type][1]
                        if left_usage <= 0:
                            satisfy_condition = False
                    else:  # 无限不用处理， 立即生效在add_modify时处理, 持续回合在回合结束时处理
                        break

def remove_modify():
    pass


def check_condition(condition, game:Game, **kwargs):
    special = []
    if condition:
        for each in condition:
            if isinstance(each, str):
                if each.startswith("STAGE_"):
                    condition_stage = each.replace("STAGE_", "")
                    if condition_stage == game.stage:
                        continue
                    else:
                        return False
                elif each == "BE_CHANGED_AS_ACTIVE":
                    if "change_to" in kwargs:
                        if kwargs["change_to"] == kwargs["invoke"]:
                            continue
                        else:
                            return False
                    else:
                        return False
                elif each == "CHANGE_TO_STANDBY" or each == "CHANGE_AVATAR":
                    if "change_from" in kwargs:
                        if kwargs["change_from"] == kwargs["invoke"]:
                            continue
                        else:
                            return False
                    else:
                        return False
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
                        continue
                    else:
                        return False
                elif each == "SELF_HURT":
                    special.append("SELF_HURT")
                elif each == "SWIRL":
                    if "reaction" in kwargs:
                        if kwargs["reaction"] == "SWIRL":
                            continue
                        else:
                            return False
                elif each == "IS_ACTIVE":
                    if game.get_now_player().get_active_character_obj() == kwargs["invoke"]:
                        continue
                    else:
                        return False
                elif each == "GET_MOST_HURT":
                    special.append({"OBJ": game.get_now_player().get_most_hurt()})
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
                elif each == "FORCE":
                    special.append("FORCE")
                elif each == "HAVE_SHIELD":
                    pass
                elif each == "REMOVE":
                    # TODO
                    pass
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
            elif isinstance(each, list):
                if each[0] == "CHECK":
                    or_condition: list[str] = each.copy().pop(0)
                    satisfy = False
                    for or_ in or_condition:
                        type_, attribute, compare = or_.split("_", 2)
                        if type_ == "COUNTER":
                            if attribute in kwargs["invoke"].counter:
                                num = kwargs["invoke"].counter[attribute]
                                if eval(str(num) + compare):
                                    satisfy = True
                                    break
                        elif type_ == "ELEMENT":
                            if attribute == "HURT":
                                if "hurt" in kwargs and "element" in kwargs:
                                    if kwargs["element"] == compare:
                                        satisfy = True
                                        break
                                    elif compare == "ELEMENT":
                                        if kwargs["element"] != "PHYSICAL" or kwargs["element"] != "PIERCE":
                                            satisfy = True
                                            break
                            elif attribute == "ATTACK":
                                if "damage" in kwargs and "element" in kwargs:
                                    if kwargs["element"] == compare:
                                        satisfy = True
                                        break
                                    elif compare == "ELEMENT":
                                        if kwargs["element"] != "PHYSICAL" or kwargs["element"] != "PIERCE":
                                            satisfy = True
                                            break
                            elif attribute == "SELF":
                                element = kwargs["invoke"].element
                                if element == compare:
                                    satisfy = True
                                    break
                        elif type_ == "WEAPON":
                            if attribute == "ACTIVE":
                                weapon = game.get_now_player().get_active_character_obj().weapon
                            else:
                                weapon = WeaponType.NONE
                            if compare == "MELEE":
                                if weapon.name in ["POLEARM", "SWORD", "CLAYMORE"]:
                                    satisfy = True
                                    break
                            else:
                                if weapon.name == compare:
                                    satisfy = True
                                    break
                        elif type_ == "HURT":
                            if "hurt" in kwargs:
                                if attribute == "ALL":
                                    if eval(str(kwargs["hurt"]) + compare):
                                        satisfy = True
                                        break
                                else:
                                    if "element" in kwargs:
                                        if attribute == kwargs["element"]:
                                            satisfy = True
                                            break
                        elif type_ == "HP":
                            if attribute == "ACTIVE":
                                hp = game.get_now_player().get_active_character_obj().get_hp()
                                if eval(str(hp) + compare):
                                    satisfy = True
                                    break
                            elif attribute == "OPPOSE":
                                hp = game.get_oppose().get_active_character_obj().get_hp()
                                if eval(str(hp) + compare):
                                    satisfy = True
                                    break
                        elif type_ == "DICE":
                            if attribute == "PLAYER":
                                dice_num = len(game.get_now_player().dices)
                                if eval(str(dice_num) + compare):
                                    satisfy = True
                                    break
                        elif type_ == "ENERGY":
                            if attribute == "NEW":
                                if "change_to" in kwargs:
                                    energy = kwargs["change_to"].energy
                                    if eval(str(energy) + compare):
                                        continue
                                    else:
                                        return False
                    if satisfy:
                        continue
                    else:
                        return False
                elif each[0] == "HAVE_CARD":
                    game: Game = kwargs["game"]
                    cards = game.get_now_player().hand_cards
                    if each[1] in cards:
                        continue
                    else:
                        return False
                elif each[0] == "DONT_HAVE_CARD":
                    cards = game.get_now_player().hand_cards
                    if each[1] in cards:
                        return False
                    else:
                        continue
                elif each[0] == "HAVE_STATE":
                    team_state = game.get_now_player().team_modifier
                    invoker_state = kwargs["invoke"].modifies
                    if each[1] in team_state or each[1] in invoker_state:
                        continue
                    else:
                        return False
                elif each[0] == "HAVE_SUMMON":
                    summons = game.get_now_player().summons
                    if each[1] in summons:
                        continue
                    else:
                        return False
                elif each[0] == "SUM":
                    type_, attribute = each[1].split("_", 1)
                    if type_ == "SUMMON":
                        if attribute == "NUM":
                            special.append({"NUMBER": len(game.get_now_player().summons)})
                    elif type_ == "COUNTER":
                        if attribute in kwargs["invoke"].counter:
                            special.append({"NUMBER": kwargs["invoke"].counter[attribute]})
                    elif type_ == "NATION":
                        nation = game.get_now_player().get_character_nation()
                        special.append({"NUMBER": nation.count(attribute)})
                    elif type_ == "CARD":
                        if attribute == "COST":
                            card_cost = kwargs["card_cost"]
                            cost = 0
                            for key, value in card_cost.items():
                                cost += value
                            special.append({"NUMBER": cost})
                elif each[0] == "GET_ELEMENT":
                    if each[1] == "SWIRL":
                        if "swirl_element" in kwargs:
                            special.append({"ELEMENT": kwargs["swirl_element"]})
                    elif each[1] == "ACTIVE":
                        element = game.get_now_player().get_active_character_obj().element
                        special.append({"ELEMENT": element})
                    elif each[1] == "SELF":
                        element = kwargs["invoke"].element
                        special.append({"ELEMENT": element})
                    else:
                        return False
                elif each[0] == "EQUIP":
                    if each[1] in kwargs["card_tag"]:
                        continue
                    else:
                        return False
                elif each[0] == "PLAY_CARD":
                    if each[1].startswith("TYPE_"):
                        tag = each[1].replace("TYPE_", "")
                        if tag in kwargs["card_tag"]:
                            continue
                        else:
                            return False
                elif each[0] == "COMPARE":
                    two = [each[1], each[3]]
                    two_side = []
                    for each_side in two:
                        type_, attribute = each_side.split("_", 1)
                        if type_ == "SUMMON":
                            if attribute == "NUM":
                                two_side.append({"NUMBER": len(game.get_now_player().summons)})
                        elif type_ == "COUNTER":
                            if attribute in kwargs["invoke"].counter:
                                two_side.append({"NUMBER": kwargs["invoke"].counter[attribute]})
                        elif type_ == "NATION":
                            nation = game.get_now_player().get_character_nation()
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
    return True