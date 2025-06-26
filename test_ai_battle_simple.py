#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版AI对战测试脚本 - 支持命令行参数

使用方法:
python test_ai_battle_simple.py --mode=same --ai=simple_medium --games=20
python test_ai_battle_simple.py --mode=mixed --ai1=simple_easy --ai2=simple_medium --ai3=shanten_hard --ai4=aggressive --games=20
"""

import sys
import os
import argparse
import time
import logging
from collections import defaultdict, Counter
from typing import Dict, List, Optional, Type, Tuple

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 禁用所有日志输出，避免干扰测试结果
logging.disable(logging.CRITICAL)
root_logger = logging.getLogger()
root_logger.disabled = True
root_logger.setLevel(logging.CRITICAL + 1)

from test_ai_battle import AIBattleSimulator, AVAILABLE_AIS, SAME_LEVEL_AIS

def main():
    parser = argparse.ArgumentParser(description='AI对战测试脚本')
    parser.add_argument('--mode', choices=['same', 'mixed'], required=True,
                        help='测试模式: same=同水平对局, mixed=混合水平对局')
    parser.add_argument('--games', type=int, default=20,
                        help='测试局数 (默认: 20)')
    
    # 同水平对局参数
    parser.add_argument('--ai', choices=list(SAME_LEVEL_AIS.keys()),
                        help='同水平对局AI类型')
    
    # 混合水平对局参数
    parser.add_argument('--ai1', choices=list(AVAILABLE_AIS.keys()),
                        help='混合对局玩家1 AI类型')
    parser.add_argument('--ai2', choices=list(AVAILABLE_AIS.keys()),
                        help='混合对局玩家2 AI类型')
    parser.add_argument('--ai3', choices=list(AVAILABLE_AIS.keys()),
                        help='混合对局玩家3 AI类型')
    parser.add_argument('--ai4', choices=list(AVAILABLE_AIS.keys()),
                        help='混合对局玩家4 AI类型')
    
    args = parser.parse_args()
    
    simulator = AIBattleSimulator()
    
    print("="*80)
    print("🀄 AI对战测试模拟器 (简化版)")
    print("="*80)
    
    if args.mode == 'same':
        if not args.ai:
            print("❌ 同水平对局模式需要指定 --ai 参数")
            print("可选AI类型:", list(SAME_LEVEL_AIS.keys()))
            return
        
        print(f"\n🤖 同水平对局测试")
        print(f"AI类型: {SAME_LEVEL_AIS[args.ai].name}")
        print(f"测试局数: {args.games}")
        print("-" * 60)
        
        simulator.run_same_level_test([args.ai], args.games)
        
    elif args.mode == 'mixed':
        if not all([args.ai1, args.ai2, args.ai3, args.ai4]):
            print("❌ 混合水平对局模式需要指定 --ai1, --ai2, --ai3, --ai4 参数")
            print("可选AI类型:", list(AVAILABLE_AIS.keys()))
            return
        
        ai_pattern = [args.ai1, args.ai2, args.ai3, args.ai4]
        
        print(f"\n⚔️ 混合水平对局测试")
        print("AI配置:")
        for i, ai_key in enumerate(ai_pattern):
            print(f"  玩家{i+1}: {AVAILABLE_AIS[ai_key].name}")
        print(f"测试局数: {args.games}")
        print("-" * 60)
        
        simulator.run_mixed_level_test(ai_pattern, args.games)

if __name__ == "__main__":
    main() 