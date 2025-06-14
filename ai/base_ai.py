# -*- coding: utf-8 -*-
"""
AI基类
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Tuple
import random

from game.tile import Tile
from game.player import Player
from game.game_engine import GameAction

class BaseAI(ABC):
    """AI基类"""
    
    def __init__(self, difficulty: str = "medium"):
        self.difficulty = difficulty
        self.name = f"AI-{difficulty}"
        
    @abstractmethod
    def choose_discard(self, player: Player, available_tiles: List[Tile]) -> Tile:
        """选择要打出的牌"""
        pass
    
    @abstractmethod
    def decide_action(self, player: Player, available_actions: List[GameAction], 
                     context: Dict) -> Optional[GameAction]:
        """决定要执行的动作"""
        pass
    
    @abstractmethod
    def choose_missing_suit(self, player: Player) -> str:
        """选择缺门（四川麻将）"""
        pass
    
    def evaluate_hand(self, player: Player) -> Dict:
        """评估手牌"""
        hand = player.hand_tiles
        evaluation = {
            "pairs": 0,
            "triplets": 0,
            "sequences": 0,
            "orphans": 0,
            "score": 0
        }
        
        # 统计每种牌的数量
        tile_counts = {}
        for tile in hand:
            key = str(tile)
            tile_counts[key] = tile_counts.get(key, 0) + 1
        
        # 统计对子、刻子
        for count in tile_counts.values():
            if count == 2:
                evaluation["pairs"] += 1
            elif count >= 3:
                evaluation["triplets"] += 1
            elif count == 1:
                evaluation["orphans"] += 1
        
        # 检查顺子可能性
        evaluation["sequences"] = self._count_potential_sequences(hand)
        
        # 计算评分
        evaluation["score"] = (
            evaluation["pairs"] * 2 +
            evaluation["triplets"] * 3 +
            evaluation["sequences"] * 2 -
            evaluation["orphans"] * 0.5
        )
        
        return evaluation
    
    def _count_potential_sequences(self, tiles: List[Tile]) -> int:
        """统计潜在顺子数量"""
        sequences = 0
        
        # 按花色分组
        suits = {}
        for tile in tiles:
            if tile.is_number_tile():
                suit = tile.tile_type.value
                if suit not in suits:
                    suits[suit] = []
                suits[suit].append(tile.value)
        
        # 检查每个花色的顺子可能性
        for suit, values in suits.items():
            values.sort()
            i = 0
            while i < len(values) - 2:
                if values[i] + 1 == values[i + 1] and values[i + 1] + 1 == values[i + 2]:
                    sequences += 1
                    i += 3
                else:
                    i += 1
        
        return sequences
    
    def calculate_discard_priority(self, player: Player, tile: Tile) -> float:
        """计算打牌优先级（数值越高越应该打出）"""
        priority = 0.0
        
        # 如果是缺门的牌，优先打出
        if player.missing_suit and tile.tile_type.value == player.missing_suit:
            priority += 10.0
        
        # 孤张牌优先打出
        same_tiles = [t for t in player.hand_tiles if str(t) == str(tile)]
        if len(same_tiles) == 1:
            priority += 5.0
        
        # 字牌相对优先打出（除非是刻子）
        if tile.is_honor_tile() and len(same_tiles) < 3:
            priority += 3.0
        
        # 边张（1,9）相对优先
        if tile.is_number_tile() and tile.value in [1, 9]:
            priority += 2.0
        
        # 随机因子
        priority += random.uniform(0, 1)
        
        return priority
    
    def can_form_winning_hand(self, tiles: List[Tile]) -> bool:
        """检查是否能组成胡牌手牌"""
        # 简化的胡牌检查
        if len(tiles) % 3 != 2:
            return False
        
        # 统计牌的数量
        tile_counts = {}
        for tile in tiles:
            key = str(tile)
            tile_counts[key] = tile_counts.get(key, 0) + 1
        
        return self._check_basic_win_pattern(tile_counts)
    
    def _check_basic_win_pattern(self, tile_counts: Dict[str, int]) -> bool:
        """检查基本胡牌牌型"""
        # 简化版本：检查是否有合理的牌型分布
        pairs = sum(1 for count in tile_counts.values() if count == 2)
        triplets = sum(1 for count in tile_counts.values() if count >= 3)
        
        # 基本要求：至少1个对子，其余为刻子或顺子
        return pairs >= 1 and (pairs + triplets) >= 5 