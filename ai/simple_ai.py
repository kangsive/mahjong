# -*- coding: utf-8 -*-
"""
简单AI实现
"""

from typing import List, Optional, Dict
import random

from .base_ai import BaseAI
from game.tile import Tile, TileType
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
        
        # 根据难度添加一些随机性
        if self.difficulty == "easy":
            # 简单AI：30%概率选择最优，70%随机
            if random.random() < 0.3:
                return priorities[0][0]
            else:
                return random.choice(available_tiles)
        elif self.difficulty == "hard":
            # 困难AI：90%概率选择最优，10%选择次优
            if random.random() < 0.9:
                return priorities[0][0]
            else:
                return priorities[min(1, len(priorities)-1)][0]
        else:  # medium
            # 中等AI：70%概率选择最优，30%选择前三名
            if random.random() < 0.7:
                return priorities[0][0]
            else:
                top_choices = priorities[:min(3, len(priorities))]
                return random.choice(top_choices)[0]
    
    def calculate_discard_priority(self, player: Player, tile: Tile) -> float:
        """计算出牌优先级（越高越应该打出）"""
        priority = 0.0
        
        # 1. 缺门牌优先打出（四川麻将规则）
        if hasattr(player, 'missing_suit') and player.missing_suit:
            missing_suit_type = {
                "万": TileType.WAN,
                "筒": TileType.TONG,
                "条": TileType.TIAO
            }.get(player.missing_suit)
            
            if tile.tile_type == missing_suit_type:
                priority += 100.0  # 缺门牌必须优先打出
        
        # 2. 孤张牌优先打出
        if self._is_isolated_tile(player, tile):
            priority += 50.0
        
        # 3. 边张和嵌张优先级较高
        if self._is_edge_or_middle_wait(player, tile):
            priority += 30.0
        
        # 4. 危险牌（可能让别人胡牌）降低优先级
        if self._is_dangerous_tile(tile):
            priority -= 20.0
        
        # 5. 字牌（风、箭）在四川麻将中优先级较高
        if tile.tile_type in [TileType.FENG, TileType.JIAN]:
            priority += 25.0
        
        # 6. 幺九牌适中优先级
        if tile.is_terminal():
            priority += 10.0
        
        return priority
    
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
        has_neighbor = False
        for v in values:
            if v != tile.value and abs(v - tile.value) <= 2:
                has_neighbor = True
                break
        
        return not has_neighbor
    
    def _is_edge_or_middle_wait(self, player: Player, tile: Tile) -> bool:
        """检查是否为边张或嵌张"""
        if not tile.is_number_tile():
            return False
        
        same_suit_tiles = [t for t in player.hand_tiles if t.tile_type == tile.tile_type]
        values = [t.value for t in same_suit_tiles if t.value != tile.value]
        
        # 检查边张（12, 89）
        if tile.value in [1, 2] and (tile.value + 1) in values:
            return True
        if tile.value in [8, 9] and (tile.value - 1) in values:
            return True
        
        # 检查嵌张（135中的3）
        if (tile.value - 1) in values and (tile.value + 1) in values:
            return True
        
        return False
    
    def _is_dangerous_tile(self, tile: Tile) -> bool:
        """检查是否为危险牌（简化判断）"""
        # 简化的危险牌判断：中张牌相对安全，边张和字牌相对危险
        if tile.is_number_tile():
            return tile.value in [1, 9]  # 幺九牌
        return True  # 字牌
    
    def decide_action(self, player: Player, available_actions: List[GameAction], 
                     context: Dict) -> Optional[GameAction]:
        """决定要执行的动作"""
        # 胡牌优先级最高
        if GameAction.WIN in available_actions:
            # 检查是否真的可以胡牌
            if self._should_win(player, context):
                return GameAction.WIN
        
        # 根据难度和策略调整行动概率
        action_probs = self._get_action_probabilities()
        
        # 按优先级检查动作
        for action in [GameAction.GANG, GameAction.PENG, GameAction.CHI]:
            if action in available_actions:
                if self._should_take_action(player, action, context, action_probs):
                    return action
        
        return GameAction.PASS
    
    def _should_win(self, player: Player, context: Dict) -> bool:
        """判断是否应该胡牌"""
        # AI总是选择胡牌，但要确保真的可以胡牌
        return self._can_actually_win(player, context.get("last_discarded_tile"))
    
    def _can_actually_win(self, player: Player, new_tile: Optional[Tile] = None) -> bool:
        """检查是否真的可以胡牌（更精确的检查）"""
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
        
        # 检查缺门条件（四川麻将）
        if not self._check_missing_suit_condition(player, test_tiles):
            return False
        
        # 检查是否为七对子
        if self._is_seven_pairs(test_tiles):
            return True
        
        # 检查基本胡牌牌型（4个面子+1个对子）
        return self._check_basic_win_pattern(test_tiles)
    
    def _check_missing_suit_condition(self, player: Player, tiles: List[Tile]) -> bool:
        """检查缺门条件"""
        if not hasattr(player, 'missing_suit') or not player.missing_suit:
            return False
        
        missing_suit_type = {
            "万": TileType.WAN,
            "筒": TileType.TONG,
            "条": TileType.TIAO
        }.get(player.missing_suit)
        
        if not missing_suit_type:
            return False
        
        # 确保没有缺门的牌
        has_missing_suit = any(tile.tile_type == missing_suit_type for tile in tiles)
        return not has_missing_suit
    
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
    
    def _check_basic_win_pattern(self, tiles: List[Tile]) -> bool:
        """检查基本胡牌牌型（4个面子+1个对子）"""
        # 统计每种牌的数量
        tile_counts = {}
        for tile in tiles:
            key = str(tile)
            tile_counts[key] = tile_counts.get(key, 0) + 1
        
        return self._try_form_melds(tile_counts, 0, False)
    
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
    
    def _is_close_to_win(self, player: Player) -> bool:
        """判断是否接近胡牌（听牌）"""
        from game.tile import FengType, JianType
        
        # 检查是否只差一张牌就能胡牌
        # 检查数字牌
        for tile_type in [TileType.WAN, TileType.TONG, TileType.TIAO]:
            for value in range(1, 10):
                test_tile = Tile(tile_type, value)
                if self._can_actually_win(player, test_tile):
                    return True
        
        # 检查风牌
        for feng_type in FengType:
            test_tile = Tile(TileType.FENG, feng_type=feng_type)
            if self._can_actually_win(player, test_tile):
                return True
        
        # 检查箭牌
        for jian_type in JianType:
            test_tile = Tile(TileType.JIAN, jian_type=jian_type)
            if self._can_actually_win(player, test_tile):
                return True
        
        return False
    
    def _should_take_action(self, player: Player, action: GameAction, 
                           context: Dict, action_probs: Dict) -> bool:
        """判断是否应该执行某个动作"""
        base_prob = action_probs.get(action, 0.5)
        
        # 根据游戏情况调整概率
        if action == GameAction.GANG:
            # 杠牌考虑：剩余牌数、当前手牌情况
            remaining_tiles = context.get("remaining_tiles", 100)
            if remaining_tiles < 20:  # 牌局后期，杠牌风险较大
                base_prob *= 0.5
            
            # 如果接近听牌，降低杠牌概率
            if self._is_close_to_win(player):
                base_prob *= 0.3
        
        elif action == GameAction.PENG:
            # 碰牌考虑：是否有助于组成面子
            if self._is_useful_peng(player, context.get("last_discarded_tile")):
                base_prob *= 1.5
        
        return random.random() < base_prob
    
    def _get_action_probabilities(self) -> Dict[GameAction, float]:
        """获取动作概率"""
        if self.difficulty == "easy":
            return {
                GameAction.GANG: 0.3,
                GameAction.PENG: 0.4,
                GameAction.CHI: 0.3,
                GameAction.PASS: 0.6
            }
        elif self.difficulty == "hard":
            return {
                GameAction.GANG: 0.7,
                GameAction.PENG: 0.8,
                GameAction.CHI: 0.6,
                GameAction.PASS: 0.2
            }
        else:  # medium
            return {
                GameAction.GANG: 0.5,
                GameAction.PENG: 0.6,
                GameAction.CHI: 0.4,
                GameAction.PASS: 0.4
            }
    
    def _is_useful_peng(self, player: Player, tile: Optional[Tile]) -> bool:
        """判断碰牌是否有用"""
        if not tile:
            return False
        
        # 如果这张牌能帮助完成缺门，则不碰
        if hasattr(player, 'missing_suit') and player.missing_suit:
            missing_suit_type = {
                "万": TileType.WAN,
                "筒": TileType.TONG,
                "条": TileType.TIAO
            }.get(player.missing_suit)
            
            if tile.tile_type == missing_suit_type:
                return False  # 缺门牌不应该碰
        
        return True
    
    def choose_missing_suit(self, player: Player) -> str:
        """选择缺门"""
        # 统计各花色的牌数
        suit_counts = {"万": 0, "筒": 0, "条": 0}
        
        for tile in player.hand_tiles:
            if tile.is_number_tile():
                suit_counts[tile.tile_type.value] += 1
        
        # 选择牌数最少的花色作为缺门
        return min(suit_counts, key=suit_counts.get) 