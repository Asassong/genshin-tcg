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

from enum import Enum


class CostType(Enum):
    NONE = 0
    SAME = 1
    ANY = 2


class ElementType(Enum):
    NONE = -1
    OMNI = 0
    CRYO = 1 # 冰
    HYDRO = 2 # 水
    PYRO = 3 # 火
    ELECTRO = 4 # 雷
    GEO = 5 # 岩
    DENDRO = 6 # 草
    ANEMO = 7 # 风


class WeaponType(Enum):
    NONE = 0
    BOW = 1 # 弓
    SWORD = 2 # 单手剑
    CLAYMORE = 3 # 双手剑
    POLEARM = 4 # 长柄武器
    CATALYST = 5 # 法器
    OTHER_WEAPONS = 6 # 其他武器


class PlayerAction(Enum):
    USING_SKILLS = 1
    ELEMENT_TUNING = 2
    END_ROUND = 3
    CHANGE_CHARACTER = 4
    PLAY_CARD = 5


class GameStage(Enum):
    NONE = 0
    GAME_START = 1
    ROUND_START = 2
    ROLL = 3
    ACTION = 4
    ROUND_END = 5
    GAME_END = 6


class Nation(Enum):
    NONE = 0
    Mondstadt = 1 # 蒙德
    Liyue = 2 # 璃月
    Inazuma = 3 # 稻妻
    Sumeru = 4 # 须弥
    Monster = 5 # 魔物
    Fatui = 6 # 愚人众
    Hilichurl = 7 # 丘丘人


class SkillType(Enum):
    NORMAL_ATTACK = 1 # a
    ELEMENTAL_SKILL = 2 # e
    ELEMENTAL_BURST = 3 # q
    PASSIVE_SKILL = 4 # 被动


class CardType(Enum):
    ANY = 0
    TALENT = 1
    WEAPON = 2
    ELEMENTAL_RESONANCE = 3
    FOOD = 4
    NORMAL_EVENT = 5
    ARTIFACT = 6


class TimeLimit(Enum):
    INFINITY = 1 # 永久存在
    IMMEDIATE = 2 # 按顺序立即生效
    ROUND = 3 # 永久存在，但每回合有生效次数存在
    USAGE = 4 # 一回合可生效多次， 但次数用尽即消失
    DURATION = 5 # 持续回合内可生效任意次， 但持续时间结束后消失
    ATTACH = 6 # 当其他modify消失时消失
    SHARE = 7 # 带有share的modify，在触发其他同名带有share的modify时，同时触发消耗


class EffectObj(Enum):
    ACTIVE = 1 # 我方场上角色
    STANDBY = 2 # 我方后台角色
    OPPOSE_ACTIVE = 3 # 对手场上角色
    OPPOSE_STANDBY = 4 # 对手后台角色
    ALL = 5 # 我方所有角色
    OPPOSE_ALL = 6 # 对手所有角色
    SELF = 7 # 我方对应角色或召唤物
    TEAM = 8 # 我方全队(角色，支援，召唤）
    OPPOSE_SELF = 9 # 对手当前场上角色，但转换为对手当前场上角色的SELF
    OPPOSE_TEAM = 10 # 对手全队(角色，支援，召唤）
    SUMMON = 11 # 我方召唤物
    OPPOSE_SUMMON = 12 # 对手召唤物
    ALL_SUMMON = 13 # 场上召唤物
    ALL_TEAM = 14 # 所有角色
    SUPPORT = 15 # 我方支援卡
    OPPOSE_SUPPORT = 16 # 对手支援卡
    ALL_SUPPORT = 17 # 场上支援卡
    DECK = 18 # 所有角色，支援卡，召唤物
    OPPOSE = 19 # 对手所有角色，但对场上和后台效果不同,可与OPPOSE_ACTIVE混用
    CARD = 20 # 我方手牌
    OPPOSE_CARD = 21 # 对手手牌
    NO_SELF = 22
    NO_OPPOSE_SELF = 23
    SUPER = 24
    STATE = 25
    PLAYER = 26

    COUNTER = 30 # 计数器


