# -*- coding: utf-8 -*-
"""
向听数AI - 基于向听数和牌效率理论的高级麻将AI

这个AI实现了现代麻将理论中的核心概念：
1. 向听数 (Shanten Number) 计算
2. 牌效率 (Tile Efficiency) 分析
3. 有效进张 (Ukeire) 最大化
4. 结合四川麻将特殊规则
"""

from typing import List, Literal, Optional, Dict, Tuple, Set, Union
import random
from collections import defaultdict, Counter
from copy import deepcopy

from rules.base_rule import BaseRule
from rules.sichuan_rule import SichuanRule

from .base_ai import BaseAI
from game.tile import Tile, TileType, FengType, JianType
from game.player import Player
from game.game_engine import GameAction

class ShantenCalculator:
    """向听数计算器"""
    
    @staticmethod
    def calculate_shanten(
        tiles: List[Tile], 
        melds_count: int = 0, 
        shentan_type: Literal["general", "pairs", "kokushi"] = "general"
    ) -> int:
        """
        计算向听数
        
        Args:
            tiles: 手牌
            melds_count: 已有的面子数量
            shentan_type: 向听数类型，可选值为 "general" (一般型)，"pairs" (七对子型)，"kokushi" (国士无双型)
            
        Returns:
            向听数 (0表示听牌，-1表示已胡牌)
        """
        if not tiles:
            return 13
        
        # 统计牌的数量
        tile_counts = ShantenCalculator._count_tiles(tiles)
        
        # 根据向听数类型计算向听数
        if shentan_type == "general":
            general_shanten = ShantenCalculator._calculate_standard_shanten(tile_counts, melds_count)
            return general_shanten
        elif shentan_type == "pairs":
            pairs_shanten = ShantenCalculator._calculate_seven_pairs_shanten(tile_counts)
            return pairs_shanten
        elif shentan_type == "kokushi":
            kokushi_shanten = ShantenCalculator._calculate_kokushi_shanten(tile_counts)
            return kokushi_shanten

        # 国士无双向听数
        # kokushi_shanten = ShantenCalculator._calculate_kokushi_shanten(tile_counts)
        
        # 返回最小值
        return min(general_shanten, pairs_shanten)
    
    @staticmethod
    def _count_tiles(tiles: List[Tile]) -> Dict[Tuple, int]:
        """统计牌的数量"""
        tile_counts = defaultdict(int)
        for tile in tiles:
            if tile.tile_type == TileType.FENG:
                key = (tile.tile_type, tile.feng_type)
            elif tile.tile_type == TileType.JIAN:
                key = (tile.tile_type, tile.jian_type)
            else:
                key = (tile.tile_type, tile.value)
            tile_counts[key] += 1
        return dict(tile_counts)
    
    @staticmethod
    def _calculate_standard_shanten(
            tile_counts: Dict[Tuple[TileType, Union[int, FengType, JianType]], int], 
            melds_count: int = 0
    ) -> int:
        """计算标准型向听数（4面子+1对子）"""
        # 简化实现：使用经典的向听数算法
        counts = deepcopy(tile_counts)
        
        # 分别处理字牌和数字牌
        honor_melds = 0
        honor_pairs = 0
        
        # 处理字牌
        for (tile_type, value), count in list(counts.items()):
            if tile_type in [TileType.FENG, TileType.JIAN]:
                if count >= 3:
                    honor_melds += count // 3
                    count = count % 3
                if count == 2:
                    honor_pairs += 1
                del counts[(tile_type, value)]
        
        # 处理数字牌
        suits_data = {}
        for suit in [TileType.WAN, TileType.TONG, TileType.TIAO]:
            suit_counts = [counts.get((suit, i), 0) for i in range(1, 10)]
            suits_data[suit] = suit_counts
        
        # 最差情况大的向听数
        min_shanten = 8
            
        # 计算数字牌的最佳组合 (面子数，搭子数，对子数)
        for wan_result in ShantenCalculator._get_suit_combinations(suits_data[TileType.WAN]):
            for tong_result in ShantenCalculator._get_suit_combinations(suits_data[TileType.TONG]):
                for tiao_result in ShantenCalculator._get_suit_combinations(suits_data[TileType.TIAO]):
                    total_melds = wan_result[0] + tong_result[0] + tiao_result[0] + honor_melds + melds_count
                    total_tatsu = wan_result[1] + tong_result[1] + tiao_result[1]
                    total_pairs = + wan_result[2] + tong_result[2] + tiao_result[2] + honor_pairs

                    # 如果手牌已经胡牌，则向听数为-1
                    if total_melds == 4 and total_pairs == 1 and total_tatsu == 0:
                        return -1
                    
                    # 计算向听数
                    shanten = ShantenCalculator._calc_shanten_from_groups(
                        total_melds, total_tatsu, total_pairs
                    )
                    min_shanten = min(min_shanten, shanten)
        
        return max(0, min_shanten)
    
    @staticmethod
    def _get_suit_combinations(suit_counts: List[int]) -> List[Tuple[int, int, int]]:
        """
        获取单个花色的所有可能组合
        
        使用递归回溯算法枚举所有可能的面子、搭子、对子组合
        返回 (面子数, 搭子数, 对子数) 的所有可能组合
        """
        if not suit_counts or len(suit_counts) != 9:
            return [(0, 0, 0)]
        
        # 如果所有牌都是0，返回空组合
        if all(count == 0 for count in suit_counts):
            return [(0, 0, 0)]
        
        results = []
        ShantenCalculator._enumerate_combinations(suit_counts[:], 0, 0, 0, results)
        
        # 去重并返回
        unique_results = list(set(results))
        return unique_results if unique_results else [(0, 0, 0)]
    
    @staticmethod
    def _enumerate_combinations(
        counts: List[int], 
        melds: int, 
        tatsu: int, 
        pairs: int, 
        results: List[Tuple[int, int, int]]
    ):
        """
        递归枚举所有可能的组合
        
        Args:
            counts: 当前各位置的牌数
            melds: 已形成的面子数
            tatsu: 已形成的搭子数  
            pairs: 已形成的对子数
            results: 结果列表
        """
        # 寻找第一个非零位置
        pos = -1
        for i in range(9):
            if counts[i] > 0:
                pos = i
                break
        
        # 如果没有牌了，记录当前组合
        if pos == -1:
            results.append((melds, tatsu, pairs))
            return
        
        # 尝试所有可能的处理方式
        
        # 1. 尝试形成刻子（如果有3张或以上）
        if counts[pos] >= 3:
            counts[pos] -= 3
            ShantenCalculator._enumerate_combinations(counts, melds + 1, tatsu, pairs, results)
            counts[pos] += 3
        
        # 2. 尝试形成顺子（如果可能）
        if pos <= 6 and counts[pos] > 0 and counts[pos + 1] > 0 and counts[pos + 2] > 0:
            counts[pos] -= 1
            counts[pos + 1] -= 1
            counts[pos + 2] -= 1
            ShantenCalculator._enumerate_combinations(counts, melds + 1, tatsu, pairs, results)
            counts[pos] += 1
            counts[pos + 1] += 1
            counts[pos + 2] += 1
        
        # 3. 尝试形成对子（如果有2张或以上）
        if counts[pos] >= 2:
            counts[pos] -= 2
            ShantenCalculator._enumerate_combinations(counts, melds, tatsu, pairs + 1, results)
            counts[pos] += 2
        
        # 4. 尝试形成两面搭子（如果可能）
        if pos <= 7 and counts[pos] > 0 and counts[pos + 1] > 0:
            counts[pos] -= 1
            counts[pos + 1] -= 1
            ShantenCalculator._enumerate_combinations(counts, melds, tatsu + 1, pairs, results)
            counts[pos] += 1
            counts[pos + 1] += 1
        
        # 5. 尝试形成嵌张搭子（如果可能）
        if pos <= 6 and counts[pos] > 0 and counts[pos + 2] > 0:
            counts[pos] -= 1
            counts[pos + 2] -= 1
            ShantenCalculator._enumerate_combinations(counts, melds, tatsu + 1, pairs, results)
            counts[pos] += 1
            counts[pos + 2] += 1
        
        # 6. 跳过当前牌（作为孤张处理）
        counts[pos] -= 1
        ShantenCalculator._enumerate_combinations(counts, melds, tatsu, pairs, results)
        counts[pos] += 1
    
    @staticmethod
    def _calc_shanten_from_groups(melds: int, tatsu: int, pairs: int) -> int:
        """
        根据基本公式(https://riichi.wiki/Shanten)计算向听数
        
        基本公式:
            basicShanten = 8 - 2 * melds - min(tatsu + pairs, 4 - melds)
            如果存在至少一个对子且 (melds + tatsu + pairs) >= 5，则再减1
        """
        shanten = 8 - 2 * melds - min(tatsu + pairs, 4 - melds)
        if pairs >= 1 and (melds + tatsu + pairs) >= 5:
            shanten -= 1
        return shanten
    
    @staticmethod
    def _calculate_seven_pairs_shanten(tile_counts: Dict[Tuple[TileType, Union[int, FengType, JianType]], int]) -> int:
        """计算七对子向听数"""
        pairs = 0
        single_tiles = 0
        
        for count in tile_counts.values():
            if count >= 2:
                pairs += count // 2
            if count % 2 == 1:
                single_tiles += 1
        
        # 如果手牌已经胡牌，则向听数为-1
        if pairs == 7:
            return -1
        
        # return 6 - pairs + max(0, single_tiles - (7 - pairs))
        return 6 - pairs
    
    @staticmethod
    def _calculate_kokushi_shanten(tile_counts: Dict[Tuple[TileType, Union[int, FengType, JianType]], int]) -> int:
        """
        计算国士无双向听数
        
        算法思想：
        1. 如果手牌里有全部n种国士无双的牌，且每种都是只有一张，则向听数是13-n
        2. 如果手牌里有n种国士无双的牌，且其中至少有一张的数量>=2，则向听数也是12-n
        """
        # 定义国士无双的13种牌的keys
        kokushi_keys = [
            (TileType.WAN, 1), (TileType.WAN, 9),
            (TileType.TONG, 1), (TileType.TONG, 9),
            (TileType.TIAO, 1), (TileType.TIAO, 9),
            (TileType.FENG, FengType.DONG), (TileType.FENG, FengType.NAN),
            (TileType.FENG, FengType.XI), (TileType.FENG, FengType.BEI),
            (TileType.JIAN, JianType.ZHONG), (TileType.JIAN, JianType.FA),
            (TileType.JIAN, JianType.BAI)
        ]
        
        # 统计手牌中有多少种国士无双牌
        kokushi_types_count = 0
        has_pair = False
        
        for key in kokushi_keys:
            count = tile_counts.get(key, 0)
            if count > 0:
                kokushi_types_count += 1
                if count >= 2:
                    has_pair = True
        
        if has_pair:
            if kokushi_types_count == 13:
                # 胡牌向听数为-1
                return -1
            shanten = 12 - kokushi_types_count
        else:
            shanten = 13 - kokushi_types_count
        
        return max(0, shanten)

