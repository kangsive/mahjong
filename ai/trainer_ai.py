# -*- coding: utf-8 -*-
"""
训练师AI - 提供指导和建议
"""

from typing import List, Optional, Dict, Tuple
import random

from .base_ai import BaseAI
from game.tile import Tile, TileType
from game.player import Player
from game.game_engine import GameAction

class TrainerAI(BaseAI):
    """训练师AI - 专门用于训练模式，提供指导"""
    
    def __init__(self):
        super().__init__("trainer")
        self.advice_history: List[str] = []
        self.teaching_points: List[str] = []
        
    def choose_discard(self, player: Player, available_tiles: List[Tile]) -> Tile:
        """选择要打出的牌"""
        # 训练师AI相对保守，注重教学
        priorities = []
        
        for tile in available_tiles:
            priority = self.calculate_discard_priority(player, tile)
            priorities.append((tile, priority))
        
        # 按优先级排序
        priorities.sort(key=lambda x: x[1], reverse=True)
        
        return priorities[0][0]
    
    def decide_action(self, player: Player, available_actions: List[GameAction], 
                     context: Dict) -> Optional[GameAction]:
        """决定要执行的动作"""
        # 训练师AI会考虑教学价值
        if GameAction.WIN in available_actions:
            return GameAction.WIN
        
        if GameAction.GANG in available_actions:
            # 杠牌有风险，但分数高
            if random.random() < 0.7:
                return GameAction.GANG
        
        if GameAction.PENG in available_actions:
            # 碰牌相对安全
            if random.random() < 0.8:
                return GameAction.PENG
        
        if GameAction.CHI in available_actions:
            # 吃牌要谨慎
            if random.random() < 0.6:
                return GameAction.CHI
        
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
    
    def provide_exchange_advice(self, player: Player) -> str:
        """提供换三张的专业建议"""
        advice = []
        advice.append("🔄 换三张策略分析：")
        
        # 按花色分组统计
        suits = {}
        for tile in player.hand_tiles:
            if tile.tile_type not in suits:
                suits[tile.tile_type] = []
            suits[tile.tile_type].append(tile)
        
        # 分析各花色情况
        suit_analysis = {}
        for suit_type, tiles in suits.items():
            if suit_type in [TileType.WAN, TileType.TONG, TileType.TIAO]:
                analysis = self._analyze_suit_for_exchange(tiles)
                suit_analysis[suit_type.value] = {
                    'tiles': tiles,
                    'count': len(tiles),
                    'analysis': analysis
                }
        
        # 显示各花色分析
        for suit_name, data in suit_analysis.items():
            advice.append(f"\n📊 {suit_name}牌分析 ({data['count']}张):")
            advice.append(f"   牌型: {[str(t) for t in data['tiles']]}")
            advice.append(f"   评估: {data['analysis']['description']}")
            advice.append(f"   建议: {data['analysis']['recommendation']}")
        
        # 给出最终建议
        best_exchange = self._recommend_best_exchange(suit_analysis)
        advice.append(f"\n🎯 最佳换牌建议:")
        advice.append(f"   推荐换出: {best_exchange['suit']}牌")
        advice.append(f"   具体牌张: {[str(t) for t in best_exchange['tiles']]}")
        advice.append(f"   理由: {best_exchange['reason']}")
        
        return "\n".join(advice)
    
    def _analyze_suit_for_exchange(self, tiles: List[Tile]) -> Dict:
        """分析单个花色的换牌价值"""
        if not tiles:
            return {"description": "无此花色", "recommendation": "无法换出（无牌）", "priority": -1000}
        
        count = len(tiles)
        
        # 如果不够三张牌，直接返回无法换出
        if count < 3:
            return {
                "description": f"数量不足（仅{count}张）",
                "recommendation": "无法换出（不够三张）",
                "priority": -1000,  # 设置极低优先级
                "pairs": 0,
                "sequences": 0,
                "isolated": count
            }
        
        values = sorted([t.value for t in tiles])
        
        # 分析牌型特征
        pairs = self._count_pairs_in_suit(values)
        sequences = self._count_potential_sequences_in_suit(values)
        isolated = self._count_isolated_tiles(values)
        
        description_parts = []
        priority = 0
        
        if pairs > 0:
            description_parts.append(f"{pairs}个对子")
            priority -= pairs * 20  # 对子价值高，不建议换出
        
        if sequences > 0:
            description_parts.append(f"{sequences}个潜在顺子")
            priority -= sequences * 15  # 顺子价值中等
        
        if isolated > 0:
            description_parts.append(f"{isolated}张孤张")
            priority += isolated * 10  # 孤张适合换出
        
        # 数量因素
        if count >= 6:
            description_parts.append("数量过多")
            priority += 15
        elif count <= 4:
            description_parts.append("数量适中")
        
        description = "、".join(description_parts) if description_parts else "普通牌型"
        
        # 生成建议（只对够三张牌的花色给建议）
        if priority > 20:
            recommendation = "强烈建议换出"
        elif priority > 0:
            recommendation = "可以考虑换出"
        elif priority > -10:
            recommendation = "中性选择"
        else:
            recommendation = "不建议换出"
        
        return {
            "description": description,
            "recommendation": recommendation,
            "priority": priority,
            "pairs": pairs,
            "sequences": sequences,
            "isolated": isolated
        }
    
    def _count_pairs_in_suit(self, values: List[int]) -> int:
        """统计对子数量"""
        pairs = 0
        i = 0
        while i < len(values) - 1:
            if values[i] == values[i + 1]:
                pairs += 1
                i += 2  # 跳过这一对
            else:
                i += 1
        return pairs
    
    def _count_potential_sequences_in_suit(self, values: List[int]) -> int:
        """统计潜在顺子数量（用于换牌分析）"""
        unique_values = list(set(values))
        unique_values.sort()
        
        sequences = 0
        i = 0
        while i < len(unique_values) - 2:
            if (unique_values[i + 1] == unique_values[i] + 1 and 
                unique_values[i + 2] == unique_values[i] + 2):
                sequences += 1
                i += 3
            else:
                i += 1
        return sequences
    
    def _count_isolated_tiles(self, values: List[int]) -> int:
        """统计孤张数量"""
        isolated = 0
        for value in set(values):
            # 检查是否为孤张（前后都没有相邻的牌）
            has_neighbor = False
            for other_value in values:
                if other_value != value and abs(other_value - value) <= 1:
                    has_neighbor = True
                    break
            if not has_neighbor:
                isolated += values.count(value)
        return isolated
    
    def _recommend_best_exchange(self, suit_analysis: Dict) -> Dict:
        """推荐最佳换牌方案"""
        if not suit_analysis:
            return {"suit": "无", "tiles": [], "reason": "无可换牌"}
        
        # 过滤出有足够三张牌的花色
        valid_suits = {k: v for k, v in suit_analysis.items() if v['count'] >= 3}
        
        if not valid_suits:
            # 如果没有任何花色有三张牌，返回错误信息
            return {"suit": "无", "tiles": [], "reason": "没有花色有足够的三张牌进行交换"}
        
        # 按优先级排序
        sorted_suits = sorted(valid_suits.items(), 
                            key=lambda x: x[1]['analysis']['priority'], 
                            reverse=True)
        
        best_suit_name, best_data = sorted_suits[0]
        
        # 智能选择最优的三张牌进行交换，并获取详细理由
        selected_tiles, tile_reasons = self._select_optimal_exchange_tiles_with_reasons(best_data['tiles'])
        
        # 组合花色选择理由
        suit_reasons = []
        analysis = best_data['analysis']
        
        if analysis['isolated'] > 0:
            suit_reasons.append(f"有{analysis['isolated']}张孤张牌")
        if best_data['count'] >= 6:
            suit_reasons.append("该花色牌张过多")
        if analysis['pairs'] == 0 and analysis['sequences'] == 0:
            suit_reasons.append("缺乏有效组合")
        
        suit_reason = "、".join(suit_reasons) if suit_reasons else "综合考虑最优选择"
        
        # 组合完整理由（花色理由 + 具体选牌理由）
        full_reason = f"{suit_reason}；具体选牌：{tile_reasons}"
        
        return {
            "suit": best_suit_name,
            "tiles": selected_tiles,
            "reason": full_reason
        }
    
    def _select_optimal_exchange_tiles(self, tiles: List[Tile]) -> List[Tile]:
        """
        智能选择最优的三张牌进行交换
        
        算法策略：
        1. 优先选择孤张牌（无法组成顺子或刻子的牌）
        2. 其次选择边张牌（1,9）
        3. 避免拆散已有的对子
        4. 避免拆散潜在的顺子组合
        5. 如果必须拆散组合，优先保留价值更高的组合
        
        Args:
            tiles: 该花色的所有牌
            
        Returns:
            选中的三张牌列表
        """
        selected_tiles, _ = self._select_optimal_exchange_tiles_with_reasons(tiles)
        return selected_tiles
    
    def _select_optimal_exchange_tiles_with_reasons(self, tiles: List[Tile]) -> tuple[List[Tile], str]:
        """
        智能选择最优的三张牌进行交换，并返回详细理由
        
        Args:
            tiles: 该花色的所有牌
            
        Returns:
            (选中的三张牌列表, 选择理由)
        """
        if len(tiles) <= 3:
            return tiles[:3], "该花色牌数不足，全部换出"
        
        # 按牌值排序，便于分析
        sorted_tiles = sorted(tiles, key=lambda t: t.value)
        
        # 计算每张牌的交换价值（价值越高越适合交换出去）
        tile_values = []
        for tile in sorted_tiles:
            value = self._calculate_tile_exchange_value(tile, sorted_tiles)
            tile_values.append((tile, value))
        
        # 按交换价值排序（价值高的优先交换）
        tile_values.sort(key=lambda x: x[1], reverse=True)
        
        # 选择前三张价值最高的牌
        selected = [tile for tile, _ in tile_values[:3]]
        selected_values = [value for _, value in tile_values[:3]]
        
        # 生成选择理由
        reasons = []
        for i, (tile, value) in enumerate(zip(selected, selected_values)):
            tile_reason = self._explain_tile_selection_reason(tile, value, sorted_tiles)
            reasons.append(f"{str(tile)}({tile_reason})")
        
        reason_text = "、".join(reasons)
        
        return selected, reason_text
    
    def _explain_tile_selection_reason(self, tile: Tile, exchange_value: float, all_tiles: List[Tile]) -> str:
        """
        解释单张牌被选择的理由
        
        Args:
            tile: 被选择的牌
            exchange_value: 该牌的交换价值分数
            all_tiles: 该花色所有牌
            
        Returns:
            选择理由的文字描述
        """
        tile_value = tile.value
        
        # 统计相同牌的数量
        same_count = sum(1 for t in all_tiles if t.value == tile_value)
        
        # 统计相邻牌的数量
        adjacent_count = sum(1 for t in all_tiles 
                           if abs(t.value - tile_value) == 1)
        
        reasons = []
        
        # 根据交换价值分数的组成来解释
        if same_count == 1 and adjacent_count == 0:
            reasons.append("孤张")
        
        if tile_value in [1, 9]:
            reasons.append("边张")
        
        if same_count >= 3:
            reasons.append("多余")
        elif same_count == 2:
            reasons.append("破坏对子")
        
        # 检查顺子潜力
        can_form_sequence = self._can_form_sequence_with_tile(tile, all_tiles)
        if can_form_sequence:
            reasons.append("破坏顺子")
        
        if tile_value in [4, 5, 6]:
            reasons.append("中张")
        
        # 字牌特殊处理
        if tile.is_honor_tile():
            if same_count == 1:
                reasons.append("单张字牌")
            elif same_count == 2:
                reasons.append("破坏字牌对子")
        
        # 如果没有特殊理由，根据分数给出通用理由
        if not reasons:
            if exchange_value > 0:
                reasons.append("适合换出")
            else:
                reasons.append("保留价值低")
        
        return "、".join(reasons)
    
    def _can_form_sequence_with_tile(self, tile: Tile, all_tiles: List[Tile]) -> bool:
        """
        检查该牌是否能与其他牌组成顺子
        
        Args:
            tile: 目标牌
            all_tiles: 该花色所有牌
            
        Returns:
            是否能组成顺子
        """
        if tile.is_honor_tile():
            return False
        
        tile_value = tile.value
        
        # 检查是否能组成顺子
        for offset in [-2, -1, 1, 2]:
            if 1 <= tile_value + offset <= 9:
                # 检查是否有足够的牌组成顺子
                needed_values = []
                if offset == -2:  # 检查 target-2, target-1, target
                    needed_values = [tile_value-2, tile_value-1]
                elif offset == -1:  # 检查 target-1, target, target+1
                    needed_values = [tile_value-1, tile_value+1]
                elif offset == 1:   # 检查 target, target+1, target+2
                    needed_values = [tile_value+1, tile_value+2]
                elif offset == 2:   # 检查 target-1, target, target+1
                    needed_values = [tile_value-1, tile_value+1]
                
                if all(1 <= v <= 9 and 
                      any(t.value == v for t in all_tiles) 
                      for v in needed_values):
                    return True
        
        return False
    
    def _calculate_tile_exchange_value(self, target_tile: Tile, all_tiles: List[Tile]) -> float:
        """
        计算单张牌的交换价值
        
        算法依据：
        1. 孤张牌价值最高（+50分）
        2. 边张牌（1,9）价值较高（+30分）
        3. 多余的牌（超过2张相同）价值较高（+20分）
        4. 破坏对子的牌价值很低（-40分）
        5. 破坏顺子的牌价值较低（-25分）
        6. 中张牌（4,5,6）价值较低（-10分，因为容易组成顺子）
        
        Args:
            target_tile: 目标牌
            all_tiles: 该花色所有牌
            
        Returns:
            交换价值分数，越高越适合交换
        """
        value = 0.0
        tile_value = target_tile.value
        
        # 统计相同牌的数量
        same_count = sum(1 for t in all_tiles if t.value == tile_value)
        
        # 统计相邻牌的数量
        adjacent_count = sum(1 for t in all_tiles 
                           if abs(t.value - tile_value) == 1)
        
        # 1. 孤张牌判断（前后都没有相邻牌，且只有一张）
        if same_count == 1 and adjacent_count == 0:
            value += 50  # 孤张牌最适合交换
        
        # 2. 边张牌（1,9）
        if tile_value in [1, 9]:
            value += 30  # 边张牌组成顺子机会少
        
        # 3. 多余的牌（超过2张相同）
        if same_count >= 3:
            value += 20  # 多余的牌可以交换
        elif same_count == 2:
            value -= 40  # 对子很宝贵，不要轻易拆散
        
        # 4. 顺子潜力分析
        # 检查是否能组成顺子
        can_form_sequence = False
        for offset in [-2, -1, 1, 2]:
            if 1 <= tile_value + offset <= 9:
                # 检查是否有足够的牌组成顺子
                needed_values = []
                if offset == -2:  # 检查 target-2, target-1, target
                    needed_values = [tile_value-2, tile_value-1]
                elif offset == -1:  # 检查 target-1, target, target+1
                    needed_values = [tile_value-1, tile_value+1]
                elif offset == 1:   # 检查 target, target+1, target+2
                    needed_values = [tile_value+1, tile_value+2]
                elif offset == 2:   # 检查 target-1, target, target+1
                    needed_values = [tile_value-1, tile_value+1]
                
                if all(1 <= v <= 9 and 
                      any(t.value == v for t in all_tiles) 
                      for v in needed_values):
                    can_form_sequence = True
                    break
        
        if can_form_sequence:
            value -= 25  # 能组成顺子的牌价值较低
        
        # 5. 中张牌（4,5,6）容易组成顺子
        if tile_value in [4, 5, 6]:
            value -= 10
        
        # 6. 字牌特殊处理（如果是字牌）
        if target_tile.is_honor_tile():
            if same_count == 1:
                value += 40  # 单张字牌很适合交换
            elif same_count == 2:
                value -= 30  # 字牌对子也很宝贵
        
        return value
    
    def provide_missing_suit_advice(self, player: Player) -> str:
        """提供选择缺门的专业建议"""
        advice = []
        advice.append("🎲 选择缺门策略分析：")
        
        # 统计各花色情况
        suit_counts = {"万": 0, "筒": 0, "条": 0}
        suit_tiles = {"万": [], "筒": [], "条": []}
        
        for tile in player.hand_tiles:
            if tile.is_number_tile():
                suit_name = tile.tile_type.value
                suit_counts[suit_name] += 1
                suit_tiles[suit_name].append(tile)
        
        # 分析各花色的缺门价值
        suit_analysis = {}
        for suit_name in ["万", "筒", "条"]:
            analysis = self._analyze_missing_suit_value(suit_tiles[suit_name])
            suit_analysis[suit_name] = {
                'count': suit_counts[suit_name],
                'tiles': suit_tiles[suit_name],
                'analysis': analysis
            }
        
        # 显示分析结果
        for suit_name, data in suit_analysis.items():
            advice.append(f"\n📊 {suit_name}牌分析 ({data['count']}张):")
            if data['tiles']:
                advice.append(f"   牌张: {[str(t) for t in data['tiles']]}")
            advice.append(f"   缺门价值: {data['analysis']['description']}")
            advice.append(f"   缺门成本: {data['analysis']['cost_description']}")
        
        # 推荐最佳缺门
        best_missing = self._recommend_best_missing_suit(suit_analysis)
        advice.append(f"\n🎯 最佳缺门建议:")
        advice.append(f"   推荐缺: {best_missing['suit']}")
        advice.append(f"   理由: {best_missing['reason']}")
        
        return "\n".join(advice)
    
    def _analyze_missing_suit_value(self, tiles: List[Tile]) -> Dict:
        """分析缺门的价值"""
        if not tiles:
            return {
                "description": "完美选择",
                "cost_description": "无损失",
                "priority": 100
            }
        
        count = len(tiles)
        values = sorted([t.value for t in tiles])
        
        # 计算损失
        pairs = self._count_pairs_in_suit(values)
        sequences = self._count_potential_sequences_in_suit(values)
        
        cost = count * 5 + pairs * 20 + sequences * 15
        priority = 100 - cost
        
        # 生成描述
        if count == 0:
            description = "完美选择"
            cost_description = "无任何损失"
        elif count <= 2:
            description = "优秀选择"
            cost_description = f"仅损失{count}张牌"
        elif count <= 4:
            description = "可接受选择"
            cost_description = f"损失{count}张牌"
        else:
            description = "代价较高"
            cost_description = f"损失{count}张牌，包括{pairs}个对子和{sequences}个潜在顺子"
        
        return {
            "description": description,
            "cost_description": cost_description,
            "priority": priority,
            "cost": cost
        }
    
    def _recommend_best_missing_suit(self, suit_analysis: Dict) -> Dict:
        """推荐最佳缺门"""
        # 按优先级排序（优先级越高越好）
        sorted_suits = sorted(suit_analysis.items(),
                            key=lambda x: x[1]['analysis']['priority'],
                            reverse=True)
        
        best_suit_name, best_data = sorted_suits[0]
        
        reasons = []
        if best_data['count'] == 0:
            reasons.append("你没有这个花色的牌")
        elif best_data['count'] <= 2:
            reasons.append(f"只有{best_data['count']}张，损失最小")
        
        analysis = best_data['analysis']
        if 'cost' in analysis and analysis['cost'] < 20:
            reasons.append("缺门成本很低")
        
        reason = "、".join(reasons) if reasons else "综合分析最优选择"
        
        return {
            "suit": best_suit_name,
            "reason": reason
        }

    def provide_advice(self, player: Player, context: Dict) -> str:
        """为人类玩家提供建议"""
        advice = []
        
        # 分析手牌
        evaluation = self.evaluate_hand(player)
        
        if player.missing_suit is None:
            advice.append(self._advice_missing_suit(player))
        
        if context.get("can_win", False):
            advice.append("🎉 你可以胡牌了！点击胡牌按钮。")
        
        if context.get("last_discarded_tile"):
            advice.extend(self._advice_response_actions(player, context))
        
        if context.get("is_your_turn", False):
            advice.extend(self._advice_discard(player))
        
        # 一般性建议
        advice.extend(self._advice_general_strategy(player, evaluation))
        
        result = "\n".join(advice)
        self.advice_history.append(result)
        
        return result
    
    def _advice_missing_suit(self, player: Player) -> str:
        """缺门建议"""
        suit_counts = {"万": 0, "筒": 0, "条": 0}
        
        for tile in player.hand_tiles:
            if tile.is_number_tile():
                suit_counts[tile.tile_type.value] += 1
        
        min_suit = min(suit_counts, key=suit_counts.get)
        min_count = suit_counts[min_suit]
        
        return f"💡 建议缺{min_suit}，你只有{min_count}张{min_suit}牌。"
    
    def _advice_response_actions(self, player: Player, context: Dict) -> List[str]:
        """响应动作建议"""
        advice = []
        last_tile = context.get("last_discarded_tile")
        
        if not last_tile:
            return advice
        
        if player.can_peng(last_tile):
            advice.append("🔥 你可以碰这张牌！碰牌可以快速组成刻子。")
        
        if player.can_gang(last_tile):
            advice.append("💪 你可以杠这张牌！杠牌分数高但要小心别人胡牌。")
        
        chi_options = player.can_chi(last_tile)
        if chi_options:
            advice.append(f"🌟 你可以吃这张牌组成顺子！有{len(chi_options)}种组合方式。")
        
        return advice
    
    def _advice_discard(self, player: Player) -> List[str]:
        """打牌建议"""
        advice = []
        
        if not player.hand_tiles:
            return advice
        
        # 找到优先级最高的牌
        priorities = []
        for tile in player.hand_tiles:
            priority = self.calculate_discard_priority(player, tile)
            priorities.append((tile, priority))
        
        priorities.sort(key=lambda x: x[1], reverse=True)
        
        best_discard = priorities[0][0]
        advice.append(f"🎯 建议打出：{best_discard}")
        
        # 解释原因
        if player.missing_suit and best_discard.tile_type.value == player.missing_suit:
            advice.append(f"   因为这是你缺的{player.missing_suit}牌")
        elif best_discard.is_honor_tile():
            advice.append("   字牌相对不容易组成顺子")
        elif best_discard.is_number_tile() and best_discard.value in [1, 9]:
            advice.append("   边张牌（1,9）组成顺子的机会较少")
        
        return advice
    
    def _advice_general_strategy(self, player: Player, evaluation: Dict) -> List[str]:
        """一般策略建议"""
        advice = []
        
        if evaluation["orphans"] > 5:
            advice.append("⚠️ 你的孤张牌太多了，考虑打出一些来整理手牌。")
        
        if evaluation["pairs"] >= 3:
            advice.append("👍 你有多个对子，胡牌的机会不错！")
        
        if evaluation["triplets"] >= 2:
            advice.append("🔥 你已经有多个刻子，考虑碰碰胡！")
        
        if player.missing_suit and not player.check_missing_suit_complete():
            missing_tiles = [t for t in player.hand_tiles 
                           if t.tile_type.value == player.missing_suit]
            if missing_tiles:
                advice.append(f"📌 尽快打出剩余的{len(missing_tiles)}张{player.missing_suit}牌。")
        
        return advice
    
    def get_teaching_points(self) -> List[str]:
        """获取教学要点"""
        return [
            "🎓 麻将基础：",
            "• 四川麻将需要先选择缺一门（万、筒、条中的一种）",
            "• 胡牌需要4个面子（刻子或顺子）+ 1个对子",
            "• 刻子：三张相同的牌；顺子：同花色连续三张",
            "",
            "🎯 策略建议：",
            "• 优先打出缺门的牌和孤张牌",
            "• 注意观察其他玩家的打牌，避免让别人胡牌",
            "• 杠牌分数高但有风险，要谨慎使用",
            "• 碰牌相对安全，可以快速组成面子",
            "",
            "⚡ 特殊牌型：",
            "• 碰碰胡：全部刻子，分数翻倍",
            "• 清一色：同一花色，分数x4",
            "• 字一色：全部字牌，分数x4"
        ]
    
    def analyze_game_situation(self, all_players: List[Player], 
                             discarded_tiles: List[Tile]) -> str:
        """分析当前局势"""
        analysis = []
        
        # 分析其他玩家
        for i, player in enumerate(all_players):
            if player.player_type == Player.PlayerType.HUMAN:
                continue
            
            hand_count = player.get_hand_count()
            meld_count = len(player.melds)
            
            analysis.append(f"玩家{i+1}: {hand_count}张手牌, {meld_count}个面子")
            
            if hand_count <= 5 and meld_count >= 2:
                analysis.append("  ⚠️ 这个玩家可能要胡牌了！")
        
        # 分析牌河
        if discarded_tiles:
            recent_discards = discarded_tiles[-5:]
            analysis.append(f"最近打出: {', '.join(str(t) for t in recent_discards)}")
        
        return "\n".join(analysis) 