class ConditionType(Enum):
    BEING_HIT = 1  # 受到攻击

    STAGE_ROUND_START = 2
    STAGE_ROLL = 3
    STAGE_ACTION = 4
    STAGE_ROUND_END = 5

    IS_ACTIVE = 6
    BEING_HIT_BY = 7 # list类型[BEING_HIT_BY,args],可能为元素类型，技能类型
    USE_SKILL = 8 # list类型[USE_SKILL, skill_name]
    NEED_HEAL = 9

    CHANGE_AVATAR = 10 # 作用对象为TEAM
    BE_CHANGED_AS_ACTIVE = 11 # 作用对象为SELF
    CHANGE_TO_STANDBY = 12 # 作用对象为SELF

    HAVE_CARD = 13
    DONT_HAVE_CARD = 14

    HAVE_STATE = 15
    HAVE_SUMMON = 16

    ONLY = 17 # 全队只有一个

    GET = 19 # list类型[GET,COUNTER|SUMMON|STATE|NATION_名称]，统计数量

    CHECK = 20 # list类型[CHECK,COUNTER|WEAPON|DAMAGE|HP|ELEMENT_名称_条件]

    EXCLUSIVE = 21 # 执行后， 不执行同名EXCLUSIVE条件modify

    ELEMENT_REACTION = 22
    ELEMENT_HURT = 23
    ELEMENT_DMG = 24
    NORMAL_ATTACK = 25
    ELEMENTAL_SKILL = 26
    ELEMENTAL_BURST = 27
    ATTACK = 28
    SKILL = 29 # 包括ELEMENTAL_SKILL ELEMENTAL_BURST

    REMOVE = 30 # TimeLimit为ATTACH时，当其他同名modify全部消失后，该modify移除。移除时效果。
    EQUIP = 31
    PLAY_CARD = 32

    PYRO_RELATED = 33
    HYDRO_RELATED = 34
    ELECTRO_RELATED = 35
    DENDRO_RELATED = 36
    CRYO_RELATED = 37
    ANEMO_RELATED = 38
    GEO_RELATED = 39

    OPPOSE_USE_SKILL = 40
    DIE = 41
    OPPOSE_DIE = 42

    HAVE_SHIELD = 43

    GET_SELECT = 47
    GET_ENERGY = 48
    GET_SKILL_NAME = 49
    GET_ELEMENT = 50 # [GET_ELEMENT, SUMMON|SWIRL|ACTIVE|HIT|ATTACK]
    SWIRL = 51 # 砂糖
    DIFFERENCE_FIRST = 53 # 纯水精灵
    GET_MOST_HURT = 54 # 望舒客栈
    COMPARE = 55 # 蒂玛乌斯


