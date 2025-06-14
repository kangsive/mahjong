# -*- coding: utf-8 -*-
"""
简单AI实现
"""

from typing import List, Optional, Dict
import random

from .base_ai import BaseAI
from game.tile import Tile
from game.player import Player
from game.game_engine import GameAction

class SimpleAI(BaseAI):
    """简单AI实现"""
    
    def __init__(self, difficulty: str = "medium"):
        super().__init__(difficulty)
        
    def choose_discard(self, player: Player, available_tiles: List[Tile]) -> Tile:
        """选择要打出的牌"""
        if not available_tiles:
            return player.hand_tiles[0] if player.hand_tiles else None
        
        # 计算每张牌的打出优先级
        priorities = []
        for tile in available_tiles:
            priority = self.calculate_discard_priority(player, tile)
            priorities.append((tile, priority))
        
        # 按优先级排序，选择优先级最高的
        priorities.sort(key=lambda x: x[1], reverse=True)
        return priorities[0][0]
    
    def decide_action(self, player: Player, available_actions: List[GameAction], 
                     context: Dict) -> Optional[GameAction]:
        """决定要执行的动作"""
        # 简单的决策逻辑
        if GameAction.WIN in available_actions:
            return GameAction.WIN
        
        # 根据难度调整行动概率
        if self.difficulty == "easy":
            action_probs = {
                GameAction.GANG: 0.3,
                GameAction.PENG: 0.5,
                GameAction.CHI: 0.4,
                GameAction.PASS: 0.7
            }
        elif self.difficulty == "hard":
            action_probs = {
                GameAction.GANG: 0.8,
                GameAction.PENG: 0.9,
                GameAction.CHI: 0.7,
                GameAction.PASS: 0.1
            }
        else:  # medium
            action_probs = {
                GameAction.GANG: 0.6,
                GameAction.PENG: 0.7,
                GameAction.CHI: 0.5,
                GameAction.PASS: 0.4
            }
        
        # 按优先级检查动作
        for action in [GameAction.GANG, GameAction.PENG, GameAction.CHI]:
            if action in available_actions:
                if random.random() < action_probs.get(action, 0.5):
                    return action
        
        return GameAction.PASS
    
    def choose_missing_suit(self, player: Player) -> str:
        """选择缺门"""
        # 统计各花色的牌数
        suit_counts = {"万": 0, "筒": 0, "条": 0}
        
        for tile in player.hand_tiles:
            if tile.is_number_tile():
                suit_counts[tile.tile_type.value] += 1
        
        # 选择牌数最少的花色作为缺门
        return min(suit_counts, key=suit_counts.get) 