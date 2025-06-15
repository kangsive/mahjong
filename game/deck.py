# -*- coding: utf-8 -*-
"""
牌堆管理类
"""

import random
from typing import List, Optional
from .tile import Tile, ALL_TILES

class Deck:
    """麻将牌堆"""
    
    def __init__(self, rule_type: str = "sichuan"):
        """
        初始化牌堆
        
        Args:
            rule_type: 规则类型 ("sichuan" 四川麻将, "national" 国标麻将)
        """
        self.rule_type = rule_type
        self.tiles: List[Tile] = []
        self.discarded_tiles: List[Tile] = []
        self._initialize_deck()
    
    def _initialize_deck(self):
        """初始化牌堆"""
        self.tiles = []
        
        if self.rule_type == "sichuan":
            # 四川麻将：只使用万、筒、条三种花色的完整牌(1-9)，不使用风牌和箭牌
            # 总共108张牌，每种牌4张
            from .tile import TileType
            
            # 万子1-9，筒子1-9，条子1-9 各4张
            for tile_type in [TileType.WAN, TileType.TONG, TileType.TIAO]:
                for value in range(1, 10):  # 1-9的完整牌
                    for _ in range(4):
                        self.tiles.append(Tile(tile_type, value))
                    
        else:  # 国标麻将
            # 136张牌，只含字牌+风牌+箭牌每种4张。（标准144张牌，加上春夏秋冬梅兰竹菊）
            for tile in ALL_TILES:
                for _ in range(4):
                    self.tiles.append(tile)
        
        # 洗牌
        self.shuffle()
    
    def shuffle(self):
        """洗牌"""
        random.shuffle(self.tiles)
    
    def draw_tile(self) -> Optional[Tile]:
        """摸牌"""
        if not self.tiles:
            return None
        return self.tiles.pop()
    
    def draw_multiple(self, count: int) -> List[Tile]:
        """摸多张牌"""
        drawn = []
        for _ in range(count):
            tile = self.draw_tile()
            if tile:
                drawn.append(tile)
            else:
                break
        return drawn
    
    def discard_tile(self, tile: Tile):
        """打出一张牌"""
        self.discarded_tiles.append(tile)
    
    def get_remaining_count(self) -> int:
        """获取剩余牌数"""
        return len(self.tiles)
    
    def get_discarded_tiles(self) -> List[Tile]:
        """获取已打出的牌"""
        return self.discarded_tiles.copy()
    
    def reset(self):
        """重置牌堆"""
        self.discarded_tiles.clear()
        self._initialize_deck()
    
    def peek_tiles(self, count: int = 1) -> List[Tile]:
        """查看牌堆顶部的几张牌（不移除）"""
        if count > len(self.tiles):
            count = len(self.tiles)
        return self.tiles[-count:] if count > 0 else [] 