class UkeireCalculator:
    """有效进张计算器"""
    
    @staticmethod
    def calculate_ukeire(
        tiles: List[Tile], # 13张
        melds_count: int = 0, 
        missing_suit: Optional[str] = None,
        discard_pool: List[Tile] = None,
        shentan_type: Literal["general", "pairs", "kokushi"] = "general"
    ) -> Dict[Tuple[TileType, Union[int, FengType, JianType]], int]:
        """
        计算有效进张
        
        Args:
            tiles: 当前手牌
            melds_count: 已有面子数 (副露)
            missing_suit: 缺门花色, 万/筒/条
            discard_pool: 已出的牌 （牌河）
            
        Returns:
            {牌的key: 有效张数}
        """
        if discard_pool is None:
            discard_pool = []
        
        current_shanten = ShantenCalculator.calculate_shanten(tiles, melds_count, shentan_type=shentan_type)
        
        # 统计已经出现的牌
        used_tiles = Counter()
        for tile in tiles + discard_pool:
            if tile.tile_type == TileType.FENG:
                key = (tile.tile_type, tile.feng_type)
            elif tile.tile_type == TileType.JIAN:
                key = (tile.tile_type, tile.jian_type)
            else:
                key = (tile.tile_type, tile.value)
            used_tiles[key] += 1
        
        # 计算各种牌的进张效果
        ukeire = {}
        
        # 遍历所有可能的牌
        for tile_type in [TileType.WAN, TileType.TONG, TileType.TIAO, TileType.FENG, TileType.JIAN]:
            if tile_type == TileType.FENG:
                values = [FengType.DONG, FengType.NAN, FengType.XI, FengType.BEI]  # 风牌
            elif tile_type == TileType.JIAN:
                values = [JianType.ZHONG, JianType.FA, JianType.BAI]  # 箭牌
            else:
                values = range(1, 10) # 0-9
            
            for value in values:
                key = (tile_type, value)
                # if tile_type == TileType.WAN and value == 9:
                #     print()
                
                # 检查是否是缺门牌
                if missing_suit and UkeireCalculator._is_missing_suit_tile(tile_type, missing_suit):
                    continue
                
                remaining_count = 4 - used_tiles.get(key, 0) # 每种花色4张，所以剩余张数就是4减去已出现过的张数
                if remaining_count <= 0:
                    continue
                
                # 模拟摸到这张牌后的向听数
                test_tiles = tiles + [UkeireCalculator._create_tile_from_key(key)]
                new_shanten = ShantenCalculator.calculate_shanten(test_tiles, melds_count, shentan_type=shentan_type)
                
                # 如果向听数减少，这是有效进张
                if new_shanten < current_shanten:
                    ukeire[key] = remaining_count
        
        return ukeire
    
    @staticmethod
    def _is_missing_suit_tile(tile_type: TileType, missing_suit: str) -> bool:
        """判断是否是缺门牌"""
        missing_suit_map = {
            "万": TileType.WAN,
            "筒": TileType.TONG,
            "条": TileType.TIAO
        }
        return tile_type == missing_suit_map.get(missing_suit)
    
    @staticmethod
    def _create_tile_from_key(key: Tuple[TileType, Union[int, FengType, JianType]]) -> Tile:
        """从key创建牌对象"""
        tile_type, value = key
        if tile_type in [TileType.WAN, TileType.TONG, TileType.TIAO]:
            return Tile(tile_type, value)
        elif tile_type == TileType.FENG:
            return Tile(tile_type, feng_type=value)
        else:
            return Tile(tile_type, jian_type=value)

