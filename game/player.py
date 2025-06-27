# -*- coding: utf-8 -*-
"""
玩家类定义
"""

from typing import List, Optional, Set
from enum import Enum
from .tile import Tile

class PlayerType(Enum):
    """玩家类型"""
    HUMAN = "human"
    AI_EASY = "ai_easy"
    AI_MEDIUM = "ai_medium"
    AI_HARD = "ai_hard"
    AI_TRAINER = "ai_trainer"  # 训练模式AI

class MeldType(Enum):
    """组合类型"""
    PENG = "碰"        # 碰
    GANG = "杠"        # 杠
    CHI = "吃"         # 吃
    SHUN = "顺"        # 顺子

class Meld:
    """牌组合"""
    def __init__(self, meld_type: MeldType, tiles: List[Tile], exposed: bool = True):
        self.meld_type = meld_type
        self.tiles = tiles
        self.exposed = exposed  # 是否已亮出
    
    def __str__(self):
        return f"{self.meld_type.value}:{[str(t) for t in self.tiles]}"

class Player:
    """玩家类"""
    
    def __init__(self, name: str, player_type: PlayerType = PlayerType.HUMAN, position: int = 0):
        self.name = name
        self.player_type = player_type
        self.position = position  # 0:东, 1:南, 2:西, 3:北
        self.player_id = position  # 添加player_id属性，与position保持一致
        
        # 手牌
        self.hand_tiles: List[Tile] = []
        self.melds: List[Meld] = []  # 已组合的牌（碰、杠、吃）
        
        # 状态
        self.is_ready = False
        self.is_winner = False
        self.can_win = False
        
        # 游戏统计
        self.score = 0
        self.wins = 0
        self.losses = 0
        
        # 四川麻将特有
        self.missing_suit: Optional[str] = None  # 缺的花色
        
        # 事件回调函数
        self.on_tile_exchange_start = None  # 换三张开始回调
        self.on_missing_suit_selection_start = None  # 选择缺一门开始回调
        
    def add_tile(self, tile: Tile):
        """添加一张牌到手牌"""
        self.hand_tiles.append(tile)
        self.sort_hand()
    
    def add_tiles(self, tiles: List[Tile]):
        """添加多张牌到手牌"""
        self.hand_tiles.extend(tiles)
        self.sort_hand()
    
    def remove_tile(self, tile: Tile) -> bool:
        """从手牌中移除一张牌"""
        if tile in self.hand_tiles:
            self.hand_tiles.remove(tile)
            return True
        return False
    
    def sort_hand(self):
        """整理手牌"""
        # 按照花色和数值排序
        def tile_sort_key(tile: Tile):
            type_order = {"万": 1, "筒": 2, "条": 3, "风": 4, "箭": 5}
            feng_order = {"东": 1, "南": 2, "西": 3, "北": 4}
            jian_order = {"中": 1, "发": 2, "白": 3}
            
            base = type_order.get(tile.tile_type.value, 0) * 100
            
            if tile.is_number_tile():
                return base + tile.value
            elif tile.tile_type.value == "风":
                return base + feng_order.get(tile.feng_type.value, 0)
            elif tile.tile_type.value == "箭":
                return base + jian_order.get(tile.jian_type.value, 0)
            
            return base
        
        self.hand_tiles.sort(key=tile_sort_key)
    
    def get_hand_count(self) -> int:
        """获取手牌数量"""
        return len(self.hand_tiles)
    
    def get_total_tiles(self) -> int:
        """获取总牌数（包括组合）"""
        meld_count = sum(len(meld.tiles) for meld in self.melds)
        return len(self.hand_tiles) + meld_count
    
    def can_peng(self, tile: Tile) -> bool:
        """是否可以碰"""
        count = sum(1 for t in self.hand_tiles if t == tile)
        return count >= 2
    
    def can_gang(self, tile: Tile) -> bool:
        """是否可以杠（明杠）"""
        count = sum(1 for t in self.hand_tiles if t == tile)
        return count >= 3
    
    def can_hidden_gang(self, tile: Optional[Tile] = None) -> List[Tile]:
        """检查是否可以暗杠，返回可暗杠的牌列表"""
        if tile:
            # 检查特定牌是否可以暗杠
            count = sum(1 for t in self.hand_tiles if str(t) == str(tile))
            return [tile] if count >= 4 else []
        
        # 检查所有可以暗杠的牌
        tile_counts = {}
        for t in self.hand_tiles:
            key = str(t)
            tile_counts[key] = tile_counts.get(key, 0) + 1
        
        hidden_gang_tiles = []
        for tile_str, count in tile_counts.items():
            if count >= 4:
                # 找到对应的牌对象
                for t in self.hand_tiles:
                    if str(t) == tile_str:
                        hidden_gang_tiles.append(t)
                        break
        
        return hidden_gang_tiles
    
    def can_add_gang(self, tile: Optional[Tile] = None) -> List[Tile]:
        """检查是否可以贴杠，返回可贴杠的牌列表"""
        if tile:
            # 检查特定牌是否可以贴杠
            # 1. 手牌中必须有这张牌
            if not any(str(t) == str(tile) for t in self.hand_tiles):
                return []
            # 2. 必须已经有这张牌的碰（副露）
            for meld in self.melds:
                if (meld.meld_type == MeldType.PENG and 
                    len(meld.tiles) >= 1 and 
                    str(meld.tiles[0]) == str(tile)):
                    return [tile]
            return []
        
        # 检查所有可以贴杠的牌
        add_gang_tiles = []
        
        # 遍历所有的碰（副露）
        for meld in self.melds:
            if meld.meld_type == MeldType.PENG and len(meld.tiles) >= 1:
                peng_tile = meld.tiles[0]  # 碰的牌（所有牌都相同）
                # 检查手牌中是否有相同的牌进行贴杠
                for hand_tile in self.hand_tiles:
                    if str(hand_tile) == str(peng_tile):
                        add_gang_tiles.append(hand_tile)
                        break  # 一个碰只能贴杠一次，找到就跳出
        
        return add_gang_tiles
    
    def can_chi(self, tile: Tile) -> List[List[Tile]]:
        """是否可以吃，返回可能的组合"""
        if not tile.is_number_tile():
            return []
        
        possible_chis = []
        tile_counts = {}
        
        # 统计同花色的牌
        for t in self.hand_tiles:
            if t.tile_type == tile.tile_type:
                tile_counts[t.value] = tile_counts.get(t.value, 0) + 1
        
        value = tile.value
        
        # 检查三种可能的顺子
        sequences = [
            [value - 2, value - 1, value],  # tile在最右
            [value - 1, value, value + 1],  # tile在中间
            [value, value + 1, value + 2]   # tile在最左
        ]
        
        for seq in sequences:
            if all(1 <= v <= 9 for v in seq):
                # 检查除了tile外，其他两张牌是否都有
                other_values = [v for v in seq if v != value]
                if all(tile_counts.get(v, 0) > 0 for v in other_values):
                    sequence_tiles = []
                    for v in seq:
                        if v == value:
                            sequence_tiles.append(tile)
                        else:
                            # 找到对应的牌
                            for t in self.hand_tiles:
                                if t.tile_type == tile.tile_type and t.value == v:
                                    sequence_tiles.append(t)
                                    break
                    if len(sequence_tiles) == 3:
                        possible_chis.append(sequence_tiles)
        
        return possible_chis
    
    def make_peng(self, tile: Tile) -> bool:
        """执行碰"""
        if not self.can_peng(tile):
            return False
        
        # 从手牌中移除两张相同的牌
        peng_tiles = [tile]
        removed_count = 0
        for t in self.hand_tiles[:]:
            if t == tile and removed_count < 2:
                self.hand_tiles.remove(t)
                peng_tiles.append(t)
                removed_count += 1
        
        # 添加到组合中
        self.melds.append(Meld(MeldType.PENG, peng_tiles, exposed=True))
        return True
    
    def make_gang(self, tile: Tile, hidden: bool = False) -> bool:
        """执行杠（明杠）"""
        if not self.can_gang(tile):
            return False
        
        # 从手牌中移除三张相同的牌
        gang_tiles = [tile]
        removed_count = 0
        for t in self.hand_tiles[:]:
            if t == tile and removed_count < 3:
                self.hand_tiles.remove(t)
                gang_tiles.append(t)
                removed_count += 1
        
        # 添加到组合中
        self.melds.append(Meld(MeldType.GANG, gang_tiles, exposed=not hidden))
        return True
    
    def make_hidden_gang(self, tile: Tile) -> bool:
        """执行暗杠"""
        if not self.can_hidden_gang(tile):
            return False
        
        # 从手牌中移除四张相同的牌
        gang_tiles = []
        removed_count = 0
        for t in self.hand_tiles[:]:
            if str(t) == str(tile) and removed_count < 4:
                self.hand_tiles.remove(t)
                gang_tiles.append(t)
                removed_count += 1
        
        if len(gang_tiles) == 4:
            # 添加到组合中，暗杠不展示
            self.melds.append(Meld(MeldType.GANG, gang_tiles, exposed=False))
            return True
        else:
            # 如果移除失败，恢复手牌
            self.hand_tiles.extend(gang_tiles)
            self.sort_hand()
            return False
    
    def make_chi(self, tiles: List[Tile]) -> bool:
        """执行吃"""
        if len(tiles) != 3:
            return False
        
        # 检查是否能组成顺子
        if not tiles[0].can_sequence_with(tiles[1], tiles[2]):
            return False
        
        # 从手牌中移除对应的牌（除了第一张，那是别人打的）
        for tile in tiles[1:]:
            if tile not in self.hand_tiles:
                return False
            self.hand_tiles.remove(tile)
        
        # 添加到组合中
        self.melds.append(Meld(MeldType.CHI, tiles, exposed=True))
        return True
    
    def set_missing_suit(self, suit: str):
        """设置缺的花色（四川麻将）"""
        self.missing_suit = suit
    
    def check_missing_suit_complete(self) -> bool:
        """检查是否已经缺完一门"""
        if not self.missing_suit:
            return True
        
        # 检查手牌和组合中是否还有指定花色的牌
        all_tiles = self.hand_tiles[:]
        for meld in self.melds:
            all_tiles.extend(meld.tiles)
        
        for tile in all_tiles:
            if tile.tile_type.value == self.missing_suit:
                return False
        
        return True
    
    def has_tile_in_hand(self, tile: Tile) -> bool:
        """检查手牌中是否有指定的牌"""
        return tile in self.hand_tiles
    
    def remove_tile_from_hand(self, tile: Tile) -> bool:
        """从手牌中移除指定的牌"""
        return self.remove_tile(tile)
    
    def add_tile_to_hand(self, tile: Tile):
        """添加牌到手牌"""
        self.add_tile(tile)
    
    def add_tiles_to_hand(self, tiles: List[Tile]):
        """添加多张牌到手牌"""
        self.add_tiles(tiles)
    
    def can_ming_gang(self, tile: Tile) -> bool:
        """是否可以明杠"""
        return self.can_gang(tile)
    
    @property
    def gang_count(self) -> int:
        """获取杠牌数量"""
        return sum(1 for meld in self.melds if meld.meld_type == MeldType.GANG)
    
    def reset(self):
        """重置玩家状态"""
        self.hand_tiles.clear()
        self.melds.clear()
        self.is_ready = False
        self.is_winner = False
        self.can_win = False
        self.missing_suit = None
    
    def make_add_gang(self, tile: Tile) -> bool:
        """执行贴杠"""
        if not self.can_add_gang(tile):
            return False
        
        # 从手牌中移除这张牌
        if not self.remove_tile(tile):
            return False
        
        # 找到对应的碰（副露）并转换为杠
        for i, meld in enumerate(self.melds):
            if (meld.meld_type == MeldType.PENG and 
                len(meld.tiles) >= 1 and 
                str(meld.tiles[0]) == str(tile)):
                # 将这张牌加入到碰中形成杠
                meld.tiles.append(tile)
                # 改变类型为杠
                meld.meld_type = MeldType.GANG
                # 贴杠仍然是明杠，保持exposed=True
                return True
        
        # 如果没找到对应的碰，恢复手牌
        self.add_tile(tile)
        return False
    
    def __str__(self):
        return f"Player({self.name}, {self.player_type.value}, 手牌:{len(self.hand_tiles)})" 