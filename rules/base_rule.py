# -*- coding: utf-8 -*-
"""
麻将规则基类
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional
from game.tile import Tile
from game.player import Player, Meld

class WinPattern:
    """胡牌牌型"""
    def __init__(self, name: str, description: str, score: int):
        self.name = name
        self.description = description
        self.score = score

class BaseRule(ABC):
    """麻将规则基类"""
    
    def __init__(self):
        self.win_patterns: List[WinPattern] = []
        self.base_score = 1
        self.max_score = 10000
        
    @abstractmethod
    def can_win(self, player: Player, new_tile: Optional[Tile] = None) -> bool:
        """检查是否可以胡牌"""
        pass
    
    @abstractmethod
    def calculate_score(self, winner: Player, players: List[Player], 
                       win_tile: Optional[Tile] = None) -> Dict[str, int]:
        """计算得分"""
        pass
    
    @abstractmethod
    def get_initial_hand_size(self) -> int:
        """获取初始手牌数量"""
        pass
    
    @abstractmethod
    def can_discard(self, player: Player, tile: Tile) -> bool:
        """是否可以打出这张牌"""
        pass
    
    def is_valid_hand(self, tiles: List[Tile]) -> bool:
        """检查是否为有效的胡牌手牌"""
        # 基本检查：手牌数量
        if len(tiles) % 3 != 2:
            return False
        
        return self._check_winning_pattern(tiles)
    
    def _check_winning_pattern(self, tiles: List[Tile]) -> bool:
        """检查胡牌牌型"""
        # 基本的胡牌规则：4个三元组 + 1个对子
        return self._has_basic_winning_pattern(tiles)
    
    def _has_basic_winning_pattern(self, tiles: List[Tile]) -> bool:
        """检查基本胡牌牌型（4个三元组+1个对子）"""
        # 统计每种牌的数量
        tile_counts = {}
        for tile in tiles:
            key = self._tile_to_key(tile)
            tile_counts[key] = tile_counts.get(key, 0) + 1
        
        return self._try_form_melds(tile_counts, 0, False)
    
    def _tile_to_key(self, tile: Tile) -> str:
        """将牌转换为字符串键"""
        return str(tile)
    
    def _try_form_melds(self, tile_counts: Dict[str, int], melds_formed: int, has_pair: bool) -> bool:
        """尝试组成面子"""
        # 如果已经组成了4个面子和1个对子
        if melds_formed == 4 and has_pair:
            return all(count == 0 for count in tile_counts.values())
        
        # 如果牌已经用完但还没形成完整的胡牌牌型
        if all(count == 0 for count in tile_counts.values()):
            return False
        
        # 找到第一个还有牌的类型
        tile_key = None
        for key, count in tile_counts.items():
            if count > 0:
                tile_key = key
                break
        
        if tile_key is None:
            return False
        
        count = tile_counts[tile_key]
        
        # 尝试组成对子（如果还没有对子）
        if not has_pair and count >= 2:
            tile_counts[tile_key] -= 2
            if self._try_form_melds(tile_counts, melds_formed, True):
                tile_counts[tile_key] += 2
                return True
            tile_counts[tile_key] += 2
        
        # 尝试组成刻子
        if count >= 3:
            tile_counts[tile_key] -= 3
            if self._try_form_melds(tile_counts, melds_formed + 1, has_pair):
                tile_counts[tile_key] += 3
                return True
            tile_counts[tile_key] += 3
        
        # 尝试组成顺子（只对数字牌）
        if self._is_number_tile_key(tile_key):
            if self._try_form_sequence(tile_counts, tile_key):
                if self._try_form_melds(tile_counts, melds_formed + 1, has_pair):
                    self._restore_sequence(tile_counts, tile_key)
                    return True
                self._restore_sequence(tile_counts, tile_key)
        
        return False
    
    def _is_number_tile_key(self, tile_key: str) -> bool:
        """检查是否为数字牌键"""
        return tile_key.endswith("万") or tile_key.endswith("筒") or tile_key.endswith("条")
    
    def _try_form_sequence(self, tile_counts: Dict[str, int], tile_key: str) -> bool:
        """尝试组成顺子"""
        if not self._is_number_tile_key(tile_key):
            return False
        
        # 解析牌的数值和花色
        value = int(tile_key[0])
        suffix = tile_key[1:]
        
        # 检查是否可以组成顺子
        if value <= 7:  # 可以作为顺子的开头
            key1 = f"{value}{suffix}"
            key2 = f"{value + 1}{suffix}"
            key3 = f"{value + 2}{suffix}"
            
            if (tile_counts.get(key1, 0) >= 1 and 
                tile_counts.get(key2, 0) >= 1 and 
                tile_counts.get(key3, 0) >= 1):
                
                tile_counts[key1] -= 1
                tile_counts[key2] -= 1
                tile_counts[key3] -= 1
                return True
        
        return False
    
    def _restore_sequence(self, tile_counts: Dict[str, int], tile_key: str):
        """恢复顺子"""
        value = int(tile_key[0])
        suffix = tile_key[1:]
        
        key1 = f"{value}{suffix}"
        key2 = f"{value + 1}{suffix}"
        key3 = f"{value + 2}{suffix}"
        
        tile_counts[key1] += 1
        tile_counts[key2] += 1
        tile_counts[key3] += 1
    
    def get_winning_patterns(self) -> List[WinPattern]:
        """获取所有胡牌牌型"""
        return self.win_patterns 