class TileEfficiencyAnalyzer:
    """牌效率分析器"""

    @staticmethod
    def analyze_discard_efficiency(
            player: Player, 
            available_tiles: List[Tile],
            discard_pool: List[Tile] = None,
            shentan_type: Literal["general", "pairs", "kokushi"] = "general",
            use_peak_theory: bool = True
    ) -> Dict[Tile, float]:
        """
        分析打牌效率 - 集成一向听顶峰理论
        
        Returns:
            {牌: 效率分数} (分数越高越应该打出)
        """
        if discard_pool is None:
            discard_pool = []

        efficiency_scores = {}
        current_shanten = ShantenCalculator.calculate_shanten(
            player.hand_tiles, len(player.melds), shentan_type=shentan_type
        )

        for tile in available_tiles:
            # 计算打出这张牌后的牌效率 - 只移除一张指定的牌
            remaining_tiles = player.hand_tiles.copy()
            remaining_tiles.remove(tile)  # remove()方法只移除第一个匹配的元素

            # 计算向听数变化
            after_shanten = ShantenCalculator.calculate_shanten(
                remaining_tiles, len(player.melds), shentan_type=shentan_type
            )

            # 计算有效进张数量
            ukeire = UkeireCalculator.calculate_ukeire(
                remaining_tiles, len(player.melds), 
                getattr(player, 'missing_suit', None), 
                discard_pool, 
                shentan_type=shentan_type
            )
            total_ukeire = sum(ukeire.values())

            # 计算效率分数
            efficiency = TileEfficiencyAnalyzer._calculate_efficiency_score(
                tile, current_shanten, after_shanten, total_ukeire, player
            )

            efficiency_scores[tile] = (efficiency, ukeire)

        # 应用一向听顶峰理论优化top3选择
        if current_shanten <= 2 and use_peak_theory:  # 在二向听和一向听时应用顶峰理论
            efficiency_scores = TileEfficiencyAnalyzer._apply_peak_theory(
                ukeire, efficiency_scores, player, discard_pool, shentan_type,
            )

        return efficiency_scores

    @staticmethod
    def _calculate_efficiency_score(
            tile: Tile, 
            current_shanten: int, 
            after_shanten: int,
            total_ukeire: int, 
            player: Player
    ) -> float:
        """计算效率分数"""
        score = 0.0

        # 向听数不增加是基本要求
        if after_shanten <= current_shanten:
            score += 50.0  # 向听数减少应该加分
        else:
            score -= 50.0  # 向听数增加应该减分

        # 有效进张数量
        score += total_ukeire * 2.0

        # 缺门牌必须打出（四川麻将规则）
        missing_suit = getattr(player, 'missing_suit', None)
        if missing_suit:
            missing_suit_map = {
                "万": TileType.WAN,
                "筒": TileType.TONG,
                "条": TileType.TIAO
            }
            if tile.tile_type == missing_suit_map.get(missing_suit):
                score += 100.0

        # 危险牌调整 - 支持高级和简化两种模式
        if hasattr(player, 'game_context') and player.game_context:
            # 高级模式：使用完整防守理论
            context = player.game_context
            danger_level = TileEfficiencyAnalyzer.evaluate_tile_danger_level(
                tile,
                context.get('discard_pool', []),
                context.get('all_visible_tiles', []),
                context.get('round_number', 1)
            )
            score -= danger_level * 15.0  # 根据危险度调整分数
        else:
            # 简化模式：使用基础判断
            if TileEfficiencyAnalyzer._is_dangerous_tile(tile):
                score -= 10.0

        return score

    @staticmethod
    def _apply_peak_theory(
        ukeire: Dict[Tuple[TileType, Union[int, FengType, JianType]], int],
        efficiency_scores: Dict[Tile, float], 
        player: Player, 
        discard_pool: List[Tile],
        shentan_type: Literal["general", "pairs", "kokushi"] = "general"
    ) -> Dict[Tile, float]:
        """
        应用一向听顶峰理论优化top3选择
        
        核心思想：
        1. 找出效率分数最高的前3张牌
        2. 对这些牌进行深度分析，计算进张后的听牌形态
        3. 优先选择能形成多面听的选择
        4. 只增不减原有分数
        """
        if not efficiency_scores:
            return efficiency_scores

        # 获取当前向听数
        current_shanten = ShantenCalculator.calculate_shanten(
            player.hand_tiles, len(player.melds), shentan_type=shentan_type
        )

        # 只在二向听和一向听时应用顶峰理论
        if current_shanten > 2:
            return efficiency_scores

        # 找出top3候选牌
        sorted_tiles = sorted(efficiency_scores.items(), key=lambda x: x[1][0], reverse=True)
        top3_tiles = sorted_tiles[:3]

        if len(top3_tiles) <= 1:
            return efficiency_scores

        # 检查top1是否有并列情况
        top_score = top3_tiles[0][1][0]
        tied_top_tiles = [tile for tile, score in top3_tiles if abs(score[0] - top_score) < 0.1]

        if len(tied_top_tiles) <= 1:
            # 没有并列，直接返回
            return efficiency_scores

        # 有并列情况，应用顶峰理论重新排序
        enhanced_scores = efficiency_scores.copy()

        for tile, original_score in top3_tiles:
            # 计算顶峰理论加分
            peak_bonus = TileEfficiencyAnalyzer._calculate_peak_theory_bonus(
                tile, player, discard_pool, current_shanten, shentan_type, ukeire
            )

            # 只增不减
            enhanced_scores[tile] = (original_score[0] + peak_bonus, original_score[1])

        return enhanced_scores

    @staticmethod
    def _calculate_peak_theory_bonus(
        discard_tile: Tile, 
        player: Player, 
        discard_pool: List[Tile],
        current_shanten: int,
        shentan_type: Literal["general", "pairs", "kokushi"] = "general",
        ukeire: Dict[Tuple[TileType, Union[int, FengType, JianType]], int] = None
    ) -> float:
        """
        计算一向听顶峰理论加分
        
        分析逻辑：
        1. 模拟打出这张牌后的手牌状态
        2. 枚举所有可能的进张
        3. 计算每种进张后能形成的听牌类型和进张数
        4. 综合评估进张后的听牌质量
        """
        if current_shanten > 2:
            return 0.0

        # 模拟打出这张牌后的手牌
        remaining_tiles = player.hand_tiles.copy()
        remaining_tiles.remove(discard_tile)

        after_shanten = ShantenCalculator.calculate_shanten(
            remaining_tiles, len(player.melds), shentan_type=shentan_type
        )

        # 如果打出后向听数变差，不给加分
        if after_shanten > current_shanten:
            return 0.0

        # 计算所有可能的进张
        if ukeire is None:
            ukeire = UkeireCalculator.calculate_ukeire(
                remaining_tiles, len(player.melds), 
                getattr(player, 'missing_suit', None), 
                discard_pool, 
                shentan_type=shentan_type
            )

        if not ukeire:
            return 0.0

        # 分析每种进张后的听牌形态
        waiting_patterns = TileEfficiencyAnalyzer._analyze_waiting_patterns(
            remaining_tiles, ukeire, player, shentan_type, discard_pool
        )

        # 计算顶峰理论加分
        peak_bonus = 0.0

        # 一向听类型奖励
        one_shanten_types = waiting_patterns.get('one_shanten_types', {})
        if one_shanten_types:
            for tile_key, one_shanten_pattern in one_shanten_types.items():
                match one_shanten_pattern:
                    case "余剩牌形":
                        peak_bonus += 10.0
                    case "完全一向听":
                        peak_bonus += 20.0
                    case "无雀头一向听":
                        peak_bonus += 30.0
                    case "双靠张一向听":
                        peak_bonus += 40.0
                    case "七对子一向听":
                        peak_bonus += 10.0
                    case "七对子与面子手复合一向听":
                        peak_bonus += 20.0
                    case "国士一向听":
                        peak_bonus += 10.0

        # 听牌类型奖励
        else:
            # 1. 两面听奖励 - 优先形成两面听
            ryanmen_wait_patterns = waiting_patterns.get('ryanmen_wait_count', 0)
            peak_bonus += ryanmen_wait_patterns * 8.0

            # 2. 高进张数奖励 - 听牌后进张数越多越好
            avg_final_ukeire = waiting_patterns.get('avg_final_ukeire', 0)
            peak_bonus += avg_final_ukeire * 1.5

            # 3. 听牌类型多样性奖励 - 能形成多种不同听牌形态
            pattern_diversity = waiting_patterns.get('pattern_diversity', 0)
            peak_bonus += pattern_diversity * 5.0

            # 4. 避免单调听牌的惩罚转换为奖励
            single_wait_penalty = waiting_patterns.get('single_wait_count', 0)
            if waiting_patterns.get('total_patterns', 1) > 0:
                single_wait_ratio = single_wait_penalty / waiting_patterns['total_patterns']
                peak_bonus -= single_wait_ratio * 5.0  # 单调听太多会减分

        return max(0.0, peak_bonus)

    @staticmethod
    def _analyze_waiting_patterns(
        remaining_tiles: List[Tile], # 13张
        ukeire: Dict[Tuple[TileType, Union[int, FengType, JianType]], int],
        player: Player,
        shentan_type: Literal["general", "pairs", "kokushi"] = "general",
        discard_pool: List[Tile] = []
    ) -> Dict[str, float]:
        """
        分析进张后的听牌形态
        
        返回听牌形态的统计信息
        """
        patterns = {
            'ryanmen_wait_count': 0,      # 两面听数量
            'single_wait_count': 0,  # 单调听数量
            'total_patterns': 0,     # 总听牌模式数
            'pattern_diversity': 0,  # 听牌类型多样性
            'avg_final_ukeire': 0.0  # 平均最终进张数
        }

        if not ukeire:
            return patterns

        total_final_ukeire = 0
        one_shanten_types = dict()
        tenpai_types = set()

        # 枚举每种可能的进张
        for tile_key, count in ukeire.items():
            # 模拟摸到这张牌
            test_tile = UkeireCalculator._create_tile_from_key(tile_key)
            test_tiles = remaining_tiles + [test_tile]

            # 检查是否听牌
            test_shanten = ShantenCalculator.calculate_shanten(
                test_tiles, len(player.melds), shentan_type=shentan_type
            )

            if test_shanten <= 1:  # 接近听牌或已听牌
                # test_tiles现在是14张（摸进后），需要找出最优打牌变成13张听牌
                final_waiting_state = TileEfficiencyAnalyzer._find_optimal_waiting_state(
                    test_tiles, player, shentan_type, discard_pool
                )

                if final_waiting_state is None:
                    pass

                if test_shanten == 1:
                    one_shanten_pattern = TileEfficiencyAnalyzer._classify_1shanten_pattern(
                        final_waiting_state[0], final_waiting_state[1]
                    )
                    one_shanten_types[tile_key] = one_shanten_pattern
                    patterns['one_shanten_types'] = one_shanten_types

                elif final_waiting_state and test_shanten == 0: # 否则听牌状态
                    final_tiles, final_ukeire = final_waiting_state
                    final_count = sum(final_ukeire.values())

                    # 分析听牌类型
                    tenpai_type = TileEfficiencyAnalyzer._classify_tenpai_pattern(
                        final_tiles, final_ukeire
                    )
                    tenpai_types.add(tenpai_type)

                    total_final_ukeire += final_count * count

                    # 统计多面听和单调听
                    if final_count > 1:  # 多面听
                        patterns['ryanmen_wait_count'] += count
                    else: 
                        patterns['single_wait_count'] += count

                    # 计算平均值和多样性
                    patterns['total_patterns'] = len(tenpai_types)
                    patterns['avg_final_ukeire'] = total_final_ukeire / patterns['total_patterns']
                    patterns['pattern_diversity'] = len(tenpai_types)

        return patterns

    @staticmethod
    def _find_optimal_waiting_state(
        tiles: List[Tile],  # 14张手牌（刚摸进后）
        player: Player,
        shentan_type: Literal["general", "pairs", "kokushi"] = "general",
        discard_pool: List[Tile] = []
    ) -> Optional[Tuple[List[Tile], Dict[Tuple[TileType, Union[int, FengType, JianType]], int]]]:
        """
        找出14张手牌的最优听牌状态
        
        逻辑：
        1. 对手牌进行打牌效率分析（不使用顶峰理论）
        2. 选择效率最高的打牌
        
        Returns:
            (打出后的手牌, 最终进张字典)
        """
        # if len(tiles) != 14:
        #     return None

        # 创建临时玩家对象来进行分析, 因为我们模拟的是多模一张牌后(不是玩家真正的手牌现状)
        temp_player = Player(f"temp_{player.name}")
        temp_player.hand_tiles = tiles

        # 继承缺门设置
        if hasattr(player, 'missing_suit'):
            temp_player.missing_suit = player.missing_suit
            temp_player.melds = deepcopy(player.melds)

        efficiency_scores = TileEfficiencyAnalyzer.analyze_discard_efficiency(
            temp_player, tiles, discard_pool=discard_pool, shentan_type=shentan_type, use_peak_theory=False
        )

        # 后者效率分数最高的牌
        sorted_tiles = sorted(efficiency_scores.items(), key=lambda x: x[1][0], reverse=True)
        discard_tile = sorted_tiles[0][0]
        final_ukeire = sorted_tiles[0][1][1]

        tiles.remove(discard_tile)

        best_final_state = (tiles, final_ukeire)

        return best_final_state

    # 判断一向听类型
    @staticmethod
    def _classify_1shanten_pattern(
        tiles: List[Tile], 
        final_ukeire: Dict[Tuple[TileType, Union[int, FengType, JianType]], int]
    ) -> str:
        """
        判断一向听类型
        """
        # 1. 余剩牌形。2面子+2搭子+1雀头+1剩余牌。这种手牌的特点是有一张不增加进张面的手牌（但可能可以改良）
        # 2. 完全一向听。2面子+1搭子+1复合搭子+1雀头。特点是手里没有一张多余的牌。
        # 3. 无雀头一向听。3面子+1或2搭子。手里没有雀头。
        # 4. 双靠张一向听（くっつき一向听）。3面子+1雀头。手里缺少搭子。
        # 5. 七对子一向听。
        # 6. 七对子与面子手复合一向听。
        # 7. 国士一向听。
        all_patterns = [
            "余剩牌形", "完全一向听", "无雀头一向听", "双靠张一向听", "七对子一向听", "七对子与面子手复合一向听", "国士一向听"
        ]
        return all_patterns[0]

    @staticmethod
    def _classify_tenpai_pattern(
        tiles: List[Tile], 
        final_ukeire: Dict[Tuple[TileType, Union[int, FengType, JianType]], int]
    ) -> str:
        """
        分类听牌形态
        
        根据可和牌的数量及牌型组合分类：
        - 单听（1张）：'penchan'(边张)、'kanchan'(嵌张)、'tanki'(单钓将)
        - 双听（2张）：'ryanmen'(两面听)、'shanpon'(双碰听)、'shuangtiao'(双钓将)
        - 多面听（3张及以上）：'sanmen'(三面听)、'duomin'(多面听)
        - 特殊听牌：'jiulian'(九莲宝灯)、'shisanyao'(十三幺)
        """
        waiting_count = len(final_ukeire)
        total_waiting_tiles = sum(final_ukeire.values())

        # 检查特殊牌型
        special_pattern = TileEfficiencyAnalyzer._check_special_tenpai_patterns(tiles, final_ukeire)
        if special_pattern:
            return special_pattern

        # 根据进张数量分类
        if waiting_count == 1:
            # 单听（1张）
            return TileEfficiencyAnalyzer._classify_single_wait(tiles, final_ukeire)
        elif waiting_count == 2:
            # 双听（2张）
            return TileEfficiencyAnalyzer._classify_double_wait(tiles, final_ukeire)
        elif waiting_count == 3:
            # 三面听
            return 'sanmen'
        elif waiting_count >= 4:
            # 多面听
            return 'duomin'
        else:
            # 异常情况
            return 'unknown'

    @staticmethod
    def _check_special_tenpai_patterns(
        tiles: List[Tile], 
        final_ukeire: Dict[Tuple[TileType, Union[int, FengType, JianType]], int]
    ) -> Optional[str]:
        """检查特殊听牌形态：九莲宝灯、十三幺等"""
        tile_counts = ShantenCalculator._count_tiles(tiles)

        # 检查十三幺听牌
        # TODO: 跟向听国士无双（十三幺）的代码有重复
        if TileEfficiencyAnalyzer._is_kokushi_tenpai(tiles, final_ukeire):
            return 'kokushi'

        # 检查九莲宝灯听牌
        if TileEfficiencyAnalyzer._is_jiulian_tenpai(tiles, final_ukeire):
            return 'jiulian'

        return None

    @staticmethod
    def _is_kokushi_tenpai(
        tiles: List[Tile], 
        final_ukeire: Dict[Tuple[TileType, Union[int, FengType, JianType]], int]
    ) -> bool:
        """判断是否为十三幺听牌"""
        # 十三幺的13种特定牌
        kokushi_keys = {
            (TileType.WAN, 1), (TileType.WAN, 9),
            (TileType.TONG, 1), (TileType.TONG, 9),
            (TileType.TIAO, 1), (TileType.TIAO, 9),
            (TileType.FENG, FengType.DONG), (TileType.FENG, FengType.NAN),
            (TileType.FENG, FengType.XI), (TileType.FENG, FengType.BEI),
            (TileType.JIAN, JianType.ZHONG), (TileType.JIAN, JianType.FA),
            (TileType.JIAN, JianType.BAI)
        }

        tile_counts = ShantenCalculator._count_tiles(tiles)

        # 检查是否只包含十三幺牌型
        for tile_key in tile_counts.keys():
            if tile_key not in kokushi_keys:
                return False

        # 检查是否有12种不同的牌，其中一种是对子
        unique_types = len(tile_counts)
        pair_count = sum(1 for count in tile_counts.values() if count == 2)

        return unique_types == 13 and pair_count == 0

    @staticmethod
    def _is_jiulian_tenpai(
        tiles: List[Tile], 
        final_ukeire: Dict[Tuple[TileType, Union[int, FengType, JianType]], int]
    ) -> bool:
        """判断是否为九莲宝灯听牌"""
        # 九莲宝灯必须是清一色
        tile_types = set(tile.tile_type for tile in tiles if tile.is_number_tile())
        if len(tile_types) != 1:
            return False

        suit = list(tile_types)[0]
        tile_counts = ShantenCalculator._count_tiles(tiles)

        # 构建该花色的牌数分布
        suit_distribution = [0] * 9
        for (tile_type, value), count in tile_counts.items():
            if tile_type == suit and 1 <= value <= 9:
                suit_distribution[value - 1] = count

        # 九莲宝灯的基本形态：1112345678999
        expected = [3, 1, 1, 1, 1, 1, 1, 1, 3]

        # 检查是否符合九莲基本形态（允许一张牌的差异）
        differences = 0
        for i in range(9):
            if suit_distribution[i] != expected[i]:
                differences += abs(suit_distribution[i] - expected[i])

        # 如果只有一张牌的差异，可能是九莲听牌
        return differences <= 2 and len(final_ukeire) >= 8

    @staticmethod
    def _classify_single_wait(
        tiles: List[Tile], 
        final_ukeire: Dict[Tuple[TileType, Union[int, FengType, JianType]], int]
    ) -> str:
        """分类单听形态"""
        waiting_tile_key = list(final_ukeire.keys())[0]
        tile_type, value = waiting_tile_key

        # 如果等待的是字牌，通常是单钓将
        if tile_type in [TileType.FENG, TileType.JIAN]:
            return 'tanki'

        # 分析数字牌的听牌类型
        tile_counts = ShantenCalculator._count_tiles(tiles)

        # 检查是否为边张听 1, 2 -> 3; 8, 9 -> 7
        if value in [3, 7]:
            return 'penchan'

        # 检查是否为嵌张听
        if 2 <= value <= 8:
            # 检查是否有两边的搭子
            left_exists = tile_counts.get((tile_type, value - 1), 0) > 0
            right_exists = tile_counts.get((tile_type, value + 1), 0) > 0
            if left_exists and right_exists:
                return 'kanchan'

        # 默认为单钓将
        return 'tanki'

    @staticmethod
    def _classify_double_wait(
        tiles: List[Tile], 
        final_ukeire: Dict[Tuple[TileType, Union[int, FengType, JianType]], int]
    ) -> str:
        """分类双听形态"""
        waiting_keys = list(final_ukeire.keys())

        # 如果其中有一个字牌，可能是双碰听（未验证）
        if any(key[0] in [TileType.FENG, TileType.JIAN] for key in waiting_keys):
            return 'shanpon'

        tile_counts = ShantenCalculator._count_tiles(tiles)

        # 如果都是同一花色的数字牌
        if len(set(key[0] for key in waiting_keys)) == 1 and waiting_keys[0][0] in [TileType.WAN, TileType.TONG, TileType.TIAO]:
            tile_type = waiting_keys[0][0]
            values = [key[1] for key in waiting_keys]
            values.sort()

            # 检查是否为两面听（相邻的两张牌）
            if len(values) == 2:
                if values[1] - values[0] == 3:
                    # 如听36，可能是两面听 (45->36)，也可能是双钓将(3456->3,6)
                    # 下列算法并未十分准确，但可以大致判断（未验证）
                    if (
                        tile_counts.get((tile_type, values[0]), 0) >= 1
                        and tile_counts.get((tile_type, values[1]), 0) >= 1
                    ):
                        return 'shuangtiao'
                    else:
                        return 'ryanmen'
                else:
                    # 检查是否为双碰听（两对等任一对成刻）（未验证）
                    if (
                        tile_counts.get((tile_type, values[0]), 0) >= 2
                        and tile_counts.get((tile_type, values[1]), 0) >= 2
                    ):
                        return 'shanpon'

        # 默认分类
        return 'ryanmen'

    @staticmethod
    def _is_single_tile(tiles: List[Tile]) -> bool:
        """
        判断手牌是否有单张
        """
        tile_counts = ShantenCalculator._count_tiles(tiles)
        for tile_type, value in tile_counts.items():
            if value == 1:
                return True
        return False

    @staticmethod
    def _has_2_pairs(tiles: List[Tile]) -> bool:
        """
        判断手牌是否有2对
        """
        tile_counts = ShantenCalculator._count_tiles(tiles)
        pair_count = 0
        for tile_type, value in tile_counts.items():
            if value == 2:
                pair_count += 1
        return pair_count == 2

    @staticmethod
    def _is_dangerous_tile(tile: Tile) -> bool:
        """
        基于麻将防守理论的危险牌判断
        
        危险度评估规则：
        1. 中张牌（3-7）相对危险，特别是456
        2. 生张（字牌）相对危险
        3. 边张（19）相对安全
        4. 字牌中，三元牌比四风牌更危险
        """
        # 数字牌的危险度判断
        if tile.is_number_tile():
            # 中张牌（3-7）比较危险，456最危险
            if 4 <= tile.value <= 6:
                return True  # 最危险的中张牌
            elif 3 <= tile.value <= 7:
                return True  # 次危险的中张牌
            else:
                return False  # 边张（1,2,8,9）相对安全

        # 字牌的危险度判断
        elif tile.is_honor_tile():
            # 箭牌（三元牌）比风牌更危险
            if tile.tile_type == TileType.JIAN:
                return True  # 中发白相对危险
            else:
                # 风牌相对安全，但仍有一定危险
                return False

        return False

    @staticmethod
    def evaluate_tile_danger_level(
        tile: Tile, 
        discard_pool: List[Tuple[Tile, str]] = None,
        all_visible_tiles: List[Tile] = None,
        round_number: int = 1
    ) -> float:
        """
        高级危险牌评估 - 基于完整防守理论
        
        Args:
            tile: 要评估的牌
            discard_pool: 出牌池 [(牌, 玩家名)]
            all_visible_tiles: 所有可见的牌（包括副露）
            round_number: 当前轮数
            
        Returns:
            危险度评分 (0.0-1.0, 越高越危险)
        """
        if discard_pool is None:
            discard_pool = []
        if all_visible_tiles is None:
            all_visible_tiles = []

        danger_score = 0.0

        # 1. 现物/生张理论 - 现物安全 生张危险
        for discarded_tile, _ in discard_pool:
            if (tile.tile_type == discarded_tile.tile_type and 
                tile.value == discarded_tile.value and
                tile.feng_type == discarded_tile.feng_type and
                tile.jian_type == discarded_tile.jian_type):
                appears_in_discard = True
                return 0.0  # 现物绝对安全

        # 2. 基础危险度
        if tile.is_number_tile():
            # 中张牌基础危险度
            if 4 <= tile.value <= 6:
                danger_score += 0.7  # 456最危险
            elif 3 <= tile.value <= 7:
                danger_score += 0.5  # 37次危险
            elif tile.value in [2, 8]:
                danger_score += 0.3  # 28有一定危险
            else:  # 1, 9
                danger_score += 0.1  # 边张相对安全
        elif tile.tile_type == TileType.JIAN:
            danger_score += 0.6  # 三元牌较危险
        else:  # 风牌
            danger_score += 0.3  # 风牌中等危险

        # 3. 筋牌理论 (Suji) - 降低危险度
        if tile.is_number_tile():
            # 检查是否有对应的筋牌被打出
            suji_pairs = {
                1: [4, 7], 2: [5, 8], 3: [6, 9],
                4: [1, 7], 5: [2, 8], 6: [3, 9],
                7: [1, 4], 8: [2, 5], 9: [3, 6]
            }

            for discarded_tile, _ in discard_pool[-10:]:  # 检查最近10张牌
                if (
                    discarded_tile.is_number_tile()
                    and discarded_tile.tile_type == tile.tile_type
                    and discarded_tile.value in suji_pairs.get(tile.value, [])
                ):
                    danger_score *= 0.7  # 筋牌减少危险度
                    break

        # 4. 壁理论 (Kabe) - 显著降低危险度
        if tile.is_number_tile():
            # 统计同类型同数值的牌已出现次数
            same_tile_count = 0
            for visible_tile in all_visible_tiles:
                if (
                    visible_tile.is_number_tile()
                    and visible_tile.tile_type == tile.tile_type
                    and visible_tile.value == tile.value
                ):
                    same_tile_count += 1

            # 如果4张都可见，形成壁
            if same_tile_count >= 4:
                # 检查邻近牌(外壁)的危险度
                adjacent_values = []
                if tile.value > 1:
                    adjacent_values.append(tile.value - 1)
                if tile.value < 9:
                    adjacent_values.append(tile.value + 1)

                # 壁的外侧牌危险度大幅降低
                if tile.value in adjacent_values:
                    danger_score *= 0.3
            elif same_tile_count >= 3:
                danger_score *= 0.8  # 3张可见也会降低危险度

        # 5. 早巡舍牌理论 - 降低危险度
        if round_number <= 5:  # 前5巡
            # 检查是否为早巡出现的牌类型
            early_discards = [tile for tile, _ in discard_pool[:5]]  # 前5张舍牌
            for early_tile in early_discards:
                if (
                    tile.is_number_tile()
                    and tile.tile_type == early_tile.tile_type
                    and abs(tile.value - early_tile.value) <= 2
                ):  # 相近的牌
                    danger_score *= 0.6  # 早巡相关牌较安全
                    break

        # 6. 生张额外危险度
        if not appears_in_discard:
            danger_score += 0.2

        # 限制在0.0-1.0范围内
        return min(1.0, max(0.0, danger_score))

