# -*- coding: utf-8 -*-
"""
麻将牌类定义
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional

class TileType(Enum):
    """麻将牌类型"""
    WAN = "万"      # 万子
    TONG = "筒"     # 筒子  
    TIAO = "条"     # 条子
    FENG = "风"     # 风牌
    JIAN = "箭"     # 箭牌

class FengType(Enum):
    """风牌类型"""
    DONG = "东"
    NAN = "南"
    XI = "西"
    BEI = "北"

class JianType(Enum):
    """箭牌类型"""
    ZHONG = "中"
    FA = "发"
    BAI = "白"

@dataclass(frozen=True)
class Tile:
    """麻将牌类"""
    tile_type: TileType
    value: int = 0  # 1-9 for 万筒条, 0 for 风箭
    feng_type: Optional[FengType] = None
    jian_type: Optional[JianType] = None
    
    def __post_init__(self):
        """初始化后验证"""
        if self.tile_type in [TileType.WAN, TileType.TONG, TileType.TIAO]:
            if not (1 <= self.value <= 9):
                raise ValueError(f"数字牌值必须在1-9之间: {self.value}")
        elif self.tile_type == TileType.FENG:
            if self.feng_type is None:
                raise ValueError("风牌必须指定feng_type")
        elif self.tile_type == TileType.JIAN:
            if self.jian_type is None:
                raise ValueError("箭牌必须指定jian_type")
    
    def __str__(self):
        """字符串表示"""
        if self.tile_type in [TileType.WAN, TileType.TONG, TileType.TIAO]:
            return f"{self.value}{self.tile_type.value}"
        elif self.tile_type == TileType.FENG:
            return self.feng_type.value
        elif self.tile_type == TileType.JIAN:
            return self.jian_type.value
        return "未知牌"
    
    def __repr__(self):
        return self.__str__()
    
    def is_number_tile(self) -> bool:
        """是否为数字牌"""
        return self.tile_type in [TileType.WAN, TileType.TONG, TileType.TIAO]
    
    def is_honor_tile(self) -> bool:
        """是否为字牌（风、箭）"""
        return self.tile_type in [TileType.FENG, TileType.JIAN]
    
    def is_terminal(self) -> bool:
        """是否为幺九牌"""
        if self.is_number_tile():
            return self.value in [1, 9]
        return self.is_honor_tile()
    
    def is_same_suit(self, other: 'Tile') -> bool:
        """是否同花色"""
        return self.tile_type == other.tile_type
    
    def can_sequence_with(self, tile2: 'Tile', tile3: 'Tile') -> bool:
        """能否组成顺子"""
        if not (self.is_number_tile() and tile2.is_number_tile() and tile3.is_number_tile()):
            return False
        
        if not (self.tile_type == tile2.tile_type == tile3.tile_type):
            return False
        
        values = sorted([self.value, tile2.value, tile3.value])
        return values == [values[0], values[0] + 1, values[0] + 2]

# 预定义所有麻将牌
ALL_TILES = []

# 数字牌 (万、筒、条)
for tile_type in [TileType.WAN, TileType.TONG, TileType.TIAO]:
    for value in range(1, 10):
        ALL_TILES.append(Tile(tile_type, value))

# 风牌
for feng_type in FengType:
    ALL_TILES.append(Tile(TileType.FENG, feng_type=feng_type))

# 箭牌
for jian_type in JianType:
    ALL_TILES.append(Tile(TileType.JIAN, jian_type=jian_type))

def create_tile_from_string(tile_str: str) -> Tile:
    """从字符串创建麻将牌"""
    if len(tile_str) == 2:
        value_str, type_str = tile_str[0], tile_str[1]
        if type_str == "万":
            return Tile(TileType.WAN, int(value_str))
        elif type_str == "筒":
            return Tile(TileType.TONG, int(value_str))
        elif type_str == "条":
            return Tile(TileType.TIAO, int(value_str))
    elif len(tile_str) == 1:
        if tile_str in ["东", "南", "西", "北"]:
            feng_map = {"东": FengType.DONG, "南": FengType.NAN, 
                       "西": FengType.XI, "北": FengType.BEI}
            return Tile(TileType.FENG, feng_type=feng_map[tile_str])
        elif tile_str in ["中", "发", "白"]:
            jian_map = {"中": JianType.ZHONG, "发": JianType.FA, "白": JianType.BAI}
            return Tile(TileType.JIAN, jian_type=jian_map[tile_str])
    
    raise ValueError(f"无法解析麻将牌字符串: {tile_str}") 