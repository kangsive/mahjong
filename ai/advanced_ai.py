# -*- coding: utf-8 -*-
"""
高级AI实现 - 基于现代麻将AI算法
包含向听数计算、牌效率分析、攻防平衡等算法
"""

from typing import List, Optional, Dict, Tuple, Set
import random
import copy
from collections import defaultdict, Counter

from .base_ai import BaseAI
from game.tile import Tile, TileType
from game.player import Player
from game.game_engine import GameAction

class AdvancedAI(BaseAI):
    """高级AI实现，包含现代麻将AI算法"""
    
    def __init__(self, difficulty: str = "expert"):
        super().__init__(difficulty)
        self.aggression_level = self._get_aggression_level()
        self.tile_danger_cache = {}
        
    def _get_aggression_level(self) -> float:
        """根据难度获取侵略性水平"""
        if self.difficulty == "expert":
            return 0.9  # 极高侵略性，积极进攻
        elif self.difficulty == "hard":
            return 0.8  # 高侵略性
        elif self.difficulty == "medium":
            return 0.6  # 平衡策略  
        else:  # easy
            return 0.4  # 保守策略
    
    def choose_discard(self, player: Player, available_tiles: List[Tile]) -> Tile:
        """选择要打出的牌 - 基于向听数和牌效率"""
        if not available_tiles:
            return player.hand_tiles[0] if player.hand_tiles else None
        
        # 计算当前手牌的向听数
        current_shanten = self.calculate_shanten(player.hand_tiles, player.melds)
        
        # 为每张可打的牌计算评分
        tile_scores = []
        for tile in available_tiles:
            score = self.evaluate_discard(player, tile, current_shanten)
            tile_scores.append((tile, score))
        
        # 排序并选择最佳选择
        tile_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 根据难度添加适当的随机性
        return self._select_with_randomness(tile_scores)
    
    def calculate_shanten(self, hand_tiles: List[Tile], melds: List = None) -> int:
        """计算向听数（距离胡牌的步数）"""
        if melds is None:
            melds = []
        
        # 统计牌型
        tile_counts = Counter()
        for tile in hand_tiles:
            tile_counts[self._tile_to_key(tile)] += 1
        
        # 计算已有的面子数
        fixed_melds = len(melds)
        
        # 尝试不同的牌型组合
        min_shanten = 8  # 最大向听数
        
        # 检查常规牌型（4面子+1对子）
        regular_shanten = self._calculate_regular_shanten(tile_counts, fixed_melds)
        min_shanten = min(min_shanten, regular_shanten)
        
        # 检查七对子
        if fixed_melds == 0:  # 七对子不能有面子
            pairs_shanten = self._calculate_pairs_shanten(tile_counts)
            min_shanten = min(min_shanten, pairs_shanten)
        
        return min_shanten
    
    def _calculate_regular_shanten(self, tile_counts: Counter, fixed_melds: int) -> int:
        """计算常规牌型的向听数"""
        # 分别计算万、筒、条、字牌
        suits = {'wan': [], 'tong': [], 'tiao': [], 'honor': []}
        
        for tile_key, count in tile_counts.items():
            suit = self._get_suit_from_key(tile_key)
            suits[suit].extend([self._get_value_from_key(tile_key)] * count)
        
        # 对数字牌排序
        for suit in ['wan', 'tong', 'tiao']:
            suits[suit].sort()
        
        min_shanten = 8
        
        # 尝试不同的对子选择
        for pair_suit in suits:
            for pair_value in set(suits[pair_suit]):
                if suits[pair_suit].count(pair_value) >= 2:
                    # 尝试以这个作为对子
                    temp_suits = copy.deepcopy(suits)
                    # 移除两张相同的牌作为对子
                    temp_suits[pair_suit] = [v for v in temp_suits[pair_suit]]
                    temp_suits[pair_suit].remove(pair_value)
                    temp_suits[pair_suit].remove(pair_value)
                    
                    melds_count = fixed_melds
                    blocks_count = 1  # 对子算一个块
                    
                    # 计算每个花色能形成的面子和搭子
                    for suit in suits:
                        if suit == 'honor':
                            honor_melds, honor_blocks = self._analyze_honor_tiles(temp_suits[suit])
                        else:
                            honor_melds, honor_blocks = self._analyze_number_tiles(temp_suits[suit])
                        melds_count += honor_melds
                        blocks_count += honor_blocks
                    
                    # 计算向听数
                    shanten = 8 - melds_count * 2 - blocks_count
                    min_shanten = min(min_shanten, shanten)
        
        return max(0, min_shanten)
    
    def _calculate_pairs_shanten(self, tile_counts: Counter) -> int:
        """计算七对子向听数"""
        pairs = 0
        single_tiles = 0
        
        for count in tile_counts.values():
            if count >= 2:
                pairs += 1
                if count % 2 == 1:
                    single_tiles += 1
            else:
                single_tiles += count
        
        return max(0, 6 - pairs + single_tiles)
    
    def _analyze_honor_tiles(self, honor_tiles: List[int]) -> Tuple[int, int]:
        """分析字牌的面子和搭子"""
        counts = Counter(honor_tiles)
        melds = 0
        blocks = 0
        
        for count in counts.values():
            melds += count // 3
            if count % 3 >= 2:
                blocks += 1
        
        return melds, blocks
    
    def _analyze_number_tiles(self, number_tiles: List[int]) -> Tuple[int, int]:
        """分析数字牌的面子和搭子"""
        if not number_tiles:
            return 0, 0
        
        counts = [0] * 10  # 索引1-9有效
        for tile in number_tiles:
            counts[tile] += 1
        
        return self._extract_melds_and_blocks(counts, 1)
    
    def _extract_melds_and_blocks(self, counts: List[int], start: int) -> Tuple[int, int]:
        """从数字牌中提取面子和搭子的最优组合"""
        if start > 9:
            return 0, 0
        
        if counts[start] == 0:
            return self._extract_melds_and_blocks(counts, start + 1)
        
        max_melds, max_blocks = 0, 0
        
        # 尝试组成刻子
        if counts[start] >= 3:
            counts[start] -= 3
            melds, blocks = self._extract_melds_and_blocks(counts, start)
            max_melds = max(max_melds, melds + 1)
            max_blocks = max(max_blocks, blocks)
            counts[start] += 3
        
        # 尝试组成顺子
        if start <= 7 and counts[start] > 0 and counts[start + 1] > 0 and counts[start + 2] > 0:
            counts[start] -= 1
            counts[start + 1] -= 1
            counts[start + 2] -= 1
            melds, blocks = self._extract_melds_and_blocks(counts, start)
            if melds + 1 > max_melds or (melds + 1 == max_melds and blocks > max_blocks):
                max_melds = melds + 1
                max_blocks = blocks
            counts[start] += 1
            counts[start + 1] += 1
            counts[start + 2] += 1
        
        # 尝试组成搭子
        original_count = counts[start]
        counts[start] = 0
        melds, blocks = self._extract_melds_and_blocks(counts, start + 1)
        
        # 对子
        if original_count >= 2:
            if melds + (blocks + 1) > max_melds + max_blocks:
                max_melds = melds
                max_blocks = blocks + 1
        
        # 两面搭
        if start <= 8 and counts[start + 1] > 0:
            if melds + (blocks + 1) > max_melds + max_blocks:
                max_melds = melds
                max_blocks = blocks + 1
        
        # 嵌张搭
        if start <= 7 and counts[start + 2] > 0:
            if melds + (blocks + 1) > max_melds + max_blocks:
                max_melds = melds
                max_blocks = blocks + 1
        
        counts[start] = original_count
        return max_melds, max_blocks
    
    def evaluate_discard(self, player: Player, tile: Tile, current_shanten: int) -> float:
        """评估打出某张牌的价值"""
        score = 0.0
        
        # 1. 向听数改进（最重要）
        shanten_improvement = self._calculate_shanten_improvement(player, tile, current_shanten)
        score += shanten_improvement * 1000  # 高权重
        
        # 2. 牌效率（有效牌数量）
        efficiency = self._calculate_tile_efficiency(player, tile)
        score += efficiency * 100
        
        # 3. 安全性（避免放炮）
        safety = self._calculate_tile_safety(tile)
        score += safety * 50
        
        # 4. 缺门条件（四川麻将特殊规则）
        missing_suit_bonus = self._get_missing_suit_bonus(player, tile)
        score += missing_suit_bonus
        
        # 5. 牌型价值
        value_bonus = self._get_tile_value_bonus(tile)
        score += value_bonus
        
        # 6. 攻防平衡
        push_fold_adjustment = self._get_push_fold_adjustment(player, tile)
        score += push_fold_adjustment
        
        return score
    
    def _calculate_shanten_improvement(self, player: Player, tile: Tile, current_shanten: int) -> float:
        """计算打出某牌后向听数的改进"""
        # 模拟打出这张牌
        temp_hand = [t for t in player.hand_tiles if t != tile]
        
        # 计算打出后可能的向听数改进
        improvement_count = 0
        total_useful_tiles = 0
        
        # 检查每种可能摸到的牌
        from game.tile import FengType, JianType
        
        for tile_type in TileType:
            if tile_type == TileType.FENG:
                for feng_type in FengType:
                    test_tile = Tile(tile_type, feng_type=feng_type)
                    test_hand = temp_hand + [test_tile]
                    new_shanten = self.calculate_shanten(test_hand, player.melds)
                    
                    if new_shanten < current_shanten:
                        improvement_count += 4  # 每种牌有4张
                    total_useful_tiles += 4
            elif tile_type == TileType.JIAN:
                for jian_type in JianType:
                    test_tile = Tile(tile_type, jian_type=jian_type)
                    test_hand = temp_hand + [test_tile]
                    new_shanten = self.calculate_shanten(test_hand, player.melds)
                    
                    if new_shanten < current_shanten:
                        improvement_count += 4  # 每种牌有4张
                    total_useful_tiles += 4
            else:
                for value in range(1, 10):
                    test_tile = Tile(tile_type, value)
                    test_hand = temp_hand + [test_tile]
                    new_shanten = self.calculate_shanten(test_hand, player.melds)
                    
                    if new_shanten < current_shanten:
                        improvement_count += 4  # 每种牌有4张
                    total_useful_tiles += 4
        
        return improvement_count / max(total_useful_tiles, 1) * 100
    
    def _calculate_tile_efficiency(self, player: Player, tile: Tile) -> float:
        """计算牌效率（基于中张牌理论）"""
        if not tile.is_number_tile():
            return 0.0
        
        # 中张牌（3-7）效率最高
        if 3 <= tile.value <= 7:
            return 100.0
        # 次中张牌（2,8）效率中等
        elif tile.value in [2, 8]:
            return 50.0
        # 边张牌（1,9）效率最低
        else:
            return 10.0
    
    def _calculate_tile_safety(self, tile: Tile) -> float:
        """计算打牌安全性"""
        # 字牌相对安全
        if not tile.is_number_tile():
            return 30.0
        
        # 边张相对安全
        if tile.value in [1, 9]:
            return 20.0
        
        # 中张牌危险
        return -10.0
    
    def _get_missing_suit_bonus(self, player: Player, tile: Tile) -> float:
        """获取缺门奖励"""
        if not hasattr(player, 'missing_suit') or not player.missing_suit:
            return 0.0
        
        missing_suit_type = {
            "万": TileType.WAN,
            "筒": TileType.TONG,  
            "条": TileType.TIAO
        }.get(player.missing_suit)
        
        if tile.tile_type == missing_suit_type:
            return 500.0  # 必须打出缺门牌
        
        return 0.0
    
    def _get_tile_value_bonus(self, tile: Tile) -> float:
        """获取牌型价值奖励"""
        # 5是最有价值的数字牌
        if tile.is_number_tile() and tile.value == 5:
            return -20.0  # 负分，不优先打出
        
        # 3,7次之
        if tile.is_number_tile() and tile.value in [3, 7]:
            return -10.0
        
        return 0.0
    
    def _get_push_fold_adjustment(self, player: Player, tile: Tile) -> float:
        """获取攻防平衡调整"""
        # 根据手牌质量和游戏阶段调整攻防倾向
        shanten = self.calculate_shanten(player.hand_tiles, player.melds)
        
        if shanten <= 1:  # 听牌或一向听
            return self.aggression_level * 50  # 倾向进攻
        elif shanten >= 3:  # 距离胡牌较远
            return -self.aggression_level * 30  # 倾向防守
        
        return 0.0
    
    def _select_with_randomness(self, tile_scores: List[Tuple[Tile, float]]) -> Tile:
        """根据难度添加随机性选择"""
        if self.difficulty == "expert":
            # 专家级：95%选择最优
            if random.random() < 0.95:
                return tile_scores[0][0]
            else:
                return tile_scores[min(1, len(tile_scores)-1)][0]
        elif self.difficulty == "hard":
            # 困难级：85%选择最优，15%选择前三
            if random.random() < 0.85:
                return tile_scores[0][0]
            else:
                top_choices = tile_scores[:min(3, len(tile_scores))]
                return random.choice(top_choices)[0]
        else:
            # 中等和简单：更多随机性
            randomness = 0.3 if self.difficulty == "medium" else 0.5
            if random.random() < (1 - randomness):
                return tile_scores[0][0]
            else:
                return random.choice(tile_scores[:min(5, len(tile_scores))])[0]
    
    def decide_action(self, player: Player, available_actions: List[GameAction], 
                     context: Dict) -> Optional[GameAction]:
        """决定行动 - 基于高级策略"""
        # 胡牌优先级最高
        if GameAction.WIN in available_actions:
            if self._should_win(player, context):
                return GameAction.WIN
        
        # 基于当前向听数和手牌质量决定行动
        current_shanten = self.calculate_shanten(player.hand_tiles, player.melds)
        
        # 杠的策略
        if GameAction.GANG in available_actions:
            if self._should_gang(player, context, current_shanten):
                return GameAction.GANG
        
        # 碰的策略
        if GameAction.PENG in available_actions:
            if self._should_peng(player, context, current_shanten):
                return GameAction.PENG
        
        # 吃的策略（如果支持）
        if GameAction.CHI in available_actions:
            if self._should_chi(player, context, current_shanten):
                return GameAction.CHI
        
        return GameAction.PASS
    
    def _should_win(self, player: Player, context: Dict) -> bool:
        """是否应该胡牌"""
        # 检查是否真的可以胡牌
        new_tile = context.get("last_discarded_tile")
        test_tiles = player.hand_tiles[:]
        if new_tile:
            test_tiles.append(new_tile)
        
        # 验证牌数和基本条件
        if len(test_tiles) + sum(len(meld.tiles) for meld in player.melds) != 14:
            return False
        
        # 检查缺门条件
        if not self._check_missing_suit_condition(player, test_tiles):
            return False
        
        return True
    
    def _should_gang(self, player: Player, context: Dict, current_shanten: int) -> bool:
        """是否应该杠"""
        # 基于侵略性调整杠牌策略
        base_prob = self.aggression_level
        
        # 如果已经听牌，根据侵略性决定
        if current_shanten == 0:
            return random.random() < (base_prob * 0.4)
        
        # 向听数较高时，积极杠牌获得更多摸牌机会
        if current_shanten >= 2:
            return random.random() < (base_prob * 0.9)
        
        return random.random() < (base_prob * 0.7)
    
    def _should_peng(self, player: Player, context: Dict, current_shanten: int) -> bool:
        """是否应该碰"""
        base_prob = self.aggression_level
        
        # 如果已经听牌，根据侵略性决定
        if current_shanten == 0:
            return random.random() < (base_prob * 0.3)
        
        # 计算碰牌后的向听数变化
        test_tile = context.get("last_discarded_tile")
        if test_tile:
            try:
                # 模拟碰牌后的手牌
                temp_hand = [t for t in player.hand_tiles if str(t) != str(test_tile)]
                temp_melds = player.melds + [type('Meld', (), {'tiles': [test_tile] * 3})]
                new_shanten = self.calculate_shanten(temp_hand, temp_melds)
                
                # 如果向听数减少或相等，积极碰牌
                if new_shanten <= current_shanten:
                    return random.random() < (base_prob * 0.8)
            except:
                # 如果计算失败，使用基础概率
                pass
        
        return random.random() < (base_prob * 0.5)
    
    def _should_chi(self, player: Player, context: Dict, current_shanten: int) -> bool:
        """是否应该吃（四川麻将通常不允许吃）"""
        # 四川麻将规则下通常不允许吃牌
        return False
    
    def _check_missing_suit_condition(self, player: Player, tiles: List[Tile]) -> bool:
        """检查缺门条件"""
        if not hasattr(player, 'missing_suit') or not player.missing_suit:
            return True  # 如果没有缺门要求，则通过
        
        missing_suit_type = {
            "万": TileType.WAN,
            "筒": TileType.TONG,
            "条": TileType.TIAO
        }.get(player.missing_suit)
        
        if not missing_suit_type:
            return True
        
        # 确保没有缺门的牌
        has_missing_suit = any(tile.tile_type == missing_suit_type for tile in tiles)
        return not has_missing_suit
    
    def choose_missing_suit(self, player: Player) -> str:
        """选择缺门花色 - 基于牌效分析"""
        suits = {"万": TileType.WAN, "筒": TileType.TONG, "条": TileType.TIAO}
        suit_counts = {suit: 0 for suit in suits.keys()}
        suit_efficiency = {suit: 0.0 for suit in suits.keys()}
        
        # 统计每种花色的数量和效率
        for tile in player.hand_tiles:
            for suit_name, suit_type in suits.items():
                if tile.tile_type == suit_type:
                    suit_counts[suit_name] += 1
                    # 计算这张牌的效率贡献
                    if 3 <= tile.value <= 7:
                        suit_efficiency[suit_name] += 3
                    elif tile.value in [2, 8]:
                        suit_efficiency[suit_name] += 2
                    else:
                        suit_efficiency[suit_name] += 1
        
        # 选择数量最少且效率最低的花色作为缺门
        best_suit = min(suits.keys(), 
                       key=lambda x: (suit_counts[x], suit_efficiency[x]))
        
        return best_suit
    
    def choose_exchange_tiles(self, player: Player, exchange_count: int) -> List[Tile]:
        """选择换牌（血战到底开局）"""
        if exchange_count <= 0:
            return []
        
        # 分析手牌，选择最不需要的牌进行换牌
        tile_values = []
        for tile in player.hand_tiles:
            value = self._evaluate_tile_keep_value(player, tile)
            tile_values.append((tile, value))
        
        # 选择价值最低的牌进行换牌
        tile_values.sort(key=lambda x: x[1])
        
        return [tile for tile, _ in tile_values[:min(exchange_count, len(tile_values))]]
    
    def _evaluate_tile_keep_value(self, player: Player, tile: Tile) -> float:
        """评估保留某张牌的价值"""
        value = 0.0
        
        # 1. 基础牌效价值
        if tile.is_number_tile():
            if 3 <= tile.value <= 7:
                value += 100
            elif tile.value in [2, 8]:
                value += 50
            else:
                value += 10
        else:
            value += 30
        
        # 2. 同花色牌的协同效应
        same_suit_tiles = [t for t in player.hand_tiles if t.tile_type == tile.tile_type]
        if len(same_suit_tiles) >= 3:
            value += 30
        
        # 3. 连张价值
        if tile.is_number_tile():
            adjacent_count = 0
            for other_tile in player.hand_tiles:
                if (other_tile.tile_type == tile.tile_type and 
                    abs(other_tile.value - tile.value) <= 2 and
                    other_tile.value != tile.value):
                    adjacent_count += 1
            value += adjacent_count * 20
        
        return value
    
    # 工具方法
    def _tile_to_key(self, tile: Tile) -> str:
        """将牌转换为字符串键"""
        return str(tile)
    
    def _get_suit_from_key(self, tile_key: str) -> str:
        """从牌键获取花色"""
        if '万' in tile_key:
            return 'wan'
        elif '筒' in tile_key:
            return 'tong'
        elif '条' in tile_key:
            return 'tiao'
        else:
            return 'honor'
    
    def _get_value_from_key(self, tile_key: str) -> int:
        """从牌键获取数值"""
        import re
        match = re.search(r'\d+', tile_key)
        if match:
            return int(match.group())
        else:
            # 对于风牌和箭牌，分配固定数值
            if '东' in tile_key:
                return 1
            elif '南' in tile_key:
                return 2
            elif '西' in tile_key:
                return 3
            elif '北' in tile_key:
                return 4
            elif '中' in tile_key:
                return 1
            elif '发' in tile_key:
                return 2
            elif '白' in tile_key:
                return 3
            else:
                return 1 