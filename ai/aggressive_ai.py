# -*- coding: utf-8 -*-
"""
激进AI实现 - 专注于降低流局率
基于简化但激进的策略，优先进攻而非防守
"""

from typing import List, Optional, Dict
import random
from collections import Counter

from .base_ai import BaseAI
from game.tile import Tile, TileType
from game.player import Player
from game.game_engine import GameAction

class AggressiveAI(BaseAI):
    """激进AI实现，专注于快速胡牌"""
    
    def __init__(self, difficulty: str = "aggressive"):
        super().__init__(difficulty)
        self.win_priority = 0.95  # 极高的胜利优先级
        self.action_threshold = 0.8  # 高行动阈值
        
    def choose_discard(self, player: Player, available_tiles: List[Tile]) -> Tile:
        """选择要打出的牌 - 激进策略"""
        if not available_tiles:
            return player.hand_tiles[0] if player.hand_tiles else None
        
        # 1. 缺门牌必须优先打出
        missing_suit_tiles = self._get_missing_suit_tiles(player, available_tiles)
        if missing_suit_tiles:
            return random.choice(missing_suit_tiles)
        
        # 2. 快速评估策略：优先打出孤张和危险牌
        tile_scores = []
        for tile in available_tiles:
            score = self._fast_evaluate_discard(player, tile)
            tile_scores.append((tile, score))
        
        # 按评分排序，选择最应该打出的
        tile_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 添加少量随机性，但主要选择最优
        if random.random() < 0.9:
            return tile_scores[0][0]
        else:
            top_choices = tile_scores[:min(3, len(tile_scores))]
            return random.choice(top_choices)[0]
    
    def _get_missing_suit_tiles(self, player: Player, available_tiles: List[Tile]) -> List[Tile]:
        """获取缺门牌"""
        if not hasattr(player, 'missing_suit') or not player.missing_suit:
            return []
        
        missing_suit_type = {
            "万": TileType.WAN,
            "筒": TileType.TONG,
            "条": TileType.TIAO
        }.get(player.missing_suit)
        
        if not missing_suit_type:
            return []
        
        return [tile for tile in available_tiles if tile.tile_type == missing_suit_type]
    
    def _fast_evaluate_discard(self, player: Player, tile: Tile) -> float:
        """快速评估打牌优先级（越高越应该打出）"""
        score = 0.0
        
        # 1. 孤张牌优先打出
        if self._is_isolated_tile(player, tile):
            score += 100.0
        
        # 2. 字牌相对安全，可以打出
        if tile.tile_type in [TileType.FENG, TileType.JIAN]:
            score += 80.0
        
        # 3. 边张牌（1,9）相对安全
        if tile.is_number_tile() and tile.value in [1, 9]:
            score += 60.0
        
        # 4. 中张牌要保留（除非是孤张）
        if tile.is_number_tile() and 3 <= tile.value <= 7:
            score -= 20.0
        
        # 5. 如果有很多相同的牌，可以打出一张
        same_count = sum(1 for t in player.hand_tiles if str(t) == str(tile))
        if same_count >= 3:
            score += 40.0
        elif same_count == 2:
            score += 10.0
        
        return score
    
    def _is_isolated_tile(self, player: Player, tile: Tile) -> bool:
        """检查是否为孤张牌"""
        if not tile.is_number_tile():
            # 字牌检查是否有对子或刻子
            count = sum(1 for t in player.hand_tiles if str(t) == str(tile))
            return count == 1
        
        # 数字牌检查周围是否有连接
        same_suit_tiles = [t for t in player.hand_tiles if t.tile_type == tile.tile_type]
        values = [t.value for t in same_suit_tiles]
        
        # 检查是否有相邻的牌
        for v in values:
            if v != tile.value and abs(v - tile.value) <= 2:
                return False
        
        return True
    
    def decide_action(self, player: Player, available_actions: List[GameAction], 
                     context: Dict) -> Optional[GameAction]:
        """决定行动 - 激进策略"""
        # 胡牌绝对优先
        if GameAction.WIN in available_actions:
            return GameAction.WIN
        
        # 非常激进的碰、杠策略
        if GameAction.GANG in available_actions:
            if random.random() < 0.85:  # 85%概率杠牌
                return GameAction.GANG
        
        if GameAction.PENG in available_actions:
            if random.random() < 0.75:  # 75%概率碰牌
                return GameAction.PENG
        
        # 四川麻将通常不支持吃牌
        if GameAction.CHI in available_actions:
            if random.random() < 0.6:  # 60%概率吃牌（如果支持）
                return GameAction.CHI
        
        return GameAction.PASS
    
    def choose_missing_suit(self, player: Player) -> str:
        """选择缺门花色 - 选择数量最少的"""
        suits = {"万": TileType.WAN, "筒": TileType.TONG, "条": TileType.TIAO}
        suit_counts = {suit: 0 for suit in suits.keys()}
        
        # 统计每种花色的数量
        for tile in player.hand_tiles:
            for suit_name, suit_type in suits.items():
                if tile.tile_type == suit_type:
                    suit_counts[suit_name] += 1
        
        # 选择数量最少的花色作为缺门
        return min(suit_counts.keys(), key=lambda x: suit_counts[x])
    
    def choose_exchange_tiles(self, player: Player, exchange_count: int) -> List[Tile]:
        """选择换牌 - 激进策略"""
        if exchange_count <= 0:
            return []
        
        # 优先换掉孤张牌和边张牌
        tiles_to_exchange = []
        
        # 按优先级排序：孤张 > 边张 > 字牌 > 其他
        tile_priorities = []
        for tile in player.hand_tiles:
            priority = 0
            
            if self._is_isolated_tile(player, tile):
                priority = 100
            elif tile.is_number_tile() and tile.value in [1, 9]:
                priority = 80
            elif tile.tile_type in [TileType.FENG, TileType.JIAN]:
                priority = 60
            else:
                priority = 10
            
            tile_priorities.append((tile, priority))
        
        # 按优先级降序排序，选择优先级最高的牌换掉
        tile_priorities.sort(key=lambda x: x[1], reverse=True)
        
        for tile, _ in tile_priorities[:exchange_count]:
            tiles_to_exchange.append(tile)
        
        return tiles_to_exchange 