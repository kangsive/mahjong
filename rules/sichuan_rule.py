# -*- coding: utf-8 -*-
"""
四川麻将规则（基于Wikipedia权威资料）
核心特点：缺一门、血战到底、不能吃牌、刮风下雨
"""

from typing import List, Dict, Optional, Tuple
from .base_rule import BaseRule, WinPattern
from game.tile import Tile, TileType
from game.player import Player

class SichuanRule(BaseRule):
    """四川麻将规则（成都麻将）"""
    
    def __init__(self):
        super().__init__()
        self.max_score = 8  # 封顶8番（满格/极品）
        self._initialize_win_patterns()
        
    def _initialize_win_patterns(self):
        """初始化胡牌牌型"""
        self.win_patterns = [
            # 基础牌型
            WinPattern("平胡", "基本胡牌", 1),
            WinPattern("断幺九", "和牌时没有幺九牌", 1),
            WinPattern("大对子", "四个刻子加一对将", 1),
            WinPattern("杠上开花", "开杠后摸的牌和牌", 1),
            WinPattern("海底捞月", "最后一张牌和牌", 1),
            WinPattern("抢杠胡", "抢别人的杠", 1),
            
            # 2番牌型
            WinPattern("七对子", "七个对子", 2),
            WinPattern("清一色", "只有一种花色", 1),
            WinPattern("全带幺", "所有面子都带幺九牌", 2),
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
        # 不需要检查总牌数，只需要检查面子+对子结构
        return self._check_win_pattern_with_melds(test_tiles, existing_melds_count)
    
    def _check_missing_suit(self, player: Player) -> bool:
        """检查是否满足缺一门条件"""
        if not hasattr(player, 'missing_suit') or not player.missing_suit:
            return False
        
        # 检查是否真的缺少该门
        missing_suit_type = {
            "万": TileType.WAN,
            "筒": TileType.TONG, 
            "条": TileType.TIAO
        }.get(player.missing_suit)
        
        if not missing_suit_type:
            return False
        
        # 检查手牌中是否有缺门的牌
        has_missing_suit_in_hand = any(tile.tile_type == missing_suit_type for tile in player.hand_tiles)
        
        # 检查已组合的牌中是否有缺门的牌
        has_missing_suit_in_melds = False
        for meld in player.melds:
            if any(tile.tile_type == missing_suit_type for tile in meld.tiles):
                has_missing_suit_in_melds = True
                break
        
        # 只有手牌和组合中都没有缺门的牌才满足缺门条件
        return not (has_missing_suit_in_hand or has_missing_suit_in_melds)
    
    def _check_basic_win_pattern(self, tiles: List[Tile]) -> bool:
        """检查基本胡牌牌型（4个面子+1个对子）"""
        # 统计每种牌的数量
        tile_counts = {}
        for tile in tiles:
            key = self._tile_to_key(tile)
            tile_counts[key] = tile_counts.get(key, 0) + 1
        
        return self._try_form_melds(tile_counts, 0, False)
    
    def _check_win_pattern_with_melds(self, hand_tiles: List[Tile], existing_melds_count: int) -> bool:
        """检查胡牌牌型，考虑已有的面子"""
        # 需要从手牌中组成的面子数 = 4 - 已有面子数
        remaining_melds_needed = 4 - existing_melds_count
        
        # 统计手牌中每种牌的数量
        tile_counts = {}
        for tile in hand_tiles:
            key = self._tile_to_key(tile)
            tile_counts[key] = tile_counts.get(key, 0) + 1
        
        # 尝试从手牌中组成所需的面子和1个对子
        return self._try_form_melds(tile_counts, 0, False, remaining_melds_needed)
    
    def _try_form_melds(self, tile_counts: Dict[tuple, int], melds_formed: int, has_pair: bool, target_melds: int = 4) -> bool:
        """尝试组成面子，支持指定目标面子数"""
        # 如果已经组成了目标数量的面子和1个对子
        if melds_formed == target_melds and has_pair:
            return all(count == 0 for count in tile_counts.values())
        
        # 如果牌已经用完但还没形成完整的胡牌牌型
        if all(count == 0 for count in tile_counts.values()):
            return melds_formed == target_melds and has_pair
        
        # 找到第一个还有牌的类型
        tile_key = None
        for key, count in tile_counts.items():
            if count > 0:
                tile_key = key
                break
        
        if tile_key is None:
            return melds_formed == target_melds and has_pair
        
        count = tile_counts[tile_key]
        
        # 尝试组成对子（如果还没有对子）
        if not has_pair and count >= 2:
            tile_counts[tile_key] -= 2
            if self._try_form_melds(tile_counts, melds_formed, True, target_melds):
                tile_counts[tile_key] += 2
                return True
            tile_counts[tile_key] += 2
        
        # 尝试组成刻子（如果还需要面子）
        if melds_formed < target_melds and count >= 3:
            tile_counts[tile_key] -= 3
            if self._try_form_melds(tile_counts, melds_formed + 1, has_pair, target_melds):
                tile_counts[tile_key] += 3
                return True
            tile_counts[tile_key] += 3
        
        # 尝试组成顺子（只对数字牌，如果还需要面子）
        if melds_formed < target_melds and self._is_number_tile_key(tile_key):
            if self._try_form_sequence(tile_counts, tile_key):
                if self._try_form_melds(tile_counts, melds_formed + 1, has_pair, target_melds):
                    self._restore_sequence(tile_counts, tile_key)
                    return True
                self._restore_sequence(tile_counts, tile_key)
        
        return False
    
    def _tile_to_key(self, tile: Tile) -> tuple:
        """将牌转换为可比较的键"""
        return (tile.tile_type, tile.value)
    

    
    def _is_number_tile_key(self, tile_key: tuple) -> bool:
        """检查是否为数字牌键"""
        tile_type, value = tile_key
        return tile_type in [TileType.WAN, TileType.TONG, TileType.TIAO]
    
    def _try_form_sequence(self, tile_counts: Dict[tuple, int], tile_key: tuple) -> bool:
        """尝试组成顺子"""
        tile_type, value = tile_key
        
        if not self._is_number_tile_key(tile_key):
            return False
        
        # 检查是否可以组成顺子
        if value <= 7:  # 可以作为顺子的开头
            key1 = (tile_type, value)
            key2 = (tile_type, value + 1)
            key3 = (tile_type, value + 2)
            
            if (tile_counts.get(key1, 0) >= 1 and 
                tile_counts.get(key2, 0) >= 1 and 
                tile_counts.get(key3, 0) >= 1):
                
                tile_counts[key1] -= 1
                tile_counts[key2] -= 1
                tile_counts[key3] -= 1
                return True
        
        return False
    
    def _restore_sequence(self, tile_counts: Dict[tuple, int], tile_key: tuple):
        """恢复顺子"""
        tile_type, value = tile_key
        
        key1 = (tile_type, value)
        key2 = (tile_type, value + 1)
        key3 = (tile_type, value + 2)
        
        tile_counts[key1] += 1
        tile_counts[key2] += 1
        tile_counts[key3] += 1
    
    def calculate_score(self, winner: Player, players: List[Player], 
                       win_tile: Optional[Tile] = None, 
                       is_self_draw: bool = False,
                       discard_player: Optional[Player] = None) -> Dict[str, int]:
        """计算得分"""
        scores = {player.name: 0 for player in players}
        
        # --------------------------------------------------
        # 1) 计算基础分
        #    • 平胡基础 1 分
        #    • 自摸加底 +1 分
        #    • 明杠 +1 分 / 每杠
        #    • 暗杠 +2 分 / 每杠
        base_points = 1  # 平胡基础

        # 自摸加底
        if is_self_draw:
            base_points += 1

        # --------------------------------------------------
        # 2) 计算番数（不含自摸加底，但包含杠番）
        #    最大 8 番封顶
        fan_count = self._calculate_fan(winner, win_tile, is_self_draw)

        # --------------------------------------------------
        # 3) 最终单家输赢 = base_points × 2^fan_count
        final_point = base_points * (2 ** fan_count)
        
        # 血战到底规则
        if is_self_draw:
            # 自摸：场上仍未胡牌的活跃玩家付钱
            payers = [p for p in players if p != winner and not getattr(p, 'is_winner', False)]
            for payer in payers:
                scores[payer.name] = -final_point
                scores[winner.name] += final_point
        else:
            # 点炮：仅放炮者付钱
            if discard_player and discard_player != winner:
                scores[discard_player.name] = -final_point
                scores[winner.name] = final_point
            else:
                # 保险：若无放炮者信息，视为自摸情况
                payers = [p for p in players if p != winner and not getattr(p, 'is_winner', False)]
                for payer in payers:
                    scores[payer.name] = -final_point
                    scores[winner.name] += final_point
        
        return scores
    
    def _calculate_fan(self, winner: Player, win_tile: Optional[Tile] = None, 
                      is_self_draw: bool = False) -> int:
        """计算番数（不包含自摸加底）"""
        fan_count = 0
        
        # 收集所有牌
        all_tiles = winner.hand_tiles[:]
        if win_tile:
            all_tiles.append(win_tile)
        
        for meld in winner.melds:
            all_tiles.extend(meld.tiles)
        
        # 基础番种判断
        
        # 七对子（2番）
        if self._is_seven_pairs(all_tiles):
            fan_count += 2
        
        # 清一色（1番）
        elif self._is_flush(all_tiles):
            fan_count += 1
        
        # 大对子（1番）
        elif self._is_all_triplets(all_tiles):
            fan_count += 1
        
        # 断幺九（1番）
        if self._is_all_simples(all_tiles):
            fan_count += 1
        
        # 全带幺（2番）
        if self._is_all_terminals_honors(all_tiles):
            fan_count += 2
        
        # 根（杠牌）加番
        gang_count = sum(1 for meld in winner.melds if meld.meld_type.value == "杠")
        fan_count += gang_count
        
        # 返回番数（不加平胡额外番，平胡记作0番）
        return min(fan_count, self.max_score)
    
    def _is_seven_pairs(self, tiles: List[Tile]) -> bool:
        """检查是否为七对子"""
        if len(tiles) != 14:
            return False
        
        tile_counts = {}
        for tile in tiles:
            tile_key = str(tile)
            tile_counts[tile_key] = tile_counts.get(tile_key, 0) + 1
        
        # 必须有7种不同的牌，每种2张
        return len(tile_counts) == 7 and all(count == 2 for count in tile_counts.values())
    
    def _is_flush(self, tiles: List[Tile]) -> bool:
        """检查是否为清一色"""
        if not tiles:
            return False
        
        first_suit = tiles[0].tile_type
        return all(tile.tile_type == first_suit for tile in tiles)
    
    def _is_all_triplets(self, tiles: List[Tile]) -> bool:
        """检查是否为大对子（对对和）"""
        # 移除七对子情况
        if self._is_seven_pairs(tiles):
            return False
        
        tile_counts = {}
        for tile in tiles:
            tile_key = str(tile)
            tile_counts[tile_key] = tile_counts.get(tile_key, 0) + 1
        
        # 检查是否为4个三张+1个对子的组合
        three_count = sum(1 for count in tile_counts.values() if count == 3)
        two_count = sum(1 for count in tile_counts.values() if count == 2)
        
        return three_count == 4 and two_count == 1
    
    def _is_all_simples(self, tiles: List[Tile]) -> bool:
        """检查是否为断幺九"""
        return all(not tile.is_terminal() for tile in tiles)
    
    def _is_all_terminals_honors(self, tiles: List[Tile]) -> bool:
        """检查是否为全带幺"""
        # 四川麻将没有字牌，所以只检查是否所有面子都带1或9
        tile_counts = {}
        for tile in tiles:
            tile_key = str(tile)
            tile_counts[tile_key] = tile_counts.get(tile_key, 0) + 1
        
        # 所有牌都必须是幺九牌或与幺九牌组成面子
        for tile in tiles:
            if not tile.is_terminal():
                # 检查是否能与幺九牌组成顺子
                if not self._has_terminal_in_sequence(tile, tiles):
                    return False
        return True
    
    def _has_terminal_in_sequence(self, tile: Tile, all_tiles: List[Tile]) -> bool:
        """检查该牌是否能与幺九牌组成顺子"""
        if not tile.is_number_tile():
            return False
        
        # 检查可能的顺子组合
        for offset in [-2, -1, 1, 2]:
            target_value = tile.value + offset
            if 1 <= target_value <= 9:
                target_tile = Tile(tile.tile_type, target_value)
                if target_tile.is_terminal() and str(target_tile) in [str(t) for t in all_tiles]:
                    return True
        return False
    
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
                missing_tiles = [t for t in player.hand_tiles if t.tile_type == missing_suit_type]
                if missing_tiles and tile.tile_type != missing_suit_type:
                    # 不允许打出非缺门牌如果手里还有缺门的牌
                    return False
        
        return True 