class EffectType(Enum):
    HURT = 1  # 受到伤害，只有str
    DMG = 2  # 改变伤害，int表示=，str(+,-,*,/)表示+=，-=，*=，/=
    CRYO = 3  # 改变冰元素伤害，int表示=，str(+,-,*,/)表示+=，-=，*=，/=
    HYDRO = 4  # 改变水元素伤害，int表示=，str(+,-,*,/)表示+=，-=，*=，/=
    PYRO = 5  # 改变火元素伤害，int表示=，str(+,-,*,/)表示+=，-=，*=，/=
    ELECTRO = 6  # 改变雷元素伤害，int表示=，str(+,-,*,/)表示+=，-=，*=，/=
    GEO = 7  # 改变岩元素伤害，int表示=，str(+,-,*,/)表示+=，-=，*=，/=
    DENDRO = 8  # 改变草元素伤害，int表示=，str(+,-,*,/)表示+=，-=，*=，/=
    ANEMO = 9  # 改变风元素伤害，int表示=，str(+,-,*,/)表示+=，-=，*=，/=
    CRYO_HURT = 10  # 受到冰元素伤害，只有str
    HYDRO_HURT = 11  # 受到水元素伤害，只有str
    PYRO_HURT = 12  # 受到火元素伤害，只有str
    ELECTRO_HURT = 13  # 受到雷元素伤害，只有str
    GEO_HURT = 14  # 受到岩元素伤害，只有str
    DENDRO_HURT = 15  # 受到草元素伤害，只有str
    ANEMO_HURT = 16  # 受到风元素伤害，只有str
    CRYO_DMG = 17  # 造成冰元素伤害，只有int
    HYDRO_DMG = 18  # 造成水元素伤害，只有int
    PYRO_DMG = 19  # 造成火元素伤害，只有int
    ELECTRO_DMG = 20  # 造成雷元素伤害，只有int
    GEO_DMG = 21  # 造成岩元素伤害，只有int
    DENDRO_DMG = 22  # 造成草元素伤害，只有int
    ANEMO_DMG = 23  # 造成风元素伤害，只有int
    PHYSICAL = 24 # 改变物理伤害，int表示=，str(+,-,*,/)表示+=，-=，*=，/=
    PHYSICAL_HURT = 25 # 受到物理伤害，只有str
    PHYSICAL_DMG = 26 # 造成物理伤害，只有int

    CHANGE_CHARACTER = 30 # 切换角色，int表示序号， +1下一个，-1上一个
    CHANGE_COST = 31 # 切换费用，只有str
    CHANGE_ACTION = 32 # 切换动作类型，只有"fast"和"combat"
    CHANGE_TO = 33 # 切换特定角色

    SHIELD = 34 # 护盾 当护盾用尽时才算usage

    PIERCE = 35 # 改变穿透伤害
    PIERCE_DMG = 36 # 造成穿透伤害
    PIERCE_HURT = 37 # 受到穿透伤害

    HEAL = 38 # 治疗
    FROZEN = 39  # 冻结，只有"TRUE"和"FALSE",当为FALSE或DURATION为0时移除

    INFUSION = 40 # 附魔，str元素类型
    APPLICATION = 41 # 元素附着，str元素类型

    REMOVE_ARTIFACT = 44
    EQUIP_ARTIFACT = 45
    EQUIP_WEAPON = 46
    DRAW_CARD = 47
    ADD_CARD = 48  # 获得卡牌
    SET_ENERGY = 49 # 改变能量
    ADD_MODIFY = 50 # dict类型，每次一个
    REMOVE_CARD = 51
    REROLL = 52
    REMOVE_COUNTER = 53
    REMOVE_WEAPON = 54

    TRIGGER = 55 # 使用召唤物技能，召唤物名称或TYPE_召唤物类型
    CONSUME_SUMMON_USAGE = 56 # 默认为1
    CONSUME_STATE_USAGE = 57 # 默认为1
    REMOVE_SUMMON = 58

    COST_ANY = 60
    COST_PYRO = 61
    COST_CRYO = 62
    COST_HYDRO = 63
    COST_DENDRO = 64
    COST_GEO = 65
    COST_ANEMO = 66
    COST_ELECTRO = 67
    COST_ELEMENT = 68

    DURATION = 70 # DURATION_名称

    APPEND_DICE = 71
    REPLACE_DICE = 72
    AUTO_CHANGE_DICE = 73

    ADD_STATE = 74
    ADD_SUMMON = 75

    CHANGE_SUMMON_ELEMENT = 101 # 砂糖
    RANDOM = 102 # 纯水精灵

class OperationType(Enum):
    none = 0
    round_start = 1
    roll_phase = 2
    round_end = 3
    element_attack = 4
    element_hurt = 5
    pierce = 6
    pierce_hurt = 7
    change_character = 8
    infusion = 9
    cost = 10
    counter = 11



