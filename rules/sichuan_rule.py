# -*- coding: utf-8 -*-
"""
四川麻将规则（基于成都血战到底规则）
核心特点：缺一门、血战到底、不能吃牌、刮风下雨

参考文档：成都血战到底麻将最全算分规则
https://ppnav.com/38.html
"""

from typing import List, Dict, Optional, Tuple
from .base_rule import BaseRule, WinPattern
from game.tile import Tile, TileType
from game.player import Player

class SichuanRule(BaseRule):
    """四川麻将规则（成都血战到底）"""
    
    def __init__(self):
        super().__init__()
        self.max_score = 8  # 封顶8番（满格/极品）
        self._initialize_win_patterns()
        
    def _initialize_win_patterns(self):
        """初始化胡牌牌型"""
        self.win_patterns = [
            # 基础牌型 (0番)
            WinPattern("标准胡", "基本胡牌", 0),
            
            # 1番牌型
            WinPattern("带根", "每根+1番", 1),
            WinPattern("对子胡", "四个刻子加一对将", 1),
            WinPattern("杠上花", "开杠后摸的牌胡牌", 1),
            WinPattern("杠上炮", "开杠后打出的牌被他人胡", 1),
            
            # 2番牌型  
            WinPattern("清一色", "只有一种花色", 2),
            WinPattern("七对子", "七个对子（暗七对）", 2),
            WinPattern("幺九牌", "全部是1或9的连牌组成", 2),
            WinPattern("报叫", "庄家或闲家配牌完成后就下叫", 2),
            
            # 3番牌型
            WinPattern("将对", "带二、五、八的对对胡", 3),
            WinPattern("清对", "清一色的对对胡", 3),
            
            # 4番牌型
            WinPattern("清七对", "清一色的七对", 4),
            WinPattern("龙七对", "暗七对中有四张相同的牌", 4),
            WinPattern("清幺九", "清一色的幺九牌", 4),
            
            # 5番牌型
            WinPattern("清龙七对", "清一色的龙七对", 5),
            WinPattern("天胡", "庄家配牌完成后就胡牌", 5),
            WinPattern("地胡", "闲家配牌完成后第一轮摸牌胡", 5),
        ]
    
    def get_initial_hand_size(self) -> int:
        """四川麻将初始手牌13张"""
        return 13
    
    def can_chow(self) -> bool:
        """四川麻将不能吃牌"""
        return False
    
    def can_win(self, player: Player, new_tile: Optional[Tile] = None) -> bool:
        """检查是否可以胡牌"""
        # 必须已经缺一门
        if not self._check_missing_suit(player):
            return False
        
        # 准备检查的手牌
        test_tiles = player.hand_tiles[:]
        if new_tile:
            test_tiles.append(new_tile)
        
        # 计算已有的面子数量
        existing_melds_count = len(player.melds)
        
        # 检查是否为七对子（只在没有melds时适用）
        if existing_melds_count == 0:
            # 七对子需要14张牌（7对）
            all_tiles = test_tiles[:]
            for meld in player.melds:
                all_tiles.extend(meld.tiles)
            if len(all_tiles) == 14 and self._is_seven_pairs(all_tiles):
                return True
        
        # 检查基本胡牌牌型（4个面子+1个对子），考虑已有的面子
        return self._check_win_pattern_with_melds(test_tiles, existing_melds_count)
    
    def _check_missing_suit(self, player: Player) -> bool:
        """检查是否符合缺一门规则"""
        if not hasattr(player, 'missing_suit') or not player.missing_suit:
            return False
        
        missing_suit_type = {
            "万": TileType.WAN,
            "筒": TileType.TONG, 
            "条": TileType.TIAO
        }.get(player.missing_suit)
        
        if not missing_suit_type:
            return False
        
        # 检查手牌中是否有缺门的牌
        for tile in player.hand_tiles:
            if tile.tile_type == missing_suit_type:
                return False
        
        # 检查副露中是否有缺门的牌
        for meld in player.melds:
            for tile in meld.tiles:
                if tile.tile_type == missing_suit_type:
                    return False
        
        return True
    
    def _check_basic_win_pattern(self, tiles: List[Tile]) -> bool:
        """检查基本胡牌牌型（简化版，用于快速检查）"""
        if len(tiles) != 14:
            return False
        return self._check_win_pattern_with_melds(tiles, 0)
    
    def _check_win_pattern_with_melds(self, hand_tiles: List[Tile], existing_melds_count: int) -> bool:
        """检查胡牌牌型，考虑已有的面子数量"""
        if not hand_tiles:
            return existing_melds_count == 4
        
        # 统计牌的数量
        tile_counts = {}
        for tile in hand_tiles:
            key = self._tile_to_key(tile)
            tile_counts[key] = tile_counts.get(key, 0) + 1
        
        # 尝试组成 (4 - existing_melds_count) 个面子 + 1个对子
        target_melds = 4 - existing_melds_count
        return self._try_form_melds(tile_counts, 0, False, target_melds)
    
    def _try_form_melds(self, tile_counts: Dict[tuple, int], melds_formed: int, has_pair: bool, target_melds: int = 4) -> bool:
        """递归尝试组成面子和对子"""
        # 检查是否已经达到目标
        total_tiles = sum(tile_counts.values())
        expected_tiles = (target_melds - melds_formed) * 3 + (0 if has_pair else 2)
        
        if total_tiles == 0:
            return melds_formed == target_melds and has_pair
        if total_tiles < expected_tiles:
            return False
        if total_tiles > expected_tiles:
            return False  # 牌数过多
        
        # 找到第一张有牌的类型
        first_key = None
        for key, count in tile_counts.items():
            if count > 0:
                first_key = key
                break
        
        if first_key is None:
            return melds_formed == target_melds and has_pair
        
        tile_type, value = first_key
        count = tile_counts[first_key]
        
        # 尝试形成对子（如果还没有对子）
        if not has_pair and count >= 2:
            tile_counts[first_key] -= 2
            if self._try_form_melds(tile_counts, melds_formed, True, target_melds):
                tile_counts[first_key] += 2
                return True
            tile_counts[first_key] += 2
        
        # 尝试形成刻子
        if count >= 3 and melds_formed < target_melds:
            tile_counts[first_key] -= 3
            if self._try_form_melds(tile_counts, melds_formed + 1, has_pair, target_melds):
                tile_counts[first_key] += 3
                return True
            tile_counts[first_key] += 3
        
        # 尝试形成顺子（只有数字牌可以组成顺子）
        if (self._is_number_tile_key(first_key) and value <= 7 and 
            melds_formed < target_melds and count >= 1):
            next_key = (tile_type, value + 1)
            next_next_key = (tile_type, value + 2)
            
            if (tile_counts.get(next_key, 0) >= 1 and 
                tile_counts.get(next_next_key, 0) >= 1):
                tile_counts[first_key] -= 1
                tile_counts[next_key] -= 1
                tile_counts[next_next_key] -= 1
                
                if self._try_form_melds(tile_counts, melds_formed + 1, has_pair, target_melds):
                    self._restore_sequence(tile_counts, first_key)
                    return True
                
                self._restore_sequence(tile_counts, first_key)
        
        return False
    
    def _tile_to_key(self, tile: Tile) -> tuple:
        """将牌转换为tuple键，避免Unicode问题"""
        if tile.tile_type in [TileType.WAN, TileType.TONG, TileType.TIAO]:
            return (tile.tile_type, tile.value)
        elif tile.tile_type == TileType.FENG:
            return (tile.tile_type, tile.feng_type)
        else:  # TileType.JIAN
            return (tile.tile_type, tile.jian_type)
    
    def _is_number_tile_key(self, tile_key: tuple) -> bool:
        """检查是否为数字牌的键"""
        tile_type, _ = tile_key
        return tile_type in [TileType.WAN, TileType.TONG, TileType.TIAO]
    
    def _try_form_sequence(self, tile_counts: Dict[tuple, int], tile_key: tuple) -> bool:
        """尝试形成顺子"""
        if not self._is_number_tile_key(tile_key):
            return False
        
        tile_type, value = tile_key
        if value > 7:  # 不能形成顺子
            return False
        
        next_key = (tile_type, value + 1)
        next_next_key = (tile_type, value + 2)
        
        if (tile_counts.get(tile_key, 0) >= 1 and
            tile_counts.get(next_key, 0) >= 1 and
            tile_counts.get(next_next_key, 0) >= 1):
            tile_counts[tile_key] -= 1
            tile_counts[next_key] -= 1
            tile_counts[next_next_key] -= 1
            return True
        
        return False
    
    def _restore_sequence(self, tile_counts: Dict[tuple, int], tile_key: tuple):
        """恢复顺子"""
        tile_type, value = tile_key
        next_key = (tile_type, value + 1)
        next_next_key = (tile_type, value + 2)
        
        tile_counts[tile_key] += 1
        tile_counts[next_key] += 1
        tile_counts[next_next_key] += 1
    
    def calculate_score(self, winner: Player, players: List[Player], 
                       win_tile: Optional[Tile] = None, 
                       is_self_draw: bool = False,
                       discard_player: Optional[Player] = None) -> Dict[str, int]:
        """
        计算得分 - 成都血战到底计分规则
        
        基础公式：
        - 底金 = 1分 (基础分)
        - 自摸加底 = +1分 (仅自摸时)  
        - 番数倍数 = 2^番数
        - 最终得分 = (底金 + 自摸加底) × 2^番数
        
        血战到底规则：
        - 点炮胡：胜者从放炮者处得分
        - 自摸胡：胜者从所有未胡牌的活跃玩家处得分
        """
        scores = {player.name: 0 for player in players}
        
        # 计算基础分数
        base_points = 1  # 底金
        
        # 自摸加底
        if is_self_draw:
            base_points += 1
        
        # 计算番数
        fan_count = self._calculate_fan(winner, win_tile, is_self_draw)
        
        # 应用番数倍数：2^番数
        multiplier = 2 ** fan_count
        final_point = base_points * multiplier
        
        # 血战到底计分规则
        if is_self_draw:
            # 自摸：所有仍在场且未胡牌的玩家付钱给胜者
            payers = [p for p in players if p != winner and not getattr(p, 'is_winner', False)]
            for payer in payers:
                scores[payer.name] = -final_point
                scores[winner.name] += final_point
        else:
            # 点炮胡：仅放炮者付钱给胜者
            if discard_player and discard_player != winner:
                scores[discard_player.name] = -final_point
                scores[winner.name] = final_point
            else:
                # 异常情况保护：无放炮者信息时按自摸处理
                payers = [p for p in players if p != winner and not getattr(p, 'is_winner', False)]
                for payer in payers:
                    scores[payer.name] = -final_point
                    scores[winner.name] += final_point
        
        return scores
    
    def _calculate_fan(self, winner: Player, win_tile: Optional[Tile] = None, 
                      is_self_draw: bool = False) -> int:
        """
        计算番数 - 根据成都血战到底规则
        
        番型累计规则：
        - 基础胡牌: 0番 (底金×1)
        - 各种特殊牌型可叠加
        - 杠牌额外加番
        """
        fan_count = 0
        
        # 收集所有牌用于判断牌型
        all_tiles = winner.hand_tiles[:]
        if win_tile:
            all_tiles.append(win_tile)
        
        for meld in winner.melds:
            all_tiles.extend(meld.tiles)
        
        # 特殊牌型判断（按优先级）
        
        # 5番牌型
        if self._is_heaven_hand(winner, is_self_draw):
            fan_count += 5  # 天胡
        elif self._is_earth_hand(winner, is_self_draw):
            fan_count += 5  # 地胡
        elif self._is_pure_dragon_seven_pairs(all_tiles):
            fan_count += 5  # 清龙七对
            
        # 4番牌型 
        elif self._is_pure_seven_pairs(all_tiles):
            fan_count += 4  # 清七对
        elif self._is_dragon_seven_pairs(all_tiles):
            fan_count += 4  # 龙七对
        elif self._is_pure_terminals(all_tiles):
            fan_count += 4  # 清幺九
            
        # 3番牌型
        elif self._is_pure_triplets(all_tiles):
            fan_count += 3  # 清对
        elif self._is_honor_triplets(all_tiles):
            fan_count += 3  # 将对
            
        # 2番牌型
        elif self._is_seven_pairs(all_tiles):
            fan_count += 2  # 七对子
        elif self._is_flush(all_tiles):
            fan_count += 2  # 清一色
        elif self._is_all_terminals(all_tiles):
            fan_count += 2  # 幺九牌
        elif self._is_early_ready(winner):
            fan_count += 2  # 报叫
            
        # 1番牌型
        elif self._is_all_triplets(all_tiles):
            fan_count += 1  # 对子胡
        
        # 额外番种
        
        # 带根（杠牌）加番 - 每个杠+1番
        gang_count = sum(1 for meld in winner.melds if meld.meld_type.value == "杠")
        fan_count += gang_count
        
        # 杠上花/杠上炮加番
        if self._is_gang_win(winner, win_tile):
            fan_count += 1
        
        # 封顶8番
        return min(fan_count, self.max_score)
    
    # 牌型判断方法
    
    def _is_seven_pairs(self, tiles: List[Tile]) -> bool:
        """检查是否为七对子（暗七对）"""
        if len(tiles) != 14:
            return False
        
        tile_counts = {}
        for tile in tiles:
            tile_key = self._tile_to_key(tile)
            tile_counts[tile_key] = tile_counts.get(tile_key, 0) + 1
        
        # 必须有7种不同的牌，每种2张
        return len(tile_counts) == 7 and all(count == 2 for count in tile_counts.values())
    
    def _is_flush(self, tiles: List[Tile]) -> bool:
        """检查是否为清一色"""
        if not tiles:
            return False
        
        # 过滤掉非数字牌（如果有的话）
        number_tiles = [t for t in tiles if t.is_number_tile()]
        if not number_tiles:
            return False
        
        first_suit = number_tiles[0].tile_type
        return all(tile.tile_type == first_suit for tile in number_tiles)
    
    def _is_all_triplets(self, tiles: List[Tile]) -> bool:
        """检查是否为大对子（对对胡）"""
        # 排除七对子情况
        if self._is_seven_pairs(tiles):
            return False
        
        tile_counts = {}
        for tile in tiles:
            tile_key = self._tile_to_key(tile)
            tile_counts[tile_key] = tile_counts.get(tile_key, 0) + 1
        
        # 检查是否为4个三张+1个对子的组合
        three_count = sum(1 for count in tile_counts.values() if count == 3)
        two_count = sum(1 for count in tile_counts.values() if count == 2)
        four_count = sum(1 for count in tile_counts.values() if count == 4)
        
        return (three_count == 4 and two_count == 1) or (three_count == 3 and four_count == 1 and two_count == 0)
    
    def _is_pure_triplets(self, tiles: List[Tile]) -> bool:
        """检查是否为清对（清一色的对对胡）"""
        return self._is_flush(tiles) and self._is_all_triplets(tiles)
    
    def _is_pure_seven_pairs(self, tiles: List[Tile]) -> bool:
        """检查是否为清七对（清一色的七对子）"""
        return self._is_flush(tiles) and self._is_seven_pairs(tiles)
    
    def _is_dragon_seven_pairs(self, tiles: List[Tile]) -> bool:
        """检查是否为龙七对（七对中有四张相同的牌）"""
        if not self._is_seven_pairs(tiles):
            return False
        
        tile_counts = {}
        for tile in tiles:
            tile_key = self._tile_to_key(tile)
            tile_counts[tile_key] = tile_counts.get(tile_key, 0) + 1
        
        # 检查是否有四张相同的牌（视为两对）
        four_count = sum(1 for count in tile_counts.values() if count == 4)
        return four_count >= 1
    
    def _is_pure_dragon_seven_pairs(self, tiles: List[Tile]) -> bool:
        """检查是否为清龙七对"""
        return self._is_flush(tiles) and self._is_dragon_seven_pairs(tiles)
    
    def _is_all_terminals(self, tiles: List[Tile]) -> bool:
        """检查是否为幺九牌（全部是1或9的连牌组成）"""
        for tile in tiles:
            if tile.is_number_tile():
                if tile.value not in [1, 9]:
                    # 检查是否与1或9组成顺子
                    if not self._has_terminal_in_sequence(tile, tiles):
                        return False
            # 字牌默认符合要求
        return True
    
    def _is_pure_terminals(self, tiles: List[Tile]) -> bool:
        """检查是否为清幺九（清一色的幺九牌）"""
        return self._is_flush(tiles) and self._is_all_terminals(tiles)
    
    def _is_honor_triplets(self, tiles: List[Tile]) -> bool:
        """检查是否为将对（全由258组成的大对子）"""
        if not self._is_all_triplets(tiles):
            return False
        
        for tile in tiles:
            if tile.is_number_tile():
                if tile.value not in [2, 5, 8]:
                    return False
        return True
    
    def _is_heaven_hand(self, winner: Player, is_self_draw: bool) -> bool:
        """检查是否为天胡（庄家配牌完成后就胡牌）"""
        # 简化实现：检查是否为自摸且为庄家的第一次胡牌
        # 实际实现需要游戏引擎提供更多上下文信息
        return False  # 暂不实现
    
    def _is_earth_hand(self, winner: Player, is_self_draw: bool) -> bool:
        """检查是否为地胡（闲家配牌完成后第一轮摸牌胡）"""
        # 简化实现：需要游戏引擎提供回合信息
        return False  # 暂不实现
    
    def _is_early_ready(self, winner: Player) -> bool:
        """检查是否为报叫（配牌完成后就下叫）"""
        # 简化实现：需要游戏引擎提供听牌时机信息
        return False  # 暂不实现
    
    def _is_gang_win(self, winner: Player, win_tile: Optional[Tile] = None) -> bool:
        """检查是否为杠上花/杠上炮"""
        # 简化实现：需要游戏引擎提供杠牌上下文
        return False  # 暂不实现
    
    def _has_terminal_in_sequence(self, tile: Tile, all_tiles: List[Tile]) -> bool:
        """检查该牌是否能与幺九牌组成顺子"""
        if not tile.is_number_tile():
            return False
        
        # 检查可能的顺子组合
        for offset in [-2, -1, 1, 2]:
            target_value = tile.value + offset
            if target_value in [1, 9]:  # 是幺九牌
                # 检查顺子是否完整
                if self._check_sequence_complete(tile, target_value, all_tiles):
                    return True
        return False
    
    def _check_sequence_complete(self, tile: Tile, terminal_value: int, all_tiles: List[Tile]) -> bool:
        """检查包含指定幺九牌的顺子是否完整"""
        # 简化实现
        return True
    
    # 其他辅助方法
    
    def choose_missing_suit(self, player: Player) -> str:
        """选择缺门花色"""
        # 统计各花色牌的数量
        suit_counts = {"万": 0, "筒": 0, "条": 0}
        
        for tile in player.hand_tiles:
            if tile.tile_type == TileType.WAN:
                suit_counts["万"] += 1
            elif tile.tile_type == TileType.TONG:
                suit_counts["筒"] += 1
            elif tile.tile_type == TileType.TIAO:
                suit_counts["条"] += 1
        
        # 选择数量最少的花色作为缺门
        missing_suit = min(suit_counts, key=suit_counts.get)
        player.missing_suit = missing_suit
        return missing_suit
    
    def get_game_modes(self) -> List[str]:
        """获取四川麻将的游戏模式"""
        return ["血战到底", "血流成河"]
    
    def is_blood_battle(self) -> bool:
        """是否为血战到底模式"""
        return True  # 四川麻将默认血战到底
    
    def can_discard(self, player: Player, tile: Tile) -> bool:
        """是否可以打出这张牌"""
        # 检查玩家是否有这张牌
        if not player.has_tile_in_hand(tile):
            return False
        
        # 四川麻将特殊规则：如果已经选择了缺门，需要优先打出缺门的牌
        if hasattr(player, 'missing_suit') and player.missing_suit:
            missing_suit_type = {
                "万": TileType.WAN,
                "筒": TileType.TONG,
                "条": TileType.TIAO
            }.get(player.missing_suit)
            
            if missing_suit_type:
                # 检查手牌中是否还有缺门的牌
                has_missing_suit_tiles = any(
                    t.tile_type == missing_suit_type for t in player.hand_tiles
                )
                
                # 如果有缺门牌，必须优先打出缺门牌
                if has_missing_suit_tiles and tile.tile_type != missing_suit_type:
                    return False
        
        return True 