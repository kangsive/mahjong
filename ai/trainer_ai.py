# -*- coding: utf-8 -*-
"""
训练师AI - 提供指导和建议
"""

from typing import List, Optional, Dict, Tuple
import random

from .base_ai import BaseAI
from game.tile import Tile
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