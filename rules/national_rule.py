# -*- coding: utf-8 -*-
"""
国标麻将规则
"""

from typing import List, Dict, Optional
from .base_rule import BaseRule, WinPattern
from game.tile import Tile
from game.player import Player

class NationalRule(BaseRule):
    """国标麻将规则"""
    
    def __init__(self):
        super().__init__()
        self._initialize_win_patterns()
        
    def _initialize_win_patterns(self):
        """初始化胡牌牌型"""
        self.win_patterns = [
            WinPattern("平胡", "基本胡牌", 8),
            WinPattern("碰碰胡", "全部刻子", 6),
            WinPattern("混一色", "一种花色+字牌", 6),
            WinPattern("清一色", "同一花色", 24),
            WinPattern("字一色", "全部字牌", 64),
            WinPattern("大三元", "三个箭刻", 88),
            WinPattern("大四喜", "四个风刻", 88),
            WinPattern("九子连环", "特殊牌型", 88),
        ]
    
    def get_initial_hand_size(self) -> int:
        """国标麻将初始手牌13张"""
        return 13
    
    def can_win(self, player: Player, new_tile: Optional[Tile] = None) -> bool:
        """检查是否可以胡牌"""
        # 准备检查的手牌
        test_tiles = player.hand_tiles[:]
        if new_tile:
            test_tiles.append(new_tile)
        
        # 加上已经组合的牌
        for meld in player.melds:
            test_tiles.extend(meld.tiles)
        
        # 检查牌数是否正确（14张）
        if len(test_tiles) != 14:
            return False
        
        # 检查基本胡牌牌型
        return self.is_valid_hand(test_tiles)
    
    def can_discard(self, player: Player, tile: Tile) -> bool:
        """是否可以打出这张牌"""
        # 国标麻将没有缺门限制
        return True
    
    def calculate_score(self, winner: Player, players: List[Player], 
                       win_tile: Optional[Tile] = None) -> Dict[str, int]:
        """计算得分"""
        scores = {player.name: 0 for player in players}
        
        # 基础分数
        base_score = self._calculate_base_score(winner, win_tile)
        
        # 其他三家平均承担
        other_players = [p for p in players if p != winner]
        each_pay = base_score // len(other_players)
        remainder = base_score % len(other_players)
        
        scores[winner.name] = base_score
        
        for i, player in enumerate(other_players):
            pay_amount = each_pay + (1 if i < remainder else 0)
            scores[player.name] = -pay_amount
        
        return scores
    
    def _calculate_base_score(self, winner: Player, win_tile: Optional[Tile] = None) -> int:
        """计算基础分数"""
        score = 8  # 基础分
        
        # 检查特殊牌型
        test_tiles = winner.hand_tiles[:]
        if win_tile:
            test_tiles.append(win_tile)
        
        for meld in winner.melds:
            test_tiles.extend(meld.tiles)
        
        # 大三元
        if self._is_big_three_dragons(test_tiles):
            score = 88
        # 大四喜
        elif self._is_big_four_winds(test_tiles):
            score = 88
        # 字一色
        elif self._is_all_honors(test_tiles):
            score = 64
        # 清一色
        elif self._is_flush(test_tiles):
            score = 24
        # 混一色
        elif self._is_mixed_flush(test_tiles):
            score = 6
        # 碰碰胡
        elif self._is_all_triplets(test_tiles):
            score = 6
        
        return min(score, self.max_score)
    
    def _is_big_three_dragons(self, tiles: List[Tile]) -> bool:
        """检查是否为大三元"""
        from game.tile import TileType, JianType
        dragon_counts = {"中": 0, "发": 0, "白": 0}
        
        for tile in tiles:
            if tile.tile_type == TileType.JIAN:
                dragon_counts[tile.jian_type.value] += 1
        
        return all(count >= 3 for count in dragon_counts.values())
    
    def _is_big_four_winds(self, tiles: List[Tile]) -> bool:
        """检查是否为大四喜"""
        from game.tile import TileType, FengType
        wind_counts = {"东": 0, "南": 0, "西": 0, "北": 0}
        
        for tile in tiles:
            if tile.tile_type == TileType.FENG:
                wind_counts[tile.feng_type.value] += 1
        
        return all(count >= 3 for count in wind_counts.values())
    
    def _is_all_honors(self, tiles: List[Tile]) -> bool:
        """检查是否为字一色"""
        return all(tile.is_honor_tile() for tile in tiles)
    
    def _is_flush(self, tiles: List[Tile]) -> bool:
        """检查是否为清一色"""
        if not tiles:
            return False
        
        # 获取第一张数字牌的花色
        first_suit = None
        for tile in tiles:
            if tile.is_number_tile():
                first_suit = tile.tile_type
                break
        
        if first_suit is None:
            return False
        
        # 检查是否所有牌都是同一花色
        return all(tile.tile_type == first_suit for tile in tiles if tile.is_number_tile())
    
    def _is_mixed_flush(self, tiles: List[Tile]) -> bool:
        """检查是否为混一色"""
        if not tiles:
            return False
        
        # 获取数字牌的花色
        number_suits = set()
        has_honors = False
        
        for tile in tiles:
            if tile.is_number_tile():
                number_suits.add(tile.tile_type)
            else:
                has_honors = True
        
        # 必须有字牌，且数字牌只有一种花色
        return has_honors and len(number_suits) == 1
    
    def _is_all_triplets(self, tiles: List[Tile]) -> bool:
        """检查是否为碰碰胡"""
        # 统计每种牌的数量
        counts = {}
        for tile in tiles:
            key = str(tile)
            counts[key] = counts.get(key, 0) + 1
        
        # 必须有一个对子和四个刻子
        pair_count = sum(1 for count in counts.values() if count == 2)
        triplet_count = sum(1 for count in counts.values() if count >= 3)
        
        return pair_count == 1 and triplet_count == 4 