class ShantenAI(BaseAI):
    """基于向听数和牌效率的高级AI"""
    
    def __init__(self, difficulty: str = "hard"):
        super().__init__(difficulty)
        self.name = f"ShantenAI-{difficulty}"
        
        # 根据难度调整参数
        if difficulty == "easy":
            self.calculation_accuracy = 0.7  # 70%准确率
            self.randomness = 0.3
        elif difficulty == "medium":  
            self.calculation_accuracy = 0.85  # 85%准确率
            self.randomness = 0.15
        else:  # hard
            self.calculation_accuracy = 0.95  # 95%准确率
            self.randomness = 0.05
    
    def choose_discard(self, player: Player, available_tiles: List[Tile]) -> Tile:
        """选择要打出的牌 - 基于牌效率分析"""
        if not available_tiles:
            return player.hand_tiles[0] if player.hand_tiles else None
        
        # 使用牌效率分析器
        efficiency_scores = TileEfficiencyAnalyzer.analyze_discard_efficiency(
            player, available_tiles
        )
        
        # 按效率排序
        sorted_tiles = sorted(efficiency_scores.items(), key=lambda x: x[1][0], reverse=True)

        # 调试用
        print("打牌效率分析 (分数越高越应该打出):")
        for i, (tile, (score, ukeire)) in enumerate(sorted_tiles[:3]):
            print(f"   {i+1}. {tile}: {score:.2f}分, {sum(ukeire.values())}张进张")
        print()
        
        # 根据难度和准确率选择
        if random.random() < self.calculation_accuracy:
            # 选择最优解
            chosen_tile = sorted_tiles[0][0]
            print(f"最优选择出的牌: {chosen_tile}")
            return chosen_tile
        else:
            # 添加一些随机性
            top_choices = sorted_tiles[:min(3, len(sorted_tiles))]
            chosen_entry = random.choice(top_choices)
            chosen_tile = chosen_entry[0]
            print(f"随机选择出的牌: {chosen_tile}")
            return chosen_tile
        
        
    
    def decide_action(self, player: Player, available_actions: List[GameAction], 
                     context: Dict) -> Optional[GameAction]:
        """决定要执行的动作 - 基于向听数分析"""
        # 胡牌优先级最高
        if GameAction.WIN in available_actions:
            return GameAction.WIN
        
        current_shanten = ShantenCalculator.calculate_shanten(player.hand_tiles, len(player.melds))
        
        # 分析各种动作的效果
        action_values = {}
        
        for action in available_actions:
            if action == GameAction.PASS:
                action_values[action] = 0.0
                continue
            
            # 模拟执行动作后的效果
            value = self._evaluate_action_effect(player, action, context, current_shanten)
            action_values[action] = value
        
        # 选择最优动作
        if not action_values:
            return GameAction.PASS
        
        best_action = max(action_values.items(), key=lambda x: x[1])
        
        # 根据难度调整决策
        if best_action[1] > 10.0:  # 明显有利的动作
            return best_action[0]
        elif random.random() < self.calculation_accuracy:
            return best_action[0]
        else:
            return GameAction.PASS
    
    def _evaluate_action_effect(self, player: Player, action: GameAction, 
                              context: Dict, current_shanten: int) -> float:
        """评估动作效果"""
        value = 0.0
        
        if action == GameAction.PENG:
            # TODO - 如果碰牌减少向听数，则无奖励或者减分
            value += 20.0
        elif action == GameAction.GANG:
            # 杠牌获得额外摸牌机会，在川麻里还有能获得一番
            value += 50.0
            # 但有一定风险
            if current_shanten <= 1:
                value -= 20.0  # 1向听牌时杠牌有风险
        elif action == GameAction.CHI:
            # 四川麻将不能吃牌
            value = -100.0
        
        return value
    
    def choose_missing_suit(self, player: Player) -> str:
        """选择缺门 - 基于向听数最小化"""
        suit_counts = {"万": 0, "筒": 0, "条": 0}
        suit_tiles = {"万": [], "筒": [], "条": []}
        
        for tile in player.hand_tiles:
            if tile.is_number_tile():
                suit_name = tile.tile_type.value
                suit_counts[suit_name] += 1
                suit_tiles[suit_name].append(tile)
        
        # 计算缺每种花色后的向听数
        best_suit = None
        best_shanten = float('inf')
        
        for suit_name in ["万", "筒", "条"]:
            # 模拟缺这种花色
            remaining_tiles = [t for t in player.hand_tiles 
                             if not (t.is_number_tile() and t.tile_type.value == suit_name)]
            
            shanten = ShantenCalculator.calculate_shanten(remaining_tiles)
            
            if shanten < best_shanten:
                best_shanten = shanten
                best_suit = suit_name
        
        return best_suit or min(suit_counts, key=suit_counts.get)
    
    def choose_exchange_tiles(self, player: Player, count: int = 3) -> List[Tile]:
        """选择换牌 - 基于牌效率优化"""
        if count > len(player.hand_tiles):
            return player.hand_tiles[:count]
        # TODO - 应该考虑该花色所有三张组合，并计算去掉这三张后的牌效率，选择效率最高的组合
        
        # 计算每张牌的保留价值
        tile_values = {}
        for tile in player.hand_tiles:
            # 移除这张牌后计算向听数
            remaining_tiles = [t for t in player.hand_tiles if t != tile]
            shanten_without = ShantenCalculator.calculate_shanten(remaining_tiles)
            
            # 保留价值 = 原向听数 - 移除后向听数（越大越应该保留）
            current_shanten = ShantenCalculator.calculate_shanten(player.hand_tiles)
            value = current_shanten - shanten_without
            tile_values[tile] = value
        
        # 选择价值最低的牌换出
        sorted_tiles = sorted(tile_values.items(), key=lambda x: x[1])
        return [tile for tile, _ in sorted_tiles[:count]]
    
    def provide_analysis(self, player: Player) -> str:
        """提供向听数分析"""
        shanten = ShantenCalculator.calculate_shanten(player.hand_tiles, len(player.melds))
        ukeire = UkeireCalculator.calculate_ukeire(
            player.hand_tiles, len(player.melds), 
            getattr(player, 'missing_suit', None)
        )
        total_ukeire = sum(ukeire.values())
        
        analysis = []
        analysis.append(f"🎯 向听数分析:")
        analysis.append(f"   当前向听数: {shanten}向听")
        analysis.append(f"   有效进张: {total_ukeire}张")
        
        if shanten == 0:
            analysis.append("   🎉 已听牌！")
        elif shanten == 1:
            analysis.append("   ⚡ 一向听，接近胡牌")
        elif shanten <= 3:
            analysis.append("   📈 进展良好")
        else:
            analysis.append("   🔧 需要整理手牌")
        
        return "\n".join(analysis)
    
    def provide_defense_analysis(self, player: Player, candidate_tiles: List[Tile], 
                               game_context: Dict = None) -> str:
        """
        提供防守分析 - 基于麻将防守理论
        
        Args:
            player: 玩家对象
            candidate_tiles: 候选出牌
            game_context: 游戏上下文信息
        """
        if not candidate_tiles:
            return "❌ 无可出牌"
        
        if not game_context:
            game_context = {}
        
        analysis = []
        analysis.append("🛡️ 防守分析:")
        analysis.append("   (基于筋牌、壁、现物、早巡理论)")
        analysis.append("")
        
        # 分析每张候选牌的危险度
        danger_scores = {}
        for tile in candidate_tiles:
            danger_level = TileEfficiencyAnalyzer.evaluate_tile_danger_level(
                tile,
                game_context.get('discard_pool', []),
                game_context.get('all_visible_tiles', []),
                game_context.get('round_number', 1)
            )
            danger_scores[tile] = danger_level
        
        # 按危险度排序
        sorted_tiles = sorted(danger_scores.items(), key=lambda x: x[1])
        
        # 显示分析结果
        for i, (tile, danger_level) in enumerate(sorted_tiles[:5]):  # 显示前5张
            safety_level = "🟢安全" if danger_level < 0.3 else "🟡注意" if danger_level < 0.6 else "🔴危险"
            percentage = int(danger_level * 100)
            
            # 分析具体原因
            reasons = self._analyze_danger_reasons(tile, game_context)
            reason_text = f" ({reasons})" if reasons else ""
            
            analysis.append(f"   {i+1}. {tile} - {safety_level} ({percentage}%){reason_text}")
        
        # 推荐出牌
        if sorted_tiles:
            safest_tile = sorted_tiles[0][0]
            analysis.append("")
            analysis.append(f"💡 推荐: 优先考虑 {safest_tile} (最安全)")
        
        return "\n".join(analysis)
    
    def _analyze_danger_reasons(self, tile: Tile, game_context: Dict) -> str:
        """分析危险牌的具体原因"""
        reasons = []
        discard_pool = game_context.get('discard_pool', [])
        all_visible_tiles = game_context.get('all_visible_tiles', [])
        round_number = game_context.get('round_number', 1)

        # TODO - 与牌效率的某些方法/代码重合，需要合并
        
        # 检查是否为现物
        for discarded_tile, _ in discard_pool:
            if (tile.tile_type == discarded_tile.tile_type and 
                tile.value == discarded_tile.value and
                tile.feng_type == discarded_tile.feng_type and
                tile.jian_type == discarded_tile.jian_type):
                reasons.append("现物")
                return "现物-绝对安全"
        
        # 检查筋牌
        if tile.is_number_tile():
            suji_pairs = {
                1: [4, 7], 2: [5, 8], 3: [6, 9],
                4: [1, 7], 5: [2, 8], 6: [3, 9],
                7: [1, 4], 8: [2, 5], 9: [3, 6]
            }
            
            for discarded_tile, _ in discard_pool[-10:]:
                if (discarded_tile.tile_type == tile.tile_type and 
                    discarded_tile.value in suji_pairs.get(tile.value, [])):
                    reasons.append("筋牌")
                    break
        
        # 检查壁
        if tile.is_number_tile():
            same_tile_count = sum(1 for visible_tile in all_visible_tiles
                                if visible_tile.tile_type == tile.tile_type and 
                                   visible_tile.value == tile.value)
            if same_tile_count >= 4:
                reasons.append("壁")
            elif same_tile_count >= 3:
                reasons.append("准壁")
        
        # 检查早巡
        if round_number <= 5:
            early_discards = [tile for tile, _ in discard_pool[:5]]
            for early_tile in early_discards:
                if (tile.tile_type == early_tile.tile_type and 
                    abs(tile.value - early_tile.value) <= 2):
                    reasons.append("早巡")
                    break
        
        # 基础危险度
        if tile.is_number_tile():
            if 4 <= tile.value <= 6:
                reasons.append("中张")
            elif tile.value in [1, 9]:
                reasons.append("边张")
        elif tile.tile_type == TileType.JIAN:
            reasons.append("三元牌")
        
        # 生张检查
        if tile.is_honor_tile():
            appears_in_discard = any(
                discarded_tile.tile_type == tile.tile_type and
                ((tile.feng_type and discarded_tile.feng_type == tile.feng_type) or
                 (tile.jian_type and discarded_tile.jian_type == tile.jian_type))
                for discarded_tile, _ in discard_pool
            )
            if not appears_in_discard:
                reasons.append("生张")
        
        return ",".join(reasons) if reasons else "普通" 
