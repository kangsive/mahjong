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
            WinPattern("清一色", "只有一种花色", 2),
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
        
        # 加上已经组合的牌
        for meld in player.melds:
            test_tiles.extend(meld.tiles)
        
        # 检查牌数是否正确（14张）
        if len(test_tiles) != 14:
            return False
        
        # 检查是否为七对子
        if self._is_seven_pairs(test_tiles):
            return True
        
        # 检查基本胡牌牌型（4个面子+1个对子）
        return self._check_basic_win_pattern(test_tiles)
    
    def _check_missing_suit(self, player: Player) -> bool:
        """检查是否满足缺一门条件"""
        if not hasattr(player, 'missing_suit') or not player.missing_suit:
            return False
        
        # 收集所有牌（手牌+已组合的牌）
        all_tiles = player.hand_tiles[:]
        for meld in player.melds:
            all_tiles.extend(meld.tiles)
        
        # 检查是否真的缺少该门
        missing_suit_type = {
            "万": TileType.WAN,
            "筒": TileType.TONG, 
            "条": TileType.TIAO
        }.get(player.missing_suit)
        
        if not missing_suit_type:
            return False
        
        # 确保没有缺门的牌
        has_missing_suit = any(tile.tile_type == missing_suit_type for tile in all_tiles)
        return not has_missing_suit
    
    def _check_basic_win_pattern(self, tiles: List[Tile]) -> bool:
        """检查基本胡牌牌型（4个面子+1个对子）"""
        # 统计每种牌的数量
        tile_counts = {}
        for tile in tiles:
            key = self._tile_to_key(tile)
            tile_counts[key] = tile_counts.get(key, 0) + 1
        
        return self._try_form_melds(tile_counts, 0, False)
    
    def _tile_to_key(self, tile: Tile) -> tuple:
        """将牌转换为可比较的键"""
        return (tile.tile_type, tile.value)
    
    def _try_form_melds(self, tile_counts: Dict[tuple, int], melds_formed: int, has_pair: bool) -> bool:
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
        
        # 计算基础番数（不包含自摸加底）
        fan_count = self._calculate_fan(winner, win_tile, False)  # 先不算自摸
        
        # 四川麻将计分规则：
        # - 平胡（1番）= 1分
        # - 其他番型按2的幂次方计算，但有封顶
        if fan_count == 1:
            # 平胡固定1分
            base_score = 1
        else:
            # 其他番型按2的幂次方计算
            base_score = min(2 ** fan_count, 2 ** self.max_score)
        
        # 自摸加底：自摸胡再加1分
        if is_self_draw:
            base_score += 1
        
        # 血战到底规则
        if is_self_draw:
            # 自摸：其他所有人都付钱
            other_players = [p for p in players if p != winner]
            for player in other_players:
                scores[player.name] = -base_score
            scores[winner.name] = base_score * len(other_players)
        else:
            # 点炮：放炮者付钱
            if discard_player and discard_player != winner:
                scores[discard_player.name] = -base_score
                scores[winner.name] = base_score
            else:
                # 如果没有明确的放炮者，按自摸处理（保险起见）
                other_players = [p for p in players if p != winner]
                for player in other_players:
                    scores[player.name] = -base_score
                scores[winner.name] = base_score * len(other_players)
        
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
        
        # 清一色（2番）
        elif self._is_flush(all_tiles):
            fan_count += 2
        
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
        
        # 至少1番（平胡）
        fan_count = max(fan_count, 1)
        
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