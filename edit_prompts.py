#!/usr/bin/env python3
"""
提示词编辑工具
允许用户通过命令行界面编辑提示词
"""

import os
import sys
import json
from utils.prompt_manager import PromptManager


def display_menu():
    """显示菜单"""
    print("\n=== 提示词编辑工具 ===")
    print("1. 查看所有提示词")
    print("2. 编辑摘要提示词")
    print("3. 编辑总体报告提示词")
    print("4. 编辑问答提示词")
    print("5. 重置指定提示词为默认值")
    print("6. 重置所有提示词为默认值")
    print("0. 退出")
    print("=" * 25)


def view_all_prompts(prompt_manager):
    """查看所有提示词"""
    prompts = prompt_manager.prompts
    for prompt_type, prompt_data in prompts.items():
        print(f"\n--- {prompt_type} ---")
        print("系统提示:")
        print(prompt_data.get("system", ""))
        print("\n用户提示:")
        print(prompt_data.get("user", ""))


def edit_prompt(prompt_manager, prompt_type):
    """编辑指定类型的提示词"""
    prompt_data = prompt_manager.get_prompt(prompt_type)
    
    print(f"\n当前 {prompt_type} 提示词:")
    print("系统提示:")
    print(prompt_data.get("system", ""))
    print("\n用户提示:")
    print(prompt_data.get("user", ""))
    
    print("\n请输入新的提示词 (直接回车保持不变):")
    
    # 编辑系统提示
    new_system = input("系统提示: ").strip()
    if not new_system:
        new_system = prompt_data.get("system", "")
        
    # 编辑用户提示
    print("用户提示 (输入多行，以空行结束):")
    lines = []
    while True:
        line = input()
        if line == "" and lines:
            break
        lines.append(line)
        
    new_user = "\n".join(lines) if lines else prompt_data.get("user", "")
    
    # 更新提示词
    prompt_manager.update_prompt(prompt_type, new_system, new_user)
    print(f"\n{prompt_type} 提示词已更新!")


def reset_prompt(prompt_manager):
    """重置指定提示词"""
    print("\n可重置的提示词类型:")
    print("1. summary (摘要)")
    print("2. overall_report (总体报告)")
    print("3. question_answer (问答)")
    
    choice = input("请选择要重置的提示词类型 (1-3): ").strip()
    prompt_types = {"1": "summary", "2": "overall_report", "3": "question_answer"}
    
    if choice in prompt_types:
        prompt_manager.reset_prompt(prompt_types[choice])
        print(f"\n{prompt_types[choice]} 提示词已重置为默认值!")
    else:
        print("无效选择!")


def main():
    """主函数"""
    prompt_manager = PromptManager()
    
    while True:
        display_menu()
        choice = input("请选择操作 (0-6): ").strip()
        
        if choice == "0":
            print("再见!")
            break
        elif choice == "1":
            view_all_prompts(prompt_manager)
        elif choice == "2":
            edit_prompt(prompt_manager, "summary")
        elif choice == "3":
            edit_prompt(prompt_manager, "overall_report")
        elif choice == "4":
            edit_prompt(prompt_manager, "question_answer")
        elif choice == "5":
            reset_prompt(prompt_manager)
        elif choice == "6":
            prompt_manager.reset_all_prompts()
            print("\n所有提示词已重置为默认值!")
        else:
            print("无效选择，请重新输入!")
        
        input("\n按回车键继续...")


if __name__ == "__main__":
    main()